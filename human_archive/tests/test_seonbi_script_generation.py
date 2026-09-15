# -*- coding: utf-8 -*-
"""Test ShipSeonbi (쉽선비) persona script generation and fact-preserving verification."""
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
from generate_verified_script import generate_seonbi_pompeii_script


def test_seonbi_script_contains_signature_voice_and_analogies():
    contract_path = _PROJECT_ROOT / "human_archive" / "templates" / "documentary_contract.yaml"
    ledger_path = _PROJECT_ROOT / "human_archive" / "sources" / "pompeii_ep01_source_ledger.json"

    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    script_seonbi = generate_seonbi_pompeii_script(contract, ledger)
    assert script_seonbi["persona"] == "ship_seonbi"
    assert len(script_seonbi["sentences"]) >= 12

    # Check for hook and signature endings
    all_text = " ".join(s["display_text"] for s in script_seonbi["sentences"])
    assert "천만의 말씀" in all_text
    assert "덤프트럭" in all_text # Modern analogy
    assert any(s["display_text"].endswith("지요.") or s["display_text"].endswith("답니다.") for s in script_seonbi["sentences"])


def test_seonbi_script_passes_strict_fact_verification():
    contract_path = _PROJECT_ROOT / "human_archive" / "templates" / "documentary_contract.yaml"
    ledger_path = _PROJECT_ROOT / "human_archive" / "sources" / "pompeii_ep01_source_ledger.json"

    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    script_seonbi = generate_seonbi_pompeii_script(contract, ledger)
    report = verify_script(script_seonbi, ledger, {})

    assert report["unsupported_count"] == 0
    assert report["unresolved_conflict_count"] == 0
    assert report["forbidden_wording_count"] == 0
    assert all(ev["status"] in ["PASS", "QUALIFIED"] for ev in report["sentence_evaluations"])
