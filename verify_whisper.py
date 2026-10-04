"""Real Whisper integration test: python verify_whisper.py path/to/speech.wav.

Creates a temporary MP4, uploads it to an isolated API, transcribes and exports SRT.
Requires a spoken WAV sample and downloads the configured model on first use.
"""
import os
import sys
import tempfile
from pathlib import Path


def make_video(audio_path: Path, destination: Path) -> None:
    import av
    import numpy as np

    with av.open(str(audio_path)) as audio:
        duration = audio.duration / av.time_base
        with av.open(str(destination), 'w') as output:
            video = output.add_stream('libx264', rate=5)
            video.width = 320
            video.height = 180
            video.pix_fmt = 'yuv420p'
            sound = output.add_stream('aac', rate=audio.streams.audio[0].rate)
            sound.layout = 'mono'
            for index in range(int(duration * 5) + 1):
                frame = av.VideoFrame.from_ndarray(np.zeros((180, 320, 3), dtype=np.uint8), format='rgb24')
                frame.pts = index
                for packet in video.encode(frame):
                    output.mux(packet)
            for packet in video.encode():
                output.mux(packet)
            for frame in audio.decode(audio=0):
                for packet in sound.encode(frame):
                    output.mux(packet)
            for packet in sound.encode():
                output.mux(packet)


def main() -> None:
    audio_path = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        os.environ['DATABASE_URL'] = 'sqlite:///' + (root / 'test.db').as_posix()
        for name in ('UPLOAD_DIR', 'EXPORT_DIR', 'PROJECT_DIR'):
            os.environ[name] = str(root / name.lower())
        from fastapi.testclient import TestClient
        from backend.main import app
        from backend.database.database import engine

        try:
            video_path = root / 'speech.mp4'
            make_video(audio_path, video_path)
            with TestClient(app) as client:
                with video_path.open('rb') as video:
                    response = client.post('/api/projects', files={'file': ('speech.mp4', video, 'video/mp4')})
                assert response.status_code == 200, response.text
                project_id = response.json()['id']
                url = f'/api/projects/{project_id}/transcription'
                response = client.post(url, json={'language': 'en'})
                assert response.status_code == 202, response.text
                result = client.get(url).json()
                assert result['status'] == 'completed', result
                assert result['segments'], result
                assert all(s['end'] >= s['start'] >= 0 for s in result['segments'])
                assert any(s['words'] for s in result['segments'])
                srt = client.get(f'/api/projects/{project_id}/subtitles.srt')
                assert srt.status_code == 200 and '-->' in srt.text
                print('PASS: real MP4 upload -> Whisper CPU -> timed subtitles -> SRT')
                print('Recognized:', result['text'])
        finally:
            engine.dispose()


if __name__ == '__main__':
    main()
