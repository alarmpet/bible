# -*- coding: utf-8 -*-
"""Test provider flow asset generation and fail-closed timeout logic."""
from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.provider_flow import FlowProviderAdapter
from generate_flow_assets_v2 import generate_assets


def test_provider_fails_closed_on_timeout(tmp_path: Path):
    adapter = FlowProviderAdapter(mode="fixture")
    fake_shot = {
        "shot_id": "ch1_001",
        "order": 1,
        "visual": {"subject": ["Test"], "place": "Rome", "era": "Ancient", "action": ["Walking"], "tone": "Calm"},
    }
    out_dir = tmp_path / "images"

    # Simulate timeout card
    fixture_cards = {"ch1_001": {"card_id": "CARD-TIMEOUT-01", "status": "TIMEOUT"}}
    asset_info = adapter.generate_shot_asset(fake_shot, out_dir, fixture_cards=fixture_cards)

    assert asset_info["status"] == "TIMEOUT"
    assert asset_info["file_path"] == ""
    assert not (out_dir / "ch1_001.jpg").exists()
    assert not (out_dir / "ch1_001.jpg.part").exists()


def test_provider_binds_completed_card_id(tmp_path: Path):
    contract_path = _PROJECT_ROOT / "human_archive" / "runs" / "ep01_pompeii_rebuild_v2" / "source" / "shot_contract.json"
    if not contract_path.exists():
        pytest.skip("shot_contract.json not yet compiled")

    fixture_cards = {
        "ch1_001": {"card_id": "CARD-FLOW-9999", "status": "COMPLETED"},
    }

    manifest = generate_assets(
        contract_path=contract_path,
        build_id="test-build-001",
        output_root=tmp_path,
        mode="fixture",
        fixture_cards=fixture_cards,
        limit_shots=["ch1_001"],
    )

    assert len(manifest["assets"]) == 1
    asset = manifest["assets"][0]
    assert asset["status"] == "COMPLETED"
    assert asset["card_id"] == "CARD-FLOW-9999"
    assert asset["sha256"] != ""
    assert (tmp_path / "test-build-001" / "images" / "ch1_001.jpg").exists()
