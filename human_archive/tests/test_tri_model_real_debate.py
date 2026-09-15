# -*- coding: utf-8 -*-
"""lib/tri_model_real_debate.py backs orchestrate_deep_tri_model_script()'s Round 1
(independent proposals) and Round 2 (cross-critique) with a real codex+grok
run_consensus_round.escalate_claim() round instead of the static f-string dicts
diagnosed in docs/superpowers/plans/2026-09-15-human-archive-nollam-script-visual-motion-multi-llm-overhaul-plan.md
§2 (Task 2's Quarantine deliverable).

No real codex/grok calls here -- escalate_claim is mocked, matching
test_fact_check_escalation.py's and test_visual_brief_cross_validation.py's
pattern exactly. These tests pin:
  - the exact `emit()`-facing shapes (`build_proposal_events` returns the three
    Studio UI lane keys "gemini_38"/"gemini_37"/"gemini_36" the frontend routes
    on; `build_cross_critique_event_data` returns a dict suitable for
    `{"type": "cross_critique", "data": ...}`),
  - that a real completed round resolves to provenance "live_orchestration" and
    an incomplete/failed one falls back to the fail-closed "simulated_fixture"
    label (never silently claiming success), and
  - that disagreement/failure is reported honestly rather than merged away.
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
from orchestration.contract import Answer, Finding  # noqa: E402
from run_consensus_round import Outcome  # noqa: E402
from lib.tri_model_real_debate import (  # noqa: E402
    build_cross_critique_event_data,
    build_proposal_events,
    build_structure_debate_spec,
    resolve_provenance,
    run_structure_debate,
)


PARALLEL_MATCH = {
    "historical_parallel": "1929년 대공황의 은행 인출 사태",
    "protagonist": "익명의 예금주들",
    "core_hook": "왜 모두가 동시에 돈을 빼려 했는가",
    "modern_lesson": "디지털 뱅크런은 더 빠르게 전염된다",
    "time_space_anchor": "1929년, 뉴욕",
    "primary_sources": ["FDIC 연차보고서", "뉴욕타임스 1929년 10월 아카이브"],
}


class _FakeEscalationResult:
    """Mirrors run_consensus_round.EscalationResult's public shape."""

    def __init__(self, *, ok: bool, agreed: bool, verdict: str | None,
                 round_dir: Path, answers: dict, outcomes: list):
        self.ok = ok
        self.agreed = agreed
        self.verdict = verdict
        self.round_dir = round_dir
        self.answers = answers
        self.outcomes = outcomes


def _answer(verdict: str, findings: list[Finding] | None = None,
            numbers: dict[str, str] | None = None, uncertainty: str = "") -> Answer:
    return Answer(verdict=verdict, findings=findings or [], numbers=numbers or {},
                  uncertainty=uncertainty)


def _both_succeeded(round_dir: Path, *, codex_verdict: str, grok_verdict: str,
                     codex_findings=None, grok_findings=None) -> _FakeEscalationResult:
    codex_answer = _answer(codex_verdict, codex_findings)
    grok_answer = _answer(grok_verdict, grok_findings)
    outcomes = [
        Outcome("codex", "proposer", True, "## VERDICT\n...", 12.0),
        Outcome("grok", "adversary", True, "## VERDICT\n...", 9.0),
    ]
    agreed = codex_verdict == grok_verdict
    return _FakeEscalationResult(
        ok=True, agreed=agreed, verdict=codex_verdict if agreed else None,
        round_dir=round_dir, answers={"codex": codex_answer, "grok": grok_answer},
        outcomes=outcomes,
    )


def _grok_failed(round_dir: Path) -> _FakeEscalationResult:
    outcomes = [
        Outcome("codex", "proposer", True, "## VERDICT\n...", 12.0),
        Outcome("grok", "adversary", False, "", 0.5, detail="grok is not on PATH"),
    ]
    return _FakeEscalationResult(
        ok=False, agreed=False, verdict=None, round_dir=round_dir,
        answers={"codex": _answer("SOUND")}, outcomes=outcomes,
    )


# ---------------------------------------------------------------------------
# build_structure_debate_spec
# ---------------------------------------------------------------------------

