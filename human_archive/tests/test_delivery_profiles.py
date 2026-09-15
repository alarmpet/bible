# -*- coding: utf-8 -*-
"""Test delivery profiles and contract validation."""
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

from lib.editorial_policy import load_delivery_profile, validate_episode_contract


@pytest.fixture
def profile_config():
    p_path = _PROJECT_ROOT / "human_archive" / "config" / "delivery_profiles.yaml"
    if not p_path.exists():
        return {}
    return yaml.safe_load(p_path.read_text(encoding="utf-8"))


def test_three_minute_slogan_is_rejected_for_standard_docu(profile_config):
    contract = {
        "schema_version": 2,
        "episode_id": "EP01",
        "format_profile": "standard_docu",
        "target_duration_sec": 1200,
        "slogan": "딱 3분 만에 귀에 쏙 넣어 드리지요",
        "research_status": "approved",
    }
    errors = validate_episode_contract(contract, profile_config)
    assert any("three-minute slogan requires quick_3m" in err for err in errors)


def test_pilot_is_never_publishable(profile_config):
    prof = load_delivery_profile("pilot", profile_config)
    assert prof["publishable"] is False
