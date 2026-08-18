# -*- coding: utf-8 -*-
"""TTS-only Korean number reading (display keeps Arabic digits)."""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from korean_number_reading import numbers_to_korean_speech  # noqa: E402
from sanitize_script import sanitize_script  # noqa: E402


def test_year_uses_sino_korean():
    assert "천팔백십사년" in numbers_to_korean_speech("1814년").replace(" ", "")


def test_hours_use_native_korean():
    out = numbers_to_korean_speech("3시간")
    assert "세" in out
    assert "시간" in out
    assert "3" not in out


def test_psalm_chapter_uses_sino_korean():
    out = numbers_to_korean_speech("시편 23편")
    assert "이십삼" in out.replace(" ", "")
    assert "23" not in out


def test_sanitize_keeps_digits_on_display_only():
    s = sanitize_script("시편 23편을 1814년에 3시간 동안 읽습니다.")
    assert "23" in s.display
    assert "1814" in s.display
    assert "3시간" in s.display.replace(" ", "")
    assert "23" not in s.tts
    assert "1814" not in s.tts
    assert "이십삼" in s.tts.replace(" ", "")
    assert "천팔백십사년" in s.tts.replace(" ", "")
    assert "세" in s.tts and "시간" in s.tts
