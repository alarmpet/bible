# -*- coding: utf-8 -*-
"""Test Evidence Contract v2 and Claim Ledger validation."""
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

from validate_fact_contract import validate_evidence_package


def test_rejects_ledger_notes_as_evidence_excerpt(valid_evidence):
    ledger, snapshots = copy.deepcopy(valid_evidence)
    snapshots["sources"][0]["evidence_spans"][0]["capture_method"] = "ledger_notes_copy"
    errors = validate_evidence_package(ledger, snapshots)
    assert any("ledger notes are not evidence" in err.lower() or "capture_method" in err for err in errors)


def test_high_risk_claim_requires_two_independent_sources(valid_evidence):
    ledger, snapshots = copy.deepcopy(valid_evidence)
    ledger["claims"][0]["risk"] = "high"
    ledger["claims"][0]["evidence_refs"] = ["SRC-PLINY:SPAN-01"]
    errors = validate_evidence_package(ledger, snapshots)
    assert any("high-risk claim requires two independent sources" in err.lower() for err in errors)
