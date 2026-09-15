# -*- coding: utf-8 -*-
"""Real codex+grok debate round backing `tri_model_debate_engine.py`'s
`orchestrate_deep_tri_model_script()` Round 1 (independent proposals) and Round 2
(cross-critique).

Before 2026-09-15's overhaul plan (Task 2's Quarantine deliverable, split out into
its own follow-up because the previous session could not verify the Studio GUI's
live event-streaming contract), Round 1 built three static `p_38`/`p_37`/`p_36`
dicts from f-string templates and Round 2 built a hardcoded Korean `critiques`
dict -- no model was ever called
(docs/superpowers/plans/2026-09-15-human-archive-nollam-script-visual-motion-multi-llm-overhaul-plan.md
§2). This module replaces both with one real
`run_consensus_round.escalate_claim()` round: codex plays `proposer`, grok plays
`adversary`, both independently graded against the SAME structural-framing spec.
Their agreement/disagreement *is* the cross-critique -- a second, separate round
would double the cost (§5.5's guardrail: full round-protocol only for low-frequency
high-value tasks, which script/topic framing already qualifies as, once per
generation, not per shot) for no real gain over comparing the two answers this
round already produced.

Kept as a standalone, directly unit-testable module (mirrors
`lib/visual_brief_cross_validation.py`'s pattern of wrapping `escalate_claim()`
rather than editing it) so `orchestrate_deep_tri_model_script()` itself -- a large,
GUI-event-streaming-coupled function this session still cannot launch and click
through live -- only has to wire calls to already-tested functions, not carry the
real logic itself.

Only two real subprocess participants exist (codex, grok; `PARTICIPANTS` in
run_consensus_round.py). The third UI lane ("gemini_36" / Empirical Fact-Checker)
is deliberately **not** filled with a fabricated third model call -- Gemini/agy is
not installed on this machine (the same constraint Task 2/3/8 already hit) and
Claude cannot be an unattended subprocess seat
(run_consensus_round.py's "programmatic escalation" comment). That lane instead
honestly points at Round 3 below, which already performs the real per-sentence
fact audit (`SentenceHistoricalFactChecker` + `escalate_claim`, Task 3).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

if False:  # pragma: no cover - typing only, avoid a hard import at module load
    from run_consensus_round import Answer, EscalationResult  # noqa: F401

DEFAULT_TIMEOUT = 480


def build_structure_debate_spec(
    *,
    title: str,
    parallel_match: dict[str, Any],
    total_dynamic_shots: int,
    total_duration_sec: float,
) -> str:
    """Spec text for a proposer/adversary round grading the episode's structural
    framing -- the core hook, the historical parallel it claims, and its
    primary-source anchoring -- not the prose quality of any single sentence
    (Round 3 below already checks sentences one at a time)."""
    primary_sources = parallel_match.get("primary_sources", []) or []
    lines = [
        f"# Script structural framing review: {title}",
        "",
        "A documentary script for this episode has already been generated from a "
        "historical-parallel template (fields below). Review whether the FRAMING "
        "this template commits to -- the core hook, the historical parallel it "
        "claims, and its primary-source anchoring -- actually holds up. Do not "
        "review sentence-level prose; a separate real fact-check pass "
        "(SentenceHistoricalFactChecker + codex/grok escalation) already runs "
        "per sentence after this round.",
        "",
        "## Episode framing under review",
        f"- Title: {title}",
        f"- Historical parallel claimed: {parallel_match.get('historical_parallel', '')}",
        f"- Protagonist: {parallel_match.get('protagonist', '')}",
        f"- Core hook: {parallel_match.get('core_hook', '')}",
        f"- Modern lesson drawn: {parallel_match.get('modern_lesson', '')}",
        f"- Time/space anchor: {parallel_match.get('time_space_anchor', '')}",
        "- Primary sources cited: " + (", ".join(primary_sources) if primary_sources else "(none listed)"),
        f"- Shot/runtime budget already computed: {total_dynamic_shots} shots over "
        f"{total_duration_sec:.0f} seconds",
        "",
        "## What to check",
        "- Grade the core hook / historical-parallel claim as your VERDICT: SOUND "
        "(well-supported by the listed primary sources and internally "
        "consistent), DEFECTIVE (the parallel is forced, unsupported, or the "
        "primary sources don't actually establish it), or CANNOT_DETERMINE (not "
        "enough information here to tell).",
        "- Is the historical parallel a genuine causal/structural echo of the "
        "modern lesson, or only a surface-level word association?",
        "- Does the primary-source list actually cover the specific claim in the "
        "core hook, or only the general topic?",
        "- In ## NUMBERS, report `total_shots` and `total_duration_sec` as you "
        "understand them from the framing above, so a second reviewer's figures "
        "can be compared for agreement.",
    ]
    return "\n".join(lines)


@dataclass
class RealDebateOutcome:
    """What Round 1/2 actually got back from the live round -- or didn't."""
    ok: bool
    agreed: bool
    verdict: str | None
    round_dir: Path
    proposer: str | None            # participant name (e.g. "codex"), or None if absent
    adversary: str | None           # participant name (e.g. "grok"), or None if absent
    proposer_answer: "Answer | None" = None
    adversary_answer: "Answer | None" = None
    failure_detail: str = ""


