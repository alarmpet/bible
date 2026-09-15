# -*- coding: utf-8 -*-
"""Test release gate v2 contract duration enforcement and negative controls."""
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

from postflight_release import verify_postflight


def test_full_contract_rejects_72_second_pilot(tmp_path: Path):
    standard_contract = tmp_path / "contract.yaml"
    standard_contract.write_text(yaml.dump({
        "schema_version": 2,
        "format_profile": "standard_docu",
        "target_duration_sec": 1200,
    }), encoding="utf-8")

    current_pilot = _PROJECT_ROOT / "human_archive" / "runs" / "ep01_pompeii_rebuild_v2" / "pilot-v2-001" / "final" / "final_pompeii_ep01_v2.mp4"
    if not current_pilot.exists():
        pytest.skip("Pilot video does not exist")

    ok, report = verify_postflight(current_pilot, standard_contract, current_pilot.parents[1], duration_mode="full")
    assert ok is False
    assert report["checks"]["contract_duration"]["status"] == "FAIL"
