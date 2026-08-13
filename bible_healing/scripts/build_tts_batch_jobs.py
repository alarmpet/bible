"""Split a Hermes scene job into resumable TTS batches."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def build_batches(source: Path, destination: Path, batch_size: int = 20) -> list[Path]:
    scenes = json.loads((source / "scenes.json").read_text(encoding="utf-8"))
    destination.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for start in range(0, len(scenes), batch_size):
        batch_no = start // batch_size + 1
        out = destination / f"batch_{batch_no:03d}"
        out.mkdir(parents=True, exist_ok=True)
        subset = scenes[start : start + batch_size]
        (out / "scenes.json").write_text(json.dumps(subset, ensure_ascii=False, indent=2), encoding="utf-8")
        for name in ("voice_map.json", "render-options.json"):
            if (source / name).exists():
                shutil.copy2(source / name, out / name)
        (out / "draft.json").write_text(json.dumps({"scenes": [{"order": i + 1, "scene_id": s["scene_id"], "narration": s["narration"]} for i, s in enumerate(subset)]}, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "job.json").write_text(json.dumps({"type": "tts_batch", "batch": batch_no, "source_start_order": start + 1, "source_end_order": start + len(subset), "scene_count": len(subset)}, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append(out)
    index = {"source": str(source), "batch_size": batch_size, "scene_count": len(scenes), "batches": [str(p) for p in outputs]}
    (destination / "batches.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return outputs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--destination", type=Path, required=True)
    ap.add_argument("--batch-size", type=int, default=20)
    args = ap.parse_args()
    result = build_batches(args.source, args.destination, args.batch_size)
    print(json.dumps({"ok": True, "batches": len(result), "scene_count": sum(len(json.loads((p / "scenes.json").read_text(encoding="utf-8"))) for p in result)}, ensure_ascii=False))
