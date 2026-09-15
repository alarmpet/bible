from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.provenance import compute_file_sha256, compute_object_sha256


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_atomic(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def record_false_positives(
    build_dir: Path,
    shot_ids: list[str],
    *,
    reviewer_id: str,
    reason: str,
) -> Path:
    build_dir = Path(build_dir)
    report = _read(build_dir / "visual_content_report.json")
    manifest = _read(build_dir / "asset_manifest.json")
    report_by_id = {str(row["shot_id"]): row for row in report.get("shots", [])}
    assets = {str(row["shot_id"]): row for row in manifest.get("assets", [])}
    output = build_dir / "visual_ocr_overrides.json"
    data = _read(output) if output.exists() else {"schema_version": 1, "reviews": []}
    reviews = {str(row.get("shot_id", "")): row for row in data.get("reviews", [])}
    now = datetime.now(timezone.utc).isoformat()
    for shot_id in shot_ids:
        content_row = report_by_id.get(shot_id)
        asset = assets.get(shot_id)
        if content_row is None or asset is None:
            raise ValueError(f"unknown OCR review shot: {shot_id}")
        raw_status = str(content_row.get("raw_status", content_row.get("status", "")))
        if raw_status != "FAIL" or not content_row.get("findings"):
            raise ValueError(f"shot has no failing OCR finding: {shot_id}")
        image_path = build_dir / "images" / str(asset.get("file_path", ""))
        if not image_path.is_file():
            raise ValueError(f"image is missing for OCR review: {shot_id}")
        review = {
            "shot_id": shot_id,
            "decision": "false_positive",
            "image_sha256": compute_file_sha256(image_path),
            "findings_sha256": compute_object_sha256(content_row["findings"]),
            "reason": reason,
            "reviewer_id": reviewer_id,
            "review_source": "local_crop_visual_inspection",
            "reviewed_at_utc": now,
        }
        crop = build_dir / "qa_crops" / f"{shot_id}-bottom-right.jpg"
        if crop.exists():
            review["crop_path"] = crop.relative_to(build_dir).as_posix()
            review["crop_sha256"] = compute_file_sha256(crop)
        reviews[shot_id] = review
    data["reviews"] = sorted(reviews.values(), key=lambda row: str(row.get("shot_id", "")))
    _write_atomic(output, data)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--shot-id", required=True, nargs="+")
    parser.add_argument("--reviewer-id", default="antigravity-local-visual-qa")
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    print(record_false_positives(
        args.build,
        args.shot_id,
        reviewer_id=args.reviewer_id,
        reason=args.reason,
    ))


if __name__ == "__main__":
    main()
