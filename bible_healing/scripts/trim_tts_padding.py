# -*- coding: utf-8 -*-
"""Trim SuperTonic leading/trailing engine padding.

Guide measurement: ~1.0s pad each side. Use -45dB / 30ms silenceremove.
Do not use silence_duration to create pacing.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

FILTER = (
    "silenceremove=start_periods=1:start_silence=0.03:start_threshold=-45dB,"
    "areverse,"
    "silenceremove=start_periods=1:start_silence=0.03:start_threshold=-45dB,"
    "areverse"
)


def ffmpeg_bin() -> str:
    try:
        from paths import FFMPEG  # type: ignore

        if Path(FFMPEG).exists():
            return str(FFMPEG)
    except Exception:
        pass
    env = os.environ.get("FFMPEG_BIN")
    if env:
        return env
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise FileNotFoundError("ffmpeg not found")


def ffprobe_bin() -> str:
    try:
        from paths import FFPROBE  # type: ignore

        if Path(FFPROBE).exists():
            return str(FFPROBE)
    except Exception:
        pass
    env = os.environ.get("FFPROBE_BIN")
    if env:
        return env
    found = shutil.which("ffprobe")
    if found:
        return found
    raise FileNotFoundError("ffprobe not found")


def _probe_duration(path: Path) -> float:
    r = subprocess.run(
        [
            ffprobe_bin(),
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
    )
    if r.returncode != 0 or not (r.stdout or "").strip():
        return -1.0
    try:
        return float(r.stdout.strip())
    except ValueError:
        return -1.0


def trim_engine_padding(src: Path, dst: Path | None = None) -> dict:
    """Trim leading/trailing silence. Writes dst (default: overwrite src via temp)."""
    src = Path(src)
    if not src.exists() or src.stat().st_size <= 0:
        raise FileNotFoundError(f"trim src missing: {src}")
    overwrite = dst is None or Path(dst).resolve() == src.resolve()
    out = src.with_suffix(".trim.wav") if overwrite else Path(dst)
    out.parent.mkdir(parents=True, exist_ok=True)
    before = _probe_duration(src)
    cmd = [
        ffmpeg_bin(),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-af",
        FILTER,
        "-c:a",
        "pcm_s16le",
        str(out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not out.exists() or out.stat().st_size <= 0:
        err = (res.stderr or res.stdout or "").strip()
        raise RuntimeError(f"ffmpeg trim failed: {err}")
    after = _probe_duration(out)
    if overwrite:
        out.replace(src)
        final = src
    else:
        final = out
    return {
        "trimmed": True,
        "src": str(src),
        "dst": str(final),
        "src_duration": before,
        "dst_duration": after,
        "filter": FILTER,
    }
