from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Callable

logger = logging.getLogger("uvicorn.error.transcription.whisper")


def get_whisper_model_name() -> str:
    return os.getenv("WHISPER_MODEL_SIZE") or os.getenv("WHISPER_MODEL") or "base"


def get_whisper_device_and_compute() -> tuple[str, str]:
    try:
        import torch
        cuda_available = torch.cuda.is_available()
    except Exception:
        cuda_available = False

    device = os.getenv("WHISPER_DEVICE")
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE")

    if not device:
        device = "cuda" if cuda_available else "cpu"
    if not compute_type:
        compute_type = "float16" if device == "cuda" else "int8"

    if device == "cuda" and compute_type in {"int8", "int16"}:
        compute_type = "float16"

    logger.info("Whisper device: %s", device)
    logger.info("Whisper compute type: %s", compute_type)
    return device, compute_type


@lru_cache(maxsize=1)
def load_model():
    from faster_whisper import WhisperModel

    device, compute_type = get_whisper_device_and_compute()
    cache = Path(os.getenv("WHISPER_MODEL_DIR", "./storage/models"))
    cache.mkdir(parents=True, exist_ok=True)

    logger.info("Loading Whisper model=%s device=%s compute_type=%s cache_dir=%s",
                get_whisper_model_name(), device, compute_type, cache)
    return WhisperModel(
        get_whisper_model_name(),
        device=device,
        compute_type=compute_type,
        download_root=str(cache),
    )


class WhisperService:
    def transcribe(
        self, audio_path: str, language: str | None = None,
        on_progress: Callable[[int], None] | None = None,
        on_stage: Callable[[str], None] | None = None,
    ) -> dict:
        if on_stage:
            on_stage("loading_model")
        model = load_model()
        beam_size = int(os.getenv("WHISPER_BEAM_SIZE", "1" if model.model.device == "cpu" else "5"))
        if beam_size < 1:
            raise ValueError("WHISPER_BEAM_SIZE must be at least 1")
        logger.info("TRANSCRIPTION PROGRESS model=%s device=%s beam_size=%s phase=preparing_audio",
                    get_whisper_model_name(), model.model.device, beam_size)
        if on_stage:
            on_stage("preparing_audio")
        segments, info = model.transcribe(
            audio_path, language=language, beam_size=beam_size, best_of=beam_size, vad_filter=True,
            word_timestamps=True, condition_on_previous_text=False,
        )
        if on_stage:
            on_stage("transcribing")
        result = []
        for segment in segments:
            text = segment.text.strip()
            if text:
                result.append({
                    "id": len(result) + 1,
                    "start": round(segment.start, 3),
                    "end": round(segment.end, 3),
                    "text": text,
                    "words": [
                        {"start": round(word.start, 3), "end": round(word.end, 3),
                         "text": word.word.strip(), "word": word.word.strip()}
                        for word in (segment.words or [])
                    ],
                })
            if on_progress:
                on_progress(min(99, int(100 * segment.end / max(info.duration, 0.001))))
        return {
            "segments": result,
            "text": " ".join(segment["text"] for segment in result),
            "language": info.language,
            "duration": round(info.duration, 3),
            "model": get_whisper_model_name(),
            "beam_size": beam_size,
        }
