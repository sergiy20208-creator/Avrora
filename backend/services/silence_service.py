from __future__ import annotations


class SilenceService:
    @staticmethod
    def analyze(audio_path: str) -> list[dict]:
        return []

    @staticmethod
    def remove_silence(silences: list[dict], preset: str = "natural") -> list[dict]:
        return silences
