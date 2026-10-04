from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from backend.database.database import ProjectRecord, get_db
from backend.schemas.project import ProjectCreateResponse, ProjectResponse
from backend.utils.media import video_response

router = APIRouter(prefix="/api", tags=["projects"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./storage/uploads")).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/projects")
async def list_projects(db: Session = Depends(get_db)) -> list[ProjectResponse]:
    projects = db.query(ProjectRecord).order_by(ProjectRecord.created_at.desc()).all()
    return [
        ProjectResponse(
            id=item.id,
            filename=item.filename,
            original_name=item.original_name,
            duration=item.duration,
            status=item.status,
            file_url=f"/api/projects/{item.id}/video",
        )
        for item in projects
    ]


@router.post("/projects", response_model=ProjectCreateResponse)
async def create_project(file: UploadFile = File(...), db: Session = Depends(get_db)) -> ProjectCreateResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    safe_name = file.filename.replace(" ", "_")
    project_id = str(uuid.uuid4())[:12]
    storage_path = UPLOAD_DIR / f"{project_id}_{safe_name}"

    with storage_path.open("wb") as dest:
        while chunk := await file.read(1024 * 1024):
            dest.write(chunk)

    project = ProjectRecord(
        id=project_id,
        filename=f"{project_id}_{safe_name}",
        original_name=file.filename,
        file_path=str(storage_path),
        mime_type=file.content_type or "application/octet-stream",
        duration=0.0,
        status="uploaded",
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return ProjectCreateResponse(
        id=project.id,
        filename=project.filename,
        status=project.status,
        message="Project created successfully",
    )


@router.get("/projects/{project_id}/video")
async def get_project_video(project_id: str, request: Request, db: Session = Depends(get_db)):
    project = db.query(ProjectRecord).filter(ProjectRecord.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    file_path = Path(project.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    return video_response(file_path, project.mime_type, request)
