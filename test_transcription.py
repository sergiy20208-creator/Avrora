"""API regression tests. No model download or changes to user projects."""
import os
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

temporary = tempfile.TemporaryDirectory()
root = Path(temporary.name)
os.environ['DATABASE_URL'] = 'sqlite:///' + (root / 'test.db').as_posix()
for name in ('UPLOAD_DIR', 'EXPORT_DIR', 'PROJECT_DIR'):
    os.environ[name] = str(root / name.lower())

from fastapi.testclient import TestClient
from backend.main import app
from backend.database.database import engine
from backend.services import transcription_service as jobs
from backend.services.subtitle_service import SubtitleService, srt_timestamp


class TranscriptionTests(unittest.TestCase):
    def setUp(self):
        self.context = TestClient(app)
        self.client = self.context.__enter__()
        response = self.client.post('/api/projects', files={
            'file': ('sample.mp4', b'test media', 'video/mp4')
        })
        self.project_id = response.json()['id']
        self.url = f'/api/projects/{self.project_id}/transcription'

    def tearDown(self):
        self.context.__exit__(None, None, None)

    def test_transcription_and_srt_persist(self):
        result = {'segments': [{'id': 1, 'start': 0.125, 'end': 1.9996,
                               'text': 'Привіт, світе!', 'words': []}],
                  'language': 'uk', 'duration': 2.5, 'text': 'Привіт, світе!', 'model': 'base'}
        self.assertEqual(self.client.get(self.url).json()['status'], 'idle')
        with patch.object(jobs.WhisperService, 'transcribe', return_value=result) as transcribe:
            response = self.client.post(self.url, json={'language': 'uk'})
            self.assertEqual(response.status_code, 202)
            self.assertEqual(response.json()['status'], 'queued')
            self.assertEqual(transcribe.call_args.kwargs['language'], 'uk')
        data = self.client.get(self.url).json()
        self.assertEqual(data['status'], 'completed')
        self.assertEqual(data['segments'], result['segments'])
        self.assertEqual(jobs.read_result(self.project_id), data)
        srt = self.client.get(f'/api/projects/{self.project_id}/subtitles.srt')
        self.assertEqual(srt.status_code, 200)
        self.assertIn('00:00:00,125 --> 00:00:02,000', srt.text)
        self.assertIn('Привіт, світе!', srt.text)
        project = next(p for p in self.client.get('/api/projects').json() if p['id'] == self.project_id)
        self.assertEqual(project['duration'], 2.5)
        self.assertEqual(project['status'], 'transcribed')

    def test_get_transcription_keeps_word_level_timestamps(self):
        raw = {
            'segments': [{
                'id': 1,
                'start': 1.2,
                'end': 4.8,
                'text': 'Сьогодні я покажу вам новий спосіб',
                'words': [
                    {'word': 'Сьогодні', 'text': 'Сьогодні', 'start': 1.2, 'end': 1.75},
                    {'word': 'я', 'text': 'я', 'start': 1.76, 'end': 1.9},
                    {'word': 'покажу', 'text': 'покажу', 'start': 1.91, 'end': 2.4},
                    {'word': 'вам', 'text': 'вам', 'start': 2.41, 'end': 2.85},
                    {'word': 'новий', 'text': 'новий', 'start': 2.86, 'end': 3.35},
                    {'word': 'спосіб', 'text': 'спосіб', 'start': 3.36, 'end': 4.2},
                ]
            }],
            'language': 'uk', 'duration': 4.8, 'text': 'Сьогодні я покажу вам новий спосіб', 'model': 'base'
        }
        with patch.object(jobs.WhisperService, 'transcribe', return_value=raw):
            self.client.post(self.url, json={'language': 'uk'})
        data = self.client.get(self.url).json()
        self.assertEqual(data['segments'][0]['words'][0]['start'], 1.2)
        self.assertEqual(data['segments'][0]['words'][-1]['end'], 4.2)
        self.assertEqual(data['segments'][0]['text'], 'Сьогодні я покажу вам новий спосіб')

    def test_failure_releases_worker_and_allows_retry(self):
        with patch.object(jobs.WhisperService, 'transcribe', side_effect=ValueError('No audio')):
            with self.assertLogs(jobs.logger, level='ERROR'):
                self.assertEqual(self.client.post(self.url, json={}).status_code, 202)
        error = self.client.get(self.url).json()
        self.assertEqual(error['status'], 'error')
        self.assertIn('No audio', error['error'])
        self.assertFalse(jobs.inference_lock.locked())
        with patch.object(jobs.WhisperService, 'transcribe', return_value={
            'segments': [], 'language': 'en', 'duration': 3, 'text': '', 'model': 'base'
        }) as transcribe:
            self.assertEqual(self.client.post(self.url, json={'language': 'auto'}).status_code, 202)
            self.assertIsNone(transcribe.call_args.kwargs['language'])
        self.assertEqual(self.client.get(self.url).json()['status'], 'completed')

    def test_validation_and_busy_worker(self):
        self.assertEqual(self.client.post(self.url, json={'language': 'invalid'}).status_code, 422)
        self.assertEqual(self.client.get('/api/projects/missing/transcription').status_code, 404)
        self.assertEqual(self.client.post('/api/projects/missing/transcription', json={}).status_code, 404)
        self.assertEqual(self.client.get(f'/api/projects/{self.project_id}/subtitles.srt').status_code, 409)
        jobs.inference_lock.acquire()
        try:
            self.assertEqual(self.client.post(self.url, json={}).status_code, 409)
        finally:
            jobs.inference_lock.release()
        self.assertEqual(self.client.get(self.url).json()['status'], 'idle')

    def test_restart_recovers_interrupted_job(self):
        jobs.update_project(self.project_id, 'transcribing')
        jobs.save_result(self.project_id, {'status': 'processing', 'progress': 42, 'segments': []})
        jobs.recover_interrupted_jobs()
        self.assertEqual(self.client.get(self.url).json()['status'], 'error')

    def test_running_whisper_does_not_block_event_loop_or_progress_reads(self):
        entered = threading.Event()
        release = threading.Event()

        def slow_whisper(*args, **kwargs):
            kwargs['on_stage']('transcribing')
            kwargs['on_progress'](42)
            kwargs['on_progress'](40)  # Progress must not go backwards.
            entered.set()
            if not release.wait(10):
                raise TimeoutError('Test worker was not released')
            return {'segments': [], 'language': 'en', 'duration': 100, 'text': '', 'model': 'base'}

        with patch.object(jobs.WhisperService, 'transcribe', side_effect=slow_whisper):
            with self.assertLogs(jobs.logger, level='INFO') as logs, ThreadPoolExecutor(max_workers=2) as pool:
                post = pool.submit(self.client.post, self.url, json={})
                try:
                    self.assertTrue(entered.wait(5))
                    # /health is async. A blocking inference on its event loop makes this time out.
                    health = pool.submit(self.client.get, '/health').result(timeout=3)
                    self.assertEqual(health.status_code, 200)
                    response = pool.submit(self.client.get, self.url).result(timeout=3)
                    state = response.json()
                    self.assertEqual(state['status'], 'processing')
                    self.assertEqual(state['progress'], 42)
                    self.assertIn('elapsed_seconds', state)
                    self.assertEqual(response.headers['cache-control'], 'no-store')
                finally:
                    release.set()
                self.assertEqual(post.result(timeout=5).json()['status'], 'queued')
            messages = '\n'.join(logs.output)
            for marker in ('TRANSCRIPTION STARTED', 'TRANSCRIPTION PROGRESS', 'TRANSCRIPTION COMPLETED'):
                self.assertIn(marker, messages)
        self.assertEqual(self.client.get(self.url).json()['progress'], 100)

    def test_whisper_progress_uses_segment_timestamps_and_keeps_words(self):
        from types import SimpleNamespace
        from backend.services.whisper_service import WhisperService

        def segments():
            for end in (25, 50, 200):
                yield SimpleNamespace(start=end - 1, end=end, text=' speech ',
                                      words=[SimpleNamespace(start=end - 1, end=end, word=' speech ')])

        model = unittest.mock.Mock()
        model.model.device = 'cpu'
        model.transcribe.return_value = (segments(), SimpleNamespace(duration=200, language='en'))
        updates = []
        with patch('backend.services.whisper_service.load_model', return_value=model):
            result = WhisperService().transcribe('sample.mp4', on_progress=updates.append)
        self.assertEqual(updates, [12, 25, 99])
        self.assertEqual(result['segments'][0]['words'][0], {'start': 24, 'end': 25, 'text': 'speech'})
        self.assertTrue(model.transcribe.call_args.kwargs['word_timestamps'])

    def test_lazy_generator_failure_is_reported(self):
        from types import SimpleNamespace

        def broken_segments():
            yield SimpleNamespace(start=0, end=25, text='hello', words=[])
            raise RuntimeError('Decoder failed after first segment')

        model = unittest.mock.Mock()
        model.model.device = 'cpu'
        model.transcribe.return_value = (broken_segments(), SimpleNamespace(duration=200, language='en'))
        with patch('backend.services.whisper_service.load_model', return_value=model):
            with self.assertLogs(jobs.logger, level='ERROR') as logs:
                self.client.post(self.url, json={})
        state = self.client.get(self.url).json()
        self.assertEqual(state['status'], 'error')
        self.assertEqual(state['progress'], 12)
        self.assertIn('Decoder failed after first segment', state['error'])
        self.assertIn('TRANSCRIPTION ERROR', '\n'.join(logs.output))
        self.assertFalse(jobs.inference_lock.locked())

    def test_missing_video(self):
        from backend.database.database import ProjectRecord, SessionLocal
        with SessionLocal() as db:
            db.get(ProjectRecord, self.project_id).file_path = str(root / 'missing.mp4')
            db.commit()
        self.assertEqual(self.client.post(self.url, json={}).status_code, 404)
        self.assertFalse(jobs.inference_lock.locked())

    def test_subtitles_default_to_two_second_windows(self):
        transcript = {
            'duration': 4.5,
            'segments': [
                {'id': 1, 'start': 0.5, 'end': 1.5, 'text': 'first', 'words': []},
                {'id': 2, 'start': 1.7, 'end': 2.8, 'text': 'second', 'words': []},
                {'id': 3, 'start': 3.8, 'end': 4.4, 'text': 'third', 'words': []},
            ]
        }
        windows = SubtitleService.build_subtitles(transcript)
        self.assertEqual([w['start'] for w in windows], [0.0, 2.0, 4.0])
        self.assertEqual([w['end'] for w in windows], [2.0, 4.0, 4.5])

    def test_srt_hour_and_rounding(self):
        self.assertEqual(srt_timestamp(3599.9996), '01:00:00,000')
        self.assertEqual(srt_timestamp(-1), '00:00:00,000')


if __name__ == '__main__':
    try:
        result = unittest.main(exit=False).result
    finally:
        engine.dispose()
        temporary.cleanup()
    sys.exit(0 if result.wasSuccessful() else 1)
