from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "export"}
