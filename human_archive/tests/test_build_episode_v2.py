# -*- coding: utf-8 -*-
"""Test build episode v2 end-to-end orchestrator."""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import build_episode_v2
from build_episode_v2 import orchestrate_episode_build


def test_orchestrator_uses_v3_motion_engine_not_the_quarantined_v2_judder_engine():
    """2026-09-16 finding, cross-verified live by two independent reviewers
    (audit/orchestration/2026-09-16-2026-09-16-workflow-review/): this
    orchestrator used to import build_motion_clips_v2 -- the quarantined
    full-shot-cosine judder engine (measured 78-84% near-duplicate frame
    rate) that build_motion_clips_v3.py replaced project-wide on
    2026-09-15 -- so this "one command full rebuild" entrypoint silently
    bypassed that fix. It must use build_motion_clips_v3."""
    source = Path(build_episode_v2.__file__).read_text(encoding="utf-8")
    assert "build_motion_clips_v3" in source
    assert "from build_motion_clips_v2 import" not in source
    assert build_episode_v2.build_motion_clips_v3.__module__ == "build_motion_clips_v3"


def test_orchestrator_stop_after_visual_contact_sheet(tmp_path: Path):
    contract_path = _PROJECT_ROOT / "human_archive" / "runs" / "ep01_pompeii_rebuild_v2" / "source" / "shot_contract.json"
    if not contract_path.exists():
        pytest.skip("shot_contract.json not available")

    build_dir = orchestrate_episode_build(
        contract_path=contract_path,
        build_id="test-orch-001",
        output_root=tmp_path,
        mode="fixture",
        stop_after="visual-contact-sheet",
    )

    assert (tmp_path / "test-orch-001" / "asset_manifest.json").exists()
    assert (tmp_path / "test-orch-001" / "contact_sheet.jpg").exists()
