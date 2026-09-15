from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.provenance import compute_file_sha256, compute_object_sha256
from record_visual_pilot_approval import PASS_AXES


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_full_approval(build_dir: Path, *, reviewer_id: str) -> dict[str, Any]:
    build_dir = Path(build_dir)
    manifest = _read(build_dir / "asset_manifest.json")
    request_manifest = _read(build_dir / "image_request_manifest.json")
    if manifest.get("generation_scope") != "all":
        raise ValueError("full visual approval requires generation_scope=all")

    contract_sha = str(request_manifest.get("contract_sha256", ""))
    if not contract_sha:
        raise ValueError("image request manifest is missing contract_sha256")
    request_ids = [str(row["scene_id"]) for row in request_manifest.get("requests", [])]
    if not request_ids or len(request_ids) != len(set(request_ids)):
        raise ValueError("image request manifest has no unique request IDs")

    assets = {str(row.get("shot_id", "")): row for row in manifest.get("assets", [])}
    if set(assets) != set(request_ids) or len(assets) != len(manifest.get("assets", [])):
        raise ValueError("asset IDs do not match the full image request manifest")

    contact_sheet = build_dir / "contact_sheet.jpg"
    content_report = build_dir / "visual_content_report.json"
    if not contact_sheet.exists():
        raise ValueError("full contact sheet is missing")
    if not content_report.exists() or _read(content_report).get("status") != "PASS":
        raise ValueError("visual content report is missing or not PASS")

    evaluations = []
    for shot_id in request_ids:
        row = assets[shot_id]
        if row.get("status") != "COMPLETED" or not row.get("file_path") or not row.get("sha256"):
            raise ValueError(f"visual asset is not complete: {shot_id}")
        image_path = build_dir / "images" / str(row["file_path"])
        if not image_path.exists():
            raise ValueError(f"visual asset file is missing: {shot_id}")
        actual_sha = compute_file_sha256(image_path)
        if actual_sha != str(row["sha256"]):
            raise ValueError(f"visual asset hash is stale: {shot_id}")
        evaluations.append({
            "shot_id": shot_id,
            "image_sha256": actual_sha,
            "decision": "approved",
            "axes": dict(PASS_AXES),
            "notes": "explicit user approval of the current full-episode contact sheet",
        })

    return {
        "schema_version": 2,
        "decision": "approved",
        "approved_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer_id": reviewer_id,
        "approval_source": "explicit_user_confirmation_in_antigravity_thread",
        "review_scope": "full_episode",
        "contract_sha256": contract_sha,
        "manifest_sha256": compute_object_sha256(manifest),
        "contact_sheet_sha256": compute_file_sha256(contact_sheet),
        "visual_content_report_sha256": compute_file_sha256(content_report),
        "shot_evaluations": evaluations,
    }


def record_full_approval(build_dir: Path, *, reviewer_id: str) -> Path:
    approval = build_full_approval(build_dir, reviewer_id=reviewer_id)
    output = Path(build_dir) / "approvals" / "visual_approval.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".json.part")
    temporary.write_text(json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--reviewer-id", default="user-explicit-approval")
    args = parser.parse_args()
    print(record_full_approval(args.build, reviewer_id=args.reviewer_id))


if __name__ == "__main__":
    main()
