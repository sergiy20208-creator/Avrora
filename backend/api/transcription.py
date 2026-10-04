from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response as APIResponse
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database.database import ProjectRecord, get_db
from backend.services import transcription_service as jobs
from backend.services.subtitle_service import build_srt, SubtitleService

router = APIRouter(prefix="/api/projects", tags=["transcription"])


class TranscriptionRequest(BaseModel):
    language: Literal["auto", "uk", "en", "pl", "de", "fr", "es", "ru"] = "auto"


def require_project(project_id: str, db: Session) -> ProjectRecord:
    project = db.get(ProjectRecord, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Проєкт не знайдено")
    return project


@router.get("/{project_id}/transcription")
def get_transcription(project_id: str, response: APIResponse, db: Session = Depends(get_db)) -> dict:
    response.headers["Cache-Control"] = "no-store"
    require_project(project_id, db)
    result = jobs.read_result(project_id)
    return result


@router.post("/{project_id}/transcription", status_code=202)
def transcribe(project_id: str, request: TranscriptionRequest,
               background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    project = require_project(project_id, db)
    if not Path(project.file_path).is_file():
        raise HTTPException(status_code=404, detail="Відеофайл не знайдено")
    if not jobs.inference_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Whisper уже обробляє відео. Дочекайтеся завершення.")
    try:
        project.status = "transcribing"
        db.commit()
        state = {"status": "queued", "progress": 0, "segments": []}
        jobs.save_result(project_id, state)
        background_tasks.add_task(jobs.run_transcription, project_id, project.file_path,
                                  None if request.language == "auto" else request.language)
        return state
    except Exception:
        jobs.inference_lock.release()
        db.rollback()
        project.status = "transcription_failed"
        db.commit()
        raise


@router.get("/{project_id}/subtitles.srt")
def download_subtitles(project_id: str, db: Session = Depends(get_db)) -> Response:
    require_project(project_id, db)
    result = jobs.read_result(project_id)
    if result["status"] != "completed":
        raise HTTPException(status_code=409, detail="Спочатку завершіть розпізнавання мовлення")
    segments = SubtitleService.build_word_level_segments(result)
    return Response(build_srt(segments), media_type="application/x-subrip",
                    headers={"Content-Disposition": f'attachment; filename="{project_id}.srt"'})


class TranscriptionUpdate(BaseModel):
    segments: list[dict]


@router.put("/{project_id}/transcription")
def update_transcription(project_id: str, update: TranscriptionUpdate, db: Session = Depends(get_db)) -> dict:
    require_project(project_id, db)
    # Load existing result (or default) and replace segments with the updated ones
    result = jobs.read_result(project_id)
    result["segments"] = update.segments
    # Mark as completed/transcribed after manual edit
    result["status"] = "completed"
    result["progress"] = 100
    jobs.save_result(project_id, result)
    jobs.update_project(project_id, "transcribed")
    return result
