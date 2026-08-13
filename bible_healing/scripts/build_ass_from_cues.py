# -*- coding: utf-8 -*-
"""Convert cues.json → ASS subtitle file using lock typography (96/100)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_full_audio_aligned_ass import build_ass_header, seconds_to_ass


def ms_to_ass(ms: int) -> str:
    return seconds_to_ass(int(ms) / 1000.0)


def build_ass(job: Path) -> Path:
    cues = json.loads((job / "cues.json").read_text(encoding="utf-8"))["cues"]
    header = build_ass_header()
    events = []
    for cue in cues:
        style = "Scripture" if cue.get("speaker") == "scripture" else "Narrator"
        text = (cue.get("text") or "").replace("\n", r"\N")
        text = text.replace("{", "(").replace("}", ")")
        events.append(
            f"Dialogue: 0,{ms_to_ass(int(cue['startMs']))},{ms_to_ass(int(cue['endMs']))},{style},,0,0,0,,{text}"
        )

    out = job / "subtitles-timed-ko.ass"
    out.write_text(header + "\n".join(events) + "\n", encoding="utf-8-sig")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    p = build_ass(Path(args.job).resolve())
    print(json.dumps({"ok": True, "ass": str(p)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
