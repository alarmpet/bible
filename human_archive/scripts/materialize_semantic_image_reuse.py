from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import uuid
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from lib.host_overlay import CANONICAL_HOST_ASSET, CANONICAL_HOST_COSTUME
from lib.provenance import compute_file_sha256


SHA256_RE = re.compile(r"^[0-9A-Fa-f]{64}$")
SHOT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
HOST_ROLE = "host_explainer"
HOST_MODE = "host_chapter_hinge"
VISUAL_ROLE_BY_MODE = {
    "host_chapter_hinge": "host_explainer",
    "historical_reconstruction": "historical_reconstruction",
    "evidence_artifact": "evidence_object",
    "place_establishing": "atmosphere",
    "analogy_explainer": "diagram_metaphor",
}
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
POSTPROCESS_FIELDS = (
    "type",
    "overlay_sha256",
    "output_sha256",
    "anchor",
    "width_ratio",
    "costume",
)
REQUIRED_FLOW_REQUEST_FIELDS = (
    "shot_id",
    "visual_mode",
    "semantic_anchors",
    "positive_prompt",
    "negative",
    "submission_prompt",
    "provider",
    "request_sha256",
)
FLOW_IMAGE_SHARED_FIELDS = (
    "visual_mode",
    "semantic_anchors",
    "positive_prompt",
    "negative",
    "submission_prompt",
)
ALLOWED_APPROVAL_SOURCES = {
    "explicit_user_confirmation_in_codex_thread",
}
SYNTHETIC_REVIEWER_MARKERS = (
    "auto",
    "automation",
    "bot",
    "agent",
    "system",
    "synthetic",
    "placeholder",
    "default",
)


