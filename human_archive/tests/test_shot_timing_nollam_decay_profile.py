# -*- coding: utf-8 -*-
"""Task 7 (pacing_scheduler wiring): plan_shot_timing() used to only ever accept
a single flat ShotTimingProfile for the whole episode, hardcode
profile_id="narration_aligned_hybrid_v1" in its output regardless of what was
actually used, and plan_narration_shots.py defaulted --profile to that same
legacy id unconditionally -- so nollam_decay_20m's 7-stage decay curve, fully
defined in config/visual_pacing_profiles.yaml, was reachable only from tests,
never from the real production entry point (2026-09-15 overhaul plan §1.6).

These tests pin: (1) NollamDecayTimingProfile resolves each zone's bounds
correctly against a measured total duration, including the dynamic
end-relative late_body/outro zones; (2) plan_shot_timing() actually applies
different bounds to shots in different zones instead of one flat profile for
the whole episode; (3) the output profile_id honestly reflects what was used.
"""
from __future__ import annotations

from lib.shot_timing import NollamDecayTimingProfile, ShotTimingProfile, plan_shot_timing

NOLLAM_DECAY_ZONES = [
    {"zone_id": "cold_open", "start_sec": 0, "end_sec": 15,
     "target_shot_sec": 4.0, "min_shot_sec": 3.0, "hard_max_shot_sec": 5.0, "max_sentences_per_shot": 1},
    {"zone_id": "hook", "start_sec": 15, "end_sec": 60,
     "target_shot_sec": 4.5, "min_shot_sec": 3.5, "hard_max_shot_sec": 6.0, "max_sentences_per_shot": 2},
    {"zone_id": "roadmap", "start_sec": 60, "end_sec": 120,
     "target_shot_sec": 6.5, "min_shot_sec": 5.0, "hard_max_shot_sec": 9.0, "max_sentences_per_shot": 2},
    {"zone_id": "early_body", "start_sec": 120, "end_sec": 300,
     "target_shot_sec": 8.5, "min_shot_sec": 6.0, "hard_max_shot_sec": 12.0, "max_sentences_per_shot": 2},
    {"zone_id": "body", "start_sec": 300, "end_sec": 600,
     "target_shot_sec": 10.0, "min_shot_sec": 7.0, "hard_max_shot_sec": 14.0, "max_sentences_per_shot": 2},
    {"zone_id": "late_body", "start_sec": 600, "end_offset_from_end_sec": 90,
     "target_shot_sec": 11.5, "min_shot_sec": 8.0, "hard_max_shot_sec": 15.0, "max_sentences_per_shot": 2},
    {"zone_id": "outro", "start_sec": -1, "end_offset_from_end_sec": 90,
     "target_shot_sec": 12.5, "min_shot_sec": 9.0, "hard_max_shot_sec": 18.0, "max_sentences_per_shot": 2},
]


def test_zone_bounds_resolve_correctly_across_the_curve_at_nominal_1200s():
    profile = NollamDecayTimingProfile("nollam_decay_20m", NOLLAM_DECAY_ZONES, total_duration_sec=1200.0)

    assert profile.bounds_for(5.0).target_shot_sec == 4.0     # cold_open
    assert profile.bounds_for(5.0).max_sentences_per_shot == 1
    assert profile.bounds_for(30.0).target_shot_sec == 4.5    # hook
    assert profile.bounds_for(90.0).target_shot_sec == 6.5    # roadmap
    assert profile.bounds_for(200.0).target_shot_sec == 8.5   # early_body
    assert profile.bounds_for(450.0).target_shot_sec == 10.0  # body
    assert profile.bounds_for(700.0).target_shot_sec == 11.5  # late_body (600 <= t < 1200-90=1110)
    assert profile.bounds_for(1150.0).target_shot_sec == 12.5  # outro (>= 1110)


def test_late_body_and_outro_scale_with_actual_measured_duration_not_a_fixed_1200s():
    # A measured runtime of 900s (within the documented 14-26 min tolerance)
    # must NOT reuse the 1200s-nominal outro boundary of 1110 -- it should be
    # end-relative: outro starts at 900 - 90 = 810.
    profile = NollamDecayTimingProfile("nollam_decay_20m", NOLLAM_DECAY_ZONES, total_duration_sec=900.0)

    assert profile.bounds_for(805.0).target_shot_sec == 11.5  # still late_body
    assert profile.bounds_for(815.0).target_shot_sec == 12.5  # now outro


