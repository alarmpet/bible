# -*- coding: utf-8 -*-
"""Unit tests for canonical_timeline_adapter.py."""
import sys
from pathlib import Path
import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.canonical_timeline_adapter import (
    build_canonical_timeline,
    extract_highlight_keywords,
    clean_display_text,
)


def test_extract_highlight_keywords():
    text = "7만 년 전에는 인종이 없었습니다. 키가 50cm 차이나고 산소가 30% 부족합니다."
    kws = extract_highlight_keywords(text)
    assert "7만" in kws or any("7" in k for k in kws)
    assert any("50" in k for k in kws)
    assert any("30" in k for k in kws)
    assert "인종" in kws
    assert "산소" in kws


def test_build_canonical_timeline_from_real_files():
    cues_path = Path(r"D:\module\scratch\human_library_top3\rank1_tPBVrfcU85g_cues.json")
    script_path = Path(r"D:\module\bible\human_archive\runs\human_library_replica\rank1_race_adaptation\script\master_script_clean.json")

    if not cues_path.exists():
        pytest.skip(f"Test cues file not found: {cues_path}")

    manifest = build_canonical_timeline(
        cues_path=cues_path,
        clean_script_path=script_path if script_path.exists() else None,
        target_duration_sec=973.167,
        target_fps=30.0,
    )

    assert manifest.total_cues == 346
    assert manifest.target_duration_sec == 973.167
    assert manifest.target_fps == 30.0
    assert manifest.target_total_frames == 29195

    # Check terminal clamping
    last_cue = manifest.cues[-1]
    assert last_cue.end_sec == 973.167
    assert last_cue.start_sec < 973.167

    # Check continuity: no gap between consecutive cues
    for i in range(len(manifest.cues) - 1):
        curr_e = manifest.cues[i].end_sec
        next_s = manifest.cues[i + 1].start_sec
        assert abs(curr_e - next_s) <= 0.001, f"Gap detected between cue {i} and {i+1}: {curr_e} vs {next_s}"

    # Verify sentence mappings exist
    if script_path.exists():
        assert manifest.total_sentences == 135
        assert len(manifest.sentence_mappings) > 100
