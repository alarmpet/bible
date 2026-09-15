# -*- coding: utf-8 -*-
from __future__ import annotations
import pytest

from lib.cinematic_effect_planner import (
    CinematicEffectPlanner,
    adapt_planned_to_render_profile,
)

def test_cut_intervals_no_gap_or_overlap():
    planner = CinematicEffectPlanner()
    master = {"shot_id": "SHOT_001", "scene_duration": 11.0, "order": 1}
    profiles = planner.plan_opening_group(master)
    
    # 3 cuts must partition 11.0s without gaps
    ratios = [p.phases[0].duration_ratio for p in profiles]
    assert round(sum(ratios), 4) == 1.0
    
    # Check tri-phasic phases
    scene_tri = {"order": 25, "shot_id": "SHOT_025", "scene_duration": 45.0, "beat_type": "threat"}
    p_tri = planner.plan_shot_effect(scene_tri, [])
    tri_ratios = [ph.duration_ratio for ph in p_tri.phases]
    assert len(tri_ratios) == 3
    assert round(sum(tri_ratios), 4) == 1.0
    assert tri_ratios[0] == 0.35
    assert tri_ratios[1] == 0.35
    assert tri_ratios[2] == 0.30
