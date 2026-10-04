from __future__ import annotations


def srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def build_srt(segments: list[dict]) -> str:
    return "".join(
        f"{index}\n{srt_timestamp(segment['start'])} --> {srt_timestamp(segment['end'])}\n"
        f"{' '.join(segment['text'].split())}\n\n"
        for index, segment in enumerate(segments, start=1)
    )


class SubtitleService:
    @staticmethod
    def normalize_word_item(word: dict) -> dict:
        text = (word.get("text") or word.get("word") or "").strip()
        start = float(word.get("start", 0.0) or 0.0)
        end = float(word.get("end", start) or start)
        if end <= start:
            end = start + 0.05
        return {"text": text, "start": round(start, 3), "end": round(end, 3), "word": text}

    @staticmethod
    def normalize_segment(segment: dict) -> dict:
        words = []
        for item in segment.get("words", []) or []:
            normalized = SubtitleService.normalize_word_item(item)
            if normalized["text"]:
                words.append(normalized)
        text = (segment.get("text") or " ".join(w["text"] for w in words)).strip()
        start = float(segment.get("start", 0.0) or 0.0)
        end = float(segment.get("end", start) or start)
        if end <= start and words:
            end = max(w["end"] for w in words)
        return {"id": segment.get("id", 0), "start": round(start, 3), "end": round(end, 3), "text": text, "words": words}

    @staticmethod
    def build_word_level_segments(transcript: dict) -> list[dict]:
        segments = transcript.get("segments", []) or []
        normalized = []
        for segment in segments:
            normalized_segment = SubtitleService.normalize_segment(segment)
            if normalized_segment["text"]:
                normalized.append(normalized_segment)
        return normalized

    @staticmethod
    def build_subtitles(transcript: dict, style: str = "minimal", split_seconds: int | None = 2) -> list[dict]:
        """Build UI subtitle blocks while keeping canonical Whisper word timestamps intact."""
        segments = SubtitleService.build_word_level_segments(transcript)
        if not split_seconds or not segments:
            return [{**segment, "style": style} for segment in segments]

        duration = transcript.get("duration")
        if duration is None:
            duration = 0.0
            for seg in segments:
                duration = max(duration, float(seg.get("end", 0)))

        windows: list[dict] = []
        t = 0.0
        while t < duration:
            window_start = t
            window_end = min(t + split_seconds, duration)
            parts: list[str] = []
            for seg in segments:
                seg_start = float(seg.get("start", 0))
                seg_end = float(seg.get("end", 0))
                if seg_end <= window_start or seg_start >= window_end:
                    continue
                text = (seg.get("text") or "").strip()
                if text:
                    parts.append(text)
            text = " ".join(p for p in parts if p).strip()
            if text:
                windows.append({"start": round(window_start, 3), "end": round(window_end, 3), "text": text, "style": style})
            t += split_seconds

        return windows