def run_structure_debate(spec_text: str, round_dir: Path, *, topic: str = "script-structure",
                          timeout: int = DEFAULT_TIMEOUT) -> RealDebateOutcome:
    """Run the real codex(proposer)/grok(adversary) round. Imported lazily (not at
    module load) so tests can monkeypatch `run_consensus_round.escalate_claim`,
    matching `tri_model_debate_engine.py`'s `execute_fact_check()` -- see
    test_fact_check_escalation.py."""
    from run_consensus_round import escalate_claim

    result = escalate_claim(topic=topic, spec_text=spec_text, round_dir=round_dir,
                             timeout=timeout, roles=("proposer", "adversary"))

    role_by_participant = {o.participant: o.role for o in result.outcomes}
    proposer = next((p for p, r in role_by_participant.items() if r == "proposer"), None)
    adversary = next((p for p, r in role_by_participant.items() if r == "adversary"), None)

    failed = [o for o in result.outcomes if not o.ok]
    failure_detail = "; ".join(f"{o.participant}: {o.detail}" for o in failed)

    return RealDebateOutcome(
        ok=result.ok,
        agreed=result.agreed,
        verdict=result.verdict,
        round_dir=result.round_dir,
        proposer=proposer,
        adversary=adversary,
        proposer_answer=result.answers.get(proposer) if proposer else None,
        adversary_answer=result.answers.get(adversary) if adversary else None,
        failure_detail=failure_detail,
    )


def _findings_as_dicts(answer: "Answer | None") -> list[dict[str, str]]:
    if answer is None:
        return []
    return [
        {"severity": f.severity, "claim": f.claim, "evidence": f.evidence, "impact": f.impact}
        for f in answer.real_findings
    ]


def _lane_from_answer(*, role_label: str, participant: str | None,
                       answer: "Answer | None", outcome: RealDebateOutcome,
                       total_dynamic_shots: int, total_duration_sec: float) -> dict[str, Any]:
    budget = f"{total_dynamic_shots}개 샷 / {total_duration_sec:.0f}초"
    if answer is not None:
        top_finding = answer.real_findings[0].claim if answer.real_findings else ""
        return {
            "model": f"{participant} ({role_label.lower()}, run_consensus_round.escalate_claim 실측)",
            "role": role_label,
            "title": f"{role_label} 실측 판정: {answer.verdict or '(파싱 실패)'}",
            "hook": top_finding or answer.uncertainty or "(추가 발견 없음 -- 이견 없이 통과)",
            "structure": "; ".join(f"[{f.severity}] {f.claim}" for f in answer.real_findings[:3]),
            "timeline_budget": budget,
            "numbers": dict(answer.numbers),
            "uncertainty": answer.uncertainty,
            "verdict": answer.verdict,
            "findings_count": len(answer.real_findings),
            "provenance": "live_orchestration",
            "round_dir": str(outcome.round_dir),
        }
    return {
        "model": f"{participant or '(참가자 없음)'} ({role_label.lower()}) -- 실시간 호출 실패/미완료",
        "role": role_label,
        "title": "실시간 codex/grok 호출 실패 -- 사람 검토 필요",
        "hook": outcome.failure_detail or "원인 미상 실패 (라운드 미완료)",
        "structure": "",
        "timeline_budget": budget,
        "provenance": "simulated_fixture",
        "round_dir": str(outcome.round_dir),
    }


