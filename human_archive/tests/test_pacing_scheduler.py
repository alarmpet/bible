from __future__ import annotations

from lib.pacing_scheduler import build_pacing_schedule


def test_runtime_benchmarks_keep_master_budget_and_7_zone_contract() -> None:
    expected = {900: 58, 1200: 71, 1500: 92}
    for runtime, master_count in expected.items():
        schedule = build_pacing_schedule(runtime)
        assert schedule["master_shot_count"] == master_count
        assert len(schedule["zones"]) == 7
        assert len(schedule["master_shots"]) == master_count
        assert schedule["master_shots"][-1]["end_sec"] == runtime


def test_first_hook_is_split_into_fast_perceptual_cuts_without_shortening_master_scene() -> None:
    schedule = build_pacing_schedule(1200)
    first_master = schedule["master_shots"][0]
    first_cuts = [cut for cut in schedule["perceptual_cuts"] if cut["master_shot_id"] == first_master["shot_id"]]

    assert first_master["duration_sec"] == 11.0
    assert len(first_cuts) == 3
    assert first_cuts[0]["duration_sec"] == 3.0
    assert first_cuts[1]["duration_sec"] == 3.5
    assert first_cuts[2]["duration_sec"] == 4.5
    assert first_cuts[0]["visual_role"] == "context_wide"
    assert first_cuts[1]["visual_role"] == "subject_action"
    assert first_cuts[2]["visual_role"] == "evidence_detail"
    assert all(cut["asset_binding"] == "FLOW_IMAGE" for cut in first_cuts)
    assert all(cut["asset_binding"] != "BARETIP_VIDEO" for cut in first_cuts)
    assert first_cuts[0]["start_sec"] == 0.0
    assert first_cuts[-1]["end_sec"] == 11.0


def test_scene_duration_decays_into_deep_long_takes() -> None:
    schedule = build_pacing_schedule(1200)
    by_tier = {
        tier: [shot["duration_sec"] for shot in schedule["master_shots"] if shot["tier"] == tier]
        for tier in ("tier_1_hook", "tier_2_context", "tier_3_deep")
    }
    assert max(by_tier["tier_1_hook"]) <= 4.5 or by_tier["tier_1_hook"][0] == 11.0
    assert 6.0 <= min(by_tier["tier_2_context"]) <= 15.0
    assert all(30.0 <= duration <= 60.0 for duration in by_tier["tier_3_deep"])
    assert sum(by_tier["tier_1_hook"]) == 120.0
    assert sum(by_tier["tier_2_context"]) == 240.0
    assert sum(by_tier["tier_3_deep"]) == 840.0


def test_twenty_minute_budget_produces_130_to_150_perceptual_cuts_and_70_derived_variants() -> None:
    schedule = build_pacing_schedule(1200)
    assert 130 <= schedule["perceptual_cut_count"] <= 150
    assert 70 <= schedule["unique_image_count"] <= 80
    assert 60 <= schedule["derived_variant_count"] <= 70
    assert schedule["perceptual_cuts"][-1]["end_sec"] == 1200.0


def test_zone_boundaries_follow_measured_runtime_ratios() -> None:
    schedule = build_pacing_schedule(900)
    zones = {zone["zone_id"]: zone for zone in schedule["zones"]}
    assert zones["cold_open"]["end_sec"] == 11.25
    assert zones["outro"]["start_sec"] == 832.5
    assert zones["outro"]["end_sec"] == 900.0
