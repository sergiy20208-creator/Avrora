from __future__ import annotations


class ExportService:
    @staticmethod
    async def export_video(project_id: str, output_path: str, aspect_ratio: str = "9:16") -> str:
        return output_path
