from __future__ import annotations

import pytest

from lib.cinematic_effect_planner import (
    CinematicEffectPlanner,
    MotionPhase,
    PlannedProfile,
)


def test_opening_group_generates_three_visible_cuts() -> None:
    planner = CinematicEffectPlanner()
    master = {"shot_id": "SHOT_001", "scene_duration": 11.0, "order": 1}
    profiles = planner.plan_opening_group(master)

    assert len(profiles) == 3
    assert profiles[0].sub_type == "opening_cut_context_wide"
    assert profiles[0].transition_out == "dissolve"
    assert profiles[1].sub_type == "opening_cut_subject_action"
    assert profiles[1].transition_out == "dissolve"
    assert profiles[2].sub_type == "opening_cut_evidence_detail"
    assert profiles[2].transition_out == "hard_cut"


def test_plan_shot_effect_rejects_opening_scenes() -> None:
    planner = CinematicEffectPlanner()
    with pytest.raises(ValueError, match="plan_opening_group"):
        planner.plan_shot_effect({"order": 1}, [])
    with pytest.raises(ValueError, match="plan_opening_group"):
        planner.plan_shot_effect({"order": 2, "scene_role": "opening_group"}, [])


@pytest.mark.parametrize(
    "beat,expected_family",
    [
        ("question", "reframe"),
        ("reveal", "lateral_reveal"),
        ("threat", "threat_push"),
        ("contradiction", "counter_axis_pan"),
        ("evidence", "evidence_macro"),
        ("consequence", "slow_pull_out"),
        ("pause", "ambient_drift"),
    ],
)
def test_seven_beat_motion_grammar_mapping(beat: str, expected_family: str) -> None:
    planner = CinematicEffectPlanner()
    scene = {
        "order": 2,
        "shot_id": "SHOT_002",
        "beat_type": beat,
        "scene_duration": 8.0,
    }
    profile = planner.plan_shot_effect(scene, [])
    assert profile.motion_family == expected_family


def test_anti_monotony_prevents_triple_identical_family() -> None:
    planner = CinematicEffectPlanner()
    history = []
    # Repeat the same beat 5 times
    for i in range(2, 7):
        scene = {
            "order": i,
            "shot_id": f"SHOT_{i:03d}",
            "beat_type": "threat",  # all requesting threat_push
            "scene_duration": 8.0,
        }
        profile = planner.plan_shot_effect(scene, history)
        history.append(profile)

    eval_res = planner.evaluate_diversity_window(history, window_size=5)
    assert eval_res["max_consecutive_family"] <= 2
    assert eval_res["max_consecutive_axis"] <= 2


def test_ten_shot_window_diversity() -> None:
    planner = CinematicEffectPlanner()
    beats = ["question", "reveal", "threat", "contradiction", "evidence", "consequence", "pause"]
    history = []
    for i in range(2, 22):
        scene = {
            "order": i,
            "shot_id": f"SHOT_{i:03d}",
            "beat_type": beats[(i - 2) % len(beats)],
            "scene_duration": 10.0,
        }
        profile = planner.plan_shot_effect(scene, history)
        history.append(profile)

    eval_res = planner.evaluate_diversity_window(history, window_size=10)
    assert eval_res["valid"] is True
    assert eval_res["min_window_family_count"] >= 4


def test_long_take_forces_tri_phasic_motion_and_subtitle_clamp() -> None:
    planner = CinematicEffectPlanner()
    scene = {
        "order": 30,
        "shot_id": "SHOT_030",
        "beat_type": "consequence",
        "scene_duration": 42.0,  # Long take
        "focal_anchor": (0.5, 0.90),  # In subtitle danger zone
    }
    profile = planner.plan_shot_effect(scene, [])
    assert profile.sub_type == "tri_phasic_ken_burns"
    assert len(profile.phases) == 3
    assert profile.phases[0].duration_ratio == 0.35
    assert profile.phases[1].duration_ratio == 0.35
    assert profile.phases[2].duration_ratio == 0.30
    assert profile.clamped_for_subtitles is True
    assert profile.focal_anchor[1] <= 0.75
