from __future__ import annotations

import subprocess
from pathlib import Path


class AudioService:
    @staticmethod
    def extract_audio(input_video: str | Path, output_audio: str | Path) -> str:
        input_path = Path(input_video)
        output_path = Path(output_audio)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]

        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return str(output_path)

    @staticmethod
    def extract_audio_for_transcription(input_video: str | Path, work_dir: str | Path) -> str:
        input_path = Path(input_video)
        output_dir = Path(work_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        return AudioService.extract_audio(input_path, output_dir / f"{input_path.stem}.transcription.wav")
