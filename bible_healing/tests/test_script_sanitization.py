# -*- coding: utf-8 -*-
"""Tests for scripture input sanitization (angry-prosody triggers)."""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from sanitize_script import sanitize_script, assert_no_emotion_triggers  # noqa: E402

PS4 = (
    "(다윗의 시. 영장으로 현악에 맞춘 노래) 내 의의 하나님이여, 내가 부를 때에 "
    "응답하소서 곤란 중에 나를 너그럽게 하셨사오니 나를 긍휼히 여기사 나의 기도를 "
    "들으소서 인생들아 ! 어느 때까지 나의 영광을 변하여 욕되게 하며 허사를 좋아하고 "
    "궤휼을 구하겠는고 (셀라) 여호와께서 자기를 위하여 경건한 자를 택하신 줄 너희가 "
    "알지어다"
)


def test_strips_title_and_selah():
    s = sanitize_script(PS4)
    assert "다윗의 시" not in s.tts
    assert "셀라" not in s.tts
    assert "영장" not in s.tts
    assert "다윗의 시" not in s.display
    assert "셀라" not in s.display


def test_bangs_and_questions_become_periods():
    s = sanitize_script("인생들아 ! 어디 있느뇨 ? 바라라 ！")
    assert "!" not in s.tts and "？" not in s.tts and "?" not in s.tts
    assert "인생들아." in s.tts.replace(" ", "") or "인생들아 ." in s.tts


def test_keeps_scripture_body():
    s = sanitize_script(PS4)
    assert "내 의의 하나님이여" in s.tts
    assert "알지어다" in s.tts


def test_blocks_expression_tags():
    s = sanitize_script("평안히 눕고 <laugh> 자기도 하리니")
    assert "<laugh>" not in s.tts
    assert_no_emotion_triggers(s.tts)


def test_tts_and_display_share_body():
    s = sanitize_script(PS4)
    assert s.tts.replace(".", "").replace(" ", "") == s.display.replace(".", "").replace(" ", "")
