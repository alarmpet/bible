# -*- coding: utf-8 -*-
"""Verification gate: Enforce 0% image reuse across all shots in documentary episode."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Force UTF-8 on Windows stdout
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")



def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def verify_zero_reuse(run_dir: Path) -> bool:
    run_dir = Path(run_dir).resolve()
    script_file = run_dir / "full_script_68shots.json"
    if not script_file.exists():
        script_file = run_dir / "full_script_36shots.json"
    if not script_file.exists():
        script_file = run_dir / "flow_image_prompts.json"

    data = json.loads(script_file.read_text(encoding="utf-8"))
    shots = data.get("shots", [])
    images_dir = run_dir / "images"

    seen_hashes: dict[str, str] = {}
    seen_names: dict[str, str] = {}
    missing_shots: list[str] = []
    duplicate_shots: list[tuple[str, str, str]] = []

    for item in shots:
        shot_id = item["shot_id"]
        # Find exact image
        img_path = images_dir / f"{shot_id}.jpg"
        if not img_path.exists():
            img_path = images_dir / f"{shot_id}.png"

        if not img_path.exists():
            missing_shots.append(shot_id)
            continue

        fhash = file_sha256(img_path)
        if fhash in seen_hashes:
            orig_shot = seen_hashes[fhash]
            duplicate_shots.append((orig_shot, shot_id, img_path.name))
        else:
            seen_hashes[fhash] = shot_id

        if img_path.name in seen_names:
            orig_shot = seen_names[img_path.name]
            duplicate_shots.append((orig_shot, shot_id, img_path.name))
        else:
            seen_names[img_path.name] = shot_id

    print("=" * 60)
    print(f" ZERO IMAGE REUSE VERIFICATION: {data.get('title')}")
    print(f" Total Shots: {len(shots)}")
    print(f" Images Found: {len(seen_hashes)} / {len(shots)}")
    print("=" * 60)

    if missing_shots:
        print(f"\n[FAIL] Missing dedicated image files for {len(missing_shots)} shots:")
        for m in missing_shots:
            print(f"  - {m}.jpg (Expected in {images_dir})")

    if duplicate_shots:
        print(f"\n[FAIL] Image recycling detected ({len(duplicate_shots)} duplicates):")
        for orig, dup, fname in duplicate_shots:
            print(f"  - Shot '{dup}' reused image '{fname}' from Shot '{orig}'!")

    if missing_shots or duplicate_shots:
        print("\n❌ GATE RESULT: BLOCK (Every shot must have a unique 1:1 dedicated image)")
        return False

    print("\n✅ GATE RESULT: PASS (100% 1:1 Unique Semantic Image Mapping Verified)")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default="human_archive/runs/ep01_pompeii_18hours")
    args = ap.parse_args()
    ok = verify_zero_reuse(Path(args.run_dir))
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
