# -*- coding: utf-8 -*-
"""Test cross-episode neutral prompt generation and entity isolation."""
from __future__ import annotations

import sys
from pathlib import Path
import pytest
import yaml

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.script_generation import build_prompt_context


@pytest.fixture
def ep01_package():
    c_path = _PROJECT_ROOT / "human_archive" / "templates" / "documentary_contract.yaml"
    contract = yaml.safe_load(c_path.read_text(encoding="utf-8"))
    inventory = {
        "schema_version": 2,
        "episode_id": "HA001",
        "claims": [{"claim_id": "POM-01", "statement": "폼페이 탈출", "risk": "low", "evidence_refs": [], "allowed_wording": [], "forbidden_wording": []}],
    }
    snapshots = {"schema_version": 2, "sources": []}
    pol_path = _PROJECT_ROOT / "human_archive" / "config" / "seonbi_narration_policy.yaml"
    policy = yaml.safe_load(pol_path.read_text(encoding="utf-8"))
    return {"contract": contract, "inventory": inventory, "snapshots": snapshots, "policy": policy}


@pytest.fixture
def generic_package():
    c_path = _PROJECT_ROOT / "human_archive" / "tests" / "fixtures" / "episode_generic_v2.yaml"
    contract = yaml.safe_load(c_path.read_text(encoding="utf-8"))
    inventory = {
        "schema_version": 2,
        "episode_id": "GENERIC-002",
        "claims": [{"claim_id": "ALEX-01", "statement": "알렉산드리아 도서관", "risk": "low", "evidence_refs": [], "allowed_wording": [], "forbidden_wording": []}],
    }
    snapshots = {"schema_version": 2, "sources": []}
    pol_path = _PROJECT_ROOT / "human_archive" / "config" / "seonbi_narration_policy.yaml"
    policy = yaml.safe_load(pol_path.read_text(encoding="utf-8"))
    return {"contract": contract, "inventory": inventory, "snapshots": snapshots, "policy": policy}


def test_two_episode_packages_do_not_leak_entities(ep01_package, generic_package):
    ep01 = build_prompt_context(**ep01_package)
    generic = build_prompt_context(**generic_package)
    assert "폼페이" in ep01
    assert "폼페이" not in generic
    assert ep01_package["contract"]["episode_id"] != generic_package["contract"]["episode_id"]
