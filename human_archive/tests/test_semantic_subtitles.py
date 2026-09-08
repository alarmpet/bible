# -*- coding: utf-8 -*-
"""Regression test suite for Semantic Subtitle Engine (Expanded 52pt / 36-char Standard).

Enforces zero-tolerance gates:
1. Number comma splitting across lines (e.g. '1,\\N100만') is strictly 0.
2. Subtitle lines per dialogue event is strictly <= 2 (at most one '\\N').
3. Line length for 52pt font is strictly <= 36 characters (+50% expansion).
4. Line 2 never begins with an isolated particle.
5. Production ASS files pass full semantic audit.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
import pytest

_TEST_DIR = Path(__file__).resolve().parent
_SCRIPTS_DIR = _TEST_DIR.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.semantic_subtitle_engine import (
    SemanticSubtitleEngine,
    split_korean_two_lines,
    split_sentence_into_clauses,
    seconds_to_ass,
)


def test_split_korean_two_lines_prevents_isolated_particles():
    text = "청년 학자 소 플리니우스는 미세눔에서 거대한 소나무 모양의 구름을 목격했습니다."
    res = split_korean_two_lines(text, max_line_chars=36)
    lines = res.split(r"\N")
    assert len(lines) <= 2
    assert all(len(l) <= 36 for l in lines)
    if len(lines) > 1:
        first_w_l2 = lines[1].strip().split()[0]
        assert first_w_l2 not in {"은", "는", "이", "가", "을", "를", "의", "에", "로", "과", "와", "도", "만", "서"}


def test_no_number_comma_split_in_subtitles():
    test_shots = [
        {
            "shot_id": "SHOT_001",
            "display_text": "20조 원의 황금과 1,100만 캐럿의 에메랄드를 가득 실은 거대한 보물선이, 단 1분 만에 칠흑 같은 심해 속으로 사라졌습니다.",
            "speech_start": 0.40,
            "speech_end": 24.68,
        },
        {
            "shot_id": "SHOT_002",
            "display_text": "바다 밑 3,100m 암흑 속에 잠든 스페인 갈레온선 산호세호. 인류 역사상 가장 거대한 보물선은 왜 300년 동안 침묵했을까요?",
            "speech_start": 25.38,
            "speech_end": 49.66,
        },
        {
            "shot_id": "SHOT_007",
            "display_text": "스페인 국왕의 황금 문장을 단 1,200톤급 거함 산호세호의 돛대가 붉은 노을을 가르며 전진하고 있었습니다.",
            "speech_start": 143.42,
            "speech_end": 163.77,
        },
    ]

    engine = SemanticSubtitleEngine(font_size=52, max_line_chars=36, max_clause_chars=70)
    for s in test_shots:
        events = engine.process_shot_to_events(s)
        for e in events:
            assert not re.search(r"\d+,\s*\\N\s*\d+", e), f"Number comma split detected in: {e}"
            assert e.count(r"\N") <= 1, f"Event has more than 2 lines: {e}"
            parts = e.split(",", 9)
            text = parts[9]
            for subline in text.split(r"\N"):
                assert len(subline.strip()) <= 36, f"Line length {len(subline.strip())} > 36 in: {subline}"


def test_seconds_to_ass_formatting():
    assert seconds_to_ass(0.0) == "0:00:00.00"
    assert seconds_to_ass(0.40) == "0:00:00.40"
    assert seconds_to_ass(65.43) == "0:01:05.43"
    assert seconds_to_ass(1200.0) == "0:20:00.00"


def test_audit_ass_file_detects_violations(tmp_path: Path):
    bad_ass = tmp_path / "bad.ass"
    bad_ass.write_text(
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        r"Dialogue: 0,0:00:00.00,0:00:05.00,DocuNarrator_v4,,0,0,0,,20조 원의 황금과 1,\N100만 캐럿" "\n"
        r"Dialogue: 0,0:00:05.00,0:00:10.00,DocuNarrator_v4,,0,0,0,,첫 번째 줄\N두 번째 줄\N세 번째 줄" "\n",
        encoding="utf-8",
    )

    audit = SemanticSubtitleEngine.audit_ass_file(bad_ass, max_line_chars=36)
    assert audit["status"] == "FAIL"
    assert audit["violations_count"] >= 2
    errors = [v["error"] for v in audit["violations"]]
    assert any("Number comma split" in err for err in errors)
    assert any("More than 2 lines" in err for err in errors)


def test_compile_ass_subtitles_for_san_jose(tmp_path: Path):
    ep_dir = _SCRIPTS_DIR.parent / "runs" / "nollam_file" / "2026-09-08" / "caribbean-san-jose-galleon-gold"
    manifest_path = ep_dir / "generation" / "master_1200s_manifest.json"
    if not manifest_path.exists():
        pytest.skip("San Jose manifest not found")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    shots = manifest["shots"]

    engine = SemanticSubtitleEngine(font_size=52, max_line_chars=36, max_clause_chars=70)
    out_file = tmp_path / "test_san_jose.ass"
    engine.compile_ass_subtitles(shots, out_file, title="San Jose Galleon Master Subtitles")

    assert out_file.exists()
    audit = SemanticSubtitleEngine.audit_ass_file(out_file, max_line_chars=36)
    assert audit["status"] == "PASS", f"Violations found: {audit['violations']}"
    assert audit["violations_count"] == 0
    assert audit["dialogue_events"] >= len(shots)


def test_san_jose_opening_hook_retention():
    ep_dir = _SCRIPTS_DIR.parent / "runs" / "nollam_file" / "2026-09-08" / "caribbean-san-jose-galleon-gold"
    manifest_path = ep_dir / "generation" / "master_1200s_manifest.json"
    if not manifest_path.exists():
        pytest.skip("San Jose manifest not found")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    shots = manifest["shots"]
    assert len(shots) >= 8
    shot1 = shots[0]["display_text"]
    assert "20조 원의 황금" in shot1, f"SHOT_001 missing 20조 원 황금 hook: {shot1}"
    assert "1,100만 캐럿" in shot1, f"SHOT_001 missing 1,100만 캐럿: {shot1}"
    assert "사료에 따라 차이가 있으나" not in shot1, f"SHOT_001 contaminated with disclaimer: {shot1}"


def test_production_ass_files_san_jose():
    ep_dir = _SCRIPTS_DIR.parent / "runs" / "nollam_file" / "2026-09-08" / "caribbean-san-jose-galleon-gold"
    for ass_rel in ["subtitles/pilot_subtitles_1200s.ass", "candidate/pilot_subtitles_1200s.ass"]:
        ass_path = ep_dir / ass_rel
        if not ass_path.exists():
            continue
        audit = SemanticSubtitleEngine.audit_ass_file(ass_path, max_line_chars=36)
        assert audit["status"] == "PASS", f"Violations in {ass_rel}: {audit['violations']}"
        assert audit["violations_count"] == 0


def test_line_length_expansion_reached():
    """Verify that subtitles actively utilize the expanded line length (>26 chars)."""
    ep_dir = _SCRIPTS_DIR.parent / "runs" / "nollam_file" / "2026-09-08" / "caribbean-san-jose-galleon-gold"
    ass_path = ep_dir / "subtitles" / "pilot_subtitles_1200s.ass"
    if not ass_path.exists():
        pytest.skip("pilot_subtitles_1200s.ass not found")

    lines = ass_path.read_text(encoding="utf-8").splitlines()
    dialogue_lines = [l for l in lines if l.startswith("Dialogue:")]
    
    # Check that there are lines longer than 26 characters (proving 50% expansion is in effect)
    long_sublines = []
    for dl in dialogue_lines:
        text = dl.split(",", 9)[9]
        for subline in text.split(r"\N"):
            if len(subline.strip()) >= 28:
                long_sublines.append(subline.strip())
    
    assert len(long_sublines) >= 10, f"Expected at least 10 expanded lines >= 28 chars, got {len(long_sublines)}"
    assert all(len(sl) <= 36 for sl in long_sublines), "All expanded lines must be <= 36 chars"
