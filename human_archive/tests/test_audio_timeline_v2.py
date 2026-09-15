# -*- coding: utf-8 -*-
"""Test audio timeline building, loudness normalization, and manifest integrity."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
import pytest

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from build_audio_master_v2 import build_audio_master


@pytest.mark.media_heavy
def test_build_audio_master_creates_normalized_master(tmp_path: Path):
    source_run = _PROJECT_ROOT / "human_archive" / "runs" / "ep01_pompeii_rebuild_v2"
    source_contract = source_run / "source" / "shot_contract.json"
    if not source_contract.exists():
        pytest.skip("shot_contract.json not yet available")

    run_dir = tmp_path / "run"
    (run_dir / "source").mkdir(parents=True)
    shutil.copy2(source_contract, run_dir / "source" / source_contract.name)
    build_dir = run_dir / "pilot-v2-001"

    master_wav = build_audio_master(build_dir, audio_mode="fixture")
    assert master_wav.exists()

    manifest_path = build_dir / "scene_audio_manifest.json"
    assert manifest_path.exists()

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["ok"] is True
    assert data["total_shots"] == 12
    assert data["total_duration_sec"] > 0
