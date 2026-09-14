# -*- coding: utf-8 -*-
"""
test_human_library_rank2_pilot_gate.py
Automated test suite verifying Gate 3 (Pacing), Gate 4 (Audio Contract),
Gate 5 (Asset Contract), and Gate 6 (Render Motion Binding) for Rank 2 Pilot-5 (23.5s).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest
from jsonschema import validate

TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent
RUN_DIR = REPO_ROOT / "runs" / "human_library_replica" / "rank2_forgotten_civilization"
METADATA_DIR = RUN_DIR / "metadata"
SCHEMA_FILE = REPO_ROOT / "schemas" / "human_library_replica_contract_v1.schema.json"
PILOT_BUNDLE_FILE = METADATA_DIR / "pilot_5_bundle.json"

SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from pilot_5_rank2_gate_verifier import (
    verify_gate3_pacing,
    verify_gate4_audio_contract,
    verify_gate5_asset_contract,
    verify_gate6_render_motion_binding,
    run_full_pilot_verification,
)


@pytest.fixture
def pilot_bundle() -> dict:
    assert PILOT_BUNDLE_FILE.exists(), f"Rank 2 Pilot bundle missing: {PILOT_BUNDLE_FILE}"
    with open(PILOT_BUNDLE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def test_rank2_pilot_bundle_exists_and_conforms_to_schema(pilot_bundle):
    assert SCHEMA_FILE.exists()
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # Validate against JSON schema
    validate(instance=pilot_bundle, schema=schema)
    assert pilot_bundle["total_shots"] == 5
    assert pilot_bundle["target_duration_sec"] == 23.5
    assert len(pilot_bundle["shots"]) == 5
    assert pilot_bundle["total_sentences"] == 5


def test_rank2_pilot_gate3_pacing(pilot_bundle):
    res = verify_gate3_pacing(pilot_bundle)
    assert res["status"] == "PASS"
    assert res["total_duration_sec"] == 23.5
    assert res["opening_cuts"] == 3
    assert res["tier1_cuts"] == 2
    assert len(res["motion_families"]) == 5
    # Ensure no 3 consecutive identical motion families
    fams = res["motion_families"]
    for i in range(len(fams) - 2):
        assert not (fams[i] == fams[i+1] == fams[i+2])
    # 5 distinct look types
    assert len(set(res["look_types"])) == 5


def test_rank2_pilot_gate4_audio_contract_and_fail_closed(pilot_bundle):
    # 1. Offline test mode (check_live_service=False) passes with pre-mux parity <= 0.040s
    res = verify_gate4_audio_contract(pilot_bundle, check_live_service=False)
    assert res["status"] == "PASS"
    assert res["pre_mux_parity_diff_sec"] <= 0.040
    assert res["target_sample_rate"] == 48000
    assert res["channels"] == 2
    assert len(res["sentence_specs"]) == 5

    # 2. Live service fail-closed check: if service is offline, check_live_service=True must raise ConnectionError
    if not res["service_online"]:
        with pytest.raises(ConnectionError, match="Gate 4 FAIL-CLOSED"):
            verify_gate4_audio_contract(pilot_bundle, check_live_service=True)


def test_rank2_pilot_gate5_asset_contract_and_prompt_safety(pilot_bundle):
    # 1. Offline test mode passes with 0 forbidden words
    res = verify_gate5_asset_contract(pilot_bundle, check_live_service=False)
    assert res["status"] == "PASS"
    assert res["forbidden_words_found"] == 0
    assert res["total_prompts_checked"] == 5

    # 2. Live service fail-closed check: if service is offline, check_live_service=True must raise ConnectionError
    if not res["service_online"]:
        with pytest.raises(ConnectionError, match="Gate 5 FAIL-CLOSED"):
            verify_gate5_asset_contract(pilot_bundle, check_live_service=True)


def test_rank2_pilot_gate6_render_motion_binding(pilot_bundle):
    res = verify_gate6_render_motion_binding(pilot_bundle)
    assert res["status"] == "PASS"
    assert res["total_bindings"] == 5

    expected_canonical = ["push_in", "pan_right", "pull_out", "push_in", "biphasic_ken_burns"]
    actual_canonical = [b["canonical_renderer_motion"] for b in res["bindings"]]
    assert actual_canonical == expected_canonical, f"Expected {expected_canonical}, got {actual_canonical}"

    for b in res["bindings"]:
        assert b["canonical_renderer_motion"] == b["dto_canonical"]
        assert b["clamped_for_subtitles"] is True


def test_rank2_pilot_full_verification_report():
    report = run_full_pilot_verification(check_live_services=False)
    assert report["overall_status"] == "ALL_GATES_PASSED"
    assert report["gates"]["gate3_pacing"]["status"] == "PASS"
    assert report["gates"]["gate4_audio"]["status"] == "PASS"
    assert report["gates"]["gate5_asset"]["status"] == "PASS"
    assert report["gates"]["gate6_render"]["status"] == "PASS"