class MaterializationError(RuntimeError):
    """A reuse contract is stale, incomplete, or unsafe to materialize."""


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise MaterializationError(f"{label} is missing: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise MaterializationError(f"{label} is not valid JSON: {path}: {error}") from error
    if not isinstance(value, dict):
        raise MaterializationError(f"{label} must be a JSON object: {path}")
    return value


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.part")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _same_path(first: Path | str, second: Path | str) -> bool:
    return str(Path(first).resolve()).casefold() == str(Path(second).resolve()).casefold()


def _require_sha(value: Any, label: str) -> str:
    digest = str(value or "")
    if not SHA256_RE.fullmatch(digest):
        raise MaterializationError(f"{label} must be a 64-character SHA-256")
    return digest.upper()


def _require_int(
    value: Any,
    label: str,
    *,
    minimum: int | None = None,
) -> int:
    if isinstance(value, bool):
        raise MaterializationError(f"{label} must be an integer")
    if isinstance(value, int):
        result = value
    elif isinstance(value, str) and re.fullmatch(r"-?(?:0|[1-9][0-9]*)", value):
        result = int(value)
    else:
        raise MaterializationError(f"{label} must be an integer")
    if minimum is not None and result < minimum:
        raise MaterializationError(f"{label} must be at least {minimum}")
    return result


def _require_shot_id(value: Any, label: str) -> str:
    shot_id = str(value or "")
    if not SHOT_ID_RE.fullmatch(shot_id):
        raise MaterializationError(f"{label} is not a safe shot ID: {shot_id!r}")
    return shot_id


def _safe_file(root: Path, relative_value: Any, label: str) -> tuple[Path, str]:
    relative_text = str(relative_value or "").replace("\\", "/")
    relative = Path(relative_text)
    if not relative_text or relative.is_absolute() or ".." in relative.parts:
        raise MaterializationError(f"{label} is not a safe relative path: {relative_text!r}")
    root = root.resolve()
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise MaterializationError(f"{label} escapes its image root: {relative_text!r}") from error
    return resolved, relative.as_posix()


def _index_unique(rows: Any, key: str, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        raise MaterializationError(f"{label} must be a list")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise MaterializationError(f"{label} contains a non-object row")
        row_id = _require_shot_id(row.get(key), f"{label}.{key}")
        if row_id in indexed:
            raise MaterializationError(f"{label} contains duplicate shot ID: {row_id}")
        indexed[row_id] = row
    return indexed


def _host_required(request: dict[str, Any], label: str) -> bool:
    visual_mode = str(request.get("visual_mode", ""))
    visual_role = str(request.get("visual_role", ""))
    expected_role = VISUAL_ROLE_BY_MODE.get(visual_mode, "atmosphere")
    if visual_role != expected_role:
        raise MaterializationError(
            f"{label} has inconsistent visual mode and visual role"
        )
    role_is_host = visual_role == HOST_ROLE
    mode_is_host = visual_mode == HOST_MODE
    overlay = request.get("host_overlay")
    if role_is_host != mode_is_host:
        raise MaterializationError(f"{label} has inconsistent host role and visual mode")
    if role_is_host and not isinstance(overlay, dict):
        raise MaterializationError(f"{label} host request is missing host_overlay")
    if not role_is_host and overlay:
        raise MaterializationError(f"{label} non-host request unexpectedly has host_overlay")
    if role_is_host:
        if overlay.get("asset") != CANONICAL_HOST_ASSET:
            raise MaterializationError(f"{label} host asset is not canonical")
        if overlay.get("costume") != CANONICAL_HOST_COSTUME:
            raise MaterializationError(f"{label} host costume is not canonical")
        try:
            width_ratio = float(overlay.get("width_ratio"))
        except (TypeError, ValueError) as error:
            raise MaterializationError(f"{label} host width_ratio is invalid") from error
        if abs(width_ratio - 0.38) > 1e-9:
            raise MaterializationError(f"{label} host width_ratio is not canonical")
    return role_is_host


def _recomputed_request_shas(flow_request: dict[str, Any]) -> set[str]:
    payload = copy.deepcopy(flow_request)
    payload.pop("request_sha256", None)
    default_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    compact_json = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return {
        hashlib.sha256(rendered.encode("utf-8")).hexdigest().upper()
        for rendered in (default_json, compact_json)
    }


def _load_request_contract(
    build: Path,
    label: str,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], str]:
    flow_path = build / "flow_image_prompts.json"
    request_path = build / "image_request_manifest.json"
    flow = _read_json(flow_path, f"{label} Flow prompt contract")
    request_manifest = _read_json(request_path, f"{label} image request manifest")
    contract_sha = compute_file_sha256(flow_path)
    recorded_contract = _require_sha(
        request_manifest.get("contract_sha256"),
        f"{label} request contract SHA",
    )
    if recorded_contract != contract_sha:
        raise MaterializationError(
            f"{label} Flow contract SHA mismatch: manifest={recorded_contract}, actual={contract_sha}"
        )

    requests = _index_unique(
        request_manifest.get("requests"),
        "scene_id",
        f"{label} requests",
    )
    for shot_id, request in requests.items():
        if request.get("shot_id") and str(request["shot_id"]) != shot_id:
            raise MaterializationError(f"{label} request scene_id/shot_id mismatch: {shot_id}")
        _require_sha(request.get("request_sha256"), f"{label} request SHA for {shot_id}")
        _require_int(
            request.get("order"),
            f"{label} request order for {shot_id}",
            minimum=1,
        )
        _host_required(request, f"{label} request {shot_id}")

    flow_rows = flow.get("requests")
    if not isinstance(flow_rows, list):
        raise MaterializationError(f"{label} Flow contract requests must be a list")
    flow_by_id: dict[str, dict[str, Any]] = {}
    for row in flow_rows:
        if not isinstance(row, dict):
            raise MaterializationError(f"{label} Flow contract contains a non-object request")
        shot_id = _require_shot_id(
            row.get("shot_id") or row.get("scene_id"),
            f"{label} Flow request ID",
        )
        if shot_id in flow_by_id:
            raise MaterializationError(f"{label} Flow contract contains duplicate shot ID: {shot_id}")
        missing_fields = [
            field for field in REQUIRED_FLOW_REQUEST_FIELDS if field not in row
        ]
        if missing_fields:
            raise MaterializationError(
                f"{label} Flow request is missing required fields for {shot_id}: "
                f"{missing_fields}"
            )
        declared_sha = _require_sha(
            row.get("request_sha256"),
            f"{label} Flow request SHA for {shot_id}",
        )
        if declared_sha not in _recomputed_request_shas(row):
            raise MaterializationError(
                f"{label} Flow request SHA does not match recomputed payload for {shot_id}"
            )
        flow_host = str(row.get("visual_mode", "")) == HOST_MODE
        flow_overlay = row.get("host_overlay")
        if flow_host != isinstance(flow_overlay, dict):
            raise MaterializationError(
                f"{label} Flow request has inconsistent host overlay for {shot_id}"
            )
        flow_by_id[shot_id] = row
    if set(flow_by_id) != set(requests):
        raise MaterializationError(f"{label} Flow and image request IDs do not match")
    for shot_id, request in requests.items():
        flow_row = flow_by_id[shot_id]
        flow_sha = _require_sha(
            flow_row.get("request_sha256"),
            f"{label} Flow request SHA for {shot_id}",
        )
        image_sha = _require_sha(
            request.get("request_sha256"),
            f"{label} image request SHA for {shot_id}",
        )
        if flow_sha != image_sha:
            raise MaterializationError(
                f"{label} Flow/image request SHA mismatch for {shot_id}"
            )
        for field in FLOW_IMAGE_SHARED_FIELDS:
            if field not in request or flow_row.get(field) != request.get(field):
                raise MaterializationError(
                    f"{label} Flow/image request {field} mismatch for {shot_id}"
                )
        if flow_row.get("host_overlay") != request.get("host_overlay"):
            raise MaterializationError(
                f"{label} Flow/image request host_overlay mismatch for {shot_id}"
            )
        if "order" in flow_row and _require_int(
            flow_row["order"],
            f"{label} Flow request order for {shot_id}",
            minimum=1,
        ) != _require_int(
            request["order"],
            f"{label} image request order for {shot_id}",
            minimum=1,
        ):
            raise MaterializationError(
                f"{label} Flow/image request order mismatch for {shot_id}"
            )
    return request_manifest, requests, contract_sha


def _validate_plan(
    plan: dict[str, Any],
    *,
    source_build: Path,
    target_build: Path,
    target_requests: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if _require_int(plan.get("schema_version"), "reuse plan schema_version") != 1:
        raise MaterializationError("reuse plan schema_version must be 1")
    if not _same_path(plan.get("source_build", ""), source_build):
        raise MaterializationError("reuse plan source_build does not match --source-build")
    if not _same_path(plan.get("target_build", ""), target_build):
        raise MaterializationError("reuse plan target_build does not match --target-build")
    decisions = list(plan.get("decisions") or [])
    if not decisions:
        raise MaterializationError("reuse plan decisions are missing")
    by_target: dict[str, dict[str, Any]] = {}
    allowed = {"auto_reuse", "review_candidate", "generate_new"}
    for row in decisions:
        if not isinstance(row, dict):
            raise MaterializationError("reuse plan contains a non-object decision")
        target_id = _require_shot_id(row.get("target_shot_id"), "reuse plan target_shot_id")
        if target_id in by_target:
            raise MaterializationError(f"reuse plan contains duplicate target shot: {target_id}")
        decision = str(row.get("decision", ""))
        if decision not in allowed:
            raise MaterializationError(f"reuse plan has invalid decision for {target_id}: {decision}")
        request = target_requests.get(target_id)
        if request is None:
            raise MaterializationError(f"reuse plan references unknown target request: {target_id}")
        if _require_int(
            row.get("target_order"),
            f"reuse plan target order for {target_id}",
            minimum=1,
        ) != _require_int(
            request.get("order"),
            f"target request order for {target_id}",
            minimum=1,
        ):
            raise MaterializationError(f"reuse plan target order is stale for {target_id}")
        planned_host = bool(row.get("target_host_required", False))
        current_host = _host_required(request, f"target request {target_id}")
        if planned_host != current_host:
            raise MaterializationError(f"reuse plan host requirement is stale for {target_id}")
        if decision in {"auto_reuse", "review_candidate"}:
            _require_shot_id(row.get("source_shot_id"), f"source shot for {target_id}")
            _require_sha(row.get("source_asset_sha256"), f"source asset SHA for {target_id}")
            if not row.get("source_asset_file_path"):
                raise MaterializationError(f"source asset file path is missing for {target_id}")
        by_target[target_id] = row
    if set(by_target) != set(target_requests):
        missing = sorted(set(target_requests) - set(by_target))
        extra = sorted(set(by_target) - set(target_requests))
        raise MaterializationError(
            f"reuse plan/request coverage mismatch: missing={missing}, extra={extra}"
        )
    actual_summary = Counter(str(row["decision"]) for row in decisions)
    recorded_summary = plan.get("summary") or {}
    for decision in allowed:
        if _require_int(
            recorded_summary.get(decision),
            f"reuse plan summary {decision}",
            minimum=0,
        ) != actual_summary[decision]:
            raise MaterializationError(f"reuse plan summary is stale for {decision}")
    reviews = [row for row in decisions if row["decision"] == "review_candidate"]
    return decisions, reviews


def _validate_approval(
    approval_path: Path | None,
    *,
    review_candidates: list[dict[str, Any]],
    plan_sha: str,
    request_contract_sha: str,
) -> tuple[dict[str, str], str]:
    if approval_path is None:
        if review_candidates:
            raise MaterializationError("review approval is required for review candidates")
        return {}, ""
    approval_path = Path(approval_path)
    if not approval_path.exists():
        raise MaterializationError(f"review approval is missing: {approval_path}")
    approval = _read_json(approval_path, "semantic reuse review approval")
    approval_sha = compute_file_sha256(approval_path)
    if _require_int(
        approval.get("schema_version"),
        "review approval schema_version",
    ) != 1:
        raise MaterializationError("review approval schema_version must be 1")
    if str(approval.get("decision", "")) != "approved":
        raise MaterializationError("review approval decision is not approved")
    if str(approval.get("plan_sha256", "")).upper() != plan_sha:
        raise MaterializationError("review approval is bound to a stale reuse plan SHA")
    if str(approval.get("request_contract_sha256", "")).upper() != request_contract_sha:
        raise MaterializationError("review approval is bound to a stale request contract SHA")
    reviewer_id = str(approval.get("reviewer_id", "")).strip()
    reviewer_normalized = reviewer_id.casefold()
    if (
        not reviewer_id
        or reviewer_normalized == "user-explicit-approval"
        or any(marker in reviewer_normalized for marker in SYNTHETIC_REVIEWER_MARKERS)
    ):
        raise MaterializationError("review approval reviewer_id is missing or synthetic")
    approval_source = str(approval.get("approval_source", "")).strip().casefold()
    if approval_source not in ALLOWED_APPROVAL_SOURCES:
        raise MaterializationError(
            "review approval_source is not an allowed explicit human confirmation source"
        )
    timestamp = str(approval.get("approved_at_utc", ""))
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise MaterializationError("review approval approved_at_utc is invalid") from error
    if parsed.tzinfo is None:
        raise MaterializationError(
            "review approval approved_at_utc must include a timezone"
        )

    expected = {str(row["target_shot_id"]): row for row in review_candidates}
    reviews = approval.get("reviews")
    if not isinstance(reviews, list):
        raise MaterializationError("review approval reviews must be a list")
    by_target: dict[str, dict[str, Any]] = {}
    for review in reviews:
        if not isinstance(review, dict):
            raise MaterializationError("review approval contains a non-object review")
        target_id = _require_shot_id(
            review.get("target_shot_id"),
            "review target_shot_id",
        )
        if target_id in by_target:
            raise MaterializationError(
                f"review approval contains duplicate review: {target_id}"
            )
        if target_id not in expected:
            raise MaterializationError(
                f"review approval contains unexpected review: {target_id}"
            )
        plan_row = expected[target_id]
        if str(review.get("source_shot_id", "")) != str(
            plan_row.get("source_shot_id", "")
        ):
            raise MaterializationError(
                f"review approval source shot is stale for {target_id}"
            )
        if str(review.get("source_asset_sha256", "")).upper() != str(
            plan_row.get("source_asset_sha256", "")
        ).upper():
            raise MaterializationError(
                f"review approval source asset SHA is stale for {target_id}"
            )
        decision = str(review.get("decision", ""))
        if decision not in {"reuse", "generate_new"}:
            raise MaterializationError(
                f"review approval decision is invalid for {target_id}"
            )
        by_target[target_id] = review
    if set(by_target) != set(expected):
        missing = sorted(set(expected) - set(by_target))
        raise MaterializationError(
            f"review approval is incomplete; missing reviews: {missing}"
        )
    return {
        target_id: str(row["decision"])
        for target_id, row in by_target.items()
    }, approval_sha


def _image_evidence(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise MaterializationError(f"{label} file is missing: {path}")
    byte_count = path.stat().st_size
    if byte_count < 20_000:
        raise MaterializationError(
            f"{label} has insufficient download evidence: {byte_count} bytes"
        )
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
    except Exception as error:
        raise MaterializationError(f"{label} is not a valid image: {path}") from error
    if width <= 0 or height <= 0:
        raise MaterializationError(f"{label} has invalid dimensions")
    return {
        "sha256": compute_file_sha256(path),
        "bytes": byte_count,
        "width": width,
        "height": height,
    }


def _load_source_assets(source_build: Path) -> dict[str, dict[str, Any]]:
    manifest = _read_json(
        source_build / "asset_manifest.json",
        "source asset manifest",
    )
    return _index_unique(manifest.get("assets"), "shot_id", "source assets")


def _validate_source_for_decision(
    decision: dict[str, Any],
    *,
    source_build: Path,
    source_assets: dict[str, dict[str, Any]],
    source_requests: dict[str, dict[str, Any]],
    target_request: dict[str, Any],
) -> dict[str, Any]:
    target_id = str(decision["target_shot_id"])
    source_id = str(decision["source_shot_id"])
    source_request = source_requests.get(source_id)
    if source_request is None:
        raise MaterializationError(
            f"source request is missing for {target_id}: {source_id}"
        )
    source_asset = source_assets.get(source_id)
    if source_asset is None:
        raise MaterializationError(
            f"source asset is missing for {target_id}: {source_id}"
        )
    if str(source_asset.get("status", "")) != "COMPLETED":
        raise MaterializationError(f"source asset is not COMPLETED for {target_id}")
    if not source_asset.get("card_id"):
        raise MaterializationError(f"source asset card_id is missing for {target_id}")
    source_request_sha = _require_sha(
        source_request.get("request_sha256"),
        f"source request SHA for {source_id}",
    )
    if str(source_asset.get("prompt_sha256", "")).upper() != source_request_sha:
        raise MaterializationError(
            f"source asset request hash is stale for {target_id}"
        )
    if str(decision.get("source_visual_mode", "")) != str(
        source_request.get("visual_mode", "")
    ):
        raise MaterializationError(f"source visual mode is stale for {target_id}")
    source_host = _host_required(source_request, f"source request {source_id}")
    target_host = _host_required(target_request, f"target request {target_id}")
    if source_host != target_host:
        raise MaterializationError(f"source/target host mode mismatch for {target_id}")
    if str(source_request.get("visual_mode", "")) != str(
        target_request.get("visual_mode", "")
    ):
        raise MaterializationError(f"source/target visual mode mismatch for {target_id}")
    if str(source_request.get("visual_role", "")) != str(
        target_request.get("visual_role", "")
    ):
        raise MaterializationError(f"source/target visual role mismatch for {target_id}")

    source_path, normalized_path = _safe_file(
        source_build / "images",
        source_asset.get("file_path"),
        f"source asset file_path for {target_id}",
    )
    planned_path = str(decision.get("source_asset_file_path", "")).replace(
        "\\",
        "/",
    )
    if normalized_path != planned_path:
        raise MaterializationError(
            f"reuse plan source file path is stale for {target_id}"
        )
    evidence = _image_evidence(source_path, f"source asset {source_id}")
    recorded_sha = _require_sha(
        source_asset.get("sha256"),
        f"source asset SHA for {source_id}",
    )
    planned_sha = _require_sha(
        decision.get("source_asset_sha256"),
        f"reuse plan source asset SHA for {target_id}",
    )
    if evidence["sha256"] != recorded_sha or evidence["sha256"] != planned_sha:
        raise MaterializationError(f"source asset SHA mismatch for {target_id}")
    for field in ("bytes", "width", "height"):
        recorded_value = _require_int(
            source_asset.get(field),
            f"source asset {field} for {target_id}",
            minimum=1,
        )
        if recorded_value != evidence[field]:
            raise MaterializationError(
                f"source asset {field} mismatch for {target_id}"
            )

    postprocess = source_asset.get("postprocess") or {}
    if source_host:
        missing_postprocess = [
            field for field in POSTPROCESS_FIELDS if field not in postprocess
        ]
        if missing_postprocess:
            raise MaterializationError(
                f"host canonical postprocess metadata is incomplete for {target_id}: "
                f"{missing_postprocess}"
            )
        if postprocess.get("type") != "canonical_host_overlay":
            raise MaterializationError(
                f"host source lacks canonical postprocess evidence for {target_id}"
            )
        if str(postprocess.get("output_sha256", "")).upper() != evidence["sha256"]:
            raise MaterializationError(
                f"host canonical output SHA is stale for {target_id}"
            )
        source_overlay = source_request.get("host_overlay") or {}
        target_overlay = target_request.get("host_overlay") or {}
        source_costume = str(source_overlay.get("costume", ""))
        target_costume = str(target_overlay.get("costume", ""))
        if (
            not source_costume
            or postprocess.get("costume") != source_costume
            or source_costume != target_costume
        ):
            raise MaterializationError(
                f"host canonical costume mismatch for {target_id}"
            )
        if postprocess.get("anchor") != "right_bottom":
            raise MaterializationError(
                f"host canonical anchor mismatch for {target_id}"
            )
        try:
            postprocess_ratio = float(postprocess.get("width_ratio"))
            source_ratio = float(source_overlay.get("width_ratio"))
            target_ratio = float(target_overlay.get("width_ratio"))
        except (TypeError, ValueError) as error:
            raise MaterializationError(
                f"host canonical width_ratio is invalid for {target_id}"
            ) from error
        if not (
            abs(postprocess_ratio - source_ratio) <= 1e-9
            and abs(source_ratio - target_ratio) <= 1e-9
        ):
            raise MaterializationError(
                f"host canonical width_ratio mismatch for {target_id}"
            )
        overlay_sha = _require_sha(
            postprocess.get("overlay_sha256"),
            f"host canonical overlay SHA for {target_id}",
        )
        canonical_overlay_path = _PROJECT_ROOT / CANONICAL_HOST_ASSET
        if not canonical_overlay_path.is_file():
            raise MaterializationError(
                f"canonical host overlay file is missing: {canonical_overlay_path}"
            )
        if compute_file_sha256(canonical_overlay_path) != overlay_sha:
            raise MaterializationError(
                f"host canonical overlay SHA mismatch for {target_id}"
            )
    elif postprocess.get("type") == "canonical_host_overlay":
        raise MaterializationError(
            f"non-host source has canonical host postprocess for {target_id}"
        )
    return {
        "asset": source_asset,
        "request": source_request,
        "path": source_path,
        "relative_path": normalized_path,
        "evidence": evidence,
        "host": source_host,
    }


def _expected_asset_row(
    decision: dict[str, Any],
    source: dict[str, Any],
    target_request: dict[str, Any],
    *,
    source_build: Path,
    plan_sha: str,
    approval_sha: str,
    request_contract_sha: str,
    provenance_decision: str,
) -> dict[str, Any]:
    target_id = str(decision["target_shot_id"])
    suffix = source["path"].suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        raise MaterializationError(
            f"source image suffix is unsupported for {target_id}: {suffix}"
        )
    digest = str(source["evidence"]["sha256"])
    relative_path = Path("reused") / f"{target_id}-{digest[:12]}{suffix}"
    row: dict[str, Any] = {
        "shot_id": target_id,
        "order": _require_int(
            target_request["order"],
            f"target request order for {target_id}",
            minimum=1,
        ),
        "card_id": f"REUSE-{target_id}-{digest[:8]}",
        "prompt_sha256": str(target_request["request_sha256"]).upper(),
        "file_path": relative_path.as_posix(),
        "sha256": digest,
        "bytes": _require_int(source["evidence"]["bytes"], "source image bytes", minimum=1),
        "width": _require_int(source["evidence"]["width"], "source image width", minimum=1),
        "height": _require_int(source["evidence"]["height"], "source image height", minimum=1),
        "status": "COMPLETED",
        "provenance": {
            "type": "semantic_image_reuse",
            "decision": provenance_decision,
            "source_build": str(source_build),
            "source_shot_id": str(decision["source_shot_id"]),
            "source_asset_file_path": str(source["relative_path"]),
            "source_asset_sha256": digest,
            "source_prompt_sha256": str(
                source["request"]["request_sha256"]
            ).upper(),
            "plan_sha256": plan_sha,
            "review_approval_sha256": approval_sha,
            "request_contract_sha256": request_contract_sha,
        },
    }
    if source["host"]:
        source_postprocess = source["asset"].get("postprocess") or {}
        row["postprocess"] = {
            field: copy.deepcopy(source_postprocess[field])
            for field in POSTPROCESS_FIELDS
            if field in source_postprocess
        }
    return row


def _asset_file_matches(
    build: Path,
    row: dict[str, Any],
    expected: dict[str, Any],
) -> bool:
    for key, value in expected.items():
        if row.get(key) != value:
            return False
    try:
        path, normalized = _safe_file(
            build / "images",
            row.get("file_path"),
            f"existing target asset {row.get('shot_id', '')}",
        )
        if normalized != expected["file_path"]:
            return False
        evidence = _image_evidence(
            path,
            f"existing target asset {row.get('shot_id', '')}",
        )
    except MaterializationError:
        return False
    return all(
        evidence[field] == expected[field]
        for field in ("sha256", "bytes", "width", "height")
    )


def _copy_files_atomically(copy_rows: list[tuple[Path, Path, str]]) -> None:
    if not copy_rows:
        return
    staging_root = (
        copy_rows[0][1].parents[1]
        / f".semantic-reuse-{uuid.uuid4().hex}.part"
    )
    staged: list[tuple[Path, Path]] = []
    committed: list[Path] = []
    try:
        staging_root.mkdir(parents=True, exist_ok=False)
        for index, (source, destination, expected_sha) in enumerate(copy_rows):
            staged_path = staging_root / f"{index:04d}{destination.suffix}"
            shutil.copyfile(source, staged_path)
            if compute_file_sha256(staged_path) != expected_sha:
                raise MaterializationError(
                    f"staged reuse copy SHA mismatch: {destination.name}"
                )
            staged.append((staged_path, destination))
        for staged_path, destination in staged:
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(staged_path, destination)
            except FileExistsError as error:
                raise MaterializationError(
                    f"reuse destination appeared concurrently and will not be overwritten: "
                    f"{destination}"
                ) from error
            except OSError as error:
                raise MaterializationError(
                    f"atomic reuse destination creation failed: {destination}: {error}"
                ) from error
            committed.append(destination)
            staged_path.unlink()
    except Exception:
        for path in reversed(committed):
            path.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


def _manifest_snapshot(path: Path) -> str | None:
    return compute_file_sha256(path) if path.is_file() else None


@contextmanager
def _exclusive_build_lock(target_build: Path):
    lock_path = target_build / ".semantic-image-reuse.lock"
    try:
        descriptor = os.open(
            lock_path,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        )
    except FileExistsError as error:
        raise MaterializationError(
            f"semantic image reuse lock already exists; another run may be active: "
            f"{lock_path}"
        ) from error
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(f"pid={os.getpid()}\n")
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def materialize_semantic_image_reuse(
    source_build: Path,
    target_build: Path,
    plan_path: Path,
    review_approval_path: Path | None = None,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    source_build = Path(source_build).resolve()
    target_build = Path(target_build).resolve()
    plan_path = Path(plan_path).resolve()
    if not source_build.is_dir():
        raise MaterializationError(
            f"source build directory is missing: {source_build}"
        )
    if not target_build.is_dir():
        raise MaterializationError(
            f"target build directory is missing: {target_build}"
        )

    plan = _read_json(plan_path, "semantic image reuse plan")
    plan_sha = compute_file_sha256(plan_path)
    _, source_requests, _ = _load_request_contract(source_build, "source")
    _, target_requests, target_contract_sha = _load_request_contract(
        target_build,
        "target",
    )
    decisions, review_candidates = _validate_plan(
        plan,
        source_build=source_build,
        target_build=target_build,
        target_requests=target_requests,
    )
    approval_path = (
        Path(review_approval_path).resolve()
        if review_approval_path is not None
        else None
    )
    review_decisions, approval_sha = _validate_approval(
        approval_path,
        review_candidates=review_candidates,
        plan_sha=plan_sha,
        request_contract_sha=target_contract_sha,
    )
    source_assets = _load_source_assets(source_build)

    selected: list[tuple[dict[str, Any], str]] = []
    pending_generation: list[str] = []
    for decision in decisions:
        target_id = str(decision["target_shot_id"])
        if decision["decision"] == "auto_reuse":
            selected.append((decision, "auto_reuse"))
        elif (
            decision["decision"] == "review_candidate"
            and review_decisions[target_id] == "reuse"
        ):
            selected.append((decision, "approved_review_reuse"))
        else:
            pending_generation.append(target_id)

    expected_rows: dict[str, dict[str, Any]] = {}
    source_paths: dict[str, Path] = {}
    for decision, provenance_decision in selected:
        target_id = str(decision["target_shot_id"])
        source = _validate_source_for_decision(
            decision,
            source_build=source_build,
            source_assets=source_assets,
            source_requests=source_requests,
            target_request=target_requests[target_id],
        )
        expected_rows[target_id] = _expected_asset_row(
            decision,
            source,
            target_requests[target_id],
            source_build=source_build,
            plan_sha=plan_sha,
            approval_sha=approval_sha,
            request_contract_sha=target_contract_sha,
            provenance_decision=provenance_decision,
        )
        source_paths[target_id] = source["path"]

    manifest_path = target_build / "asset_manifest.json"
    manifest_snapshot = _manifest_snapshot(manifest_path)
    manifest = (
        _read_json(manifest_path, "target asset manifest")
        if manifest_path.exists()
        else {
            "schema_version": 2,
            "build_id": target_build.name,
            "assets": [],
        }
    )
    active_by_id = _index_unique(
        manifest.get("assets", []),
        "shot_id",
        "target assets",
    )
    history_rows = manifest.get("asset_history", [])
    if not isinstance(history_rows, list) or any(
        not isinstance(row, dict) for row in history_rows
    ):
        raise MaterializationError(
            "target asset_history must be a list of objects"
        )
    request_sha_by_id = {
        shot_id: str(request["request_sha256"]).upper()
        for shot_id, request in target_requests.items()
    }
    stale_rows = [
        row
        for shot_id, row in active_by_id.items()
        if shot_id not in request_sha_by_id
        or str(row.get("prompt_sha256", "")).upper()
        != request_sha_by_id[shot_id]
    ]
    stale_object_ids = {id(row) for row in stale_rows}
    current_rows = {
        shot_id: row
        for shot_id, row in active_by_id.items()
        if id(row) not in stale_object_ids
    }
    referenced_paths = {
        str(row.get("file_path", "")).replace("\\", "/")
        for row in [*stale_rows, *history_rows]
        if row.get("file_path")
    }

    already_materialized: list[str] = []
    copy_rows: list[tuple[Path, Path, str]] = []
    update_rows: dict[str, dict[str, Any]] = {}
    preexisting_reused: list[str] = []
    for target_id, expected in expected_rows.items():
        current = current_rows.get(target_id)
        if current is not None:
            if _asset_file_matches(target_build, current, expected):
                already_materialized.append(target_id)
                continue
            raise MaterializationError(
                f"current same-prompt asset conflict for {target_id}; "
                "refusing to overwrite"
            )
        destination, normalized = _safe_file(
            target_build / "images",
            expected["file_path"],
            f"target reuse destination for {target_id}",
        )
        if normalized != expected["file_path"]:
            raise MaterializationError(
                f"target reuse path normalization failed for {target_id}"
            )
        if destination.exists():
            if expected["file_path"] not in referenced_paths:
                raise MaterializationError(
                    f"orphan target reuse file exists for {target_id}: {destination}"
                )
            evidence = _image_evidence(
                destination,
                f"pre-existing reused target {target_id}",
            )
            if any(
                evidence[field] != expected[field]
                for field in ("sha256", "bytes", "width", "height")
            ):
                raise MaterializationError(
                    f"pre-existing reused target evidence mismatch for {target_id}"
                )
            preexisting_reused.append(target_id)
        else:
            copy_rows.append(
                (source_paths[target_id], destination, expected["sha256"])
            )
        update_rows[target_id] = expected

    current_without_replacements = [
        row
        for shot_id, row in current_rows.items()
        if shot_id not in update_rows
    ]
    next_assets = sorted(
        [*current_without_replacements, *update_rows.values()],
        key=lambda row: (
            _require_int(
                row.get("order"),
                f"target asset order for {row.get('shot_id', '')}",
                minimum=1,
            ),
            str(row.get("shot_id", "")),
        ),
    )
    next_manifest = copy.deepcopy(manifest)
    next_manifest["schema_version"] = 2
    next_manifest["build_id"] = target_build.name
    next_manifest["assets"] = next_assets

    history = [copy.deepcopy(row) for row in history_rows]
    history_keys = {
        (
            str(row.get("shot_id", "")),
            str(row.get("prompt_sha256", "")),
            str(row.get("sha256", "")),
        )
        for row in history
    }
    archive_time = datetime.now(timezone.utc).isoformat()
    for source_row in stale_rows:
        row = copy.deepcopy(source_row)
        shot_id = str(row.get("shot_id", ""))
        row["archive_reason"] = (
            "stale_request_hash"
            if shot_id in request_sha_by_id
            else "unknown_request_id"
        )
        row["archived_at_utc"] = archive_time
        key = (
            shot_id,
            str(row.get("prompt_sha256", "")),
            str(row.get("sha256", "")),
        )
        if key not in history_keys:
            history.append(row)
            history_keys.add(key)
    if history:
        next_manifest["asset_history"] = history
    else:
        next_manifest.pop("asset_history", None)

    stable_materialization = {
        "type": "semantic_image_reuse",
        "source_build": str(source_build),
        "plan_sha256": plan_sha,
        "review_approval_sha256": approval_sha,
        "request_contract_sha256": target_contract_sha,
        "materialized_shot_ids": sorted(expected_rows),
    }
    previous_materialization = manifest.get("reuse_materialization") or {}
    metadata_current = all(
        previous_materialization.get(key) == value
        for key, value in stable_materialization.items()
    )
    logical_change = bool(
        copy_rows
        or update_rows
        or stale_rows
        or not metadata_current
    )
    if logical_change:
        now = datetime.now(timezone.utc).isoformat()
        next_manifest["reuse_materialization"] = {
            **stable_materialization,
            "materialized_at_utc": now,
        }
        next_manifest["generated_at_utc"] = now

    would_materialize = [
        str(row[0]["target_shot_id"])
        for row in selected
    ]
    report = {
        "schema_version": 1,
        "dry_run": bool(dry_run),
        "source_build": str(source_build),
        "target_build": str(target_build),
        "plan_sha256": plan_sha,
        "review_approval_sha256": approval_sha,
        "request_contract_sha256": target_contract_sha,
        "would_materialize_shot_ids": would_materialize,
        "copied_shot_ids": [],
        "already_materialized_shot_ids": sorted(already_materialized),
        "preexisting_reused_shot_ids": sorted(preexisting_reused),
        "pending_generation_shot_ids": pending_generation,
    }
    if dry_run:
        return report
    if not logical_change:
        return report

    committed_paths: list[Path] = []
    try:
        with _exclusive_build_lock(target_build):
            if _manifest_snapshot(manifest_path) != manifest_snapshot:
                raise MaterializationError(
                    "target asset manifest changed after preflight; refusing concurrent update"
                )
            _copy_files_atomically(copy_rows)
            committed_paths = [destination for _, destination, _ in copy_rows]
            if _manifest_snapshot(manifest_path) != manifest_snapshot:
                raise MaterializationError(
                    "target asset manifest changed during materialization; refusing overwrite"
                )
            _write_json_atomic(manifest_path, next_manifest)
    except Exception:
        for path in reversed(committed_paths):
            path.unlink(missing_ok=True)
        raise
    report["copied_shot_ids"] = [
        target_id
        for target_id in would_materialize
        if target_id not in already_materialized
        and target_id not in preexisting_reused
    ]
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize SHA-bound semantic image reuse before Flow generation."
        )
    )
    parser.add_argument("--source-build", type=Path, required=True)
    parser.add_argument("--target-build", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument(
        "--review-approval",
        type=Path,
        help="Required when the reuse plan contains review_candidate rows.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        report = materialize_semantic_image_reuse(
            args.source_build,
            args.target_build,
            args.plan,
            args.review_approval,
            dry_run=args.dry_run,
        )
    except MaterializationError as error:
        raise SystemExit(f"Semantic image reuse blocked: {error}") from error
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
