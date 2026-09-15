# -*- coding: utf-8 -*-
"""Test visual pilot approval gate for rebuild run."""
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

from verify_visual_assets import verify_visual_build


def test_visual_pilot_review_approval_gate():
    pilot_dir = _PROJECT_ROOT / "human_archive" / "runs" / "ep01_pompeii_rebuild_v2" / "pilot-v2-001"
    manifest_path = pilot_dir / "asset_manifest.json"
    approval_path = pilot_dir / "approvals" / "visual_pilot_review.json"

    if not manifest_path.exists() or not approval_path.exists():
        pytest.skip("Pilot run assets or approval not yet created")

    ok, errors = verify_visual_build(build_dir=pilot_dir)
    assert ok is True, f"Pilot visual verification errors: {errors}"
