"""Content-addressed invalidation for script-dependent production artifacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


DOWNSTREAM_STAGES = [
    "sentence_audio",
    "shot_timing",
    "visual_brief",
    "image_request",
    "asset_manifest",
    "render",
]
_CONTENT_FIELDS = ("display_text", "tts_text", "narration", "text")


def _revision_sha256(shots: Sequence[Mapping[str, Any]]) -> str:
    projection = []
    for index, shot in enumerate(shots):
        projection.append({
            "shot_id": str(shot.get("shot_id") or shot.get("scene_id") or f"SHOT_{index + 1:03d}"),
            "order": shot.get("order", index + 1),
            **{field: str(shot.get(field, "")) for field in _CONTENT_FIELDS},
        })
    payload = json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_script_revision_invalidation_report(
    previous_shots: Sequence[Mapping[str, Any]],
    revised_shots: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return a deterministic report describing which downstream work is stale."""
    previous_by_id = {
        str(shot.get("shot_id") or shot.get("scene_id") or f"SHOT_{index + 1:03d}"): shot
        for index, shot in enumerate(previous_shots)
    }
    revised_by_id = {
        str(shot.get("shot_id") or shot.get("scene_id") or f"SHOT_{index + 1:03d}"): shot
        for index, shot in enumerate(revised_shots)
    }
    changed_ids = []
    for shot_id in sorted(set(previous_by_id) | set(revised_by_id)):
        before = previous_by_id.get(shot_id, {})
        after = revised_by_id.get(shot_id, {})
        if any(str(before.get(field, "")) != str(after.get(field, "")) for field in _CONTENT_FIELDS):
            changed_ids.append(shot_id)
    return {
        "schema_version": 1,
        "changed_shot_ids": changed_ids,
        "changed_count": len(changed_ids),
        "downstream_stages": list(DOWNSTREAM_STAGES),
        "previous_revision_sha256": _revision_sha256(previous_shots),
        "revision_sha256": _revision_sha256(revised_shots),
        "invalidation_required": bool(changed_ids),
    }


def invalidate_downstream_artifacts(
    artifacts: Mapping[str, Sequence[Mapping[str, Any]]],
    changed_shot_ids: Sequence[str],
    *,
    reason: str = "script_revision",
) -> dict[str, list[dict[str, Any]]]:
    """Clone artifact rows and fail closed for rows tied to changed shots."""
    changed = {str(shot_id) for shot_id in changed_shot_ids}
    updated: dict[str, list[dict[str, Any]]] = {}
    for stage, rows in artifacts.items():
        stage_rows: list[dict[str, Any]] = []
        for source in rows:
            row = dict(source)
            shot_id = str(row.get("shot_id") or row.get("scene_id") or "")
            if shot_id in changed:
                previous_status = row.get("status")
                row["status"] = "BLOCKED"
                row["stale"] = True
                row["stale_reason"] = reason
                row["previous_status"] = previous_status
            stage_rows.append(row)
        updated[str(stage)] = stage_rows
    return updated
