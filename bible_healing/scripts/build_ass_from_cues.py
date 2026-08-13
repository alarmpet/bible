# -*- coding: utf-8 -*-
"""Convert cues.json → ASS subtitle file (Hermes-ish bottom captions)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from paths_bh import CONFIG


def ms_to_ass(ms: int) -> str:
    # H:MM:SS.cs (centiseconds)
    cs = int(round(ms / 10))
    h = cs // 360000
    cs %= 360000
    m = cs // 6000
    cs %= 6000
    s = cs // 100
    cs %= 100
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def build_ass(job: Path) -> Path:
    policy = json.loads((CONFIG / "healing_caption_policy.json").read_text(encoding="utf-8"))
    ty = policy["typography_render"]
    cues = json.loads((job / "cues.json").read_text(encoding="utf-8"))["cues"]

    font = ty.get("fontName") or "Malgun Gothic"
    size = int(ty.get("fontSizePx_1080p") or 48)
    outline = int(ty.get("outlinePx") or 4)
    shadow = int(ty.get("shadowPx") or 2)
    margin_v = int(ty.get("marginV_px") or 72)
    margin_l = int(ty.get("marginL_px") or 80)
    margin_r = int(ty.get("marginR_px") or 80)
    primary = ty.get("primaryColour") or "&H00FFFFFF"
    outline_c = ty.get("outlineColour") or "&H00000000"
    back = ty.get("backColour") or "&H80000000"
    align = int(ty.get("alignment") or 2)

    # Scripture slightly larger style
    size_s = int(policy.get("scripture_emphasis", {}).get("fontSizePx_1080p") or size + 4)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Narrator,{font},{size},{primary},&H000000FF,{outline_c},{back},-1,0,0,0,100,100,0,0,1,{outline},{shadow},{align},{margin_l},{margin_r},{margin_v},1
Style: Scripture,{font},{size_s},{primary},&H000000FF,{outline_c},{back},-1,0,0,0,100,100,0,0,1,{outline},{shadow},{align},{margin_l},{margin_r},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for c in cues:
        style = "Scripture" if c.get("speaker") == "scripture" else "Narrator"
        text = (c.get("text") or "").replace("\n", r"\N")
        # escape ASS specials lightly
        text = text.replace("{", "(").replace("}", ")")
        events.append(
            f"Dialogue: 0,{ms_to_ass(int(c['startMs']))},{ms_to_ass(int(c['endMs']))},{style},,0,0,0,,{text}"
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
    import json

    main()
