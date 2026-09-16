# -*- coding: utf-8 -*-
"""Task 8 (scene visual-brief cross-validation): generate_visual_briefs.py used to
have no cross-check at all beyond schema/field validation -- the Studio path's
40-char narration truncation (§1.3) had nothing analogous on the CLI v5/v6 side
either, it just trusted whatever antigravity-cli returned. This wires the same
codex+grok escalate_claim() machinery Task 3 used for fact-checking onto a
selection of already-generated briefs, reusing the existing proposer/adversary
review contract (adversary.md explicitly lists the visual-brief failure modes
this plan diagnosed) instead of inventing a new role.

No real codex/grok calls here -- escalate_claim is mocked, matching
test_fact_check_escalation.py's pattern exactly.
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
import orchestration.prompt_assembly as prompt_assembly  # noqa: E402
from lib.visual_brief_cross_validation import (  # noqa: E402
    build_critique_spec,
    critique_visual_briefs,
    screen_with_groq,
    select_scenes_for_critique,
    summarize_critique_results,
)


class _FakeEscalationResult:
    def __init__(self, ok: bool, agreed: bool, verdict: str | None, round_dir: Path):
        self.ok = ok
        self.agreed = agreed
        self.verdict = verdict
        self.round_dir = round_dir
        self.answers: dict = {"codex": object()} if ok else {}
        self.outcomes: list = []


BRIEF_A = {
    "shot_id": "ha_nollam_shot_001",
    "visual_mode": "diagram_metaphor",
    "focal_subject": "two closed archival document boxes",
    "action": "boxes sit undisturbed on a shelf",
    "place": "a records archive",
    "era": "unspecified historical period",
    "camera": "medium wide, static",
    "motion_profile": "subpixel_push_in",
    "text_overlay_policy": "no letters, digits, or watermarks",
}
BRIEF_B = {"shot_id": "ha_nollam_shot_002", "focal_subject": "a satellite view of a coastline"}
BRIEF_C = {"shot_id": "ha_nollam_shot_003", "focal_subject": "a quantum computer chip macro shot"}
BRIEF_D = {"shot_id": "ha_nollam_shot_004", "focal_subject": "a glacier calving into the sea"}
ALL_BRIEFS = [BRIEF_A, BRIEF_B, BRIEF_C, BRIEF_D]


def test_build_critique_spec_includes_shot_id_narration_and_fields():
    spec = build_critique_spec(BRIEF_A, "실록에는 이 사건에 대한 기록이 전혀 없습니다.")
    assert "ha_nollam_shot_001" in spec
    assert "실록에는 이 사건에 대한 기록이 전혀 없습니다." in spec
    assert "diagram_metaphor" in spec
    assert "two closed archival document boxes" in spec


def test_select_scenes_for_critique_explicit_ids_win_over_sample():
    selected = select_scenes_for_critique(ALL_BRIEFS, scene_ids=["ha_nollam_shot_003"], sample_size=4)
    assert [b["shot_id"] for b in selected] == ["ha_nollam_shot_003"]


def test_select_scenes_for_critique_sample_is_deterministic_and_spans_the_list():
    selected = select_scenes_for_critique(ALL_BRIEFS, sample_size=2)
    ids = [b["shot_id"] for b in selected]
    # deterministic: same call twice gives the same result
    assert ids == [b["shot_id"] for b in select_scenes_for_critique(ALL_BRIEFS, sample_size=2)]
    assert len(ids) == 2


def test_select_scenes_for_critique_disabled_by_default():
    assert select_scenes_for_critique(ALL_BRIEFS) == []
    assert select_scenes_for_critique(ALL_BRIEFS, sample_size=0) == []


def test_critique_visual_briefs_calls_escalate_claim_once_per_selected_shot(monkeypatch, tmp_path: Path):
    calls = []

    def fake_escalate(topic, spec_text, timeout=480, round_dir=None, roles=("proposer", "adversary")):
        calls.append({"topic": topic, "round_dir": round_dir})
        return _FakeEscalationResult(True, True, "SOUND", round_dir or tmp_path)

    monkeypatch.setattr(run_consensus_round, "escalate_claim", fake_escalate)

    narration = {"ha_nollam_shot_001": "실록에는 기록이 없다.", "ha_nollam_shot_003": "이 칩은 이렇게 작동한다."}
    results, groq_outcomes = critique_visual_briefs(
        ALL_BRIEFS, narration,
        scene_ids=["ha_nollam_shot_001", "ha_nollam_shot_003"],
        round_dir_root=tmp_path,
    )

    assert len(calls) == 2
    assert set(results.keys()) == {"ha_nollam_shot_001", "ha_nollam_shot_003"}
    assert calls[0]["topic"].startswith("visual-brief-ha_nollam_shot_0")
    assert groq_outcomes == {}  # include_groq_screen defaults to off


def test_critique_visual_briefs_disabled_when_no_ids_or_sample_given(monkeypatch):
    calls = []
    monkeypatch.setattr(run_consensus_round, "escalate_claim",
                         lambda *a, **kw: calls.append(1) or _FakeEscalationResult(True, True, "SOUND", Path(".")))
    results, groq_outcomes = critique_visual_briefs(ALL_BRIEFS, {})
    assert calls == []
    assert groq_outcomes == {}
    assert results == {}


def test_screen_with_groq_sends_the_same_inlined_spec_through_assemble(monkeypatch, tmp_path: Path):
    """2026-09-16 finding (audit/orchestration/2026-09-16-2026-09-16-groq-placement/,
    independently confirmed by two reviewers): unlike escalate_claim()'s
    fact-check packet, build_critique_spec() already inlines everything Groq
    needs (no file-read tool access required), so it is a valid additive
    third screener here."""
    calls = []
    monkeypatch.setattr(run_consensus_round, "_invoke",
                         lambda *a, **kw: calls.append(a) or object())
    monkeypatch.setattr(prompt_assembly, "assemble", lambda role, spec: f"PROMPT[{role}]::{spec}")

    screen_with_groq(BRIEF_A, "실록에는 기록이 없다.", round_dir=tmp_path, timeout=99)

    assert len(calls) == 1
    participant, role, prompt, round_dir, timeout = calls[0]
    assert participant == "groq"
    assert role == "proposer"
    assert prompt.startswith("PROMPT[proposer]::")
    assert "ha_nollam_shot_001" in prompt
    assert round_dir == tmp_path
    assert timeout == 99


def test_critique_visual_briefs_include_groq_screen_is_additive_and_opt_in(monkeypatch, tmp_path: Path):
    """The Groq screen must never change escalate_claim()'s own result (still
    exactly the codex+grok pair), and must default to off. The flag lives on
    critique_visual_briefs() (plural) -- critique_visual_brief() (singular)
    has no knowledge of Groq at all."""
    escalate_calls = []
    groq_calls = []

    def fake_escalate(topic, spec_text, timeout=480, round_dir=None, roles=("proposer", "adversary")):
        escalate_calls.append(topic)
        return _FakeEscalationResult(True, True, "SOUND", round_dir or tmp_path)

    monkeypatch.setattr(run_consensus_round, "escalate_claim", fake_escalate)
    monkeypatch.setattr(run_consensus_round, "_invoke",
                         lambda *a, **kw: groq_calls.append(a) or object())
    monkeypatch.setattr(prompt_assembly, "assemble", lambda role, spec: spec)

    # default: off
    results_default, groq_default = critique_visual_briefs(
        ALL_BRIEFS, {"ha_nollam_shot_001": "내레이션"},
        scene_ids=["ha_nollam_shot_001"], round_dir_root=tmp_path,
    )
    assert groq_calls == []
    assert groq_default == {}
    assert results_default["ha_nollam_shot_001"].verdict == "SOUND"

    # opt-in: additive, escalate_claim's own result is untouched
    results_with_groq, groq_outcomes = critique_visual_briefs(
        ALL_BRIEFS, {"ha_nollam_shot_001": "내레이션"},
        scene_ids=["ha_nollam_shot_001"], round_dir_root=tmp_path,
        include_groq_screen=True,
    )
    assert len(groq_calls) == 1
    assert set(groq_outcomes.keys()) == {"ha_nollam_shot_001"}
    result = results_with_groq["ha_nollam_shot_001"]
    assert result.ok is True
    assert result.agreed is True
    assert result.verdict == "SOUND"
    assert len(escalate_calls) == 2  # once per critique_visual_briefs call above

    # the Groq _invoke call used the "proposer" role and this shot's own round_dir
    participant, role, prompt, round_dir, timeout = groq_calls[0]
    assert participant == "groq"
    assert role == "proposer"
    assert round_dir == result.round_dir


def test_summarize_critique_results_surfaces_groq_screen_without_changing_status(tmp_path: Path):
    """groq_outcomes is purely additive -- status stays derived from the
    codex+grok pair alone, per critique_visual_briefs()'s design."""
    from run_consensus_round import Outcome

    results = {"shot_sound": _FakeEscalationResult(True, True, "SOUND", tmp_path)}
    groq_outcomes = {
        "shot_sound": Outcome("groq", "proposer", True,
                               "## VERDICT\nDEFECTIVE\n\n## FINDINGS\n- none\n", 3.1),
    }
    summary = summarize_critique_results(results, groq_outcomes)
    # codex+grok agreement still drives status, unaffected by Groq disagreeing
    assert summary["shot_sound"]["status"] == "PASS"
    assert summary["shot_sound"]["groq_screen"]["ok"] is True
    assert summary["shot_sound"]["groq_screen"]["verdict"] == "DEFECTIVE"


def test_summarize_critique_results_omits_groq_screen_when_not_given(tmp_path: Path):
    results = {"shot_sound": _FakeEscalationResult(True, True, "SOUND", tmp_path)}
    summary = summarize_critique_results(results)
    assert "groq_screen" not in summary["shot_sound"]


def test_summarize_critique_results_flags_disagreement_and_defect(tmp_path: Path):
    results = {
        "shot_sound": _FakeEscalationResult(True, True, "SOUND", tmp_path),
        "shot_defective": _FakeEscalationResult(True, True, "DEFECTIVE", tmp_path),
        "shot_disagree": _FakeEscalationResult(True, False, None, tmp_path),
        "shot_incomplete": _FakeEscalationResult(False, False, None, tmp_path),
    }
    summary = summarize_critique_results(results)
    assert summary["shot_sound"]["status"] == "PASS"
    assert summary["shot_defective"]["status"] == "REVIEW_REQUIRED"
    assert summary["shot_disagree"]["status"] == "REVIEW_REQUIRED"
    assert summary["shot_incomplete"]["status"] == "REVIEW_REQUIRED"
