# -*- coding: utf-8 -*-
"""Assembly-stage SuperTonic pacing (guide 0.05 / 0.6)."""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from tts_assembly import assembly_gap_seconds, load_assembly_policy  # noqa: E402


def test_same_speaker_gap_is_short():
    policy = {"assembly_gap_same_speaker": 0.05, "assembly_gap_scene": 0.6}
    assert assembly_gap_seconds("narrator", "narrator", policy) == 0.05
    assert assembly_gap_seconds("scripture", "scripture", policy) == 0.05


def test_speaker_change_uses_scene_gap():
    policy = {"assembly_gap_same_speaker": 0.05, "assembly_gap_scene": 0.6}
    assert assembly_gap_seconds("narrator", "scripture", policy) == 0.6


def test_first_clip_has_no_leading_gap():
    policy = {"assembly_gap_same_speaker": 0.05, "assembly_gap_scene": 0.6}
    assert assembly_gap_seconds(None, "narrator", policy) == 0.0


def test_lock_defaults_match_guide():
    policy = load_assembly_policy(
        {"tts": {"assembly_gap_same_speaker": 0.05, "assembly_gap_scene": 0.6}}
    )
    assert policy["same"] == 0.05
    assert policy["scene"] == 0.6
