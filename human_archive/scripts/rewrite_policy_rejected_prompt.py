# -*- coding: utf-8 -*-
"""Rewrite explicitly policy-rejected image requests through the semantic retry ladder."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.prompt_compiler import compile_policy_safe_retry


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_atomic(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("_.-") or "reason"


def _request_for_scene(requests: list[dict[str, Any]], requested_id: str) -> dict[str, Any] | None:
    for request in requests:
        if str(request.get("scene_id", "")) == requested_id:
            return request
    for request in requests:
        if str(request.get("shot_id", "")) == requested_id:
            return request
    return None


def _retry_source(
    build_dir: Path,
    request: dict[str, Any],
    *,
    contract: dict[str, Any] | None,
    briefs_by_shot: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    shot_id = str(request.get("shot_id") or request.get("scene_id") or "")
    if briefs_by_shot:
        brief = briefs_by_shot.get(shot_id)
        if brief is None:
            raise ValueError(f"missing visual brief for shot ID: {shot_id}")
        source = deepcopy(brief)
    else:
        if contract is None:
            raise ValueError(f"no visual brief or legacy visual contract for {shot_id}")
        scenes = {str(scene["scene_id"]): scene for scene in contract.get("scenes", [])}
        scene = scenes.get(str(request.get("scene_id") or shot_id))
        if scene is None:
            raise ValueError(f"missing legacy scene for {request.get('scene_id') or shot_id}")
        source = deepcopy(scene)
    source["scene_id"] = str(request.get("scene_id") or shot_id)
    source["shot_id"] = shot_id
    for key in ("visual_mode", "semantic_anchors", "claim_ids", "place", "era", "action"):
        if key not in source and key in request:
            source[key] = request[key]
    return source


def _current_asset_path(build_dir: Path, shot_id: str) -> Path | None:
    manifest_path = build_dir / "asset_manifest.json"
    if manifest_path.exists():
        manifest = _read_json(manifest_path)
        for asset in manifest.get("assets", []):
            if str(asset.get("shot_id")) != shot_id or asset.get("status") != "COMPLETED":
                continue
            relative = Path(str(asset.get("file_path", "")))
            for candidate in (build_dir / "images" / relative, build_dir / relative):
                if candidate.is_file():
                    return candidate
    fallback = build_dir / "images" / f"{shot_id}.jpg"
    return fallback if fallback.is_file() else None


def _archive_current_asset(build_dir: Path, shot_id: str, attempt: int, transform: str, reason: str) -> dict[str, Any] | None:
    source = _current_asset_path(build_dir, shot_id)
    if source is None:
        return None
    archive_dir = build_dir / "rejected_policy_variants" / shot_id
    archive_dir.mkdir(parents=True, exist_ok=True)
    source_sha = _sha256(source)
    existing = sorted(path for path in archive_dir.glob("attempt-*.*") if path.is_file())
    for path in existing:
        if _sha256(path) == source_sha:
            return {
                "file_path": path.relative_to(build_dir).as_posix(),
                "sha256": source_sha,
                "bytes": path.stat().st_size,
                "reused": True,
            }
    destination = archive_dir / (
        f"attempt-{int(attempt):03d}-{_safe_name(transform)}-{_safe_name(reason)}{source.suffix.lower()}"
    )
    shutil.copy2(source, destination)
    return {
        "file_path": destination.relative_to(build_dir).as_posix(),
        "sha256": source_sha,
        "bytes": destination.stat().st_size,
        "reused": False,
    }


def _archive_old_request(build_dir: Path, shot_id: str, attempt: int, old_request: dict[str, Any]) -> dict[str, Any]:
    archive_dir = build_dir / "rejected_policy_variants" / shot_id / "metadata"
    archive_dir.mkdir(parents=True, exist_ok=True)
    request_sha = str(old_request.get("request_sha256", ""))
    destination = archive_dir / f"request-{int(attempt):03d}-{_safe_name(request_sha or 'unknown')}.json"
    was_existing = destination.exists()
    if was_existing and json.loads(destination.read_text(encoding="utf-8")) != old_request:
        raise ValueError(f"immutable request archive collision: {destination}")
    if not was_existing:
        destination.write_text(json.dumps(old_request, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "file_path": destination.relative_to(build_dir).as_posix(),
        "sha256": request_sha,
        "file_sha256": _sha256(destination),
        "bytes": destination.stat().st_size,
        "reused": was_existing,
    }


def _flow_contract_rows(flow: Any) -> list[dict[str, Any]]:
    if isinstance(flow, list):
        rows = flow
    elif isinstance(flow, dict) and isinstance(flow.get("requests"), list):
        rows = flow["requests"]
    else:
        raise ValueError("Flow prompt contract has an unrecognized shape")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("Flow prompt contract contains an unrecognized request row")
    return rows


def _preflight_flow_prompt_contract(build_dir: Path, shot_ids: list[str]) -> Any:
    flow_path = build_dir / "flow_image_prompts.json"
    if not flow_path.exists():
        raise ValueError(f"Flow prompt contract is missing: {flow_path}")
    try:
        flow = _read_json(flow_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Flow prompt contract is unreadable: {flow_path}") from error
    rows = _flow_contract_rows(flow)
    for shot_id in dict.fromkeys(shot_ids):
        matches = [row for row in rows if str(row.get("shot_id", "")) == shot_id]
        if not matches:
            raise ValueError(f"Flow prompt contract is missing target row for shot ID: {shot_id}")
        if len(matches) > 1:
            raise ValueError(f"Flow prompt contract has duplicate target rows for shot ID: {shot_id}")
    return flow


def _update_flow_prompt_contract(
    build_dir: Path,
    flow: Any,
    shot_id: str,
    new_request: dict[str, Any],
) -> str:
    rows = _flow_contract_rows(flow)
    for index, row in enumerate(rows):
        if str(row.get("shot_id", "")) == shot_id:
            rows[index] = dict(new_request)
            break
    _write_json_atomic(build_dir / "flow_image_prompts.json", flow)
    return _sha256(build_dir / "flow_image_prompts.json")


def _next_attempt(audit_rows: list[dict[str, Any]], scene_id: str, shot_id: str) -> int:
    attempts = []
    matched_count = 0
    for row in audit_rows:
        if str(row.get("scene_id", "")) not in {scene_id, shot_id} and str(row.get("shot_id", "")) not in {scene_id, shot_id}:
            continue
        matched_count += 1
        try:
            raw_attempt = row.get("attempt", row.get("policy_retry_attempt"))
            attempts.append(int(raw_attempt) if raw_attempt is not None else 0)
        except (TypeError, ValueError):
            attempts.append(0)
    return max(max(attempts, default=0), matched_count) + 1


def _mark_review_required(build_dir: Path, request: dict[str, Any], attempt: int, reason: str) -> dict[str, Any]:
    request["lifecycle"] = "REVIEW_REQUIRED"
    request["lifecycle_reason"] = reason
    asset_path = build_dir / "asset_manifest.json"
    if asset_path.exists():
        manifest = _read_json(asset_path)
        shot_id = str(request.get("shot_id") or request.get("scene_id"))
        for asset in manifest.get("assets", []):
            if str(asset.get("shot_id")) == shot_id:
                asset["status"] = "REVIEW_REQUIRED"
                asset["lifecycle_reason"] = reason
        _write_json_atomic(asset_path, manifest)
    return {
        "scene_id": str(request.get("scene_id") or request.get("shot_id")),
        "shot_id": str(request.get("shot_id") or request.get("scene_id")),
        "attempt": attempt,
        "lifecycle": "REVIEW_REQUIRED",
        "reason": reason,
    }


def rewrite_policy_rejected(
    build_dir: Path,
    scene_ids: list[str],
    *,
    attempt: int | None = None,
    reason: str = "provider_policy_rejected",
) -> list[dict[str, Any]]:
    build_dir = Path(build_dir)
    request_path = build_dir / "image_request_manifest.json"
    audit_path = build_dir / "policy_retry_manifest.json"
    request_manifest = _read_json(request_path)
    requests = list(request_manifest.get("requests", []))
    briefs_path = build_dir / "visual_brief_manifest.json"
    briefs_by_shot = {}
    contract = None
    if briefs_path.exists():
        briefs_by_shot = {
            str(brief["shot_id"]): brief
            for brief in _read_json(briefs_path).get("briefs", [])
        }
    else:
        contract_path = build_dir / "episode_visual_contract_v2.json"
        if contract_path.exists():
            contract = _read_json(contract_path)

    selected: list[dict[str, Any]] = []
    for requested_id in scene_ids:
        request = _request_for_scene(requests, requested_id)
        if request is None:
            raise ValueError(f"unknown scene or shot ID: {requested_id}")
        selected.append(request)

    flow_contract = _preflight_flow_prompt_contract(
        build_dir,
        [str(request.get("shot_id") or request.get("scene_id")) for request in selected],
    )

    audit = _read_json(audit_path) if audit_path.exists() else {"schema_version": 1, "retries": []}
    audit_rows = [dict(row) for row in audit.get("retries", [])]
    updates: list[dict[str, Any]] = []
    for old_request in selected:
        scene_id = str(old_request.get("scene_id") or old_request.get("shot_id"))
        shot_id = str(old_request.get("shot_id") or scene_id)
        inferred_attempt = _next_attempt(audit_rows, scene_id, shot_id)
        current_attempt = int(attempt) if attempt is not None else inferred_attempt
        if current_attempt > 2:
            old_request["lifecycle"] = "REVIEW_REQUIRED"
            old_request["lifecycle_reason"] = reason
            request_manifest["contract_sha256"] = _update_flow_prompt_contract(
                build_dir,
                flow_contract,
                shot_id,
                old_request,
            )
            updates.append(_mark_review_required(build_dir, old_request, current_attempt, reason))
            continue
        if current_attempt < 1:
            raise ValueError("attempt must be at least one")
        source = _retry_source(build_dir, old_request, contract=contract, briefs_by_shot=briefs_by_shot)
        new_request = compile_policy_safe_retry(
            source,
            current_attempt,
            provider=str(old_request.get("provider", "flow")),
            reason=reason,
            previous_request_sha256=str(old_request.get("request_sha256", "")) or None,
        )
        transform = str(new_request["policy_retry_transform"])
        archived_asset = _archive_current_asset(build_dir, shot_id, current_attempt, transform, reason)
        archived_request = _archive_old_request(build_dir, shot_id, current_attempt, old_request)
        replacement = {**old_request, **new_request, "scene_id": scene_id, "shot_id": shot_id}
        flow_contract_sha = _update_flow_prompt_contract(build_dir, flow_contract, shot_id, replacement)
        requests[requests.index(old_request)] = replacement
        request_manifest["contract_sha256"] = flow_contract_sha
        item = {
            "scene_id": scene_id,
            "shot_id": shot_id,
            "reason": reason,
            "attempt": current_attempt,
            "transform": transform,
            "old_request_sha256": old_request.get("request_sha256"),
            "new_request_sha256": replacement["request_sha256"],
            "old_submission_prompt": old_request.get("submission_prompt"),
            "new_submission_prompt": replacement.get("submission_prompt"),
            "archived_request": archived_request,
            "rewritten_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        if archived_asset is not None:
            item["archived_asset"] = archived_asset
        audit_rows.append(item)
        updates.append(item)

    request_manifest["requests"] = sorted(requests, key=lambda item: int(item.get("order", 0)))
    audit["retries"] = audit_rows
    _write_json_atomic(request_path, request_manifest)
    _write_json_atomic(audit_path, audit)
    return updates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--scene-id", required=True, nargs="+")
    parser.add_argument("--attempt", type=int, choices=[1, 2])
    parser.add_argument(
        "--reason",
        choices=["provider_policy_rejected", "embedded_text_detected", "visual_mismatch"],
        default="provider_policy_rejected",
    )
    args = parser.parse_args()
    updates = rewrite_policy_rejected(args.build, args.scene_id, attempt=args.attempt, reason=args.reason)
    for item in updates:
        print(f"{item['scene_id']}: {item.get('old_request_sha256', '')} -> {item.get('new_request_sha256', '')} ({item.get('lifecycle', 'RETRY')})")


if __name__ == "__main__":
    main()
