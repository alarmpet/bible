"""Pipeline status, action, and log-stream routes for the NOLLAM studio."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


class PipelineActionRequest(BaseModel):
    action: str


def _find_master_video(active_ep: Path) -> Path | None:
    """Find the active episode's publishable-looking master without episode-name coupling."""
    for folder in (active_ep / "candidate", active_ep / "output", active_ep):
        if not folder.exists():
            continue
        candidates = sorted(folder.glob("*.mp4"), key=lambda item: item.stat().st_mtime, reverse=True)
        for candidate in candidates:
            name = candidate.name.lower()
            if candidate.is_file() and ".part" not in name and "raw" not in name and "clip" not in name:
                if "master" in name or "final" in name:
                    return candidate
    return None


def create_pipeline_router(
    *,
    get_current_ep_dir: Callable[[], Path],
    scripts_dir: Path,
    run_pipeline_command: Callable[..., Any],
    log_queue: asyncio.Queue,
) -> APIRouter:
    """Create pipeline routes with explicit filesystem and execution dependencies."""
    router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

    @router.get("/status")
    async def get_pipeline_status() -> dict[str, Any]:
        active_ep = get_current_ep_dir()
        manifest_path = active_ep / "generation" / "master_1200s_manifest.json"
        manifest = {"shots": []}
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                manifest = {"shots": []}
        shots = manifest.get("shots", [])

        img_count = sum(1 for shot in shots if Path(shot.get("image_path", "")).exists())
        wav_count = sum(1 for shot in shots if Path(shot.get("wav_path", "")).exists())

        motion_clips_dir = active_ep / "candidate" / "motion_clips"
        motion_clips_count = (
            len(list(motion_clips_dir.glob("SHOT_*_motion.mp4")))
            if motion_clips_dir.exists()
            else 0
        )

        target_video = _find_master_video(active_ep)
        master_exists = target_video is not None
        master_size_mb = (
            target_video.stat().st_size / (1024 * 1024)
            if master_exists
            else 0.0
        )

        return {
            "total_required_shots": len(shots),
            "images_ready": f"{img_count}/{len(shots)}",
            "audio_ready": f"{wav_count}/{len(shots)}",
            "motion_clips_ready": f"{motion_clips_count}/{len(shots)}",
            "master_video_ready": master_exists,
            "master_video_size_mb": round(master_size_mb, 2),
            "target_duration_sec": 1200.0,
            "target_duration_window": "840s ~ 1560s (20분 ±30%)",
            "min_duration_sec": 840.0,
            "max_duration_sec": 1560.0,
        }

    actions = {
        "normalize_intro": "normalize_intro_videos.py",
        "validate_qa": "validate_intro_videos.py",
        "assemble_master": "assemble_master_20min.py",
        "cinematic_hybrid_master": "build_cinematic_master_pipeline.py",
        "full_intro_pipeline": "ingest_and_assemble_intro.py",
    }

    @router.post("/run_action")
    async def trigger_pipeline_action(
        req: PipelineActionRequest,
        background_tasks: BackgroundTasks,
    ) -> dict[str, Any]:
        script_name = actions.get(req.action)
        if not script_name:
            raise HTTPException(status_code=400, detail=f"알 수 없는 액션입니다: {req.action}")
        command = [sys.executable, str(scripts_dir / script_name)]
        background_tasks.add_task(run_pipeline_command, command)
        return {
            "status": "LAUNCHED",
            "action": req.action,
            "command": " ".join(command),
        }

    @router.get("/stream_logs")
    async def stream_logs(request: Request) -> StreamingResponse:
        """Stream pipeline output as Server-Sent Events."""
        async def event_generator():
            while True:
                if await request.is_disconnected():
                    break
                try:
                    line = await asyncio.wait_for(log_queue.get(), timeout=1.0)
                    yield f"data: {json.dumps({'log': line})}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    return router
