# -*- coding: utf-8 -*-
"""Test atomic release gate and SHA-256 validation."""
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

from release_episode import promote_release, validate_release_approval


@pytest.fixture
def valid_approval():
    return {
        "schema_version": 2,
        "decision": "approved",
        "reviewer_id": "REL-01",
        "artifacts": {
            "candidate_video_sha256": "A" * 64,
        },
    }


@pytest.mark.parametrize("bad_hash", ["ANY", "PENDING", "VERIFIED_POSTFLIGHT", "ABC123"])
def test_approval_rejects_non_sha256(bad_hash, valid_approval):
    valid_approval["artifacts"]["candidate_video_sha256"] = bad_hash
    assert any("invalid sha256" in err for err in validate_release_approval(valid_approval))