def test_late_body_and_outro_still_win_when_short_duration_makes_them_overlap_early_body():
    """2026-09-16 finding from a real quick_3m (~190s) episode: early_body's
    fixed end_sec=300 and late_body's fixed start_sec=600 are calibrated for
    the nominal 1200s curve and don't shrink with a much shorter measured
    duration, so outro's dynamic start (total-90) can fall inside early_body's
    still-fixed [120, 300) range. The real end of a short episode must still
    resolve to outro's pacing, not early_body's stale bounds."""
    total = 190.0  # quick_3m-scale
    profile = NollamDecayTimingProfile("nollam_decay_20m", NOLLAM_DECAY_ZONES, total_duration_sec=total)

    # outro dynamically starts at 190 - 90 = 100s, well inside early_body's
    # fixed [120, 300) -- wait, 100 < 120, so also check a point that lands in
    # the genuine overlap window [120, 190):
    assert profile.bounds_for(150.0).target_shot_sec == 12.5  # outro, not early_body's 8.5
    assert profile.bounds_for(189.0).target_shot_sec == 12.5  # the true final seconds
    # times before outro's dynamic start still resolve to the normal curve
    assert profile.bounds_for(30.0).target_shot_sec == 4.5    # hook
    assert profile.bounds_for(65.0).target_shot_sec == 6.5    # roadmap


def test_plan_shot_timing_applies_different_zone_bounds_to_the_same_episode():
    """A script whose early sentences fall in cold_open (target 4s) and later
    ones fall in body (target 10s) must actually get different shot groupings
    -- not the single flat profile the old hardcoded entry point always used."""
    profile = NollamDecayTimingProfile("nollam_decay_20m", NOLLAM_DECAY_ZONES, total_duration_sec=1200.0)

    # Two short sentences early (inside cold_open, 0-15s): cold_open's
    # max_sentences_per_shot=1 forces them into separate shots even though a
    # flat 2-sentence-per-shot profile would combine them.
    script = {
        "episode_id": "HA_NOLLAM_TEST",
        "sentences": [
            {"sentence_id": "S1", "order": 1, "chapter": 1, "beat": "hook", "tts_text": "하나"},
            {"sentence_id": "S2", "order": 2, "chapter": 1, "beat": "hook", "tts_text": "둘"},
            {"sentence_id": "S3", "order": 3, "chapter": 1, "beat": "body", "tts_text": "셋"},
            {"sentence_id": "S4", "order": 4, "chapter": 1, "beat": "body", "tts_text": "넷"},
        ],
    }
    audio = {
        "sentences": [
            {"sentence_id": "S1", "start_sec": 0.0, "end_sec": 3.5},
            {"sentence_id": "S2", "start_sec": 3.5, "end_sec": 7.0},
            {"sentence_id": "S3", "start_sec": 350.0, "end_sec": 356.0},
            {"sentence_id": "S4", "start_sec": 356.0, "end_sec": 361.0},
        ],
    }

    result = plan_shot_timing(script, audio, {}, profile, profile_id="nollam_decay_20m")

    # cold_open: forced to split (max_sentences_per_shot=1)
    cold_open_shots = [s for s in result["shots"] if s["start_sec"] < 15.0]
    assert len(cold_open_shots) == 2, "cold_open zone must force one sentence per shot"

    # body zone (S3/S4 at ~350s): max_sentences_per_shot=2, short sentences
    # under target -> combined into one shot like the legacy flat profile would.
    body_shots = [s for s in result["shots"] if s["start_sec"] >= 300.0]
    assert len(body_shots) == 1
    assert [seg["sentence_id"] for seg in body_shots[0]["sentence_spans"]] == ["S3", "S4"]

    assert result["profile_id"] == "nollam_decay_20m"


def test_plan_shot_timing_still_defaults_profile_id_for_flat_profiles_without_explicit_override():
    # Backward-compat: existing callers that pass a flat ShotTimingProfile
    # without profile_id= keep getting the historical default label.
    profile = ShotTimingProfile(9, 10.5, 12, 15, 2)
    script = {
        "episode_id": "HA002",
        "sentences": [{"sentence_id": "S1", "order": 1, "chapter": 1, "beat": "body", "tts_text": "하나"}],
    }
    audio = {"sentences": [{"sentence_id": "S1", "start_sec": 0, "end_sec": 4}]}
    result = plan_shot_timing(script, audio, {}, profile)
    assert result["profile_id"] == "narration_aligned_hybrid_v1"
