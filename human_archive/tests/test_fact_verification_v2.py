# -*- coding: utf-8 -*-
"""Test fact verification v2 against fabricated text and empty collections."""
from __future__ import annotations

import copy
import sys
from pathlib import Path
import pytest

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.fact_verification import verify_script


@pytest.fixture
def valid_fact_inputs(valid_evidence):
    ledger, snapshots = valid_evidence
    claims = {"claims": ledger["claims"]}
    script = {
        "schema_version": 2,
        "episode_id": "EP01",
        "persona": "ship_seonbi",
        "title": "테스트",
        "target_duration_sec": 930,
        "sentences": [
            {
                "sentence_id": "s-01",
                "beat": "body",
                "display_text": "소 플리니우스는 미세눔에서 거대한 소나무 모양 구름을 목격했습니다.",
                "segments": [
                    {
                        "kind": "fact",
                        "text": "소 플리니우스는 미세눔에서 거대한 소나무 모양 구름을 목격했습니다.",
                        "claim_id": "CLM-001",
                        "evidence_span_ids": ["SRC-PLINY:SPAN-01"],
                    }
                ],
            }
        ],
    }
    return script, claims, snapshots


def test_rejects_fabricated_text_with_existing_claim(valid_fact_inputs):
    script, claims, snapshots = valid_fact_inputs
    script["sentences"][0]["segments"][0]["text"] = "모든 시민 몰살당했다."
    report = verify_script(script, claims, snapshots)
    assert report["overall_status"] == "FAIL"
    assert report["fail_count"] >= 1


def test_rejects_empty_sentence_collection(valid_evidence):
    ledger, snapshots = valid_evidence
    claims = {"claims": ledger["claims"]}
    report = verify_script({"schema_version": 2, "sentences": []}, claims, snapshots)
    assert report["overall_status"] == "FAIL"


def test_rejects_nonexistent_evidence_span_id(valid_fact_inputs):
    script, claims, snapshots = copy.deepcopy(valid_fact_inputs)
    script["sentences"][0]["segments"][0]["evidence_span_ids"] = ["SRC-PLINY:NONEXISTENT-SPAN"]
    report = verify_script(script, claims, snapshots)
    assert report["overall_status"] == "FAIL"
    assert any("not found in source snapshots" in w for w in report["warnings"])


def test_direct_quote_requires_evidence_span(valid_fact_inputs):
    script, claims, snapshots = copy.deepcopy(valid_fact_inputs)
    script["sentences"][0]["segments"][0]["kind"] = "direct_quote"
    script["sentences"][0]["segments"][0]["evidence_span_ids"] = []
    report = verify_script(script, claims, snapshots)
    assert report["overall_status"] == "FAIL"
    assert any("Direct quote segment requires evidence_span_ids" in w for w in report["warnings"])

