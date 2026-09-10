"""Script, fact-check, manifest, and subtitle routes for the NOLLAM studio."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


class FactCheckApplyRequest(BaseModel):
    shot_id: str
    revised_text: str


class SubtitleStyleUpdate(BaseModel):
    font_name: str = "Pretendard"
    font_size: int = 52
    outline: float = 3.5
    shadow: float = 2.0
    margin_v: int = 55
    margin_l: int = 60
    margin_r: int = 60
    primary_color: str = "&H00FFFFFF"


def create_script_router(
    *,
    get_manifest_path: Callable[[], Path],
    fallback_manifest_path: Path,
    get_ass_path: Callable[[], Path],
    fact_checker_factory: Callable[[], Any],
) -> APIRouter:
    """Create script routes with explicit manifest, ASS, and fact-check dependencies."""
    router = APIRouter(tags=["script"])

    def resolve_manifest_path() -> Path:
        active_path = get_manifest_path()
        return active_path if active_path.exists() else fallback_manifest_path

    @router.get("/api/manifest/full")
    async def get_full_manifest() -> dict[str, Any]:
        manifest_path = resolve_manifest_path()
        if not manifest_path.exists():
            raise HTTPException(status_code=404, detail="매니페스트 파일을 찾을 수 없습니다.")
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=500, detail=f"매니페스트를 읽을 수 없습니다: {exc}") from exc

    @router.get("/api/factcheck/sentence_audit")
    async def get_sentence_factcheck_audit() -> dict[str, Any]:
        manifest_path = resolve_manifest_path()
        if not manifest_path.exists():
            raise HTTPException(status_code=404, detail="매니페스트를 찾을 수 없습니다.")

        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            checker = fact_checker_factory()
            audit_results = []
            for shot in data.get("shots", []):
                result = checker.audit_sentence(shot.get("display_text", ""))
                result["shot_id"] = shot.get("shot_id")
                result["order"] = shot.get("order")
                audit_results.append(result)
        except Exception as exc:
            return {"status": "ERROR", "error": str(exc), "statistics": {}, "audit_results": []}

        statistics = {
            "total_shots": len(audit_results),
            **{
                f"grade_{grade.lower()}_count": sum(
                    1 for item in audit_results if item.get("grade") == grade
                )
                for grade in "ABCD"
            },
        }
        return {"status": "SUCCESS", "statistics": statistics, "audit_results": audit_results}

    @router.post("/api/factcheck/apply_revision")
    async def apply_factcheck_revision(req: FactCheckApplyRequest) -> dict[str, Any]:
        manifest_path = resolve_manifest_path()
        if not manifest_path.exists():
            raise HTTPException(status_code=404, detail="매니페스트를 찾을 수 없습니다.")

        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=500, detail=f"매니페스트를 읽을 수 없습니다: {exc}") from exc

        target = next(
            (shot for shot in data.get("shots", []) if shot.get("shot_id") == req.shot_id),
            None,
        )
        if not target:
            raise HTTPException(status_code=404, detail=f"{req.shot_id} 샷을 찾을 수 없습니다.")

        target["display_text"] = req.revised_text
        target["tts_text"] = req.revised_text
        manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "status": "SUCCESS",
            "shot_id": req.shot_id,
            "updated_text": req.revised_text,
            "message": f"[{req.shot_id}] 대본이 팩트체크 보정문으로 즉시 업데이트되었습니다.",
        }

    @router.post("/api/subtitles/update")
    async def update_subtitle_styles(style: SubtitleStyleUpdate) -> dict[str, Any]:
        ass_path = get_ass_path()
        if not ass_path.exists():
            raise HTTPException(status_code=404, detail="ASS 파일을 찾을 수 없습니다.")

        content = ass_path.read_text(encoding="utf-8")
        new_style_line = (
            f"Style: DocuNarrator_v4,{style.font_name},{style.font_size},"
            f"{style.primary_color},&H000000FF,&H000C0C12,&H90000000,-1,0,0,0,100,100,0,0,1,"
            f"{style.outline:.1f},{style.shadow:.1f},2,{style.margin_l},{style.margin_r},{style.margin_v},1"
        )
        pattern = r"Style:\s*DocuNarrator_v4[^\r\n]*"
        if not re.search(pattern, content):
            raise HTTPException(status_code=500, detail="ASS 파일에서 스타일을 찾지 못했습니다.")

        ass_path.write_text(re.sub(pattern, new_style_line, content), encoding="utf-8")
        return {
            "status": "SUCCESS",
            "message": (
                f"자막 스타일이 성공적으로 변경되었습니다 ({style.font_size}pt "
                f"{style.font_name}, 외곽선={style.outline}px, 하단여백={style.margin_v}px)"
            ),
            "new_style_line": new_style_line,
        }

    return router
