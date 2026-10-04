from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/reels", tags=["reels"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "reels"}
