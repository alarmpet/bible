# -*- coding: utf-8 -*-
"""Test canonical shot contract compilation and schema validation."""
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

from compile_shot_contract import compile_contract
from validate_shot_contract import validate_shot_plan_and_contract


def test_rejects_duplicate_or_invalid_shots(tmp_path: Path):
    bad_plan = {
        "shots": [
            {
                "shot_id": "ch1_01",
                "order": 1,
                "chapter": 1,
                "sentence_ids": ["s-999"], # Non-existent sentence
                "visual": {"subject": ["Test"], "place": "Rome", "era": "Ancient"}, # Missing action
            },
            {
                "shot_id": "ch1_01", # Duplicate ID
                "order": 1,        # Duplicate order
                "chapter": 1,
                "sentence_ids": [],
                "visual": {},
            },
        ]
    }
    p_path = tmp_path / "shot_plan.yaml"
    p_path.write_text(yaml.dump(bad_plan), encoding="utf-8")

    errors, report = validate_shot_plan_and_contract(p_path, None)
    assert any("Duplicate shot_id" in err for err in errors)
    assert any("Duplicate order" in err for err in errors)
    assert any("Missing required visual anchor" in err for err in errors)


def test_compiled_shot_contract_passes_validation(tmp_path: Path):
    source_dir = _PROJECT_ROOT / "human_archive" / "runs" / "ep01_pompeii_rebuild_v2" / "source"
    shot_plan = source_dir / "shot_plan.yaml"
    script_draft = source_dir / "script_draft.json"
    claims = source_dir / "claim_inventory.json"
    fact_appr = source_dir / "approvals" / "fact_approval.json"
    plan_appr = source_dir / "approvals" / "shot_plan_approval.json"
    out_contract = tmp_path / "shot_contract.json"

    contract = compile_contract(
        shot_plan,
        script_draft,
        claims,
        fact_appr,
        plan_appr,
        out_contract,
    )

    assert contract["contract_sha256"] != ""
    assert len(contract["shots"]) == 12

    errors, report = validate_shot_plan_and_contract(None, out_contract)
    assert errors == [], f"Validation errors: {errors}"


def test_contract_schema_validation_is_not_silently_skipped(tmp_path: Path):
    contract = tmp_path / "run" / "source" / "shot_contract.json"
    contract.parent.mkdir(parents=True)
    contract.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")

    errors, _ = validate_shot_plan_and_contract(None, contract)

    assert any("schema violation" in error.lower() for error in errors)
