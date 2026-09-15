# -*- coding: utf-8 -*-
from __future__ import annotations
import pytest

from lib.cinematic_effect_planner import (
    CinematicEffectPlanner,
    MotionPhase,
    PlannedProfile,
    RenderMotionProfile,
    adapt_planned_to_render_profile,
    resolve_render_motion,
)


def test_adapt_planned_to_render_profile_preserves_axis_and_family():
    phase = MotionPhase(duration_ratio=1.0, zoom_start=1.0, zoom_end=1.1, center_start=(0.5, 0.5), center_end=(0.5, 0.5))
    planned = PlannedProfile(
        effect_id="shot_002_lateral_reveal_pan_right",
        motion_family="lateral_reveal",
        axis="pan_right",
        focal_anchor=(0.5, 0.5),
        phases=(phase,),
        transition_out="hard_cut",
        reason_codes=("reveal",),
    )
    render_prof = adapt_planned_to_render_profile(planned, duration_sec=8.0)
    assert isinstance(render_prof, RenderMotionProfile)
    assert render_prof.motion_family == "lateral_reveal"
    assert render_prof.axis == "pan_right"
    assert render_prof.canonical_renderer_motion == "pan_right"
    assert render_prof.is_tri_phasic is False


def test_adapt_planned_to_render_profile_long_take_forces_tri_phasic():
    phases = (
        MotionPhase(duration_ratio=0.35, zoom_start=1.01, zoom_end=1.04, center_start=(0.5, 0.5), center_end=(0.5, 0.5)),
        MotionPhase(duration_ratio=0.35, zoom_start=1.05, zoom_end=1.17, center_start=(0.5, 0.5), center_end=(0.5, 0.5)),
        MotionPhase(duration_ratio=0.30, zoom_start=1.17, zoom_end=1.22, center_start=(0.5, 0.5), center_end=(0.5, 0.5)),
    )
    planned = PlannedProfile(
        effect_id="shot_022_long_take_tri_phasic",
        motion_family="ambient_drift",
        axis="pan_right",
        focal_anchor=(0.5, 0.85),
        phases=phases,
        transition_out="hard_cut",
        reason_codes=("long_take",),
        sub_type="tri_phasic_ken_burns",
        clamped_for_subtitles=True,
    )
    render_prof = adapt_planned_to_render_profile(planned, duration_sec=42.0)
    assert render_prof.canonical_renderer_motion == "tri_phasic"
    assert render_prof.is_tri_phasic is True
    assert render_prof.clamped_for_subtitles is True


def test_resolve_render_motion_fails_closed_on_unknown():
    with pytest.raises(ValueError, match="Fail-Closed"):
        resolve_render_motion("alien_warp_effect_xyz")


def test_resolve_render_motion_maps_planned_effect_strings():
    assert resolve_render_motion("shot_002_lateral_reveal_pan_right", 8.0) == "pan_right"
    assert resolve_render_motion("shot_003_threat_push_zoom_in", 6.0) == "push_in"
    assert resolve_render_motion("shot_004_counter_axis_pan_pan_left", 7.0) == "pan_left"
    assert resolve_render_motion("shot_006_slow_pull_out_zoom_out", 9.0) == "pull_out"
    assert resolve_render_motion("shot_007_counter_axis_pan_tilt_up", 8.0) == "tilt_up"
    assert resolve_render_motion("shot_022_long_take_tri_phasic", 45.0) == "tri_phasic"
