# -*- coding: utf-8 -*-
"""Estimate episode duration from segment char counts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths_bh import CONFIG, episode_dir  # noqa: E402


def estimate(episode_id: str) -> dict:
    cfg = yaml.safe_load((CONFIG / "duration_healing.yaml").read_text(encoding="utf-8"))
    segs = json.loads(
        (episode_dir(episode_id) / "script_segments.json").read_text(encoding="utf-8")
    )
    cpm_n = cfg["chars_per_minute"]["narrator"]
    cpm_s = cfg["chars_per_minute"]["scripture"]
    silence = cfg.get("silence_overhead_ratio", 0.08)

    narr_chars = sum(len(s["text"]) for s in segs if s["speaker"] == "narrator")
    script_chars = sum(len(s["text"]) for s in segs if s["speaker"] == "scripture")
    speak_min = narr_chars / cpm_n + script_chars / cpm_s
    total_min = speak_min * (1 + silence)

    report = {
        "episode": episode_id,
        "narrator_chars": narr_chars,
        "scripture_chars": script_chars,
        "total_chars": narr_chars + script_chars,
        "speak_minutes": round(speak_min, 1),
        "with_silence_minutes": round(total_min, 1),
        "target": cfg["target_minutes"],
        "range": [cfg["min_minutes"], cfg["max_minutes"]],
        "in_range": cfg["min_minutes"] <= total_min <= cfg["max_minutes"],
        "delta_to_target": round(total_min - cfg["target_minutes"], 1),
        "hint": (
            "OK"
            if cfg["min_minutes"] <= total_min <= cfg["max_minutes"]
            else (
                "ADD_NARRATION_OR_VERSES"
                if total_min < cfg["min_minutes"]
                else "TRIM_NARRATION"
            )
        ),
    }
    out = episode_dir(episode_id) / "duration_estimate.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", default="ep01_anxious_night")
    args = ap.parse_args()
    estimate(args.episode)


if __name__ == "__main__":
    main()
