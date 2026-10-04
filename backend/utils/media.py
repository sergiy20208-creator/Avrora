"""Single byte-range delivery for seeking on the pinned Starlette version."""
import re
from pathlib import Path

from fastapi import Request
from fastapi.responses import FileResponse, Response, StreamingResponse


def video_response(path: Path, mime_type: str, request: Request) -> Response:
    stat = path.stat()
    full = FileResponse(path, media_type=mime_type, stat_result=stat,
                        headers={"Accept-Ranges": "bytes"})
    header = request.headers.get("range")
    if_range = request.headers.get("if-range")
    if not header or (if_range and if_range not in (full.headers['etag'], full.headers['last-modified'])):
        return full
    # Multiple ranges are optional; serve the full resource for those requests.
    if ',' in header or not header.startswith('bytes='):
        return full
    match = re.fullmatch(r'bytes=(\d*)-(\d*)', header)
    try:
        if not match or not any(match.groups()):
            raise ValueError('Invalid range')
        first, last = match.groups()
        size = stat.st_size
        if first:
            start = int(first)
            end = min(int(last), size - 1) if last else size - 1
        else:
            suffix = int(last)
            if suffix <= 0:
                raise ValueError('Invalid suffix')
            start, end = max(0, size - suffix), size - 1
        if start >= size or start > end:
            raise ValueError('Unsatisfiable range')
    except ValueError:
        return Response(status_code=416, headers={'Content-Range': f'bytes */{stat.st_size}'})

    def chunks():
        with path.open('rb') as source:
            source.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = source.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    headers = dict(full.headers)
    headers['content-range'] = f'bytes {start}-{end}/{size}'
    headers['content-length'] = str(end - start + 1)
    return StreamingResponse(chunks(), status_code=206, media_type=mime_type, headers=headers)