def build_proposal_events(
    outcome: RealDebateOutcome, *,
    parallel_match: dict[str, Any],
    total_dynamic_shots: int,
    total_duration_sec: float,
) -> list[tuple[str, dict[str, Any]]]:
    """Three `(model_key, data)` pairs, one per Studio UI lane
    (`gemini_38`/`gemini_37`/`gemini_36`), preserving the lane-routing keys the
    frontend switches on (`static/index.html`'s `listenToDebateStream`) even
    though only two of the three are backed by a real model call."""
    events: list[tuple[str, dict[str, Any]]] = [
        ("gemini_38", _lane_from_answer(
            role_label="PROPOSER", participant=outcome.proposer,
            answer=outcome.proposer_answer, outcome=outcome,
            total_dynamic_shots=total_dynamic_shots, total_duration_sec=total_duration_sec)),
        ("gemini_37", _lane_from_answer(
            role_label="ADVERSARY", participant=outcome.adversary,
            answer=outcome.adversary_answer, outcome=outcome,
            total_dynamic_shots=total_dynamic_shots, total_duration_sec=total_duration_sec)),
    ]

    primary_sources = parallel_match.get("primary_sources", []) or []
    events.append(("gemini_36", {
        "model": "Round 3에서 실행 (SentenceHistoricalFactChecker + codex/grok escalate_claim, Task 3)",
        "role": "Empirical Fact-Checker",
        "title": f"1차 사료 {len(primary_sources)}종 확보 -- 문장별 전수 대조는 아래 Round 3에서 실행",
        "primary_sources": primary_sources,
        "note": (
            "이 레인은 독립적인 세 번째 LLM 제안이 아니다. Gemini/agy CLI가 이 PC에 설치되지 "
            "않아(§5.6 확장 지점만 존재) 세 번째 실시간 모델 좌석이 없고, Claude는 무인 파이프라인의 "
            "구독 참가자가 될 수 없다. 실제 문장 단위 전수 검증은 아래 Round 3가 수행한다."
        ),
        "provenance": "not_applicable",
    }))
    return events


def build_cross_critique_event_data(outcome: RealDebateOutcome) -> dict[str, Any]:
    """`data` payload for the `cross_critique` event -- derived from the SAME real
    round (agreement/disagreement between the real proposer/adversary answers),
    not a second round."""
    source = "run_consensus_round.escalate_claim (codex=proposer, grok=adversary)"
    if outcome.proposer_answer is None or outcome.adversary_answer is None:
        return {
            "source": source,
            "ok": False,
            "round_dir": str(outcome.round_dir),
            "note": (
                "실시간 codex/grok 교차비평 라운드가 불완전했다"
                + (f" ({outcome.failure_detail})" if outcome.failure_detail else "")
                + " -- 사람 검토 필요. 하드코딩 비평문으로 대체하지 않았다."
            ),
        }
    return {
        "source": source,
        "ok": True,
        "agreed": outcome.agreed,
        "verdict": outcome.verdict,
        "proposer_verdict": outcome.proposer_answer.verdict,
        "adversary_verdict": outcome.adversary_answer.verdict,
        "adversary_findings": _findings_as_dicts(outcome.adversary_answer),
        "proposer_findings": _findings_as_dicts(outcome.proposer_answer),
        "round_dir": str(outcome.round_dir),
        "note": (
            "합의(SOUND, 두 참가자 verdict 일치)"
            if (outcome.agreed and outcome.verdict == "SOUND") else
            "불일치 또는 결함 발견 -- 표로만 제시하고 자동 병합하지 않는다 "
            "(agreement is not evidence, docs/orchestration/HARD_GATES.md)."
        ),
    }


def resolve_provenance(outcome: RealDebateOutcome) -> tuple[str, str]:
    """(`provenance`, `provenance_detail`) for `final_manifest["metadata"]`.
    `"simulated_fixture"` (the literal string `postflight_release.py`'s
    `verify_postflight()` gates on) is kept verbatim for the failure path so a
    build whose Round 1/2 debate did not actually complete is still blocked from
    release; a real completed round gets `"live_orchestration"` instead."""
    if outcome.ok:
        return "live_orchestration", (
            "Round 1/2 proposals and cross-critique are real codex+grok calls via "
            f"run_consensus_round.escalate_claim() (round_dir={outcome.round_dir}). "
            f"Verdicts {'agreed' if outcome.agreed else 'disagreed'}"
            + (f" ({outcome.verdict})" if outcome.agreed else "") + "."
        )
    return "simulated_fixture", (
        "Live codex/grok escalation round for Round 1/2 failed or was incomplete "
        f"(round_dir={outcome.round_dir}; {outcome.failure_detail or 'unknown failure'}). "
        "Falling back to the fail-closed simulated_fixture label so release is blocked "
        "pending a rerun with working providers (Task 2 §5.3 rule 4)."
    )