def test_spec_includes_real_framing_fields_not_placeholders():
    spec = build_structure_debate_spec(
        title="대공황 뱅크런의 교훈", parallel_match=PARALLEL_MATCH,
        total_dynamic_shots=64, total_duration_sec=1180.0,
    )
    assert "1929년 대공황의 은행 인출 사태" in spec
    assert "FDIC 연차보고서" in spec
    assert "64 shots" in spec
    assert "SOUND" in spec and "DEFECTIVE" in spec and "CANNOT_DETERMINE" in spec


# ---------------------------------------------------------------------------
# run_structure_debate -- wiring onto run_consensus_round.escalate_claim
# ---------------------------------------------------------------------------

def test_run_structure_debate_calls_escalate_claim_with_proposer_adversary_roles(
        tmp_path: Path, monkeypatch):
    calls = []

    def fake_escalate(**kw):
        calls.append(kw)
        return _both_succeeded(tmp_path, codex_verdict="SOUND", grok_verdict="SOUND")

    monkeypatch.setattr(run_consensus_round, "escalate_claim", fake_escalate)
    outcome = run_structure_debate("spec text", tmp_path, topic="t")

    assert len(calls) == 1
    assert calls[0]["roles"] == ("proposer", "adversary")
    assert outcome.ok is True
    assert outcome.proposer == "codex"
    assert outcome.adversary == "grok"
    assert outcome.proposer_answer.verdict == "SOUND"
    assert outcome.adversary_answer.verdict == "SOUND"


def test_run_structure_debate_surfaces_a_failed_participant_without_crashing(
        tmp_path: Path, monkeypatch):
    monkeypatch.setattr(run_consensus_round, "escalate_claim",
                        lambda **kw: _grok_failed(tmp_path))
    outcome = run_structure_debate("spec text", tmp_path, topic="t")

    assert outcome.ok is False
    assert outcome.adversary_answer is None
    assert "grok is not on PATH" in outcome.failure_detail


# ---------------------------------------------------------------------------
# build_proposal_events -- the Studio UI lane contract
# ---------------------------------------------------------------------------

