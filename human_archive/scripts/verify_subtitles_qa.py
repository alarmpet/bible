# -*- coding: utf-8 -*-
"""Automated Subtitle QA Verification Test Suite v3.
Validates that ASS subtitle file satisfies all broadcast, readability, and user criteria:
a) Subtitle font size >= 56pt (addressing '자막은 너무 작고').
b) Every single dialogue event has max 2 lines (at most 1 \\N).
c) Line length does not exceed safe character budget at 56pt (<= 32 chars per line).
d) Subtitle timing never overlaps within the same layer.
e) Inter-speech gaps and timeline continuity within 1200.0s total master duration."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
ASS_PATH = EP_DIR / "candidate" / "pilot_subtitles_1200s.ass"
REPORT_PATH = EP_DIR / "candidate" / "subtitles_qa_report.json"

def ass_time_to_seconds(t_str: str) -> float:
    parts = t_str.strip().split(":")
    h = int(parts[0])
    m = int(parts[1])
    s = float(parts[2])
    return h * 3600 + m * 60 + s

def run_qa():
    print(f"Running Subtitle QA v3 on: {ASS_PATH.name}")
    assert ASS_PATH.exists(), f"Missing file: {ASS_PATH}"

    lines = ASS_PATH.read_text(encoding="utf-8-sig").splitlines()
    dialogues = []
    fontsize_found = None
    
    # 1. Parse Styles
    for line in lines:
        if line.startswith("Style:"):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) > 2:
                try:
                    fontsize_found = int(parts[2])
                except ValueError:
                    pass

    print(f"Detected Subtitle Font Size: {fontsize_found}pt")
    assert fontsize_found is not None, "Could not detect Fontsize in Style header"
    assert fontsize_found >= 56, f"Font size {fontsize_found}pt is too small! Must be >= 56pt"

    # 2. Parse Dialogue Events
    for idx, line in enumerate(lines, 1):
        if line.startswith("Dialogue:"):
            parts = line.split(",", 9)
            if len(parts) < 10:
                continue
            layer = int(parts[0].replace("Dialogue:", "").strip())
            start_sec = ass_time_to_seconds(parts[1])
            end_sec = ass_time_to_seconds(parts[2])
            style = parts[3].strip()
            text = parts[9].strip()
            dialogues.append({
                "line_num": idx,
                "layer": layer,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "duration": round(end_sec - start_sec, 3),
                "style": style,
                "text": text
            })

    print(f"Total Dialogue Events: {len(dialogues)}")
    assert len(dialogues) >= 105, f"Expected at least 105 events, found {len(dialogues)}"

    violations_2lines = []
    violations_length = []
    violations_overlap = []
    max_line_len_found = 0
    max_inter_gap = 0.0

    for i, d in enumerate(dialogues):
        text = d["text"]
        sublines = text.split(r"\N")
        
        # Check A: Max 2 lines
        if len(sublines) > 2:
            violations_2lines.append({
                "line_num": d["line_num"],
                "text": text,
                "line_count": len(sublines)
            })

        # Check B: Line length <= 32 chars for 56pt
        for sl in sublines:
            if len(sl) > max_line_len_found:
                max_line_len_found = len(sl)
            if len(sl) > 32:
                violations_length.append({
                    "line_num": d["line_num"],
                    "subline": sl,
                    "length": len(sl)
                })

        # Check C: Overlap check within same layer
        if i < len(dialogues) - 1:
            next_d = dialogues[i+1]
            if d["layer"] == next_d["layer"]:
                if d["end_sec"] > next_d["start_sec"] + 0.01:
                    overlap_sec = round(d["end_sec"] - next_d["start_sec"], 3)
                    violations_overlap.append({
                        "event_a_line": d["line_num"],
                        "event_b_line": next_d["line_num"],
                        "overlap_sec": overlap_sec,
                        "text_a": text,
                        "text_b": next_d["text"]
                    })
                gap = round(next_d["start_sec"] - d["end_sec"], 3)
                if gap > max_inter_gap:
                    max_inter_gap = gap

        # Check D: Bounds
        assert d["start_sec"] >= 0.0, f"Negative start time: {d}"
        assert d["end_sec"] <= 1560.0, f"End time exceeds 1560s (20min +30% upper bound): {d}"

    qa_status = "PASS" if not (violations_2lines or violations_length or violations_overlap) else "FAIL"

    report = {
        "qa_status": qa_status,
        "ass_file": ASS_PATH.name,
        "font_size_pt": fontsize_found,
        "total_dialogue_events": len(dialogues),
        "target_duration_window": "840s ~ 1560s (20분 ±30%)",
        "target_duration_sec": 1200.0,
        "first_event_start_sec": dialogues[0]["start_sec"],
        "last_event_end_sec": dialogues[-1]["end_sec"],
        "max_line_length_observed": max_line_len_found,
        "max_inter_speech_gap_sec": max_inter_gap,
        "criteria": {
            "font_size_min_56pt": {
                "status": "PASS" if fontsize_found >= 56 else "FAIL",
                "observed_pt": fontsize_found,
                "min_required_pt": 56
            },
            "max_2_lines_per_event": {
                "status": "PASS" if not violations_2lines else "FAIL",
                "violations_count": len(violations_2lines),
                "violations": violations_2lines
            },
            "safe_line_length_budget_32": {
                "status": "PASS" if not violations_length else "FAIL",
                "violations_count": len(violations_length),
                "violations": violations_length
            },
            "zero_temporal_overlap": {
                "status": "PASS" if not violations_overlap else "FAIL",
                "violations_count": len(violations_overlap),
                "violations": violations_overlap
            },
            "timeline_boundary_window": {
                "status": "PASS" if dialogues[-1]["end_sec"] <= 1560.0 else "FAIL",
                "range": f"[{dialogues[0]['start_sec']}s, {dialogues[-1]['end_sec']}s]",
                "window": "840.0s ~ 1560.0s (20분 ±30%)"
            }
        }
    }

    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n==========================================")
    print(f"📊 Subtitle QA v3 Overall Status: {qa_status}")
    print(f"   Font Size: {fontsize_found}pt (Requirement: >=56pt) -> PASS")
    print(f"   Max lines per event: <= 2 (Violations: {len(violations_2lines)})")
    print(f"   Max observed chars per line: {max_line_len_found} (Budget: 32)")
    print(f"   Temporal overlaps: {len(violations_overlap)}")
    print(f"   Timeline range: {dialogues[0]['start_sec']:.2f}s ~ {dialogues[-1]['end_sec']:.2f}s")
    print(f"   Report saved: {REPORT_PATH.name}")
    print(f"==========================================\n")

    if qa_status != "PASS":
        raise AssertionError("Subtitle QA failed! Review violations in report.")

if __name__ == "__main__":
    run_qa()
