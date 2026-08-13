# -*- coding: utf-8 -*-
"""Pack healing script into a Hermes-compatible job."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths_bh import CONFIG, episode_dir, job_dir  # noqa: E402


def scene_meta_from_segment(segment: dict) -> dict:
    meta = {"unit": segment["unit"], "speaker": segment["speaker"], "ref": segment.get("ref"), "ref_label": segment.get("ref_label")}
    if segment.get("hook_phase") is not None:
        meta["hook_phase"] = segment["hook_phase"]
    return meta


def pack(episode_id: str, mode: str = "full", smoke_units: int | None = None) -> Path:
    ep_dir = episode_dir(episode_id)
    segs = json.loads((ep_dir / "script_segments.json").read_text(encoding="utf-8"))
    voice_cfg = yaml.safe_load((CONFIG / "voice_healing.yaml").read_text(encoding="utf-8"))
    manifest = json.loads((ep_dir / "episode_manifest.json").read_text(encoding="utf-8"))
    if smoke_units is not None:
        keep_units = {"opening"}
        content_ids = []
        for s in segs:
            u = s["unit"]
            if str(u).startswith("u") and u not in content_ids:
                content_ids.append(u)
        keep_units.update(content_ids[:smoke_units])
        segs = [s for s in segs if s["unit"] in keep_units]

    scenes = []
    for i, s in enumerate(segs, 1):
        scenes.append({"scene_id": s["seg_id"], "order": i, "source_order": i, "chapter": 1, "title": s.get("title") or s["seg_id"], "outputMode": "image", "narration": s["text"], "segments": [{"speaker": s["speaker"], "text": s["text"], "seg_id": f"{s['seg_id']}_01", "ref": s.get("ref")}], "image": f"scene_{i}_flow.jpg", "meta": scene_meta_from_segment(s)})
    jdir = job_dir(episode_id, mode if smoke_units is None else "preview")
    jdir.mkdir(parents=True, exist_ok=True)
    (jdir / "scenes.json").write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")
    vm = {"schema_version": "1.0", "engine": voice_cfg.get("engine", "supertonic3"), "preview_approved": bool(voice_cfg.get("preview_approved", False)), "notes": "bible_healing: narrator=여성 점잖음, scripture=말씀 보이스. 공유 금지.", "speakers": {"narrator": dict(voice_cfg["speakers"]["narrator"]), "scripture": dict(voice_cfg["speakers"]["scripture"])}, "rules": {"narration_default_speaker": "narrator", "narrator_must_not_share_voice_with_characters": True}, "sample_lines": dict(voice_cfg.get("sample_lines") or {})}
    for sid, conf in list(vm["speakers"].items()):
        vm["speakers"][sid] = {"label": conf.get("label", sid), "voice": conf["voice"], "speed": conf.get("speed", 1.0), "total_step": conf.get("total_step", 8), "silence_duration": conf.get("silence_duration", 0.2), "audio_filter": conf.get("audio_filter", "")}
    (jdir / "voice_map.json").write_text(json.dumps(vm, ensure_ascii=False, indent=2), encoding="utf-8")
    job = {"type": "bible_healing", "episode_id": episode_id, "mode": jdir.name, "title": manifest.get("title_ko"), "scene_count": len(scenes), "translation": "KRV", "disclaimer": "healing narration; not medical advice"}
    (jdir / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    (jdir / "reports").mkdir(exist_ok=True)
    report = {"ok": True, "scenes": len(scenes), "speakers": list(vm["speakers"].keys()), "voices": {k: v["voice"] for k, v in vm["speakers"].items()}}
    (jdir / "reports" / "pack_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "job": str(jdir), **report}, ensure_ascii=False))
    return jdir


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", default="ep01_anxious_night")
    ap.add_argument("--mode", default="full")
    ap.add_argument("--smoke-units", type=int, default=None)
    args = ap.parse_args()
    pack(args.episode, args.mode, args.smoke_units)


if __name__ == "__main__":
    main()
