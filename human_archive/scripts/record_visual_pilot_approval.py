from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from generate_flow_batch import pilot_asset_fingerprint
from lib.provenance import compute_file_sha256, compute_object_sha256

PASS_AXES = {
    "semantic_match": "PASS",
    "historical_subject": "PASS",
    "host_presence": "PASS",
    "embedded_text": "PASS",
    "composition_density": "PASS",
    "style_profile": "PASS",
    "dignity": "PASS",
    "service_mark": "PASS",
}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_pilot_approval(build_dir: Path, *, reviewer_id: str) -> dict[str, Any]:
    build_dir = Path(build_dir)
    manifest = _read(build_dir / "asset_manifest.json")
    request_manifest = _read(build_dir / "image_request_manifest.json")
    pilot_sets = manifest.get("pilot_sets", {})
    pilot_ids = [*pilot_sets.get("cold_open", []), *pilot_sets.get("coverage", [])]
    if not pilot_ids:
        raise ValueError("asset manifest has no v5 pilot_sets")
    if len(pilot_ids) != len(set(pilot_ids)):
        raise ValueError("pilot sets contain duplicate shot IDs")
    assets = {str(row["shot_id"]): row for row in manifest.get("assets", [])}
    evaluations = []
    for shot_id in pilot_ids:
        row = assets.get(str(shot_id))
        if not row or row.get("status") != "COMPLETED" or not row.get("sha256"):
            raise ValueError(f"pilot asset is not complete: {shot_id}")
        evaluations.append({
            "shot_id": str(shot_id),
            "image_sha256": str(row["sha256"]),
            "decision": "approved",
            "axes": dict(PASS_AXES),
            "notes": "explicit user approval of the current dual-pilot contact sheets",
        })
    approval = {
        "schema_version": 2,
        "decision": "approved",
        "approved_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer_id": reviewer_id,
        "approval_source": "explicit_user_confirmation_in_antigravity_thread",
        "review_scope": "pilot_dual",
        "contract_sha256": str(request_manifest.get("contract_sha256", "")),
        "manifest_sha256": compute_object_sha256(manifest),
        "pilot_asset_fingerprint_sha256": pilot_asset_fingerprint(manifest, [str(value) for value in pilot_ids]),
        "shot_evaluations": evaluations,
    }
    for name in ("pilot_cold_open_contact_sheet.jpg", "pilot_coverage_contact_sheet.jpg", "visual_content_report.json"):
        path = build_dir / name
        if path.exists():
            approval[name.replace(".jpg", "").replace(".json", "") + "_sha256"] = compute_file_sha256(path)
    return approval


def record_pilot_approval(build_dir: Path, *, reviewer_id: str) -> Path:
    approval = build_pilot_approval(build_dir, reviewer_id=reviewer_id)
    output = Path(build_dir) / "approvals" / "visual_pilot_review.json"
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
    print(record_pilot_approval(args.build, reviewer_id=args.reviewer_id))


if __name__ == "__main__":
    main()
