"""Google Flow API routes extracted from the studio server monolith."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


class FlowGenerateRequest(BaseModel):
    scene_id: str
    prompt: Optional[str] = None


class FlowBatchRequest(BaseModel):
    scene_ids: Optional[List[str]] = None
    overwrite: bool = False


def create_flow_router(
    *,
    get_current_ep_dir: Callable[[], Path],
    check_cdp_status: Callable[..., Any],
    generate_single_scene_cdp: Callable[..., Any],
    batch_manager: Any,
) -> APIRouter:
    """Create Flow routes with explicit service dependencies."""
    router = APIRouter(prefix="/api/flow", tags=["flow"])

    @router.get("/status")
    async def get_flow_status() -> dict[str, Any]:
        return await check_cdp_status()

    @router.post("/generate_single")
    async def api_flow_generate_single(req: FlowGenerateRequest) -> dict[str, Any]:
        prompt = req.prompt
        if not prompt:
            from generate_video_prompts import compile_dynamic_docu_prompts

            all_prompts = compile_dynamic_docu_prompts(ep_dir=get_current_ep_dir())
            target = next(
                (
                    item
                    for item in all_prompts
                    if item.get("scene_id") == req.scene_id or item.get("shot_id") == req.scene_id
                ),
                None,
            )
            if target:
                prompt = target.get("compiled_prompt") or target.get("video_prompt")
        if not prompt:
            raise HTTPException(status_code=400, detail=f"{req.scene_id} 프롬프트를 찾을 수 없습니다.")
        return await generate_single_scene_cdp(req.scene_id, prompt)

    @router.post("/generate_batch")
    async def api_flow_generate_batch(req: FlowBatchRequest) -> dict[str, Any]:
        from generate_video_prompts import compile_dynamic_docu_prompts

        active_ep = get_current_ep_dir()
        all_prompts = compile_dynamic_docu_prompts(ep_dir=active_ep)
        if req.scene_ids:
            target_items = [
                item
                for item in all_prompts
                if item.get("scene_id") in req.scene_ids or item.get("shot_id") in req.scene_ids
            ]
        else:
            approved_dir = active_ep / "generation" / "downloads" / "approved"
            approved_dir.mkdir(parents=True, exist_ok=True)
            target_items = []
            for item in all_prompts:
                scene_id = item.get("scene_id") or item.get("shot_id")
                if req.overwrite or not (approved_dir / f"{scene_id}.jpg").exists():
                    target_items.append(item)

        if not target_items:
            return {"status": "IDLE", "message": "생성할 대상 씬이 없습니다. 모든 이미지가 이미 생성 완료되었습니다."}
        return batch_manager.start_batch(target_items, overwrite=req.overwrite)

    @router.get("/batch_status")
    async def api_flow_batch_status() -> dict[str, Any]:
        return batch_manager.get_status()

    @router.post("/batch_stop")
    async def api_flow_batch_stop() -> dict[str, Any]:
        return batch_manager.stop()

    return router
