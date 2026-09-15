# -*- coding: utf-8 -*-
"""Guard against release/publish entrypoints accepting isolated research paths."""
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.production_path_guard import IsolatedResearchPathError, assert_not_isolated_research_path


def test_allows_normal_production_path(tmp_path):
    build = tmp_path / "runs" / "nollam_file" / "2026-09-15" / "some-topic"
    assert_not_isolated_research_path(build / "final" / "out.mp4", build)


def test_blocks_isolated_benchmark_path(tmp_path):
    isolated = tmp_path / "research" / "human_library_benchmark_internal_only" / "rank1_race_adaptation"
    with pytest.raises(IsolatedResearchPathError):
        assert_not_isolated_research_path(isolated / "video" / "out.mp4")


def test_blocks_legacy_replica_path(tmp_path):
    legacy = tmp_path / "runs" / "human_library_replica" / "rank2_forgotten_civilization"
    with pytest.raises(IsolatedResearchPathError):
        assert_not_isolated_research_path(legacy / "candidate.mp4")


def test_none_entries_are_ignored():
    assert_not_isolated_research_path(None, None)
