# -*- coding: utf-8 -*-
"""
test_human_library_timeline.py
Validates 100% sentence span coverage, exact zero-gap/zero-overlap continuity,
and 3-Tier dynamic pacing monotonicity.
"""

import json
from pathlib import Path
import pytest

TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent
RUN_DIR = REPO_ROOT / "runs" / "human_library_replica" / "rank1_race_adaptation"
BUNDLE_FILE = RUN_DIR / "metadata" / "normalized_replica_bundle.json"
SCRIPT_FILE = RUN_DIR / "script" / "normalized_script.json"

def test_100pct_sentence_coverage_and_uniqueness():
    with open(BUNDLE_FILE, "r", encoding="utf-8") as f:
        bundle = json.load(f)
    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        script = json.load(f)

    all_script_sentence_ids = [s["sentence_id"] for s in script["sentences"]]
    assert len(all_script_sentence_ids) == 135

    assigned_sentence_ids = []
    for shot in bundle["shots"]:
        spans = shot["sentence_spans"]
        assert len(spans) >= 1, f"Shot {shot['shot_id']} has empty spans!"
        assigned_sentence_ids.extend(spans)

    assert len(assigned_sentence_ids) == 135, f"Expected 135 sentences, got {len(assigned_sentence_ids)}"
    assert len(set(assigned_sentence_ids)) == 135, "Found duplicate sentence assignments!"
    assert assigned_sentence_ids == all_script_sentence_ids, "Sentence ordering mismatch!"

def test_timeline_exact_continuity_zero_gap():
    with open(BUNDLE_FILE, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    shots = bundle["shots"]
    assert shots[0]["start_sec"] == 0.0

    for i in range(len(shots) - 1):
        cur_end = shots[i]["end_sec"]
        next_start = shots[i+1]["start_sec"]
        assert abs(cur_end - next_start) < 0.001, (
            f"Gap detected between {shots[i]['shot_id']} (end={cur_end}) "
            f"and {shots[i+1]['shot_id']} (start={next_start})"
        )

    # Check total duration matches last end
    last_end = shots[-1]["end_sec"]
    assert abs(last_end - bundle["target_duration_sec"]) < 0.01

def test_3tier_dynamic_pacing_monotonicity():
    with open(BUNDLE_FILE, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    shots = bundle["shots"]
    opening_shots = [s for s in shots if s["pacing_tier"] == "Opening"]
    tier1_shots = [s for s in shots if s["pacing_tier"] == "Tier 1"]
    tier2_shots = [s for s in shots if s["pacing_tier"] == "Tier 2"]
    tier3_shots = [s for s in shots if s["pacing_tier"] == "Tier 3"]

    assert len(opening_shots) == 3
    assert len(tier1_shots) == 7
    assert len(tier2_shots) == 12
    assert len(tier3_shots) == 18

    opening_dur = sum(s["duration_sec"] for s in opening_shots)
    assert abs(opening_dur - 11.0) < 0.05

    tier1_avg = sum(s["duration_sec"] for s in tier1_shots) / len(tier1_shots)
    tier2_avg = sum(s["duration_sec"] for s in tier2_shots) / len(tier2_shots)
    tier3_avg = sum(s["duration_sec"] for s in tier3_shots) / len(tier3_shots)

    # Tier 1 avg < Tier 2 avg < Tier 3 avg
    assert tier1_avg < tier2_avg < tier3_avg, (
        f"Monotonicity violation: Tier 1={tier1_avg:.2f}s, Tier 2={tier2_avg:.2f}s, Tier 3={tier3_avg:.2f}s"
    )
    assert 4.0 <= tier1_avg <= 6.0
    assert 15.0 <= tier2_avg <= 20.0
    assert 35.0 <= tier3_avg <= 45.0
