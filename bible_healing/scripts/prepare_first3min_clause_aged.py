# -*- coding: utf-8 -*-
"""Pack a 10-scene first-3-minute job from the current full scenes + lock voices."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "runs" / "ep01_anxious_night" / "hermes_jobs" / "full"
DST = ROOT / "runs" / "ep01_anxious_night" / "hermes_jobs" / "first3min_clause_aged"


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    scenes = json.loads((SRC / "scenes.json").read_text(encoding="utf-8"))[:10]
    for i, scene in enumerate(scenes, 1):
        scene["order"] = i
    vc = yaml.safe_load((ROOT / "config" / "voice_healing.yaml").read_text(encoding="utf-8"))

    def speaker(key: str) -> dict:
        c = vc["speakers"][key]
        d = {
            "label": c["label"],
            "voice": c["voice"],
            "speed": c["speed"],
            "total_step": c["total_step"],
            "silence_duration": c["silence_duration"],
            "audio_filter": c.get("audio_filter") or "",
        }
        if c.get("max_chunk_length") is not None:
            d["max_chunk_length"] = c["max_chunk_length"]
        return d

    vm = {
        "schema_version": "1.0",
        "engine": "supertonic3",
        "preview_approved": True,
        "notes": "first3min clause-punctuated aged M4",
        "speakers": {"narrator": speaker("narrator"), "scripture": speaker("scripture")},
        "sample_lines": vc.get("sample_lines") or {},
    }
    (DST / "scenes.json").write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")
    (DST / "voice_map.json").write_text(json.dumps(vm, ensure_ascii=False, indent=2), encoding="utf-8")
    (DST / "reports").mkdir(exist_ok=True)
    print(json.dumps({"ok": True, "job": str(DST), "scenes": len(scenes)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
