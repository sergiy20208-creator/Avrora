"""UI integration test with a fake recognizer and real MP4 playback in Edge.

Usage: python verify_browser.py path/to/speech.wav
Requires requirements-dev.txt and Microsoft Edge. User data remains untouched.
"""
import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

from verify_whisper import make_video


def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        os.environ['DATABASE_URL'] = 'sqlite:///' + (root / 'test.db').as_posix()
        for name in ('UPLOAD_DIR', 'EXPORT_DIR', 'PROJECT_DIR'):
            os.environ[name] = str(root / name.lower())
        import uvicorn
        from playwright.sync_api import sync_playwright, expect
        from backend.main import app
        from backend.database.database import engine
        from backend.services.transcription_service import WhisperService

        video_path = root / 'speech.mp4'
        make_video(Path(sys.argv[1]), video_path)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
            server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
            thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
            thread.start()
            deadline = time.monotonic() + 15
            while not server.started:
                if not thread.is_alive() or time.monotonic() > deadline:
                    raise RuntimeError('Test server did not start')
                time.sleep(0.05)

            def recognize(*args, **kwargs):
                time.sleep(0.5)
                return {'status': 'completed', 'language': 'en', 'duration': 5.9,
                        'text': 'Hello world. Speech recognition works.', 'model': 'test',
                        'segments': [{'id': 1, 'start': 1.0, 'end': 3.0, 'text': 'Hello world.', 'words': []},
                                     {'id': 2, 'start': 3.0, 'end': 5.0, 'text': 'Speech recognition works.', 'words': []}]}

            try:
                with patch.object(WhisperService, 'transcribe', side_effect=recognize), sync_playwright() as p:
                    browser = p.chromium.launch(channel='msedge', headless=True)
                    try:
                        page = browser.new_page(viewport={'width': 1280, 'height': 1000})
                        errors = []
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        page.goto(f'http://127.0.0.1:{port}')
                        page.locator('#videoUploadInput').set_input_files(str(video_path))
                        expect(page.locator('.project-card')).to_have_count(1)
                        expect(page.locator('#transcribeBtn')).to_be_enabled()
                        page.locator('#transcriptionLanguage').select_option('en')
                        page.locator('#transcribeBtn').click()
                        expect(page.locator('#transcriptSegments button')).to_have_count(2, timeout=30000)
                        page.wait_for_function('document.getElementById("videoPlayer").readyState >= 1')
                        print('Media:', page.locator('#videoPlayer').evaluate('(v) => ({duration:v.duration, time:v.currentTime, seekable:v.seekable.length, error:v.error?.message})'), flush=True)
                        page.locator('#transcriptSegments button').first.click()
                        print('After seek:', page.locator('#videoPlayer').evaluate('(v) => ({time:v.currentTime, seeking:v.seeking, error:v.error?.message})'), flush=True)
                        expect(page.locator('#subtitleOverlay')).to_have_text('Hello world.')
                        page.wait_for_function('Math.abs(document.getElementById("videoPlayer").currentTime - 1) < 0.1')
                        with page.expect_download() as download:
                            page.locator('#downloadSrt').click()
                        assert Path(download.value.path()).read_text(encoding='utf-8').startswith('1\n00:00:01,000')
                        page.reload()
                        page.locator('.project-card').click()
                        expect(page.locator('#transcriptSegments button')).to_have_count(2)
                        page.set_viewport_size({'width': 390, 'height': 844})
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                        page.screenshot(path=str(Path('.venv') / 'whisper-ui.png'), full_page=True)
                        assert not errors, errors
                        print('PASS: upload, recognition UI, timed overlay, seeking, SRT download, reload, mobile layout')
                    finally:
                        browser.close()
            finally:
                server.should_exit = True
                thread.join(timeout=30)
                engine.dispose()


if __name__ == '__main__':
    main()
