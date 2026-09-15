"""Bounded media fixtures shared by audio tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .audio_timeline import get_wav_duration


def create_silence_tone_wav(
    output_path: Path,
    *,
    silence_duration_sec: float = 0.4,
    tone_duration_sec: float = 0.8,
    trailing_silence_sec: float = 0.0,
    timeout_sec: float = 10.0,
    max_output_bytes: int = 1_000_000,
) -> dict[str, float | int | str]:
    """Create a finite PCM fixture and reject unexpected output growth."""
    if silence_duration_sec <= 0 or tone_duration_sec <= 0 or trailing_silence_sec < 0:
        raise ValueError("fixture durations must be positive except optional trailing silence")
    if max_output_bytes <= 44:
        raise ValueError("max_output_bytes must allow a WAV header")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    expected_duration = silence_duration_sec + tone_duration_sec + trailing_silence_sec
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"anullsrc=r=48000:cl=mono:d={silence_duration_sec:.3f}",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=440:duration={tone_duration_sec:.3f}",
    ]
    if trailing_silence_sec:
        cmd.extend([
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r=48000:cl=mono:d={trailing_silence_sec:.3f}",
            "-filter_complex",
            "[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]",
        ])
    else:
        cmd.extend(["-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[a]"])
    cmd.extend([
        "-map",
        "[a]",
        "-t",
        f"{expected_duration:.3f}",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ])
    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"audio fixture timed out after {timeout_sec}s") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"audio fixture FFmpeg failed: {exc.stderr}") from exc

    if not output_path.is_file():
        raise RuntimeError(f"audio fixture was not created: {output_path}")
    byte_count = output_path.stat().st_size
    if byte_count <= 44 or byte_count > max_output_bytes:
        raise RuntimeError(
            f"audio fixture size {byte_count} outside safe range (45..{max_output_bytes})"
        )

    duration_sec = get_wav_duration(output_path)
    if abs(duration_sec - expected_duration) > 0.05:
        raise RuntimeError(
            f"audio fixture duration {duration_sec:.3f}s differs from {expected_duration:.3f}s"
        )
    return {
        "path": str(output_path),
        "duration_sec": duration_sec,
        "bytes": byte_count,
    }
