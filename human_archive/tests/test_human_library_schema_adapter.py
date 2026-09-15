# -*- coding: utf-8 -*-
"""
test_human_library_schema_adapter.py
Validates canonical schema adaptation, required fields, and jsonschema integrity.
"""

import json
from pathlib import Path
import pytest
import jsonschema

TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent
RUN_DIR = REPO_ROOT / "runs" / "human_library_replica" / "rank1_race_adaptation"
SCHEMA_FILE = REPO_ROOT / "schemas" / "human_library_replica_contract_v1.schema.json"
BUNDLE_FILE = RUN_DIR / "metadata" / "normalized_replica_bundle.json"

def test_bundle_file_exists():
    assert BUNDLE_FILE.exists(), f"Normalized bundle not found: {BUNDLE_FILE}"
    assert SCHEMA_FILE.exists(), f"Schema file not found: {SCHEMA_FILE}"

def test_bundle_conforms_to_schema():
    with open(BUNDLE_FILE, "r", encoding="utf-8") as f:
        bundle = json.load(f)
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        schema = json.load(f)

    jsonschema.validate(instance=bundle, schema=schema)

def test_canonical_fields_present_and_clean():
    with open(BUNDLE_FILE, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    assert bundle["schema_version"] == 1
    assert bundle["episode_id"] == "human_library_rank1_race_adaptation"
    assert bundle["total_shots"] == 40
    assert bundle["total_sentences"] == 135

    valid_tiers = {"Opening", "Tier 1", "Tier 2", "Tier 3"}
    for idx, shot in enumerate(bundle["shots"]):
        assert shot["shot_id"] == f"SHOT_{idx+1:03d}"
        assert shot["order"] == idx + 1
        assert shot["pacing_tier"] in valid_tiers
        assert shot["duration_sec"] > 0
        assert shot["end_sec"] > shot["start_sec"]
        assert len(shot["sentence_spans"]) >= 1
        assert len(shot["spoken_text"]) > 0
        assert len(shot["display_text"]) > 0

        # Visual contract
        vis = shot["visual"]
        assert len(vis["subject"]) > 0
        assert len(vis["prompt_en"]) >= 20

        # Motion profile
        motion = shot["motion_profile"]
        assert motion["motion_family"] in {
            "push_in", "pull_out", "pan", "tilt", "biphasic_ken_burns", "tri_phasic"
        }
        assert motion["axis"] in {
            "z_forward", "z_backward", "x_right", "x_left", "y_up", "y_down", "compound"
        }
