from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from backend.database.database import ProjectRecord, SessionLocal
from backend.services.audio_service import AudioService
from backend.services.whisper_service import WhisperService

logger = logging.getLogger("uvicorn.error.transcription")
# One local inference at a time avoids exhausting CPU/RAM. Run one uvicorn worker.
inference_lock = threading.Lock()
result_lock = threading.RLock()


def result_path(project_id: str) -> Path:
    # Only stored project IDs are used by API callers.
    return Path(os.getenv("PROJECT_DIR", "./storage/projects")) / project_id / "transcript.json"


def read_result(project_id: str) -> dict:
    with result_lock:
        path = result_path(project_id)
        if not path.exists():
            return {"status": "idle", "progress": 0, "segments": []}
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.exception("TRANSCRIPTION ERROR project=%s phase=reading_result", project_id)
            return {"status": "error", "progress": 0, "segments": [],
                    "error": "Не вдалося прочитати результат транскрипції. Запустіть її повторно."}
        if result.get("status") == "failed":
            result["status"] = "error"  # Compatibility with results saved before this fix.
        if result.get("status") == "processing" and result.get("started_at"):
            result["elapsed_seconds"] = round(max(0, (
                datetime.now(timezone.utc) - datetime.fromisoformat(result["started_at"])
            ).total_seconds()), 1)
        return result


def save_result(project_id: str, data: dict) -> None:
    with result_lock:
        path = result_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)


def update_project(project_id: str, status: str, duration: float | None = None) -> None:
    with SessionLocal() as db:
        project = db.get(ProjectRecord, project_id)
        if project:
            project.status = status
            if duration is not None:
                project.duration = duration
            db.commit()


def recover_interrupted_jobs() -> None:
    with SessionLocal() as db:
        for project in db.query(ProjectRecord).filter_by(status="transcribing").all():
            saved = read_result(project.id)
            if saved.get("status") == "completed":
                project.status = "transcribed"
                project.duration = saved["duration"]
            else:
                save_result(project.id, {
                    "status": "error", "progress": saved.get("progress", 0), "segments": [],
                    "error": "Сервер було перезапущено. Запустіть розпізнавання ще раз.",
                })
                project.status = "transcription_failed"
                logger.error("TRANSCRIPTION ERROR project=%s reason=server_restarted", project.id)
        db.commit()


def run_transcription(project_id: str, file_path: str, language: str | None) -> None:
    # Deliberately synchronous: Starlette BackgroundTask runs this entire function,
    # including iteration of Whisper's lazy generator, via anyio.to_thread.
    started = time.monotonic()
    state = {"status": "processing", "progress": 0, "segments": [],
             "started_at": datetime.now(timezone.utc).isoformat(), "phase": "loading_model"}
    try:
        save_result(project_id, state)
        logger.info("TRANSCRIPTION STARTED project=%s language=%s thread=%s", project_id,
                    language or "auto", threading.current_thread().name)
        last_progress = -1

        def stage(value: str) -> None:
            state["phase"] = value
            save_result(project_id, state)
            logger.info("TRANSCRIPTION PROGRESS project=%s progress=%s phase=%s elapsed=%.1fs",
                        project_id, state["progress"], value, time.monotonic() - started)

        def progress(value: int) -> None:
            nonlocal last_progress
            value = max(state["progress"], min(99, value))
            if value != last_progress:
                state["progress"] = value
                save_result(project_id, state)
                logger.info("TRANSCRIPTION PROGRESS project=%s progress=%s phase=transcribing elapsed=%.1fs",
                            project_id, value, time.monotonic() - started)
                last_progress = value

        audio_path = file_path
        try:
            if Path(file_path).suffix.lower() not in {'.wav', '.mp3', '.m4a', '.aac', '.flac'}:
                audio_path = AudioService.extract_audio_for_transcription(file_path, Path(file_path).parent)
                logger.info("TRANSCRIPTION AUDIO_EXTRACTED project=%s source=%s output=%s", project_id, file_path, audio_path)
        except Exception as exc:
            logger.warning("TRANSCRIPTION AUDIO_FALLBACK project=%s source=%s reason=%s", project_id, file_path, exc)
            audio_path = file_path

        result = WhisperService().transcribe(audio_path, language=language, on_progress=progress, on_stage=stage)
        elapsed = round(time.monotonic() - started, 3)
        save_result(project_id, {**result, "status": "completed", "progress": 100,
                                "started_at": state["started_at"], "elapsed_seconds": elapsed})
        update_project(project_id, "transcribed", result["duration"])
        logger.info("TRANSCRIPTION COMPLETED project=%s progress=100 elapsed=%.3fs segments=%s words=%s",
                    project_id, elapsed, len(result["segments"]),
                    sum(len(segment.get("words", [])) for segment in result["segments"]))
    except Exception as exc:
        logger.exception("TRANSCRIPTION ERROR project=%s phase=%s elapsed=%.1fs",
                         project_id, state.get("phase"), time.monotonic() - started)
        save_result(project_id, {
            **state, "status": "error", "elapsed_seconds": round(time.monotonic() - started, 3),
            "error": f"Не вдалося виконати транскрипцію Whisper ({type(exc).__name__}): {str(exc)[:500]}. "
                     "Перевірте аудіодоріжку та налаштування моделі. Подробиці — у журналі сервера.",
        })
        update_project(project_id, "transcription_failed")
    finally:
        inference_lock.release()
