"""Create a disposable six-scene audio smoke job for first-minute timing."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def build(source: Path, destination: Path, count: int = 6) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    scenes = json.loads((source / "scenes.json").read_text(encoding="utf-8"))[:count]
    (destination / "scenes.json").write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")
    for name in ("voice_map.json", "render-options.json"):
        path = source / name
        if path.exists():
            shutil.copy2(path, destination / name)
    (destination / "job.json").write_text(json.dumps({"type": "hook_smoke", "scene_count": len(scenes)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "job": str(destination), "scenes": len(scenes)}, ensure_ascii=False))
    return destination


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--destination", type=Path, required=True)
    args = ap.parse_args()
    build(args.source, args.destination)
