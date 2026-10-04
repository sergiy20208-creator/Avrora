from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/subtitles", tags=["subtitles"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "subtitles"}
