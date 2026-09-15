# -*- coding: utf-8 -*-
"""Task 7: plan_narration_shots.py's --profile used to default to the literal
string "narration_aligned_hybrid_v1" no matter which channel profile was
active, so nollam_file_v1 builds never actually used nollam_decay_20m even
though config/channel_profiles.yaml is the documented source of truth for
per-channel policy everywhere else in the pipeline. These tests pin the
resolution order: explicit --profile wins; otherwise read pacing_profile_id
off the channel profile.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from plan_narration_shots import build_timing_profile, resolve_pacing_profile_id  # noqa: E402
from lib.shot_timing import NollamDecayTimingProfile, ShotTimingProfile  # noqa: E402


def test_explicit_profile_always_wins():
    assert resolve_pacing_profile_id("narration_aligned_hybrid_v1", "nollam_file_v1") == "narration_aligned_hybrid_v1"


def test_nollam_file_v1_defaults_to_the_decay_curve_not_the_legacy_flat_profile():
    assert resolve_pacing_profile_id(None, "nollam_file_v1") == "nollam_decay_20m"


def test_doodle_seonbi_v1_defaults_to_the_legacy_flat_profile():
    assert resolve_pacing_profile_id(None, "doodle_seonbi_v1") == "narration_aligned_hybrid_v1"


def test_omitting_channel_profile_falls_back_to_the_config_default_profile_id():
    # channel_profiles.yaml's default_profile_id is nollam_file_v1.
    assert resolve_pacing_profile_id(None, None) == "nollam_decay_20m"


def test_build_timing_profile_returns_zoned_profile_for_nollam_decay_20m():
    profile = build_timing_profile("nollam_decay_20m", total_duration_sec=1200.0)
    assert isinstance(profile, NollamDecayTimingProfile)
    assert profile.profile_id == "nollam_decay_20m"


def test_build_timing_profile_returns_flat_profile_for_narration_aligned_hybrid_v1():
    profile = build_timing_profile("narration_aligned_hybrid_v1", total_duration_sec=600.0)
    assert isinstance(profile, ShotTimingProfile)
