# -*- coding: utf-8 -*-
"""Build ~5min dual-voice job: opening + u01 (no rest), F_10 / M_10 voices."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs" / "ep01_anxious_night" / "hermes_jobs" / "sample5_F10_M10"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    segs = json.loads(
        (ROOT / "runs" / "ep01_anxious_night" / "script_segments.json").read_text(
            encoding="utf-8"
        )
    )
    # opening + u01 + u02 (no rest) ≈ 5–7 min depending on voice speed
    keep = [
        s
        for s in segs
        if s["unit"] in ("opening", "u01", "u02")
        and not str(s.get("seg_id", "")).endswith("_rest")
    ]
    vc = yaml.safe_load((ROOT / "config" / "voice_healing.yaml").read_text(encoding="utf-8"))

    scenes = []
    for i, s in enumerate(keep, 1):
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

    (OUT / "scenes.json").write_text(
        json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    def spk(key: str) -> dict:
        c = vc["speakers"][key]
        return {
            "label": c["label"],
            "voice": c["voice"],
            "speed": c["speed"],
            "total_step": c["total_step"],
            "silence_duration": c["silence_duration"],
            "audio_filter": "",
        }

    vm = {
        "schema_version": "1.0",
        "engine": "supertonic3",
        "preview_approved": False,
        "notes": "casting F_10=F5@0.95 / M_10=M5@0.87 ~5min opening+u01",
        "speakers": {"narrator": spk("narrator"), "scripture": spk("scripture")},
        "rules": {
            "narration_default_speaker": "narrator",
            "narrator_must_not_share_voice_with_characters": True,
        },
        "sample_lines": vc.get("sample_lines") or {},
    }
    (OUT / "voice_map.json").write_text(
        json.dumps(vm, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    draft = {
        "title": "voice sample 5min F10/M10",
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
    (OUT / "draft.json").write_text(
        json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "job.json").write_text(
        json.dumps(
            {
                "type": "bible_healing_voice_sample",
                "female": "F_10 (F5@0.95)",
                "male": "M_10 (M5@0.87)",
                "scene_count": len(scenes),
                "chars": sum(len(s["text"]) for s in keep),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (OUT / "reports").mkdir(exist_ok=True)

    # readable script
    md = ["# 5분 샘플 대본 — F_10 + M_10", ""]
    for s in keep:
        md.append(f"### [{s['speaker']}] {s.get('title') or s['seg_id']}")
        if s.get("ref_label"):
            md.append(f"*{s['ref_label']}*")
        md.append(s["text"])
        md.append("")
    (OUT / "script_sample5.md").write_text("\n".join(md), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "job": str(OUT),
                "scenes": len(scenes),
                "chars": sum(len(s["text"]) for s in keep),
                "voices": {
                    "narrator": vm["speakers"]["narrator"]["voice"],
                    "scripture": vm["speakers"]["scripture"]["voice"],
                },
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