def test_proposal_events_cover_exactly_the_three_studio_lanes(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(run_consensus_round, "escalate_claim",
                        lambda **kw: _both_succeeded(tmp_path, codex_verdict="SOUND",
                                                      grok_verdict="SOUND"))
    outcome = run_structure_debate("spec", tmp_path, topic="t")
    events = build_proposal_events(outcome, parallel_match=PARALLEL_MATCH,
                                    total_dynamic_shots=64, total_duration_sec=1180.0)

    lane_keys = [k for k, _ in events]
    assert lane_keys == ["gemini_38", "gemini_37", "gemini_36"], (
        "frontend static/index.html's listenToDebateStream routes on these exact "
        "model keys ('gemini_38'/'gemini_37'/'gemini_36') to three fixed lanes")
    for _, data in events:
        assert isinstance(data, dict)


def test_gemini_38_and_37_lanes_carry_real_answer_content(tmp_path: Path, monkeypatch):
    finding = Finding(severity="P1", claim="핵심 근거 사료 미인용", evidence="FDIC 1929")
    monkeypatch.setattr(run_consensus_round, "escalate_claim",
                        lambda **kw: _both_succeeded(
                            tmp_path, codex_verdict="SOUND", grok_verdict="DEFECTIVE",
                            grok_findings=[finding]))
    outcome = run_structure_debate("spec", tmp_path, topic="t")
    events = dict(build_proposal_events(outcome, parallel_match=PARALLEL_MATCH,
                                         total_dynamic_shots=64, total_duration_sec=1180.0))

    assert events["gemini_38"]["verdict"] == "SOUND"
    assert events["gemini_38"]["provenance"] == "live_orchestration"
    assert events["gemini_37"]["verdict"] == "DEFECTIVE"
    assert "핵심 근거 사료 미인용" in events["gemini_37"]["hook"]


def test_gemini_36_lane_is_never_a_fabricated_third_proposal(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(run_consensus_round, "escalate_claim",
                        lambda **kw: _both_succeeded(tmp_path, codex_verdict="SOUND",
                                                      grok_verdict="SOUND"))
    outcome = run_structure_debate("spec", tmp_path, topic="t")
    events = dict(build_proposal_events(outcome, parallel_match=PARALLEL_MATCH,
                                         total_dynamic_shots=64, total_duration_sec=1180.0))

    lane36 = events["gemini_36"]
    assert lane36["provenance"] == "not_applicable"
    assert lane36["primary_sources"] == PARALLEL_MATCH["primary_sources"]
    assert "Round 3" in lane36["note"] or "Round 3" in lane36["title"]


def test_failed_round_lane_is_flagged_not_silently_blank(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(run_consensus_round, "escalate_claim",
                        lambda **kw: _grok_failed(tmp_path))
    outcome = run_structure_debate("spec", tmp_path, topic="t")
    events = dict(build_proposal_events(outcome, parallel_match=PARALLEL_MATCH,
                                         total_dynamic_shots=64, total_duration_sec=1180.0))

    assert events["gemini_37"]["provenance"] == "simulated_fixture"
    assert "실패" in events["gemini_37"]["title"] or "실패" in events["gemini_37"]["hook"]
    # codex (proposer) still succeeded and must still carry real content
    assert events["gemini_38"]["provenance"] == "live_orchestration"


# ---------------------------------------------------------------------------
# build_cross_critique_event_data
# ---------------------------------------------------------------------------

def test_cross_critique_reports_real_agreement(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(run_consensus_round, "escalate_claim",
                        lambda **kw: _both_succeeded(tmp_path, codex_verdict="SOUND",
                                                      grok_verdict="SOUND"))
    outcome = run_structure_debate("spec", tmp_path, topic="t")
    data = build_cross_critique_event_data(outcome)

    assert data["ok"] is True
    assert data["agreed"] is True
    assert data["verdict"] == "SOUND"
    assert data["source"].startswith("run_consensus_round.escalate_claim")


def test_cross_critique_reports_real_disagreement_not_a_merged_answer(
        tmp_path: Path, monkeypatch):
    monkeypatch.setattr(run_consensus_round, "escalate_claim",
                        lambda **kw: _both_succeeded(tmp_path, codex_verdict="SOUND",
                                                      grok_verdict="DEFECTIVE"))
    outcome = run_structure_debate("spec", tmp_path, topic="t")
    data = build_cross_critique_event_data(outcome)

    assert data["ok"] is True
    assert data["agreed"] is False
    assert data["proposer_verdict"] == "SOUND"
    assert data["adversary_verdict"] == "DEFECTIVE"
    assert "verdict" not in data or data.get("verdict") is None


def test_cross_critique_on_incomplete_round_flags_review_not_canned_text(
        tmp_path: Path, monkeypatch):
    monkeypatch.setattr(run_consensus_round, "escalate_claim",
                        lambda **kw: _grok_failed(tmp_path))
    outcome = run_structure_debate("spec", tmp_path, topic="t")
    data = build_cross_critique_event_data(outcome)

    assert data["ok"] is False
    assert "실패" in data["note"] or "불완전" in data["note"]


# ---------------------------------------------------------------------------
# resolve_provenance -- the fail-closed release gate label
# ---------------------------------------------------------------------------

def test_provenance_is_live_orchestration_when_round_completed(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(run_consensus_round, "escalate_claim",
                        lambda **kw: _both_succeeded(tmp_path, codex_verdict="SOUND",
                                                      grok_verdict="SOUND"))
    outcome = run_structure_debate("spec", tmp_path, topic="t")
    provenance, detail = resolve_provenance(outcome)

    assert provenance == "live_orchestration"
    assert "codex+grok" in detail


def test_provenance_falls_back_to_simulated_fixture_when_round_incomplete(
        tmp_path: Path, monkeypatch):
    monkeypatch.setattr(run_consensus_round, "escalate_claim",
                        lambda **kw: _grok_failed(tmp_path))
    outcome = run_structure_debate("spec", tmp_path, topic="t")
    provenance, detail = resolve_provenance(outcome)

    assert provenance == "simulated_fixture", (
        "postflight_release.py's verify_postflight() gates on this exact literal string")
    assert "grok is not on PATH" in detail or "failed" in detail.lower()
