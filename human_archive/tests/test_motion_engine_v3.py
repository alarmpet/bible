# -*- coding: utf-8 -*-
"""Unit tests for the v3 motion trajectory math -- the specific bugs from the 2026-09-15
diagnosis (docs/superpowers/plans/2026-09-15-human-archive-nollam-script-visual-motion-multi-llm-overhaul-plan.md
§1.5, §2.5) each get a regression test here: full-shot cosine easing, direction reversal,
named-preset duplication, and duration-independent magnitude.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_LIB_DIR = Path(__file__).resolve().parents[1] / "scripts" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from motion_engine_v3 import (  # noqa: E402
    MOTION_INTENTS, MotionKeyframe, compute_crop_box, ease_ramp_cruise, interpolate,
    resolve_motion_keyframes,
)


# --- ease_ramp_cruise --------------------------------------------------------------

def test_boundary_values_are_exact():
    assert ease_ramp_cruise(0.0) == pytest.approx(0.0)
    assert ease_ramp_cruise(1.0) == pytest.approx(1.0)


def test_monotonic_non_decreasing():
    xs = [i / 500.0 for i in range(501)]
    ys = [ease_ramp_cruise(x) for x in xs]
    for a, b in zip(ys, ys[1:]):
        assert b >= a - 1e-9


@pytest.mark.parametrize("ramp_frac", [0.0, 0.05, 0.15, 0.3, 0.49])
def test_boundary_values_hold_for_any_ramp_frac(ramp_frac):
    assert ease_ramp_cruise(0.0, ramp_frac) == pytest.approx(0.0, abs=1e-9)
    assert ease_ramp_cruise(1.0, ramp_frac) == pytest.approx(1.0, abs=1e-9)


def test_zero_ramp_is_pure_linear():
    for t in (0.0, 0.2, 0.5, 0.8, 1.0):
        assert ease_ramp_cruise(t, ramp_frac=0.0) == pytest.approx(t, abs=1e-9)


def test_cruise_phase_has_constant_nonzero_velocity():
    """This is the actual fix: the legacy engines' single full-shot cosine has ~0
    velocity near both ends of a shot. Here the middle of the shot (well inside the
    cruise phase) must move at a constant, non-trivial rate -- not decelerate toward
    either boundary."""
    r = 0.15
    h = 1e-4
    velocities = []
    for t in (0.3, 0.4, 0.5, 0.6, 0.7):  # safely inside [r, 1-r] for r=0.15
        v = (ease_ramp_cruise(t + h, r) - ease_ramp_cruise(t - h, r)) / (2 * h)
        velocities.append(v)
    # All cruise-phase velocities should agree with each other (constant speed).
    for v in velocities:
        assert v == pytest.approx(velocities[0], rel=1e-3)
    assert velocities[0] > 0.5, "cruise velocity should be well above zero"


def test_ramp_velocity_is_continuous_at_the_cruise_boundary():
    """No jerk: velocity approaching the ramp/cruise boundary from either side should
    match, unlike a naive linear-ramp-then-cruise splice which has a visible kink."""
    r = 0.2
    h = 1e-5
    v_just_inside_ramp = (ease_ramp_cruise(r + h, r) - ease_ramp_cruise(r - h, r)) / (2 * h)
    v_cruise = (ease_ramp_cruise(0.5 + h, r) - ease_ramp_cruise(0.5 - h, r)) / (2 * h)
    assert v_just_inside_ramp == pytest.approx(v_cruise, rel=0.05)


def test_velocity_is_near_zero_only_at_the_very_edges_not_across_the_whole_shot():
    """The legacy defect, precisely: verify velocity a short way into the shot is
    already close to full cruise speed, unlike a full-shot cosine where it would still
    be small at t=0.15."""
    r = 0.15
    h = 1e-4
    v_at_ramp_end = (ease_ramp_cruise(r + h, r) - ease_ramp_cruise(r - h, r)) / (2 * h)
    v_at_shot_start = (ease_ramp_cruise(0.01 + h, r) - ease_ramp_cruise(0.01 - h, r)) / (2 * h)
    assert v_at_shot_start < v_at_ramp_end, "velocity should still be ramping up this early"
    # but by the end of the (short) ramp, velocity must be near its cruise value
    v_cruise = (ease_ramp_cruise(0.5 + h, r) - ease_ramp_cruise(0.5 - h, r)) / (2 * h)
    assert v_at_ramp_end == pytest.approx(v_cruise, rel=0.05)


# --- interpolate / direction-reversal regression -----------------------------------

def _axis_values(start: MotionKeyframe, end: MotionKeyframe, axis: str, n: int = 200):
    return [getattr(interpolate(start, end, i / (n - 1)), axis) for i in range(n)]


@pytest.mark.parametrize("motion_intent", ["push_in", "pull_out", "pan_left", "pan_right",
                                            "tilt_up", "tilt_down", "detail_crop"])
def test_no_axis_ever_reverses_direction(motion_intent):
    """Regression test for the legacy `tilt_up` bug: crop offset went 0 -> peak -> 0
    because max_dy(t) (increasing) was multiplied by (1 - ease(t)) (decreasing). Here
    every axis is a straight interpolation between two fixed keyframes, so it can only
    move monotonically (or stay flat) for the whole shot -- verified numerically for
    every real motion_intent, not just asserted by construction.
    """
    start, end = resolve_motion_keyframes(motion_intent, duration_sec=8.0)
    for axis in ("zoom", "center_x", "center_y"):
        values = _axis_values(start, end, axis)
        deltas = [b - a for a, b in zip(values, values[1:])]
        signs = {1 if d > 1e-9 else (-1 if d < -1e-9 else 0) for d in deltas}
        signs.discard(0)
        assert len(signs) <= 1, f"{motion_intent}.{axis} changes direction mid-shot: {signs}"


def test_static_intent_never_moves():
    start, end = resolve_motion_keyframes("static", duration_sec=8.0)
    assert start == end == MotionKeyframe()


def test_unknown_intent_falls_back_to_static_not_a_random_default():
    start, end = resolve_motion_keyframes("nonexistent_intent_xyz", duration_sec=8.0)
    assert start == end == MotionKeyframe()


# --- named-preset duplication regression --------------------------------------------

def test_every_motion_intent_produces_a_distinct_trajectory():
    """Regression test for the legacy bug where `kenburns_zoom_pan_in`, `pan_right`, and
    `kenburns_hero_push` all computed the identical crop_x/crop_y formula despite having
    different names. Every real motion_intent here must actually differ from every
    other, at some point in the shot."""
    trajectories = {}
    for intent in MOTION_INTENTS:
        if intent == "static":
            continue
        start, end = resolve_motion_keyframes(intent, duration_sec=8.0)
        trajectories[intent] = [interpolate(start, end, i / 49) for i in range(50)]

    names = list(trajectories)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            same = all(
                pytest.approx(x.zoom, abs=1e-6) == y.zoom
                and pytest.approx(x.center_x, abs=1e-6) == y.center_x
                and pytest.approx(x.center_y, abs=1e-6) == y.center_y
                for x, y in zip(trajectories[a], trajectories[b])
            )
            assert not same, f"{a} and {b} compute the identical trajectory"


def test_push_in_and_pull_out_are_time_reversals_not_the_same_direction():
    s_in, e_in = resolve_motion_keyframes("push_in", duration_sec=8.0)
    s_out, e_out = resolve_motion_keyframes("pull_out", duration_sec=8.0)
    assert s_in.zoom < e_in.zoom, "push_in must zoom in over time"
    assert s_out.zoom > e_out.zoom, "pull_out must zoom out over time"


# --- duration-aware magnitude --------------------------------------------------------

def test_longer_shots_get_a_larger_zoom_delta_to_stay_visible():
    """The legacy engines used the same ~3.5% delta for every duration, so a 27s shot
    moved imperceptibly slowly. Here a longer shot must be assigned at least as much
    zoom range as a shorter one of the same motion_intent."""
    short_start, short_end = resolve_motion_keyframes("push_in", duration_sec=3.0)
    long_start, long_end = resolve_motion_keyframes("push_in", duration_sec=20.0)
    short_delta = short_end.zoom - short_start.zoom
    long_delta = long_end.zoom - long_start.zoom
    assert long_delta >= short_delta


def test_cruise_phase_pixel_velocity_clears_a_visibility_floor_for_long_shots():
    """Direct measurement, in output pixels, that a long shot's cruise-phase motion is
    not imperceptibly slow -- the actual complaint behind the diagnosis."""
    duration_sec, fps, width, height = 20.0, 25, 1920, 1080
    start, end = resolve_motion_keyframes("push_in", duration_sec, fps=fps, width=width)
    total_frames = round(duration_sec * fps)
    mid = total_frames // 2
    h = 1
    box_a = compute_crop_box(width, height, width, height,
                              interpolate(start, end, (mid - h) / (total_frames - 1)))
    box_b = compute_crop_box(width, height, width, height,
                              interpolate(start, end, (mid + h) / (total_frames - 1)))
    px_delta = abs(box_b[2] - box_a[2])  # right-edge displacement between adjacent frames
    assert px_delta > 0.3, "cruise-phase motion should be visible frame-to-frame, not near-zero"


# --- crop box geometry (unchanged correctness, kept as a regression guard) ----------

def test_crop_box_center_at_zoom_one_is_full_frame():
    box = compute_crop_box(1920, 1080, 1920, 1080, MotionKeyframe(zoom=1.0, center_x=0.5, center_y=0.5))
    assert box == pytest.approx((0.0, 0.0, 1920.0, 1080.0))


def test_crop_box_stays_within_canvas_bounds_across_the_full_center_range():
    for cx in (0.0, 0.25, 0.5, 0.75, 1.0):
        left, top, right, bottom = compute_crop_box(1920, 1080, 1920, 1080,
                                                      MotionKeyframe(zoom=1.2, center_x=cx, center_y=0.5))
        assert -1e-6 <= left and right <= 1920 + 1e-6
