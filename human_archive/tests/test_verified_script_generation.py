# -*- coding: utf-8 -*-
"""Test verified script generation and sentence-level fact verification."""
from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest
import yaml

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.fact_verification import verify_script
from generate_verified_script import generate_pompeii_script


def test_detects_forbidden_wording_and_unsupported_claims():
    fake_claims = {
        "claims": [
            {
                "claim_id": "CLM-001",
                "statement": "Test statement",
                "type": "verified_fact",
                "forbidden_wording": ["500도", "대다수가 머물"],
            }
        ]
    }
    bad_script = {
        "sentences": [
            {
                "sentence_id": "s-bad-1",
                "display_text": "폼페이 전역이 500도 고열로 뒤덮였습니다.",
                "claim_ids": ["CLM-001"],
                "statement_type": "verified_fact",
                "certainty": "fact",
            },
            {
                "sentence_id": "s-bad-2",
                "display_text": "아무런 출처가 없는 허구의 주장입니다.",
                "claim_ids": ["NON_EXISTENT_CLM"],
                "statement_type": "verified_fact",
                "certainty": "fact",
            },
        ]
    }

    report = verify_script(bad_script, fake_claims, {})
    assert report["unsupported_count"] == 1
    assert report["forbidden_wording_count"] >= 1
    assert any(ev["sentence_id"] == "s-bad-1" and ev["status"] == "FAIL" for ev in report["sentence_evaluations"])
    assert any(ev["sentence_id"] == "s-bad-2" and ev["status"] == "FAIL" for ev in report["sentence_evaluations"])


def test_verified_pompeii_script_passes_full_pipeline(tmp_path: Path):
    contract_path = _PROJECT_ROOT / "human_archive" / "templates" / "documentary_contract.yaml"
    ledger_path = _PROJECT_ROOT / "human_archive" / "sources" / "pompeii_ep01_source_ledger.json"

    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    script_draft = generate_pompeii_script(contract, ledger)
    report = verify_script(script_draft, ledger, {})

    assert report["unsupported_count"] == 0
    assert report["unresolved_conflict_count"] == 0
    assert report["forbidden_wording_count"] == 0
    assert all(ev["status"] in ["PASS", "QUALIFIED"] for ev in report["sentence_evaluations"])
