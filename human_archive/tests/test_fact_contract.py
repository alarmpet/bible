# -*- coding: utf-8 -*-
"""Test fact contract and source ledger validity against academic consensus."""
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

from validate_fact_contract import validate_contract_and_ledger


def test_rejects_unfounded_myths_in_contract(tmp_path: Path):
    bad_contract = {
        "title": "폼페이 18시간",
        "duration_tier": "standard_docu",
        "target_duration_sec": 1200,
        "core_paradox": "시민 대다수가 머물렀고 재산 집착 때문에 18시간 동안 탈출하지 못했다.",
        "content_disclosure": "재현",
        "opening_hooks": {"hook_12s": "질문", "context_40s": "범위"},
    }
    c_path = tmp_path / "contract.yaml"
    c_path.write_text(yaml.dump(bad_contract), encoding="utf-8")

    l_path = tmp_path / "ledger.json"
    l_path.write_text(json.dumps({"claims": []}), encoding="utf-8")

    errors = validate_contract_and_ledger(c_path, l_path)
    assert any("core_paradox contains unverified claim" in err for err in errors)


def test_requires_duration_within_840_to_1560_seconds(tmp_path: Path):
    bad_contract = {
        "title": "폼페이 최후의 밤",
        "duration_tier": "standard_docu",
        "target_duration_sec": 600, # 10분 - 너무 짧음 (840초 미만)
        "core_paradox": "많은 이들은 떠났고 누가 남았는가?",
        "content_disclosure": "역사적 사료 및 AI 재현 고지",
        "opening_hooks": {"hook_12s": "질문", "context_40s": "범위"},
    }
    c_path = tmp_path / "contract.yaml"
    c_path.write_text(yaml.dump(bad_contract), encoding="utf-8")
    l_path = tmp_path / "ledger.json"
    l_path.write_text(json.dumps({"claims": []}), encoding="utf-8")

    errors = validate_contract_and_ledger(c_path, l_path)
    assert any("target_duration_sec must be between 840 and 1560" in err for err in errors)


def test_actual_contract_and_ledger_pass():
    contract_path = _PROJECT_ROOT / "human_archive" / "templates" / "documentary_contract.yaml"
    ledger_path = _PROJECT_ROOT / "human_archive" / "sources" / "pompeii_ep01_source_ledger.json"

    if not ledger_path.exists():
        pytest.skip("Source ledger not yet created")

    errors = validate_contract_and_ledger(contract_path, ledger_path)
    assert errors == [], f"Validation errors: {errors}"
