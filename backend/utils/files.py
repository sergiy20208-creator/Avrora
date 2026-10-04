from __future__ import annotations

from pathlib import Path


def safe_filename(name: str) -> str:
    return name.replace(" ", "_")


def ensure_dirs(*paths: str) -> None:
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)
