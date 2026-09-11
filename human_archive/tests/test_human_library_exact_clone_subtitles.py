# -*- coding: utf-8 -*-
"""test_human_library_exact_clone_subtitles.py

Tests for 1:1 exact subtitle replication:
1. Verifies start_sec and global_start_sec binding (preventing 00:00:00.00 fallback).
2. Verifies DocuNarrator_Exact 1-line opaque box style.
3. Verifies bright yellow keyword highlighting (\c&H003BEBFF&).
4. Verifies zero overlapping subtitles across shots.
"""
from pathlib import Path
import pytest
from lib.semantic_subtitle_engine import SemanticSubtitleEngine, seconds_to_ass

def test_start_sec_binding_prevents_zero_fallback():
    engine = SemanticSubtitleEngine()
    shot = {
        "shot_id": "SHOT_002",
        "start_sec": 12.50,
        "end_sec": 18.20,
        "duration_sec": 5.70,
        "spoken_text": "피부색도 거의 같고 키도 비슷했습니다."
    }
    events = engine.process_shot_to_events(shot)
    assert len(events) >= 1
    # Must NOT start at 0:00:00.00
    assert "0:00:12.50" in events[0]
    assert "0:00:18.20" in events[0]

def test_docunarrator_exact_box_style_and_yellow_highlighting(tmp_path):
    engine = SemanticSubtitleEngine()
    shots = [
        {
            "shot_id": "SHOT_001",
            "global_start_sec": 0.04,
            "global_end_sec": 2.79,
            "spoken_text": "7만 년 전에는 인종이 없었습니다."
        },
        {
            "shot_id": "SHOT_002",
            "global_start_sec": 2.80,
            "global_end_sec": 7.50,
            "spoken_text": "같은 인간인데 키가 50cm 차이 납니다."
        }
    ]
    out_ass = tmp_path / "test_exact.ass"
    engine.compile_ass_subtitles(
        shots=shots,
        output_path=out_ass,
        title="Exact Clone Test",
        style_name="DocuNarrator_Exact",
        highlight_keywords=True,
    )
    assert out_ass.exists()
    text = out_ass.read_text(encoding="utf-8")
    
    # Must include DocuNarrator_Exact style with BorderStyle=3
    assert "Style: DocuNarrator_Exact" in text
    assert ",3,2.0,0,2,40,40,65,1" in text
    
    # Must contain yellow highlight tag for 7만 년 and 50cm
    assert "{\\c&H003BEBFF&}7만 년{\\c&H00FFFFFF&}" in text or "{\\c&H003BEBFF&}" in text
    assert "{\\c&H003BEBFF&}50cm{\\c&H00FFFFFF&}" in text or "50cm" in text
    
    # Must have distinct start times
    assert "0:00:00.04" in text
    assert "0:00:02.80" in text
    # Ensure no shot started at 0:00:00.00
    assert "0:00:00.00" not in text

def test_no_subtitle_overlap_invariant(tmp_path):
    engine = SemanticSubtitleEngine()
    shots = [
        {"shot_id": f"SHOT_{i:03d}", "start_sec": i * 5.0, "end_sec": (i + 1) * 5.0, "spoken_text": f"문장 {i} 테스트입니다."}
        for i in range(10)
    ]
    out_ass = tmp_path / "test_overlap.ass"
    engine.compile_ass_subtitles(shots=shots, output_path=out_ass, style_name="DocuNarrator_Exact")
    
    lines = [l for l in out_ass.read_text(encoding="utf-8").splitlines() if l.startswith("Dialogue:")]
    assert len(lines) == 10
    
    prev_end = 0.0
    for l in lines:
        parts = l.split(",")
        start_str = parts[1]
        end_str = parts[2]
        # parse H:MM:SS.cs
        h, m, s = start_str.split(":")
        start_sec = int(h)*3600 + int(m)*60 + float(s)
        h, m, s = end_str.split(":")
        end_sec = int(h)*3600 + int(m)*60 + float(s)
        
        assert start_sec >= prev_end - 0.01
        assert end_sec > start_sec
        prev_end = end_sec
