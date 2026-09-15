# -*- coding: utf-8 -*-
"""Dynamic Subtitle Compiler Engine v3 for 20-minute master documentary.
Enforces:
1. 56pt Pretendard Bold typography (addressing '자막은 너무 작고').
2. Strict 2-line maximum rule (assert text.count(r"\\N") <= 1).
3. Recalibrated Dynamic Programming line-break splitter targeting 18~25 chars per line.
4. Continuous temporal coverage with dynamic lead-in/lead-out buffers."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
MANIFEST_PATH = EP_DIR / "generation" / "master_sentence_aligned_manifest.json"
ASS_OUTPUT = EP_DIR / "candidate" / "pilot_subtitles_1200s.ass"
ASS_BACKUP = EP_DIR / "subtitles" / "subtitles_dynamic_v3.ass"

def seconds_to_ass(s: float) -> str:
    cs = int(round(s * 100))
    m, cs = divmod(cs, 6000)
    h, m = divmod(m, 60)
    s_int, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s_int:02d}.{cs:02d}"

def split_sentence_for_56pt(text: str, max_single_line: int = 22) -> list[str]:
    """Split sentence into 1 or 2 clauses, each having at most 2 lines, targeting 18~24 chars."""
    text = text.strip()
    text = re.sub(r"\(([A-Za-z\s]+)\)", "", text) # strip english gloss
    
    if len(text) <= max_single_line:
        return [text]

    # If sentence is long (> 42 chars) and has a major comma clause break, split into two events
    if len(text) > 42 and "," in text:
        parts = text.split(",", 1)
        c1 = parts[0].strip() + ","
        c2 = parts[1].strip()
        clauses = [c1, c2]
    else:
        clauses = [text]

    out_events = []
    for c in clauses:
        if len(c) <= max_single_line:
            out_events.append(c)
        else:
            words = c.split()
            if len(words) <= 1:
                out_events.append(c)
                continue
            best_max = 999
            best_idx = 1
            for i in range(1, len(words)):
                l1 = " ".join(words[:i])
                l2 = " ".join(words[i:])
                m = max(len(l1), len(l2))
                if words[i-1].endswith(","):
                    m -= 2
                if m < best_max:
                    best_max = m
                    best_idx = i
            line1 = " ".join(words[:best_idx])
            line2 = " ".join(words[best_idx:])
            out_events.append(line1 + r"\N" + line2)

    return out_events

def compile_subtitles_v3():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    sentences = data["sentences"]
    print(f"Compiling 56pt ASS subtitles v3 from {len(sentences)} sentence items...")

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: DocuNarrator,Pretendard,56,&H00FFFFFF,&H000000FF,&H000C0C12,&H90000000,-1,0,0,0,100,100,0,0,1,4.5,2.5,2,140,140,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    
    for i, item in enumerate(sentences):
        raw_text = item["display_text"].strip()
        sub_events = split_sentence_for_56pt(raw_text)
        
        t_start = max(0.0, item["speech_start"] - 0.05)
        t_end = min(item["scene_end"], item["speech_end"] + 0.15)
        total_dur = max(0.8, t_end - t_start)
        
        # Allocate sub-event timing if split into multiple clauses
        if len(sub_events) == 1:
            txt = sub_events[0]
            assert txt.count(r"\N") <= 1, f"Violated 2-line rule: {txt}"
            start_ass = seconds_to_ass(t_start)
            end_ass = seconds_to_ass(t_end)
            events.append(f"Dialogue: 0,{start_ass},{end_ass},DocuNarrator,,0,0,0,,{txt}")
        else:
            lens = [len(x) for x in sub_events]
            sum_l = sum(lens)
            cur_t = t_start
            for idx, txt in enumerate(sub_events):
                dur_ev = total_dur * (lens[idx] / sum_l)
                ev_start = cur_t
                ev_end = cur_t + dur_ev
                if idx < len(sub_events) - 1:
                    ev_end = max(ev_start + 0.4, ev_end - 0.02)
                assert txt.count(r"\N") <= 1, f"Violated 2-line rule: {txt}"
                start_ass = seconds_to_ass(ev_start)
                end_ass = seconds_to_ass(ev_end)
                events.append(f"Dialogue: 0,{start_ass},{end_ass},DocuNarrator,,0,0,0,,{txt}")
                cur_t = ev_end + 0.02

    full_ass = header + "\n".join(events) + "\n"
    ASS_OUTPUT.write_text(full_ass, encoding="utf-8-sig")
    ASS_BACKUP.write_text(full_ass, encoding="utf-8-sig")
    print(f"Generated {len(events)} ASS subtitle events (56pt): {ASS_OUTPUT}")

if __name__ == "__main__":
    compile_subtitles_v3()
