"""check_independence() is the one honesty check in run_consensus_round.py that has no
enforcement power -- it can't stop a participant from reading a round directory another
participant already wrote into, it can only notice after the fact and say so. That makes
it easy to accidentally leave untested (nothing breaks if it silently stops reporting
exposure), which is exactly the failure mode this plan's Task 2 completion criterion
("check_independence" coverage) is asking to guard against.

2026-09-15 overhaul plan Task 2. Placed alongside test_run_consensus_round.py and
test_contract.py rather than at tests/test_orchestration_independence.py (the path the
plan doc's Task 2 literally names) to match how this repo already organizes the ported
orchestration test suite -- see the "완료 기준 검증" note under Task 2 in that plan.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from run_consensus_round import check_independence  # noqa: E402


def _write_with_mtime(path: Path, text: str, age_seconds: float) -> None:
    path.write_text(text, encoding="utf-8")
    now = time.time()
    stamp = now - age_seconds
    os.utime(path, (stamp, stamp))


def test_returns_empty_when_fewer_than_two_answers_exist(tmp_path: Path) -> None:
    _write_with_mtime(tmp_path / "propose.codex.md", "answer", age_seconds=0)
    assert check_independence(tmp_path, "propose") == []


def test_returns_empty_when_all_answers_finished_close_together(tmp_path: Path) -> None:
    # Both written within a couple seconds of each other -- normal parallel completion.
    _write_with_mtime(tmp_path / "propose.codex.md", "answer", age_seconds=2)
    _write_with_mtime(tmp_path / "propose.grok.md", "answer", age_seconds=0)
    assert check_independence(tmp_path, "propose") == []


def test_flags_an_answer_that_finished_well_before_the_others(tmp_path: Path) -> None:
    # codex finished 60s before grok did -- grok's process could have read codex's
    # answer off disk while it was still running. Not proof of leakage, but reportable.
    _write_with_mtime(tmp_path / "propose.codex.md", "answer", age_seconds=60)
    _write_with_mtime(tmp_path / "propose.grok.md", "answer", age_seconds=0)
    exposed = check_independence(tmp_path, "propose")
    assert exposed == ["codex"]


def test_does_not_flag_the_participant_that_finished_last(tmp_path: Path) -> None:
    _write_with_mtime(tmp_path / "propose.codex.md", "answer", age_seconds=60)
    _write_with_mtime(tmp_path / "propose.grok.md", "answer", age_seconds=0)
    exposed = check_independence(tmp_path, "propose")
    assert "grok" not in exposed


def test_flags_multiple_early_finishers_relative_to_the_last(tmp_path: Path) -> None:
    _write_with_mtime(tmp_path / "propose.codex.md", "answer", age_seconds=90)
    _write_with_mtime(tmp_path / "propose.grok.md", "answer", age_seconds=45)
    _write_with_mtime(tmp_path / "propose.claude.md", "answer", age_seconds=0)
    exposed = check_independence(tmp_path, "propose")
    assert set(exposed) == {"codex", "grok"}


def test_ignores_files_for_a_different_stem(tmp_path: Path) -> None:
    _write_with_mtime(tmp_path / "propose.codex.md", "answer", age_seconds=60)
    _write_with_mtime(tmp_path / "critique.grok.md", "answer", age_seconds=0)
    # Only one "propose.*.md" file exists -- nothing to compare.
    assert check_independence(tmp_path, "propose") == []


def test_prints_a_readable_warning_when_exposure_is_found(tmp_path: Path, capsys) -> None:
    _write_with_mtime(tmp_path / "propose.codex.md", "answer", age_seconds=60)
    _write_with_mtime(tmp_path / "propose.grok.md", "answer", age_seconds=0)
    check_independence(tmp_path, "propose")
    out = capsys.readouterr().out
    assert "INDEPENDENCE" in out
    assert "codex" in out
