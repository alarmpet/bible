from pathlib import Path

import pytest

from lib.audio_timeline import measure_active_bounds, trim_outer_silence
from lib.audio_test_media import create_silence_tone_wav


def _wav(path: Path, *, trailing_silence_sec: float = 0.0) -> None:
    create_silence_tone_wav(path, trailing_silence_sec=trailing_silence_sec)


def test_measure_active_bounds_detects_leading_and_trailing_silence(tmp_path: Path):
    source = tmp_path / "source.wav"
    _wav(source)
    bounds = measure_active_bounds(source)
    assert bounds["start_sec"] == pytest.approx(0.4, abs=0.05)
    assert bounds["end_sec"] == pytest.approx(1.2, abs=0.05)


def test_trim_outer_silence_preserves_small_padding(tmp_path: Path):
    source = tmp_path / "source.wav"
    trimmed = tmp_path / "trimmed.wav"
    _wav(source, trailing_silence_sec=0.10)
    result = trim_outer_silence(source, trimmed, keep_lead_sec=0.08, keep_tail_sec=0.10)
    assert trimmed.exists()
    assert result["trimmed_duration_sec"] == pytest.approx(0.98, abs=0.08)


