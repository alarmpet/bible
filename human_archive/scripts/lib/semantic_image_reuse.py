from __future__ import annotations

from collections import Counter
from typing import Any


def _sentence_ids(shot: dict[str, Any]) -> tuple[str, ...]:
    result: list[str] = []
    for span in shot.get("sentence_spans", []):
        sentence_id = str(span.get("sentence_id", ""))
        if sentence_id and sentence_id not in result:
            result.append(sentence_id)
    return tuple(result)


def _asset_is_available(asset: dict[str, Any] | None) -> bool:
    if not asset:
        return False
    return (
        str(asset.get("status", "")) == "COMPLETED"
        and bool(asset.get("file_path"))
        and bool(asset.get("sha256"))
    )


def _request_index(manifest: dict[str, Any], label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in manifest.get("requests", []):
        request_id = str(row.get("scene_id") or row.get("shot_id") or "")
        if not request_id:
            raise ValueError(f"{label} request is missing scene_id/shot_id")
        if request_id in indexed:
            raise ValueError(f"duplicate {label} request: {request_id}")
        indexed[request_id] = row
    return indexed


def _demote_incompatible_request_pairs(
    decisions: list[dict[str, Any]],
    source_request_manifest: dict[str, Any],
    target_request_manifest: dict[str, Any],
) -> None:
    source_requests = _request_index(source_request_manifest, "source")
    target_requests = _request_index(target_request_manifest, "target")
    for row in decisions:
        if row.get("decision") not in {"auto_reuse", "review_candidate"}:
            continue
        source = source_requests.get(str(row.get("source_shot_id", "")))
        target = target_requests.get(str(row.get("target_shot_id", "")))
        reason = ""
        if source is None or target is None:
            reason = "source_target_request_missing"
        else:
            for field in ("visual_mode", "visual_role"):
                source_value = str(source.get(field, ""))
                target_value = str(target.get(field, ""))
                if not source_value or not target_value:
                    reason = f"source_target_{field}_missing"
                    break
                if source_value != target_value:
                    reason = f"source_target_{field}_mismatch"
                    break
        if not reason:
            continue
        row["decision"] = "generate_new"
        row["reason"] = reason
        for key in list(row):
            if key.startswith("source_"):
                row.pop(key)


def _source_fields(
    source_shot: dict[str, Any],
    source_brief: dict[str, Any],
    source_asset: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_shot_id": source_shot["shot_id"],
        "source_order": source_shot["order"],
        "source_sentence_ids": list(_sentence_ids(source_shot)),
        "source_visual_mode": source_brief.get("visual_mode"),
        "source_semantic_anchors": source_brief.get("semantic_anchors", []),
        "source_narration_digest": source_brief.get("narration_digest", ""),
        "source_asset_file_path": source_asset.get("file_path"),
        "source_asset_sha256": source_asset.get("sha256"),
    }


def plan_semantic_image_reuse(
    source_timing: dict[str, Any],
    target_timing: dict[str, Any],
    source_briefs: dict[str, Any],
    source_assets: dict[str, Any],
    *,
    base_sentence_ids: set[str],
    target_host_shot_ids: set[str] | None = None,
    source_request_manifest: dict[str, Any] | None = None,
    target_request_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_shots = source_timing.get("shots", [])
    target_shots = target_timing.get("shots", [])
    brief_by_id = {
        str(row.get("shot_id", "")): row
        for row in source_briefs.get("briefs", [])
    }
    asset_by_id = {
        str(row.get("shot_id", "")): row
        for row in source_assets.get("assets", [])
    }
    source_by_group: dict[tuple[str, ...], dict[str, Any]] = {}
    target_host_shot_ids = set(target_host_shot_ids or set())
    for source_shot in source_shots:
        group = _sentence_ids(source_shot)
        if group in source_by_group:
            raise ValueError(f"duplicate source sentence group: {group}")
        source_by_group[group] = source_shot

    decisions: list[dict[str, Any]] = []
    for target_shot in target_shots:
        target_ids = _sentence_ids(target_shot)
        row: dict[str, Any] = {
            "target_shot_id": target_shot["shot_id"],
            "target_order": target_shot["order"],
            "target_sentence_ids": list(target_ids),
            "target_host_required": target_shot["shot_id"] in target_host_shot_ids,
        }
        exact = source_by_group.get(target_ids)
        if exact:
            source_id = str(exact["shot_id"])
            source_brief = brief_by_id.get(source_id, {})
            asset = asset_by_id.get(source_id)
            source_is_host = (
                str(source_brief.get("visual_mode", "")) == "host_chapter_hinge"
            )
            target_is_host = target_shot["shot_id"] in target_host_shot_ids
            if source_is_host != target_is_host:
                row.update(
                    {
                        "decision": "generate_new",
                        "match_basis": "exact_sentence_group",
                        "score": 1.0,
                        "reason": "visual_mode_host_mismatch",
                    }
                )
            elif _asset_is_available(asset):
                row.update(
                    {
                        "decision": "auto_reuse",
                        "match_basis": "exact_sentence_group",
                        "score": 1.0,
                        "reason": "same ordered narration sentence group",
                    }
                )
                row.update(
                    _source_fields(
                        exact,
                        source_brief,
                        asset or {},
                    )
                )
            else:
                row.update(
                    {
                        "decision": "generate_new",
                        "match_basis": "exact_sentence_group",
                        "score": 1.0,
                        "reason": "exact_match_asset_unavailable",
                    }
                )
            decisions.append(row)
            continue

        includes_new_sentence = not set(target_ids) <= set(base_sentence_ids)
        candidates = []
        for source_shot in source_shots:
            source_id = str(source_shot["shot_id"])
            asset = asset_by_id.get(source_id)
            if not _asset_is_available(asset):
                continue
            source_is_host = (
                str(brief_by_id.get(source_id, {}).get("visual_mode", ""))
                == "host_chapter_hinge"
            )
            target_is_host = target_shot["shot_id"] in target_host_shot_ids
            if source_is_host != target_is_host:
                continue
            source_ids = set(_sentence_ids(source_shot))
            overlap = len(set(target_ids) & source_ids)
            if not overlap:
                continue
            union = len(set(target_ids) | source_ids)
            score = overlap / union
            candidates.append(
                (
                    overlap,
                    score,
                    -abs(int(target_shot["order"]) - int(source_shot["order"])),
                    source_shot,
                    asset,
                )
            )

        if includes_new_sentence or not candidates:
            row.update(
                {
                    "decision": "generate_new",
                    "match_basis": "none",
                    "score": 0.0,
                    "reason": (
                        "target_contains_new_narration"
                        if includes_new_sentence
                        else "no_completed_overlap_candidate"
                    ),
                }
            )
        else:
            _, score, _, source_shot, asset = max(
                candidates,
                key=lambda candidate: candidate[:3],
            )
            source_id = str(source_shot["shot_id"])
            row.update(
                {
                    "decision": "review_candidate",
                    "match_basis": "partial_base_sentence_overlap",
                    "score": round(score, 6),
                    "reason": "base-only regrouping requires semantic review",
                }
            )
            row.update(
                _source_fields(
                    source_shot,
                    brief_by_id.get(source_id, {}),
                    asset,
                )
            )
        decisions.append(row)

    if (source_request_manifest is None) != (target_request_manifest is None):
        raise ValueError(
            "source and target request manifests must be provided together"
        )
    if source_request_manifest is not None and target_request_manifest is not None:
        _demote_incompatible_request_pairs(
            decisions,
            source_request_manifest,
            target_request_manifest,
        )

    summary = Counter(row["decision"] for row in decisions)
    return {
        "schema_version": 1,
        "summary": {
            "auto_reuse": summary["auto_reuse"],
            "review_candidate": summary["review_candidate"],
            "generate_new": summary["generate_new"],
        },
        "decisions": decisions,
    }
