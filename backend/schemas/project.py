from __future__ import annotations

from pydantic import BaseModel, Field


class ProjectCreateResponse(BaseModel):
    id: str
    filename: str
    status: str = "uploaded"
    message: str = "Project created"


class ProjectResponse(BaseModel):
    id: str
    filename: str
    original_name: str
    duration: float = 0.0
    status: str
    file_url: str | None = None
