"""Build a first-minute smoke job with one alternate scripture voice."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def build(source: Path, destination: Path, voice: str, speed: float, silence: float) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    scenes = json.loads((source / "scenes.json").read_text(encoding="utf-8"))[:6]
    (destination / "scenes.json").write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")
    voice_map = json.loads((source / "voice_map.json").read_text(encoding="utf-8"))
    voice_map["speakers"]["scripture"].update({"voice": voice, "speed": speed, "silence_duration": silence, "total_step": 20})
    (destination / "voice_map.json").write_text(json.dumps(voice_map, ensure_ascii=False, indent=2), encoding="utf-8")
    (destination / "draft.json").write_text(json.dumps({"scenes": [{"order": i + 1, "scene_id": s["scene_id"], "narration": s["narration"]} for i, s in enumerate(scenes)]}, ensure_ascii=False, indent=2), encoding="utf-8")
    (destination / "job.json").write_text(json.dumps({"type": "voice_candidate_smoke", "voice": voice, "speed": speed, "silence": silence, "scene_count": len(scenes)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "job": str(destination), "voice": voice, "scenes": len(scenes)}, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--destination", type=Path, required=True)
    ap.add_argument("--voice", default="M3")
    ap.add_argument("--speed", type=float, default=0.76)
    ap.add_argument("--silence", type=float, default=0.48)
    args = ap.parse_args()
    build(args.source, args.destination, args.voice, args.speed, args.silence)
