# -*- coding: utf-8 -*-
"""Fail-closed verification for visual completeness, OCR, role compliance, and approval hashes."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.host_overlay import CANONICAL_HOST_COSTUME
from lib.provenance import compute_file_sha256, compute_object_sha256
from lib.visual_content_qa import build_rapidocr_adapter, inspect_generated_text
from lib.visual_qa import check_near_duplicates, validate_visual_evaluation, verify_image_pixel_integrity

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_OCR_UNSET = object()


def validate_ocr_false_positive_override(
    review: dict[str, Any],
    *,
    shot_id: str,
    image_sha256: str,
    findings: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    if review.get("decision") != "false_positive":
        errors.append("decision is not false_positive")
    if str(review.get("shot_id", "")) != shot_id:
        errors.append("shot ID is stale")
    if str(review.get("image_sha256", "")) != image_sha256:
        errors.append("image SHA is stale")
    if str(review.get("findings_sha256", "")) != compute_object_sha256(findings):
        errors.append("OCR findings SHA is stale")
    if not str(review.get("reason", "")).strip():
        errors.append("reason is missing")
    return errors


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _approval_for_build(build_dir: Path) -> Path:
    full = build_dir / "approvals" / "visual_approval.json"
    pilot = build_dir / "approvals" / "visual_pilot_review.json"
    return full if full.exists() else pilot


def verify_visual_build(
    contract_path: Path | None = None,
    manifest_path: Path | None = None,
    approval_path: Path | None = None,
    build_dir: Path | None = None,
    *,
    ocr: Any = _OCR_UNSET,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if build_dir:
        build_dir = Path(build_dir).resolve()
        manifest_path = build_dir / "asset_manifest.json"
        inferred_contract = build_dir / "episode_visual_contract_v2.json"
        contract_path = inferred_contract if inferred_contract.exists() else contract_path
        approval_path = _approval_for_build(build_dir)
    elif manifest_path:
        build_dir = Path(manifest_path).resolve().parent

    if not manifest_path or not Path(manifest_path).exists():
        return False, [f"Asset manifest missing: {manifest_path}"]
    manifest_path = Path(manifest_path)
    manifest_data = _read_json(manifest_path)
    assets = manifest_data.get("assets", [])
    images_dir = manifest_path.parent / "images"
    request_manifest_path = manifest_path.parent / "image_request_manifest.json"
    request_manifest: dict[str, Any] | None = None
    request_sha_by_id: dict[str, str] = {}
    if request_manifest_path.exists():
        request_manifest = _read_json(request_manifest_path)
        request_sha_by_id = {
            str(request["scene_id"]): str(request.get("request_sha256", ""))
            for request in request_manifest.get("requests", [])
        }

    contract_data: dict[str, Any] | None = None
    contract_binding_sha = ""
    scenes_by_id: dict[str, dict[str, Any]] = {}
    if contract_path:
        contract_path = Path(contract_path)
        if not contract_path.exists():
            errors.append(f"Visual contract missing: {contract_path}")
        else:
            contract_data = _read_json(contract_path)
            scenes_by_id = {str(scene["scene_id"]): scene for scene in contract_data.get("scenes", [])}
            contract_binding_sha = compute_object_sha256(contract_data)
    elif request_manifest and request_manifest.get("requests"):
        v5_scenes = [
            request for request in request_manifest.get("requests", [])
            if request.get("scene_id") and request.get("visual_role")
        ]
        if v5_scenes:
            contract_data = {
                "schema_version": request_manifest.get("schema_version", 2),
                "source": "image_request_manifest_v5",
                "scenes": v5_scenes,
            }
            scenes_by_id = {str(scene["scene_id"]): scene for scene in v5_scenes}
            contract_binding_sha = str(request_manifest.get("contract_sha256", ""))
            if not contract_binding_sha:
                errors.append("V5 image request manifest is missing contract_sha256")

    if not approval_path or not Path(approval_path).exists():
        errors.append(f"Required visual approval missing: {approval_path}")

    asset_ids = [str(asset.get("shot_id", "")) for asset in assets]
    if len(asset_ids) != len(set(asset_ids)):
        errors.append("Asset manifest contains duplicate shot IDs")
    verification_ids = list(scenes_by_id)
    if scenes_by_id and manifest_data.get("generation_scope") in {"pilot", "selected"}:
        verification_ids = [str(scene_id) for scene_id in manifest_data.get("expected_ids", [])]
        unknown_expected = [scene_id for scene_id in verification_ids if scene_id not in scenes_by_id]
        if unknown_expected:
            errors.append(f"Manifest scope references unknown scene IDs: {unknown_expected}")
    if scenes_by_id:
        expected_ids = verification_ids
        missing_ids = [scene_id for scene_id in expected_ids if scene_id not in set(asset_ids)]
        extra_ids = [shot_id for shot_id in asset_ids if shot_id not in scenes_by_id]
        if missing_ids:
            errors.append(f"Missing visual assets: {missing_ids}")
        if extra_ids:
            errors.append(f"Unexpected visual assets: {extra_ids}")

    verification_id_set = set(verification_ids)
    verification_assets = [
        asset for asset in assets
        if not scenes_by_id or str(asset.get("shot_id", "")) in verification_id_set
    ]

    image_paths: list[Path] = []
    completed_assets: list[dict[str, Any]] = []
    actual_sha_by_id: dict[str, str] = {}
    for asset in verification_assets:
        shot_id = str(asset.get("shot_id", ""))
        expected_request_sha = request_sha_by_id.get(shot_id)
        if expected_request_sha and str(asset.get("prompt_sha256", "")) != expected_request_sha:
            errors.append(
                f"[{shot_id}] Asset has stale request hash: "
                f"manifest={asset.get('prompt_sha256', '')}, current={expected_request_sha}"
            )
        if asset.get("status") != "COMPLETED":
            errors.append(f"Shot {shot_id} has status '{asset.get('status')}'")
            continue
        if scenes_by_id:
            role = str(scenes_by_id.get(shot_id, {}).get("visual_role", ""))
            postprocess = asset.get("postprocess") or {}
            if role == "host_explainer":
                if postprocess.get("type") != "canonical_host_overlay":
                    errors.append(f"[{shot_id}] Host scene is missing canonical host overlay postprocess record")
                elif postprocess.get("costume") != CANONICAL_HOST_COSTUME:
                    errors.append(f"[{shot_id}] Canonical host overlay costume metadata is inconsistent")
            elif postprocess.get("type") == "canonical_host_overlay":
                errors.append(f"[{shot_id}] Non-host scene unexpectedly contains canonical host overlay")
        image_path = images_dir / str(asset.get("file_path", ""))
        ok, pixel_issues = verify_image_pixel_integrity(image_path)
        if not ok:
            errors.extend([f"[{shot_id}] {issue}" for issue in pixel_issues])
            continue
        image_paths.append(image_path)
        completed_assets.append(asset)
        actual_sha = compute_file_sha256(image_path)
        actual_sha_by_id[shot_id] = actual_sha
        if actual_sha != asset.get("sha256"):
            recorded = str(asset.get("sha256", ""))
            errors.append(f"[{shot_id}] SHA mismatch: manifest={recorded[:8]}, actual={actual_sha[:8]}")
        postprocess = asset.get("postprocess") or {}
        if postprocess.get("type") == "canonical_host_overlay" and postprocess.get("output_sha256") != actual_sha:
            errors.append(f"[{shot_id}] Canonical host overlay output SHA is stale")

    if len(image_paths) >= 2:
        for first, second, distance in check_near_duplicates(image_paths):
            errors.append(f"Near duplicate detected between {first} and {second} (pHash dist={distance})")

    if scenes_by_id:
        ocr_engine = build_rapidocr_adapter() if ocr is _OCR_UNSET else ocr
        override_path = manifest_path.parent / "visual_ocr_overrides.json"
        override_data = _read_json(override_path) if override_path.exists() else {"reviews": []}
        override_rows = list(override_data.get("reviews", []))
        override_ids = [str(row.get("shot_id", "")) for row in override_rows]
        if len(override_ids) != len(set(override_ids)):
            errors.append("OCR override file contains duplicate shot IDs")
        overrides = {str(row.get("shot_id", "")): row for row in override_rows}
        content_rows = []
        for asset in completed_assets:
            shot_id = str(asset["shot_id"])
            image_path = images_dir / str(asset["file_path"])
            inspection = inspect_generated_text(image_path, ocr_engine)
            raw_status = inspection.status
            effective_status = raw_status
            review = overrides.get(shot_id)
            applied_review: dict[str, Any] | None = None
            if raw_status == "FAIL" and review is not None:
                override_errors = validate_ocr_false_positive_override(
                    review,
                    shot_id=shot_id,
                    image_sha256=actual_sha_by_id.get(shot_id, ""),
                    findings=inspection.findings,
                )
                if override_errors:
                    errors.extend([f"[{shot_id}] Invalid OCR override: {issue}" for issue in override_errors])
                else:
                    effective_status = "PASS"
                    applied_review = review
            content_row = {
                "shot_id": shot_id,
                "status": effective_status,
                "raw_status": raw_status,
                "findings": inspection.findings,
                "error": inspection.error,
            }
            if applied_review is not None:
                content_row["ocr_override"] = applied_review
            content_rows.append(content_row)
            if effective_status == "FAIL":
                errors.append(f"[{shot_id}] Embedded text detected in generated base image")
            elif effective_status == "REVIEW_REQUIRED":
                errors.append(f"[{shot_id}] OCR review required: {inspection.error}")
        report = {
            "schema_version": 1,
            "contract_sha256": contract_binding_sha,
            "manifest_sha256": compute_object_sha256(manifest_data),
            "status": "PASS" if all(row["status"] == "PASS" for row in content_rows) else "FAIL",
            "shots": content_rows,
        }
        (manifest_path.parent / "visual_content_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    if approval_path and Path(approval_path).exists():
        approval_data = _read_json(Path(approval_path))
        top_level_decision = approval_data.get("decision")
        if top_level_decision is not None and top_level_decision != "approved":
            errors.append("Visual approval decision is not approved")
        if contract_data is not None and top_level_decision != "approved":
            errors.append("Role-aware visual approval requires decision=approved")
        if contract_data is not None:
            current_manifest_sha = compute_object_sha256(manifest_data)
            if approval_data.get("contract_sha256") != contract_binding_sha:
                errors.append("Visual approval contract hash is missing or stale")
            if approval_data.get("manifest_sha256") != current_manifest_sha:
                errors.append("Visual approval manifest hash is missing or stale")
        evaluations = {str(item["shot_id"]): item for item in approval_data.get("shot_evaluations", [])}
        evaluation_ids = verification_ids if scenes_by_id else asset_ids
        for shot_id in evaluation_ids:
            evaluation = evaluations.get(shot_id)
            if evaluation is None:
                errors.append(f"Missing visual approval evaluation for shot {shot_id}")
                continue
            if scenes_by_id:
                for issue in validate_visual_evaluation(scenes_by_id[shot_id], evaluation):
                    errors.append(f"[{shot_id}] {issue}")
            else:
                if evaluation.get("decision") != "approved":
                    errors.append(f"Visual approval rejected for shot {shot_id}")
                for axis, value in evaluation.get("axes", {}).items():
                    if value == "FAIL":
                        errors.append(f"[{shot_id}] Failed required axis '{axis}'")
    return len(errors) == 0, errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--build", type=Path)
    args = parser.parse_args()
    ok, errors = verify_visual_build(args.contract, args.manifest, args.approval, args.build)
    if not ok:
        print("Visual Asset Verification FAILED:")
        for error in errors:
            print(f"  - {error}")
        raise SystemExit(1)
    print("Visual Asset Verification PASSED")


if __name__ == "__main__":
    main()
