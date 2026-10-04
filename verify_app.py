"""Smoke test with isolated database and storage."""
import os
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    os.environ['DATABASE_URL'] = 'sqlite:///' + (root / 'test.db').as_posix()
    for name in ('UPLOAD_DIR', 'EXPORT_DIR', 'PROJECT_DIR'):
        os.environ[name] = str(root / name.lower())

    from backend.main import app
    from backend.database.database import engine
    from fastapi.testclient import TestClient

    try:
        with TestClient(app) as client:
            assert client.get('/health').json()['status'] == 'ok'
            for url in ('/', '/css/style.css', '/js/app.js', '/js/config/fonts.js', '/assets/fonts/README.md', '/manifest.json'):
                assert client.get(url).status_code == 200, url
            assert client.get('/api/projects').json() == []
            payload = b'video transport smoke test'
            response = client.post('/api/projects', files={
                'file': ('sample.mp4', payload, 'video/mp4')
            })
            assert response.status_code == 200, response.text
            project_id = response.json()['id']
            assert len(client.get('/api/projects').json()) == 1
            video = client.get(f'/api/projects/{project_id}/video')
            assert video.status_code == 200
            assert video.headers['content-type'] == 'video/mp4'
            assert video.content == payload
            video_url = f'/api/projects/{project_id}/video'
            for header, expected in [('bytes=0-4', payload[:5]), ('bytes=6-', payload[6:]),
                                     ('bytes=-4', payload[-4:]), ('bytes=0-999', payload)]:
                ranged = client.get(video_url, headers={'Range': header})
                assert ranged.status_code == 206, ranged.text
                assert ranged.content == expected
                assert int(ranged.headers['content-length']) == len(expected)
            for header in ('bytes=999-', 'bytes=4-1', 'bytes=-0', 'bytes=-', 'bytes=abc'):
                assert client.get(video_url, headers={'Range': header}).status_code == 416
            assert client.get(video_url, headers={'Range': 'bytes=0-1', 'If-Range': 'old'}).status_code == 200
            assert client.get('/api/projects/missing/video').status_code == 404
        print('PASS: startup, assets, upload, listing, video delivery, byte ranges, missing project')
    finally:
        engine.dispose()
