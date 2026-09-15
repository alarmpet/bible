# -*- coding: utf-8 -*-
"""Test AV pilot approval review gate."""
from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]


def test_av_pilot_review_is_approved():
    approval_file = _PROJECT_ROOT / "human_archive" / "runs" / "ep01_pompeii_rebuild_v2" / "pilot-v2-001" / "approvals" / "av_pilot_review.json"
    if not approval_file.exists():
        pytest.skip("av_pilot_review.json not created")

    data = json.loads(approval_file.read_text(encoding="utf-8"))
    assert data["decision"] == "approved"
    assert data["postflight_status"] == "PASS"
