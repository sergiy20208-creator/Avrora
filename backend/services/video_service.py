from __future__ import annotations

from pathlib import Path


class VideoService:
    @staticmethod
    def ensure_storage_dirs() -> None:
        for folder in ["./storage/uploads", "./storage/exports", "./storage/projects"]:
            Path(folder).mkdir(parents=True, exist_ok=True)
