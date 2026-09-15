# -*- coding: utf-8 -*-
"""
test_human_library_asset_provenance.py
Validates Gate 0 evidence manifest, fact inventory DOIs, and opening visibility.
"""

import json
from pathlib import Path
import pytest

TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent
RUN_DIR = REPO_ROOT / "runs" / "human_library_replica" / "rank1_race_adaptation"
EVIDENCE_FILE = RUN_DIR / "metadata" / "source_evidence_manifest.json"
FACT_FILE = RUN_DIR / "metadata" / "scientific_fact_inventory.json"
BUNDLE_FILE = RUN_DIR / "metadata" / "normalized_replica_bundle.json"

def test_source_evidence_manifest_integrity():
    assert EVIDENCE_FILE.exists(), f"Evidence file missing: {EVIDENCE_FILE}"
    with open(EVIDENCE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["gate"] == "Gate 0 - Evidence & Originality Gate"
    assert data["status"] == "PASSED"
    assert data["provenance_metrics"]["raw_cue_count"] == 406
    assert data["provenance_metrics"]["logical_sentence_count"] == 135
    assert data["provenance_metrics"]["clean_char_count_no_space"] == 4937

    # All files in inventory must exist and have valid sha256
    for name, item in data["evidence_file_inventory"].items():
        assert item["exists"] is True, f"Evidence file not found: {name} ({item['path']})"
        assert len(item["sha256"]) == 64, f"Invalid SHA-256 for: {name}"

def test_scientific_fact_inventory_citations():
    assert FACT_FILE.exists(), f"Fact file missing: {FACT_FILE}"
    with open(FACT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    claims = data["claims"]
    assert len(claims) == 7

    # Ensure all claims have valid DOI citations
    for c in claims:
        assert c["claim_id"].startswith("CLAIM_")
        assert len(c["citations"]) >= 1
        for cite in c["citations"]:
            assert "doi" in cite and len(cite["doi"]) > 5

    # Check dual plague + smallpox in Claim 7
    claim7 = [c for c in claims if c["claim_id"] == "CLAIM_007"][0]
    assert "천연두" in claim7["statement"]
    assert "흑사병" in claim7["statement"]

def test_opening_3cut_visible_first_invariants():
    with open(BUNDLE_FILE, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    shots = bundle["shots"]
    opening_shots = shots[:3]

    assert opening_shots[0]["look_type"] == "context_wide"
    assert opening_shots[1]["look_type"] == "subject_action"
    assert opening_shots[2]["look_type"] == "evidence_detail"

    for s in opening_shots:
        # Must not be bare-tip or placeholder
        assert "bare_tip" not in s["visual"]["prompt_en"].lower()
        assert len(s["visual"]["prompt_en"]) > 50
