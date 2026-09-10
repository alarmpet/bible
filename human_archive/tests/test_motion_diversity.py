from __future__ import annotations

import json
import subprocess
from pathlib import Path
from PIL import Image
import pytest

from smooth_subpixel_motion_engine import (
    compute_trajectory,
    compute_tri_phasic_trajectory,
    check_trajectory_static_hold,
    render_composite_opening_clip,
)


def test_static_hold_detector_flags_frozen_trajectory() -> None:
    frozen = [(1.0, 0.5, 0.5)] * 50
    assert not check_trajectory_static_hold(frozen, window_size=25, min_displacement_px=3.0)


def test_static_hold_detector_passes_push_in() -> None:
    pts = [compute_trajectory(f, 250, 'push_in') for f in range(250)]
    assert check_trajectory_static_hold(pts, window_size=25, min_displacement_px=3.0)


def test_static_hold_detector_passes_tri_phasic_long_take() -> None:
    pts = [compute_tri_phasic_trajectory(f, 1000) for f in range(1000)]
    assert check_trajectory_static_hold(pts, window_size=25, min_displacement_px=3.0)


def test_render_composite_opening_clip_creates_valid_mp4(tmp_path: Path) -> None:
    img1 = tmp_path / 'cut01.jpg'
    img2 = tmp_path / 'cut02.jpg'
    img3 = tmp_path / 'cut03.jpg'

    Image.new('RGB', (1920, 1080), (100, 150, 200)).save(img1)
    Image.new('RGB', (1920, 1080), (150, 200, 100)).save(img2)
    Image.new('RGB', (1920, 1080), (200, 100, 150)).save(img3)

    out_mp4 = tmp_path / 'opening_composite.mp4'

    cuts = [
        {'image_path': img1, 'duration': 0.35, 'motion': 'pan_right', 'visual_role': 'context_wide'},
        {'image_path': img2, 'duration': 0.35, 'motion': 'push_in', 'visual_role': 'subject_action'},
        {'image_path': img3, 'duration': 0.40, 'motion': 'push_in', 'visual_role': 'evidence_detail'},
    ]

    rendered = render_composite_opening_clip(
        output_path=out_mp4,
        cuts=cuts,
        duration=1.1,
        fps=25,
        width=1920,
        height=1080,
        dissolve_frames=3,
    )

    assert rendered.is_file()
    assert rendered.stat().st_size > 5000

    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration:stream=width,height,r_frame_rate',
        '-of', 'json',
        str(rendered)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    probe = json.loads(res.stdout)
    dur = float(probe['format']['duration'])
    assert 0.95 <= dur <= 1.25
