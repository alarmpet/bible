# -*- coding: utf-8 -*-
"""Empirical proof, not just trajectory math: render a real clip with motion_engine_v3
and measure how many frames ffmpeg's `mpdecimate` considers near-duplicates. The Aug26
diagnosis measured 78-84% near-duplicate frames on the legacy engines' real output
(docs/superpowers/plans/2026-08-26-human-archive-script-image-motion-upgrade.md §2.5);
this is the same measurement technique applied to v3's output.

Requires a real `ffmpeg` on PATH (the whole pipeline already depends on it). Kept small
(low resolution, short duration) to stay fast.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

_LIB_DIR = Path(__file__).resolve().parents[1] / "scripts" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from motion_engine_v3 import render_motion_clip_v3  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not on PATH")

WIDTH, HEIGHT, FPS, DURATION_SEC = 480, 270, 25, 3.0


def _make_high_frequency_test_image(path: Path) -> None:
    """A fine checkerboard so any real pixel motion is detectable -- a flat/blank image
    would read as 'no motion' under any trajectory and make this test meaningless."""
    src_w, src_h, cell = 1200, 900, 6
    img = Image.new("RGB", (src_w, src_h))
    px = img.load()
    for y in range(src_h):
        for x in range(src_w):
            on = ((x // cell) + (y // cell)) % 2 == 0
            px[x, y] = (230, 230, 230) if on else (20, 20, 20)
    img.save(path)


def _count_frames_after_mpdecimate(clip_path: Path, width: int, height: int) -> int:
    raw_out = clip_path.with_suffix(".decimated.raw")
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(clip_path),
         "-vf", "mpdecimate=hi=64*12:lo=64*5:frac=0.33",
         "-pix_fmt", "yuv420p", "-f", "rawvideo", str(raw_out)],
        check=True,
    )
    frame_bytes = width * height * 3 // 2  # yuv420p plane size
    size = raw_out.stat().st_size
    raw_out.unlink(missing_ok=True)
    return max(0, size // frame_bytes)


def _near_duplicate_rate(clip_path: Path, width: int, height: int, total_frames: int) -> float:
    retained = _count_frames_after_mpdecimate(clip_path, width, height)
    return 1.0 - (retained / float(total_frames))


@pytest.mark.parametrize("motion_intent", ["push_in", "pan_right", "tilt_up"])
def test_v3_cadence_clears_the_legacy_near_duplicate_baseline(tmp_path: Path, motion_intent: str) -> None:
    """The Aug26-measured legacy baseline was 78-84% near-duplicate frames. v3's
    constant-velocity cruise phase should keep this well below that -- generous
    threshold (50%) chosen to clearly separate "fixed" from "still judders", not to
    claim a specific physiologically-derived number.
    """
    img_path = tmp_path / "source.png"
    _make_high_frequency_test_image(img_path)
    clip_path = tmp_path / f"{motion_intent}.mkv"

    render_motion_clip_v3(img_path, clip_path, DURATION_SEC, motion_intent=motion_intent,
                           fps=FPS, width=WIDTH, height=HEIGHT, lossless=True)

    total_frames = round(DURATION_SEC * FPS)
    rate = _near_duplicate_rate(clip_path, WIDTH, HEIGHT, total_frames)
    assert rate < 0.50, (
        f"{motion_intent}: near-duplicate rate {rate:.1%} is not clearly better than the "
        f"legacy 78-84% baseline")


def test_static_intent_is_allowed_to_be_mostly_duplicate_frames(tmp_path: Path) -> None:
    """static is a normal, intentional profile (Aug26 principle: not every image must
    move) -- it should NOT be held to the same cadence bar as a moving shot."""
    img_path = tmp_path / "source.png"
    _make_high_frequency_test_image(img_path)
    clip_path = tmp_path / "static.mkv"

    render_motion_clip_v3(img_path, clip_path, DURATION_SEC, motion_intent="static",
                           fps=FPS, width=WIDTH, height=HEIGHT, lossless=True)

    total_frames = round(DURATION_SEC * FPS)
    rate = _near_duplicate_rate(clip_path, WIDTH, HEIGHT, total_frames)
    assert rate > 0.90, "a static shot should decode as almost entirely duplicate frames"
