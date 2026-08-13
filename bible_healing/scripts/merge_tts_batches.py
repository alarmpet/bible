"""Merge completed TTS batch outputs into one full job without hiding gaps."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def merge(batch_root: Path, full_job: Path, expected_scene_count: int) -> dict:
    items: dict[int, dict] = {}
    for batch in sorted(batch_root.glob("batch_*")):
        manifest_path = batch / "scene_audio_manifest.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rows = manifest.get("scenes") or manifest.get("items") or []
        for row in rows:
            order = int(row["order"])
            if order in items:
                raise ValueError(f"duplicate scene order: {order}")
            items[order] = row
        for wav in batch.glob("scene_*.wav"):
            shutil.copy2(wav, full_job / wav.name)
    missing = [i for i in range(1, expected_scene_count + 1) if i not in items]
    if missing:
        raise ValueError(f"missing scene orders: {missing[:10]}")
    ordered = [items[i] for i in range(1, expected_scene_count + 1)]
    out = {"ok": True, "schemaVersion": 2, "status": "batch-merged-unlocked", "scene_count": expected_scene_count, "items": ordered}
    (full_job / "scene_audio_manifest.batch_merged.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "scene_count": expected_scene_count, "manifest": str(full_job / "scene_audio_manifest.batch_merged.json"), "missing": missing}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-root", type=Path, required=True)
    ap.add_argument("--full-job", type=Path, required=True)
    ap.add_argument("--scene-count", type=int, required=True)
    args = ap.parse_args()
    args.full_job.mkdir(parents=True, exist_ok=True)
    print(json.dumps(merge(args.batch_root, args.full_job, args.scene_count), ensure_ascii=False))
