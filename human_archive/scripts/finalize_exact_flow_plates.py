"""Bind verified Google Flow downloads to the exact-release plate registry."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

from PIL import Image

from lib.exact_release_verifier import validate_plate_manifest


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    shutil.copyfile(source, temporary)
    with open(temporary, "r+b") as handle:
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)


def _atomic_normalize_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    with Image.open(source) as image:
        image.convert("RGB").resize((2304, 1296), Image.Resampling.LANCZOS).save(
            temporary, format="JPEG", quality=95
        )
    with open(temporary, "r+b") as handle:
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)


def finalize_plate_plan(
    plan_path: Path,
    asset_manifest_path: Path,
    source_dir: Path,
    output_dir: Path,
    *,
    expected_count: int = 80,
) -> dict[str, Any]:
    plan_path = Path(plan_path)
    asset_manifest_path = Path(asset_manifest_path)
    source_dir = Path(source_dir).resolve()
    output_dir = Path(output_dir).resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    manifest = json.loads(asset_manifest_path.read_text(encoding="utf-8"))
    plates = list(plan.get("plates", []))
    if len(plates) != expected_count:
        raise ValueError(f"Expected {expected_count} planned plates, found {len(plates)}")

    rows = {
        str(row.get("scene_id") or row.get("asset_id") or row.get("shot_id")): row
        for row in manifest.get("assets", [])
    }
    updated: list[dict[str, Any]] = []
    physical_rows: list[dict[str, Any]] = []
    for plate in plates:
        plate_id = str(plate["plate_id"])
        row = rows.get(plate_id)
        if not row or row.get("status") != "COMPLETED":
            raise RuntimeError(f"Missing completed Flow asset row: {plate_id}")
        source = (source_dir / str(row.get("file_path", ""))).resolve()
        try:
            source.relative_to(source_dir)
        except ValueError as error:
            raise RuntimeError(f"Flow asset path escapes source directory: {plate_id}") from error
        if not source.is_file() or source.stat().st_size <= 0:
            raise FileNotFoundError(f"Missing Flow download: {source}")
        actual_hash = _sha256(source)
        if actual_hash != str(row.get("sha256", "")).upper():
            raise RuntimeError(f"Flow asset hash mismatch: {plate_id}")
        with Image.open(source) as image:
            if image.size not in {(1920, 1080), (2304, 1296)}:
                raise RuntimeError(
                    f"Flow asset dimensions are not a supported 16:9 source: {plate_id} -> {image.size}"
                )

        target = output_dir / f"{plate_id}.jpg"
        with Image.open(source) as image:
            needs_normalization = image.size != (2304, 1296)
        if needs_normalization:
            _atomic_normalize_copy(source, target)
        else:
            _atomic_copy(source, target)
        target_hash = _sha256(target)
        entry = dict(plate)
        entry.update({
            "path": str(target),
            "sha256": target_hash,
            "bytes": target.stat().st_size,
            "width": 2304,
            "height": 1296,
            "provider": "google_flow_cdp_playwright",
            "flow_card_id": str(row.get("card_id", "")),
        })
        updated.append(entry)
        physical_rows.append({
            "plate_id": plate_id,
            "path": str(target),
            "sha256": target_hash,
            "width": 2304,
            "height": 1296,
        })

    physical_check = validate_plate_manifest(physical_rows, expected_count=expected_count)
    if physical_check["status"] != "PASS":
        raise RuntimeError("Finalized plate validation failed: " + "; ".join(physical_check["errors"]))

    result = dict(plan)
    result["plates"] = updated
    result["provider"] = "google_flow_cdp_playwright"
    result["target_dimensions"] = {"width": 2304, "height": 1296}
    result["physical_validation"] = physical_check
    temporary = plan_path.with_suffix(plan_path.suffix + ".part")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    with open(temporary, "r+b") as handle:
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, plan_path)
    return {"status": "PASS", "plate_count": expected_count, "physical_validation": physical_check}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--asset-manifest", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=80)
    args = parser.parse_args()
    print(json.dumps(finalize_plate_plan(args.plan, args.asset_manifest, args.source_dir, args.output_dir, expected_count=args.expected_count), ensure_ascii=False))


if __name__ == "__main__":
    main()
