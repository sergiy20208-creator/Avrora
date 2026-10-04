from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/silence", tags=["silence"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "silence"}
