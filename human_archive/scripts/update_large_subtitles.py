# -*- coding: utf-8 -*-
"""Regenerate high-visibility 2x large subtitles for Himalaya GLOF Episode."""
from pathlib import Path
import json

EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
SOURCE_DIR = EP_DIR / "source"
SUBTITLES_DIR = EP_DIR / "subtitles"
CANDIDATE_DIR = EP_DIR / "candidate"

manifest = json.loads((SOURCE_DIR / "scene_script_manifest_v2.json").read_text(encoding="utf-8"))
scenes = manifest["scenes"]

def format_ass_time(sec):
    hrs = int(sec // 3600)
    mins = int((sec % 3600) // 60)
    secs = int(sec % 60)
    csecs = int(round((sec - int(sec)) * 100))
    return f"{hrs:01d}:{mins:02d}:{secs:02d}.{csecs:02d}"

# 2x Larger Premium ASS Subtitle Style (Fontsize 92px, High Contrast Black Outline 5.5, Soft Drop Shadow 2.5, MarginV 90)
ass_header = """[Script Info]
Title: Nollam File Himalaya GLOF (Large Subtitles)
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Pretendard,92,&H00FFFFFF,&H000000FF,&H0012141A,&H80000000,-1,0,0,0,100,100,0,0,1,5.5,2.5,2,100,100,90,1
Style: Highlight,Pretendard,92,&H0052D1F5,&H000000FF,&H0012141A,&H80000000,-1,0,0,0,100,100,0,0,1,5.5,2.5,2,100,100,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# Full 20m subtitles
all_events = []
# 120s pilot subtitles
pilot_events = []

for s in scenes:
    start_t = format_ass_time(s["start_sec"])
    end_t = format_ass_time(s["end_sec"])
    text = s["narration"]
    line = f"Dialogue: 0,{start_t},{end_t},Default,,0,0,0,,{text}"
    all_events.append(line)
    if s["end_sec"] <= 120.0:
        pilot_events.append(line)

(SUBTITLES_DIR / "subtitles.ass").write_text(ass_header + "\n".join(all_events), encoding="utf-8")
(CANDIDATE_DIR / "pilot_subtitles_120s.ass").write_text(ass_header + "\n".join(pilot_events), encoding="utf-8")

print(f"Updated 2x Large Subtitles: Fontsize 92px, MarginV 90, Outline 5.5 ({len(pilot_events)} pilot lines, {len(all_events)} full lines)")
