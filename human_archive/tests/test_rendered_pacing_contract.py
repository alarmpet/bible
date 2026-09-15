# -*- coding: utf-8 -*-
from __future__ import annotations
import pytest
from pathlib import Path

from lib.cinematic_effect_planner import (
    CinematicEffectPlanner,
    adapt_planned_to_render_profile,
    resolve_render_motion,
)
from smooth_subpixel_motion_engine import (
    compute_trajectory,
    compute_perceptual_cut_trajectory,
    compute_tri_phasic_trajectory,
    render_perceptual_cut_subscenes,
)

def test_fifteen_second_opening_and_tier_pacing():
    planner = CinematicEffectPlanner()
    
    # 1. Opening group (scene 1)
    opening_shots = planner.plan_opening_group({"shot_id": "SHOT_001", "scene_duration": 11.0, "order": 1})
    assert len(opening_shots) == 3
    assert opening_shots[0].sub_type == "opening_cut_context_wide"
    assert opening_shots[1].sub_type == "opening_cut_subject_action"
    assert opening_shots[2].sub_type == "opening_cut_evidence_detail"
    
    # Total duration of opening is 11.0s
    dur1 = 11.0 * opening_shots[0].phases[0].duration_ratio
    dur2 = 11.0 * opening_shots[1].phases[0].duration_ratio
    dur3 = 11.0 * opening_shots[2].phases[0].duration_ratio
    assert round(dur1 + dur2 + dur3, 2) == 11.0
    
    # 2. Tier 1 Subcut (scene 2, ~8.0s)
    traj_subcut = [compute_perceptual_cut_trajectory(f, 200, fps=25, cut_time_sec=5.0) for f in range(200)]
    # Frame 124 (before 5.0s = 125 frames) has zoom ~1.02-1.06
    assert traj_subcut[124][0] < 1.07
    # Frame 125 (after 5.0s) jumps to >= 1.18
    assert traj_subcut[125][0] >= 1.18
    
    # 3. Tier 3 Tri-Phasic long take (scene 22, 40s)
    traj_tri = [compute_tri_phasic_trajectory(f, 1000) for f in range(1000)]
    # Phase 1: zoom <= 1.05
    assert traj_tri[0][0] < 1.02
    assert traj_tri[350][0] <= 1.06
    # Phase 2: zoom up to 1.17
    assert traj_tri[700][0] >= 1.16
    # Phase 3: zoom up to 1.22
    assert traj_tri[999][0] >= 1.20
