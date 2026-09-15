# -*- coding: utf-8 -*-
"""Test renderer v2 hash chain enforcement, build manifest creation, and candidate output."""
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

from lib.build_manifest import verify_upstream_hash_freshness
from build_motion_clips_v2 import build_motion_clips
from render_episode_v2 import render_build


def test_rejects_render_when_upstream_missing(tmp_path: Path):
    empty_build = tmp_path / "empty_build"
    empty_build.mkdir()

    ok, errors = verify_upstream_hash_freshness(empty_build)
    assert ok is False
    assert len(errors) >= 1


def test_render_episode_v2_pilot_build():
    build_dir = _PROJECT_ROOT / "human_archive" / "runs" / "ep01_pompeii_rebuild_v2" / "pilot-v2-001"
    if not (build_dir / "asset_manifest.json").exists():
        pytest.skip("Pilot asset manifest not yet created")

    build_motion_clips(build_dir)

    out_mp4 = render_build(build_dir)
    assert out_mp4.exists()
    assert "candidate" in str(out_mp4)

    build_manifest = build_dir / "build_manifest.json"
    assert build_manifest.exists()
    data = json.loads(build_manifest.read_text(encoding="utf-8"))
    assert data["candidate_video_sha256"] != ""
