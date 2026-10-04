from __future__ import annotations


class OpenRouterService:
    async def analyze_transcript(self, transcript: dict) -> dict:
        return {"reels": [], "transcript": transcript}

    async def find_reels(self, transcript: dict) -> dict:
        return {"reels": []}

    async def correct_transcript(self, transcript: dict) -> dict:
        return transcript

    async def generate_title(self, transcript: dict) -> str:
        return "Untitled"
