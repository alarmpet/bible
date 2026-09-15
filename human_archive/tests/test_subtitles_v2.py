# -*- coding: utf-8 -*-
"""Test Korean caption splitting and ASS subtitle generation."""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.korean_caption import format_ass_timestamp, split_korean_two_lines
from build_subtitles_v2 import build_ass_subtitles


def test_split_korean_two_lines_prevents_isolated_particles():
    text = "청년 학자 소 플리니우스는 미세눔에서 거대한 소나무 모양의 구름을 목격했습니다."
    lines = split_korean_two_lines(text, max_chars=22)

    assert len(lines) == 2
    assert len(lines[0]) <= 25
    assert len(lines[1]) <= 25
    # Ensure line 2 does not start with an isolated particle
    first_w_l2 = lines[1].split()[0]
    assert first_w_l2 not in {"은", "는", "이", "가", "을", "를", "의"}


def test_format_ass_timestamp():
    assert format_ass_timestamp(0.0) == "0:00:00.00"
    assert format_ass_timestamp(65.43) == "0:01:05.43"
    assert format_ass_timestamp(3661.05) == "1:01:01.05"


def test_build_ass_subtitles():
    build_dir = _PROJECT_ROOT / "human_archive" / "runs" / "ep01_pompeii_rebuild_v2" / "pilot-v2-001"
    if not (build_dir / "scene_audio_manifest.json").exists():
        pytest.skip("Audio manifest not yet created")

    ass_path = build_ass_subtitles(build_dir)
    assert ass_path.exists()
    content = ass_path.read_text(encoding="utf-8-sig")
    assert "DocuMain" in content
    assert "Dialogue:" in content


def test_build_ass_subtitles_accepts_double_size_for_sample_v3(tmp_path: Path):
    (tmp_path / "scene_audio_manifest.json").write_text(
        '{"shots":[{"shot_id":"HA002-Q3-001","startSeconds":0.0,'
        '"endSeconds":3.0,"display_text":"새 이미지와 맞는 문장입니다."}]}',
        encoding="utf-8",
    )

    ass_path = build_ass_subtitles(tmp_path, font_size=108)

    content = ass_path.read_text(encoding="utf-8-sig")
    assert "Style: DocuMain,Malgun Gothic,108," in content


def test_double_size_caption_splits_long_sentence_into_safe_cues(tmp_path: Path):
    long_text = "정사인 실록과 승정원일기에는 장희빈의 발악이나 난동 기록이 전혀 없답니다."
    (tmp_path / "scene_audio_manifest.json").write_text(
        '{"shots":[{"shot_id":"HA002-Q3-011","startSeconds":0.0,'
        f'"endSeconds":7.0,"display_text":"{long_text}"}}]}}',
        encoding="utf-8",
    )

    ass_path = build_ass_subtitles(tmp_path, font_size=108, max_chars_per_line=14)

    dialogues = [
        line for line in ass_path.read_text(encoding="utf-8-sig").splitlines()
        if line.startswith("Dialogue:")
    ]
    assert len(dialogues) >= 2
    for dialogue in dialogues:
        caption = dialogue.split(",", 9)[9]
        assert all(len(line) <= 14 for line in caption.split(r"\N"))
