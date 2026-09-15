# -*- coding: utf-8 -*-
"""execute_fact_check() must not let the rule-based checker's silent "VERIFIED_FACT"
default pass as verification. This exercises the escalation wiring added 2026-09-15
(docs/superpowers/plans/2026-09-15-human-archive-nollam-script-visual-motion-multi-llm-overhaul-plan.md
Task 3) against a mocked `escalate_claim` -- no real codex/grok calls here, those are
covered by the live smoke test recorded under
human_archive/audit/orchestration/2026-09-15-ep02-clm-jh-001-smoketest/.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
_LIB_DIR = _SCRIPTS_DIR / "lib"
for p in (_SCRIPTS_DIR, _LIB_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import run_consensus_round  # noqa: E402
import tri_model_debate_engine as engine_module  # noqa: E402
from run_consensus_round import Answer  # noqa: E402
from tri_model_debate_engine import TriModelDebateEngine  # noqa: E402
from workspace_manager import workspace_mgr  # noqa: E402


class _FakeEscalationResult:
    def __init__(self, ok: bool, agreed: bool, verdict: str | None, round_dir: Path):
        self.ok = ok
        self.agreed = agreed
        self.verdict = verdict
        self.round_dir = round_dir
        self.answers: dict[str, Answer] = {}
        self.outcomes: list = []


@pytest.fixture()
def episode(tmp_path: Path) -> Path:
    ep_dir = tmp_path / "ep"
    (ep_dir / "source").mkdir(parents=True)
    (ep_dir / "audit").mkdir(parents=True)
    workspace_mgr.set_current_ep_dir(ep_dir)
    return ep_dir


def _engine(ep_dir: Path) -> TriModelDebateEngine:
    return TriModelDebateEngine(episode_dir=ep_dir)


# A dramatic question hook and a curated-pattern sentence must never trigger escalation:
# the rule-based checker has a real, specific answer for them already.
CURATED_SHOTS = [
    {"scene_id": "SHOT_001", "narration": "왜 300년 동안 아무도 몰랐을까요?"},
]

# No curated pattern covers this -- it must fall through to the silent "VERIFIED_FACT"
# default and therefore must be escalated.
UNMATCHED_SHOT = {"scene_id": "SHOT_002", "narration": "화산은 1991년에 크게 분화했다.",
                   "claim_id": "CLM-VOLCANO-001"}


def test_curated_pattern_sentence_is_never_escalated(episode: Path, monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(run_consensus_round, "escalate_claim",
                        lambda **kw: calls.append(kw) or _FakeEscalationResult(True, True, "SOUND", episode))
    result = _engine(episode).execute_fact_check(script_shots=CURATED_SHOTS)
    assert calls == [], "a dramatic-question-hook sentence has a real curated answer already"
    assert result["findings"][0]["grade"] == "A"


def test_unmatched_sentence_is_escalated_exactly_once(episode: Path, monkeypatch) -> None:
    calls = []

    def fake_escalate(**kw):
        calls.append(kw)
        return _FakeEscalationResult(True, True, "SOUND", episode / "round1")

    monkeypatch.setattr(run_consensus_round, "escalate_claim", fake_escalate)
    # Two shots citing the SAME claim_id must only cost one escalation round.
    shots = [dict(UNMATCHED_SHOT, scene_id="SHOT_002"),
             dict(UNMATCHED_SHOT, scene_id="SHOT_003")]
    result = _engine(episode).execute_fact_check(script_shots=shots)

    assert len(calls) == 1, "the same claim_id must be escalated once, not per shot"
    assert result["summary"]["escalated_claims"] == 1
    for f in result["findings"]:
        assert f["grade"] == "A"


def test_agreed_sound_upgrades_status_but_keeps_grade_a(episode: Path, monkeypatch) -> None:
    monkeypatch.setattr(run_consensus_round, "escalate_claim",
                        lambda **kw: _FakeEscalationResult(True, True, "SOUND", episode))
    result = _engine(episode).execute_fact_check(script_shots=[UNMATCHED_SHOT])
    finding = result["findings"][0]
    assert finding["grade"] == "A"
    assert result["summary"]["escalation_agreed_count"] == 1
    assert result["summary"]["review_required_count"] == 0


def test_disagreement_becomes_review_required_not_silent_grade_a(episode: Path, monkeypatch) -> None:
    monkeypatch.setattr(run_consensus_round, "escalate_claim",
                        lambda **kw: _FakeEscalationResult(True, False, None, episode))
    result = _engine(episode).execute_fact_check(script_shots=[UNMATCHED_SHOT])
    finding = result["findings"][0]
    assert finding["grade"] == "REVIEW_REQUIRED"
    assert finding["verdict"] == "ESCALATED_REVIEW_REQUIRED"
    assert result["summary"]["review_required_count"] == 1
    assert result["summary"]["pass_count"] == 0, "a disagreement must not also be counted as a pass"


def test_a_failed_participant_becomes_review_required(episode: Path, monkeypatch) -> None:
    """ok=False means the round itself is incomplete (docs/orchestration/HARD_GATES.md
    gate 7: a verdict reached without the adversary is not an adversarial result)."""
    monkeypatch.setattr(run_consensus_round, "escalate_claim",
                        lambda **kw: _FakeEscalationResult(False, False, None, episode))
    result = _engine(episode).execute_fact_check(script_shots=[UNMATCHED_SHOT])
    assert result["findings"][0]["grade"] == "REVIEW_REQUIRED"


def test_review_required_does_not_rewrite_the_narration_text(episode: Path, monkeypatch) -> None:
    monkeypatch.setattr(run_consensus_round, "escalate_claim",
                        lambda **kw: _FakeEscalationResult(True, False, None, episode))
    result = _engine(episode).execute_fact_check(script_shots=[UNMATCHED_SHOT])
    finding = result["findings"][0]
    assert finding["revised_text"] == UNMATCHED_SHOT["narration"], (
        "REVIEW_REQUIRED must flag the sentence for a human, not silently rewrite it")


def test_final_grade_reports_review_required_count_instead_of_claiming_perfection(
        episode: Path, monkeypatch) -> None:
    monkeypatch.setattr(run_consensus_round, "escalate_claim",
                        lambda **kw: _FakeEscalationResult(True, False, None, episode))
    result = _engine(episode).execute_fact_check(script_shots=[UNMATCHED_SHOT])
    assert "REVIEW_REQUIRED" in result["summary"]["final_grade"]
    assert "완벽 검증" not in result["summary"]["final_grade"], (
        "must not claim perfect verification while a claim is pending human review")


def test_no_escalation_needed_is_reported_honestly_not_as_a_canned_critique(
        episode: Path, monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(run_consensus_round, "escalate_claim",
                        lambda **kw: calls.append(kw))
    result = _engine(episode).execute_fact_check(script_shots=CURATED_SHOTS)
    assert calls == []
    assert result["summary"]["escalated_claims"] == 0
