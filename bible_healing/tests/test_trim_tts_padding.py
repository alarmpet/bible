# -*- coding: utf-8 -*-
"""Engine padding trim: silenceremove -45dB / 30ms."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
MODERN = Path(__file__).resolve().parents[2] / "modern" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(MODERN))

from paths import FFMPEG, FFPROBE  # noqa: E402
from trim_tts_padding import trim_engine_padding  # noqa: E402


def _ff() -> str:
    if FFMPEG.exists():
        return str(FFMPEG)
    found = shutil.which("ffmpeg")
    if not found:
        pytest.skip("ffmpeg not available")
    return found


def _probe(path: Path) -> float:
    probe = str(FFPROBE) if FFPROBE.exists() else shutil.which("ffprobe")
    if not probe:
        pytest.skip("ffprobe not available")
    r = subprocess.run(
        [
            probe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(r.stdout.strip())


def test_trim_removes_leading_and_trailing_silence(tmp_path: Path):
    ff = _ff()
    padded = tmp_path / "padded.wav"
    trimmed = tmp_path / "trimmed.wav"
    subprocess.run(
        [
            ff,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "aevalsrc=0:d=1:s=24000",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.4:sample_rate=24000",
            "-f",
            "lavfi",
            "-i",
            "aevalsrc=0:d=1:s=24000",
            "-filter_complex",
            "[0][1][2]concat=n=3:v=0:a=1",
            "-c:a",
            "pcm_s16le",
            str(padded),
        ],
        check=True,
        capture_output=True,
    )
    before = _probe(padded)
    info = trim_engine_padding(padded, trimmed)
    after = _probe(trimmed)
    assert before == pytest.approx(2.4, abs=0.05)
    assert after < 0.7
    assert after > 0.3
    assert info["trimmed"] is True
    assert info["src_duration"] > info["dst_duration"]
