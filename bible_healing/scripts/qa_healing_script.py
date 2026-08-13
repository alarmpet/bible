# -*- coding: utf-8 -*-
"""QA gates for healing dual-speaker scripts."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths_bh import episode_dir  # noqa: E402
from verse_lib import get_text  # noqa: E402

FORBIDDEN = [
    r"병을\s*고칩니다",
    r"반드시\s*치유",
    r"치료\s*대체",
    r"안\s*믿으면",
    r"저주",
    r"지옥에\s*떨어",
    r"기적처럼\s*나을",
]


def qa(episode_id: str) -> dict:
    d = episode_dir(episode_id)
    segs = json.loads((d / "script_segments.json").read_text(encoding="utf-8"))
    blocks = []
    warns = []

    speakers = {s["speaker"] for s in segs}
    if "narrator" not in speakers or "scripture" not in speakers:
        blocks.append("Q5: missing narrator or scripture speaker")

    for s in segs:
        text = s.get("text") or ""
        if not text.strip():
            blocks.append(f"empty text: {s.get('seg_id')}")
        # Forbidden claims apply to original narration only (not KRV scripture text)
        if s["speaker"] == "narrator":
            for pat in FORBIDDEN:
                if re.search(pat, text):
                    blocks.append(f"Q3/Q4 forbidden pattern in {s.get('seg_id')}: {pat}")

        if s["speaker"] == "scripture":
            ref = s.get("ref")
            if not ref:
                blocks.append(f"Q1 scripture without ref: {s.get('seg_id')}")
                continue
            try:
                db_text = get_text(ref)
            except Exception as e:
                blocks.append(f"Q1 verse lookup fail {ref}: {e}")
                continue
            # normalize whitespace for compare
            a = re.sub(r"\s+", "", text)
            b = re.sub(r"\s+", "", db_text)
            if a != b:
                blocks.append(
                    f"Q1 text mismatch {s.get('seg_id')} ref={ref} "
                    f"(script {len(a)} vs db {len(b)})"
                )

    total_chars = sum(len(s["text"]) for s in segs)
    # Prefer duration_estimate.json if present; else blended ~340 cpm soft check
    est_path = d / "duration_estimate.json"
    if est_path.exists():
        est_min = json.loads(est_path.read_text(encoding="utf-8")).get(
            "with_silence_minutes", total_chars / 340
        )
    else:
        est_min = total_chars / 340
    if est_min < 80 or est_min > 120:
        warns.append(f"Q6 duration estimate {est_min:.1f} min outside 80–120 (chars={total_chars})")

    # unit structure: each unit should have modern empathy (after) — check unit counts
    units = {s["unit"] for s in segs if str(s["unit"]).startswith("u")}
    if len(units) < 10:
        warns.append(f"Q7 few units: {len(units)}")

    report = {
        "ok": len(blocks) == 0,
        "blocks": blocks,
        "warns": warns,
        "segment_count": len(segs),
        "total_chars": total_chars,
        "est_minutes_blended": round(est_min, 1),
    }
    (d / "qa_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if blocks:
        raise SystemExit(1)
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", default="ep01_anxious_night")
    args = ap.parse_args()
    qa(args.episode)


if __name__ == "__main__":
    main()
