# -*- coding: utf-8 -*-
from __future__ import annotations
import pytest

from lib.cinematic_effect_planner import (
    CinematicEffectPlanner,
    adapt_planned_to_render_profile,
    resolve_render_motion,
)
from smooth_subpixel_motion_engine import compute_trajectory, check_trajectory_static_hold

def test_shot_022_tri_phasic_render_binding():
    planner = CinematicEffectPlanner()
    scene = {
        "order": 22,
        "shot_id": "SHOT_022",
        "beat_type": "consequence",
        "scene_duration": 36.5,
        "focal_anchor": (0.5, 0.45),
    }
    planned = planner.plan_shot_effect(scene, [])
    assert planned.sub_type == "tri_phasic_ken_burns"
    
    render_prof = adapt_planned_to_render_profile(planned, duration_sec=36.5)
    assert render_prof.canonical_renderer_motion == "tri_phasic"
    assert render_prof.is_tri_phasic is True
    
    # Verify trajectory evaluation for 36.5s * 25fps = 912 frames
    total_frames = int(round(36.5 * 25))
    points = [compute_trajectory(f, total_frames, render_prof.canonical_renderer_motion) for f in range(total_frames)]
    assert len(points) == total_frames
    
    # Phase 1: zoom <= 1.05
    p0 = points[0]
    assert p0[0] < 1.02
    
    # Phase 3: zoom >= 1.17
    p_last = points[-1]
    assert p_last[0] >= 1.17
    
    # Verify no static hold across all frames
    passed = check_trajectory_static_hold(points, window_size=25, min_displacement_px=1.5)
    assert passed is True
