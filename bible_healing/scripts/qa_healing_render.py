# -*- coding: utf-8 -*-
"""QA gates G1–G3 for timed captions + basic render report."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths_bh import CONFIG  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    job = Path(args.job).resolve()
    policy = json.loads((CONFIG / "healing_caption_policy.json").read_text(encoding="utf-8"))
    max_chars = int(policy["display"]["maxDisplayCharacters"])
    min_ms = int(float(policy["display"]["minDisplaySeconds"]) * 1000)

    cues = json.loads((job / "cues.json").read_text(encoding="utf-8"))["cues"]
    blocks = []
    warns = []
    for c in cues:
        if len(c["text"]) > max_chars:
            blocks.append(f"G1 maxLineChars {len(c['text'])}>{max_chars}: {c['text']}")
        dur = int(c["endMs"]) - int(c["startMs"])
        if dur < min_ms - 100:
            warns.append(f"G3 short cue {dur}ms: {c['text']}")
        if "\n" in c["text"] and c["text"].count("\n") >= int(policy["display"].get("maxLines") or 2):
            blocks.append(f"G2 too many lines: {c['text']}")

    plain = job / "reports" / "plain_bg_report.json"
    if plain.exists():
        pr = json.loads(plain.read_text(encoding="utf-8"))
        if pr.get("text_in_image"):
            blocks.append("G5 text_in_image true")
    else:
        warns.append("plain_bg_report missing")

    report = {
        "ok": len(blocks) == 0,
        "blocks": blocks,
        "warns": warns[:30],
        "cue_count": len(cues),
        "maxDisplayCharacters": max_chars,
    }
    (job / "reports" / "qa_healing_render.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if blocks:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
