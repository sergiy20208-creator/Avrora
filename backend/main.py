from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.projects import router as projects_router
from backend.api.transcription import router as transcription_router
from backend.database.database import init_db
from backend.services.transcription_service import recover_interrupted_jobs

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="Avrora AI Video Editor", version="0.1.0")

app.include_router(projects_router)
app.include_router(transcription_router)

app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    os.makedirs(os.getenv("UPLOAD_DIR", "./storage/uploads"), exist_ok=True)
    os.makedirs(os.getenv("EXPORT_DIR", "./storage/exports"), exist_ok=True)
    os.makedirs(os.getenv("PROJECT_DIR", "./storage/projects"), exist_ok=True)
    recover_interrupted_jobs()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "avrora"}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/manifest.json")
async def manifest() -> FileResponse:
    return FileResponse(str(FRONTEND_DIR / "manifest.json"))


@app.get("/service-worker.js")
async def service_worker() -> FileResponse:
    return FileResponse(str(FRONTEND_DIR / "service-worker.js"))
