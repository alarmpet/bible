"""Production-history listing and streaming routes for the NOLLAM studio."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from lib.production_history_service import ProductionHistoryService
from routes.media_routes import _stream_file


def create_history_router(
    *,
    get_current_ep_dir: Callable[[], Path],
    runs_base_dir: Path,
    history_db_path: Path,
    collect_projects: Callable[[], list[dict[str, Any]]] | None = None,
    service: ProductionHistoryService | None = None,
) -> APIRouter:
    """Create history routes with explicit episode and archive dependencies."""
    router = APIRouter(prefix="/api/history", tags=["history"])

    history_service = service or ProductionHistoryService(
        history_db_path=history_db_path,
        runs_base_dir=runs_base_dir,
        get_current_ep_dir=get_current_ep_dir,
    )

    def get_projects() -> list[dict[str, Any]]:
        if collect_projects is not None:
            return collect_projects()
        return history_service.collect_projects()

    @router.get("/videos")
    async def get_history_videos() -> dict[str, Any]:
        videos = get_projects()
        total_size_mb = round(sum(float(item.get("file_size_mb", 0)) for item in videos), 2)
        return {
            "status": "SUCCESS",
            "total_count": len(videos),
            "total_size_mb": total_size_mb,
            "total_size_gb": round(total_size_mb / 1024, 2),
            "videos": videos,
        }

    @router.get("/stream/{video_id}")
    async def stream_history_video(video_id: str, request: Request) -> StreamingResponse:
        videos = get_projects()
        target = next((item for item in videos if item["video_id"] == video_id), None)
        if not target:
            raise HTTPException(status_code=404, detail=f"히스토리 비디오를 찾을 수 없습니다: {video_id}")
        path = Path(target["file_path"])
        if not path.is_file():
            raise HTTPException(status_code=404, detail=f"물리 비디오 파일이 존재하지 않습니다: {path}")
        return _stream_file(path, request, "video/mp4")

    return router
