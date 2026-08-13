# -*- coding: utf-8 -*-
"""Pack full ep01 hermes job from script_segments + voice defaults."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    episode = "ep01_anxious_night"
    segs = json.loads(
        (ROOT / "runs" / episode / "script_segments.json").read_text(encoding="utf-8")
    )
    # drop rest layer for cleaner duration/quality (optional: keep)
    segs = [s for s in segs if not str(s.get("seg_id", "")).endswith("_rest")]
    vc = yaml.safe_load((ROOT / "config" / "voice_healing.yaml").read_text(encoding="utf-8"))
    out = ROOT / "runs" / episode / "hermes_jobs" / "full"
    out.mkdir(parents=True, exist_ok=True)

    scenes = []
    for i, s in enumerate(segs, 1):
        scenes.append(
            {
                "scene_id": s["seg_id"],
                "order": i,
                "source_order": i,
                "chapter": 1,
                "title": s.get("title") or s["seg_id"],
                "outputMode": "image",
                "narration": s["text"],
                "segments": [
                    {
                        "speaker": s["speaker"],
                        "text": s["text"],
                        "seg_id": f"{s['seg_id']}_01",
                        "ref": s.get("ref"),
                    }
                ],
                "image": f"scene_{i}_flow.jpg",
                "meta": {
                    "unit": s["unit"],
                    "speaker": s["speaker"],
                    "ref": s.get("ref"),
                    "ref_label": s.get("ref_label"),
                },
            }
        )

    def spk(key: str) -> dict:
        c = vc["speakers"][key]
        d = {
            "label": c["label"],
            "voice": c["voice"],
            "speed": c["speed"],
            "total_step": c["total_step"],
            "silence_duration": c["silence_duration"],
            "audio_filter": "",
        }
        if c.get("max_chunk_length") is not None:
            d["max_chunk_length"] = c["max_chunk_length"]
        return d

    vm = {
        "schema_version": "1.0",
        "engine": "supertonic3",
        "preview_approved": True,
        "notes": "full ep01 defaults F5/M5",
        "speakers": {"narrator": spk("narrator"), "scripture": spk("scripture")},
        "rules": {
            "narration_default_speaker": "narrator",
            "narrator_must_not_share_voice_with_characters": True,
        },
        "sample_lines": vc.get("sample_lines") or {},
    }

    (out / "scenes.json").write_text(
        json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "voice_map.json").write_text(
        json.dumps(vm, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    draft = {
        "title": "불안한 밤을 위한 말씀",
        "scenes": [
            {
                "order": sc["order"],
                "narration": sc["narration"],
                "outputMode": "image",
                "flowOutputMode": "image",
                "section": "main",
                "chapter": 1,
                "scene_id": sc["scene_id"],
                "title": sc["title"],
            }
            for sc in scenes
        ],
    }
    (out / "draft.json").write_text(
        json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "job.json").write_text(
        json.dumps(
            {
                "type": "bible_healing_full",
                "episode": episode,
                "scene_count": len(scenes),
                "chars": sum(len(s["text"]) for s in segs),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (out / "reports").mkdir(exist_ok=True)
    print(
        json.dumps(
            {
                "ok": True,
                "job": str(out),
                "scenes": len(scenes),
                "chars": sum(len(s["text"]) for s in segs),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
