from pathlib import Path

import pytest

from lib.audio_test_media import create_silence_tone_wav
from lib.audio_timeline import get_wav_duration


def test_silence_tone_fixture_is_duration_bounded_and_small(tmp_path: Path):
    output_path = tmp_path / "source.wav"

    result = create_silence_tone_wav(output_path)

    assert output_path.exists()
    assert result["duration_sec"] == pytest.approx(1.2, abs=0.05)
    assert get_wav_duration(output_path) == pytest.approx(1.2, abs=0.05)
    assert 44 < result["bytes"] < 1_000_000


def test_silence_tone_fixture_can_include_trailing_silence(tmp_path: Path):
    output_path = tmp_path / "source-with-tail.wav"

    result = create_silence_tone_wav(output_path, trailing_silence_sec=0.10)

    assert result["duration_sec"] == pytest.approx(1.3, abs=0.05)
