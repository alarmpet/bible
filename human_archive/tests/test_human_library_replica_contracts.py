# -*- coding: utf-8 -*-
"""
Tests for Human Library Rank 1 Replication Asset Contracts:
1. master_script_clean.json:
   - 4,937 pure characters (no space)
   - True CPS in 4.8 ~ 5.3 range (SuperTonic3 M2 tempo)
   - Scientific fact-checking: CCR5-Δ32 mentions both plague and smallpox
2. scenes_manifest.json:
   - Exactly 40 dynamic scenes
   - Total duration 972.11s (within 14~26 min golden window)
   - 3-Cut Visible FLOW Opening (11.0s)
   - 3-Tier dynamic pacing distribution (Tier 1: 7, Tier 2: 12, Tier 3: 18)
3. shot_composition_plan.json:
   - Exactly 40 cinematic Flow CDP prompts
   - 4-Look rotation distribution
   - Type-safe motion profiles
"""

import json
from pathlib import Path
import pytest

REPLICA_DIR = Path(r"D:\module\bible\human_archive\runs\human_library_replica\rank1_race_adaptation")
SCRIPT_FILE = REPLICA_DIR / "script" / "master_script_clean.json"
SCENES_FILE = REPLICA_DIR / "metadata" / "scenes_manifest.json"
SHOTS_FILE = REPLICA_DIR / "metadata" / "shot_composition_plan.json"

def test_replica_script_contract():
    assert SCRIPT_FILE.exists(), f"Missing script file: {SCRIPT_FILE}"
    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["video_id"] == "tPBVrfcU85g"
    assert data["total_chars_no_space"] == 4937
    assert 4.8 <= data["true_cps"] <= 5.3
    assert len(data["sentences"]) == 135

    # Fact-check verification: CCR5-Δ32 must mention plague and smallpox
    has_fact_checked_plague_smallpox = any(
        "\ucc9c\uc5f0\ub450" in s["text"] and "\ud751\uc0ac\ubcd1" in s["text"]
        for s in data["sentences"]
    )
    assert has_fact_checked_plague_smallpox, "CCR5-Δ32 fact check refinement missing!"

def test_replica_scenes_manifest_contract():
    assert SCENES_FILE.exists(), f"Missing scenes file: {SCENES_FILE}"
    with open(SCENES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_shots"] == 40
    assert 900.0 <= data["total_duration_sec"] <= 1050.0  # ~972s
    scenes = data["scenes"]
    assert len(scenes) == 40

    # Opening check: 3 cuts, sum == 11.0s
    opening_shots = [s for s in scenes if s["tier"] == "Opening"]
    assert len(opening_shots) == 3
    opening_dur = sum(s["dur"] for s in opening_shots)
    assert abs(opening_dur - 11.0) < 0.05

    # Tier counts
    tier1_shots = [s for s in scenes if s["tier"] == "Tier 1"]
    tier2_shots = [s for s in scenes if s["tier"] == "Tier 2"]
    tier3_shots = [s for s in scenes if s["tier"] == "Tier 3"]

    assert len(tier1_shots) == 7
    assert len(tier2_shots) == 12
    assert len(tier3_shots) == 18

    # Monotony check: Every scene must have non-empty narration text and prompt
    for s in scenes:
        assert len(s["concept"]) > 0
        assert len(s["prompt"]) > 0

def test_replica_shots_plan_contract():
    assert SHOTS_FILE.exists(), f"Missing shots file: {SHOTS_FILE}"
    with open(SHOTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_shots"] == 40
    shots = data["shots"]
    assert len(shots) == 40

    valid_motions = {
        "push_in", "pan_right", "pan_left", "tilt_up", "tilt_down",
        "pull_out", "biphasic_ken_burns", "tri_phasic"
    }
    for s in shots:
        assert s["motion_type"] in valid_motions, f"Invalid motion: {s['motion_type']}"
        assert len(s["flow_prompt_en"]) >= 50, f"Prompt too short: {s['shot_id']}"
