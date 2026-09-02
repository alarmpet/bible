# -*- coding: utf-8 -*-
"""Shared fixtures for flow automation tests."""
from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
HIMALAYA_ROOT = (
    ROOT
    / "runs"
    / "nollam_file"
    / "2026-09-02"
    / "himalaya-glof-water-crisis"
)


@pytest.fixture
def himalaya_manifest() -> Path:
    return HIMALAYA_ROOT / "source" / "scene_script_manifest_v2.json"


@pytest.fixture
def episode_dir(tmp_path: Path) -> Path:
    episode_dir = tmp_path / "himalaya-glof-water-crisis"
    episode_dir.mkdir(parents=True, exist_ok=True)
    return episode_dir
