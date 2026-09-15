from __future__ import annotations

import pytest

from smooth_subpixel_motion_engine import (
    compute_biphasic_trajectory,
    compute_tri_phasic_trajectory,
    compute_trajectory,
)
from lib.motion_engine_v3 import trajectory


def test_biphasic_motion_pans_then_pushes_into_focal_subject() -> None:
    values = [compute_biphasic_trajectory(frame, 100, "pan_left") for frame in range(100)]

    assert values[0][0] == 1.04
    assert values[49][1] < values[0][1]
    assert values[50][1] == pytest.approx(values[49][1], abs=0.001)
    assert values[-1][0] > values[50][0]
    assert values[-1][1] == 0.5


def test_legacy_motion_engine_delegates_to_smooth_ssot() -> None:
    assert trajectory(50, 100, "push_in") == compute_trajectory(50, 100, "push_in")
    assert trajectory(50, 100, "tri_phasic") == compute_trajectory(50, 100, "tri_phasic")


def test_perceptual_cut_trajectory_jumps_at_five_seconds() -> None:
    # 250 frames @ 25fps = 10.0 seconds. 5.0s cut occurs at frame 125.
    before_cut = compute_trajectory(124, 250, "layer3_perceptual_cut")
    at_cut = compute_trajectory(125, 250, "layer3_perceptual_cut")

    # Before cut: wide shot (zoom ~1.06)
    assert before_cut[0] < 1.10
    assert before_cut[2] == 0.5

    # At cut: jump cut to extreme close-up (zoom >= 1.18, reframed to 0.45)
    assert at_cut[0] >= 1.18
    assert at_cut[2] == 0.45
    assert at_cut[0] - before_cut[0] > 0.10  # Sharp discontinuous jump cut reframe


def test_tri_phasic_trajectory_transitions_three_phases() -> None:
    # 1000 frames: Phase 1 (0..350), Phase 2 (350..700), Phase 3 (700..1000)
    total = 1000
    p1 = compute_tri_phasic_trajectory(150, total)
    p2 = compute_tri_phasic_trajectory(500, total)
    p3 = compute_tri_phasic_trajectory(850, total)

    # Phase 1: subtle zoom (1.01-1.05), horizontal ambient drift
    assert 1.01 <= p1[0] <= 1.05
    assert p1[1] != 0.50

    # Phase 2: dynamic approach, zoom increasing
    assert p1[0] < p2[0] < p3[0]

    # Phase 3: focal lock and micro breathing
    assert p3[0] >= 1.17


def test_tri_phasic_motion_clamps_subtitles_clear_zone() -> None:
    # Even when focal position is lower, center_y must not exceed 0.75
    for f in range(0, 500, 50):
        _, _, y = compute_tri_phasic_trajectory(f, 500, focal_position="lower", clamped_for_subtitles=True)
        assert y <= 0.75

