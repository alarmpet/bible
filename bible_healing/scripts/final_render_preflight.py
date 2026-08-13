# -*- coding: utf-8 -*-
"""Fail-fast checks required before a *preview* final render (first3min path).

NOTE (본편 / full release):
  Use media_rules_preflight.py --job <full> as the canonical full-job gate.
  This script remains for actual_first3min_pause_split / policy-based segment
  checks referenced by older docs; it is not the full 50-min release gate.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "bible_healing/config/final_render_policy.json"
DEFAULT_JOB = (
    ROOT / "bible_healing/runs/ep01_anxious_night/hermes_jobs/actual_first3min_pause_split"
)


def run_checks(job: Path, policy_path: Path = POLICY) -> dict:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    scenes = json.loads((job / "scenes.json").read_text(encoding="utf-8"))
    allowed = set(policy["speakers"])
    bad: list[str] = []
    segment_count = 0
    for scene in scenes:
        for seg in scene.get("segments", []):
            segment_count += 1
            speaker = seg.get("speaker")
            text = (seg.get("text") or "").strip()
            if speaker not in allowed:
                bad.append(f"speaker:{speaker}")
            if not text:
                bad.append(f"empty:{seg.get('seg_id')}")
            if speaker == "scripture":
                if re.search(r"[()]|셀라|첼라|다윗의 시|영장으로|!", text):
                    bad.append(f"unclean_scripture:{seg.get('seg_id')}")
            wav = (
                job
                / "segments"
                / f"{seg.get('seg_id')}_{speaker}_{'M4' if speaker == 'scripture' else 'F5'}.wav"
            )
            if not wav.exists():
                bad.append(f"missing_audio:{wav.name}")
    return {
        "policy": str(policy_path),
        "job": str(job),
        "segments": segment_count,
        "errors": bad,
        "ok": not bad,
        "note": "For full-job release gates use media_rules_preflight.py --job <full>",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "First3min/policy preflight. "
            "For 본편 full job use media_rules_preflight.py --job instead."
        )
    )
    ap.add_argument(
        "--job",
        default=str(DEFAULT_JOB),
        help="Job directory (default: actual_first3min_pause_split)",
    )
    ap.add_argument("--policy", default=str(POLICY))
    args = ap.parse_args(argv)
    result = run_checks(Path(args.job), Path(args.policy))
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
