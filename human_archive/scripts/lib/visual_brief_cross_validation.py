# -*- coding: utf-8 -*-
"""Cross-validate an already-generated visual brief against the same codex+grok
escalation machinery Task 3 wired up for fact-checking (`run_consensus_round.
escalate_claim`), instead of the Studio path's 40-char narration truncation
(§1.3 of the 2026-09-15 overhaul plan) or no check at all.

This deliberately reuses `proposer`/`adversary` roles rather than
`designer`/`critic`: `designer`/`critic` rounds expect Claude as a live
in-loop seat (see run_consensus_round.py's "programmatic escalation" comment)
and have no seat for reviewing a *single already-written* brief -- they are
built for several competing from-scratch proposals. `proposer.md` explicitly
covers "If you are proposing scene content" and `adversary.md` explicitly
lists the exact visual-brief failure modes this plan diagnosed (narration-
truncation-as-design, round-robin motion assignment, text/watermarks in
prompts, character drift), so the existing review contract
(VERDICT/FINDINGS/NUMBERS/UNCERTAINTY) already fits without a new role file.

Cost guardrail (plan §5.5): a full episode is 100-180 shots. This is meant to
be applied to a deliberately small, explicit selection of shots (an operator-
chosen sample or specific scene ids under suspicion), not run unconditionally
for every shot of every build.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, TYPE_CHECKING

import sys

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

if TYPE_CHECKING:
    from run_consensus_round import EscalationResult, Outcome

_BRIEF_FIELDS = (
    "visual_mode",
    "semantic_anchors",
    "focal_subject",
    "action",
    "place",
    "era",
    "shot_scale",
    "camera",
    "foreground",
    "midground",
    "background",
    "prop_motifs",
    "text_overlay_policy",
    "motion_profile",
    "safety_treatment",
)


def build_critique_spec(brief: dict[str, Any], narration_text: str) -> str:
    """Spec text for a proposer/adversary round reviewing one existing visual brief."""
    shot_id = brief.get("shot_id", "UNKNOWN_SHOT")
    lines = [
        f"# Visual brief review: {shot_id}",
        "",
        "A visual brief for one documentary shot has already been produced for the "
        "narration below. Do not design a replacement from scratch. Review this "
        "specific brief: does it actually depict what the narration says, or is it "
        "closer to a generic/templated scene that happens to be topically adjacent?",
        "",
        "## Narration for this shot",
        narration_text.strip() or "(no narration text available)",
        "",
        "## Brief under review",
    ]
    for field in _BRIEF_FIELDS:
        if field in brief:
            lines.append(f"- {field}: {brief[field]!r}")
    lines += [
        "",
        "## What to check",
        "- Does `focal_subject`/`action`/`place` reflect the narration's actual meaning "
        "(a reversal, an absence of evidence, a specific claim), or only its topic "
        "keyword (adversary checklist item 4)?",
        "- Is `motion_profile` tied to a stated reason for this shot, or a fixed-list "
        "cycle (item 5)?",
        "- Does `text_overlay_policy` actually forbid letters/digits/watermarks, and "
        "does nothing else in the brief implicitly ask for on-image text (item 6, hard "
        "gate 6)?",
        "- If this shot recurs a channel subject/character, is the description locked "
        "and consistent rather than drifting (item 7)?",
    ]
    return "\n".join(lines)


def select_scenes_for_critique(
    briefs: list[dict[str, Any]],
    *,
    scene_ids: list[str] | None = None,
    sample_size: int = 0,
) -> list[dict[str, Any]]:
    """Explicit scene_ids always win. Otherwise take an evenly-spaced, deterministic
    sample of size sample_size (not random -- reproducible builds matter more here
    than sampling variety, and an operator can always pass explicit scene_ids for a
    targeted look)."""
    if scene_ids:
        wanted = set(scene_ids)
        return [b for b in briefs if b.get("shot_id") in wanted]
    if sample_size <= 0 or not briefs:
        return []
    if sample_size >= len(briefs):
        return list(briefs)
    step = len(briefs) / float(sample_size)
    indices = sorted({int(i * step) for i in range(sample_size)})
    return [briefs[i] for i in indices]


def screen_with_groq(
    brief: dict[str, Any],
    narration_text: str,
    *,
    timeout: int = 480,
    round_dir: Path,
) -> "Outcome":
    """Additive third screener on an already-produced visual brief -- does NOT
    replace or touch escalate_claim()'s codex+grok pair, and never affects its
    `ok`/`agreed` fields. A caller decides whether to also weigh this.

    2026-09-16 workflow-review finding (audit/orchestration/2026-09-16-2026-09-16-
    groq-placement/), independently confirmed by two reviewers who read this file
    and run_consensus_round.py directly: unlike escalate_claim()'s fact-check
    packet (tri_model_debate_engine.py's execute_fact_check(), which inlines the
    claim sentence but not the evidence excerpt -- Groq has no file-read tool
    access, so that packet leaves it correctly answering CANNOT_DETERMINE),
    build_critique_spec() above already inlines everything needed to judge a
    brief -- the narration text and every _BRIEF_FIELDS value -- so this spec is
    fully self-contained and Groq can meaningfully screen it.

    round_dir is required (not optional) because this must land in the same
    round directory escalate_claim() already wrote to, as a third file
    (`proposer.groq.md` alongside `proposer.codex.md`/`adversary.grok.md` or
    whichever roles that round assigned) -- never a separate round.
    """
    # Imported lazily, and in this order, so run_consensus_round's own
    # sys.path setup (inserting scripts/lib) runs before importing
    # orchestration.prompt_assembly -- mirrors how escalate_claim() itself
    # resolves that import.
    from run_consensus_round import _invoke
    from orchestration.prompt_assembly import assemble

    spec = build_critique_spec(brief, narration_text)
    prompt = assemble("proposer", spec)
    # 2026-09-16 efficiency round (audit/orchestration/2026-09-16-2026-09-16-
    # groq-efficiency/): the default retries=1/backoff=20.0 undershoots the
    # measured token-bucket refill time for one full-size call (24.4s =
    # 3259 measured tokens / (8000 tok/min / 60)) by 4.4s, so a real 429 on a
    # tight loop can fail its one retry before the quota has actually
    # refilled. Groq gets its own, more patient retry budget; codex/grok's
    # global default (used by escalate_claim) is untouched.
    return _invoke("groq", "proposer", prompt, round_dir, timeout, retries=3, backoff=25.0)


def critique_visual_brief(
    brief: dict[str, Any],
    narration_text: str,
    *,
    timeout: int = 480,
    round_dir: Path | None = None,
) -> "EscalationResult":
    # Imported lazily (not at module load) so tests can monkeypatch
    # run_consensus_round.escalate_claim, matching tri_model_debate_engine.py's
    # execute_fact_check() -- see test_fact_check_escalation.py.
    from run_consensus_round import escalate_claim

    shot_id = brief.get("shot_id", "unknown_shot")
    spec = build_critique_spec(brief, narration_text)
    return escalate_claim(f"visual-brief-{shot_id}", spec, timeout=timeout, round_dir=round_dir)


def critique_visual_briefs(
    briefs: list[dict[str, Any]],
    sentence_texts_by_shot: dict[str, str],
    *,
    scene_ids: list[str] | None = None,
    sample_size: int = 0,
    timeout: int = 480,
    round_dir_root: Path | None = None,
    include_groq_screen: bool = False,
) -> tuple[dict[str, EscalationResult], dict[str, "Outcome"]]:
    """Critique a selection of already-generated briefs. Returns
    (shot_id -> EscalationResult, shot_id -> Groq Outcome) for the shots
    actually selected; the second dict is {} unless include_groq_screen=True.
    Callers decide how to act on REVIEW_REQUIRED (disagreement) or DEFECTIVE
    verdicts -- this function never raises on a bad brief, matching
    execute_fact_check()'s "flag, don't silently block" philosophy (Task 3).

    Kept as a separate dict rather than folded into EscalationResult: Groq's
    opinion is an additive third signal, not a vote in escalate_claim()'s
    codex+grok agreement contract (which has its own pinned tests). Pass the
    second dict to summarize_critique_results() to surface it in the summary
    without changing PASS/REVIEW_REQUIRED status.

    2026-09-16 efficiency round recommendation: cap sample_size at 8 (12 for
    denser coverage) when include_groq_screen is on -- 8 x the measured 3259
    tokens/call = 3.26 minutes against the real 8000-tokens/min budget; the
    100-180 nominal shot count would take 40-73 minutes of pure Groq-quota
    wall time (see audit/orchestration/2026-09-16-2026-09-16-groq-efficiency/).
    """
    selected = select_scenes_for_critique(briefs, scene_ids=scene_ids, sample_size=sample_size)
    results: dict[str, EscalationResult] = {}
    groq_outcomes: dict[str, "Outcome"] = {}
    for brief in selected:
        shot_id = brief.get("shot_id", "unknown_shot")
        narration = sentence_texts_by_shot.get(shot_id, "")
        rd = (round_dir_root / shot_id) if round_dir_root else None
        result = critique_visual_brief(brief, narration, timeout=timeout, round_dir=rd)
        results[shot_id] = result
        if include_groq_screen:
            groq_outcomes[shot_id] = screen_with_groq(
                brief, narration, timeout=timeout, round_dir=result.round_dir,
            )
    return results, groq_outcomes


def summarize_critique_results(
    results: dict[str, EscalationResult],
    groq_outcomes: dict[str, "Outcome"] | None = None,
) -> dict[str, Any]:
    """Compact, JSON-serializable summary suitable for embedding in the brief
    manifest. `status` (PASS/REVIEW_REQUIRED) is derived only from the
    escalate_claim() codex+grok pair, unchanged by groq_outcomes -- Groq is an
    additive third opinion surfaced for a human to read, not a vote (see
    critique_visual_briefs()'s docstring)."""
    from orchestration.contract import parse

    summary: dict[str, Any] = {}
    for shot_id, result in results.items():
        row = {
            "ok": result.ok,
            "agreed": result.agreed,
            "verdict": result.verdict,
            "status": "PASS" if (result.agreed and result.verdict == "SOUND")
            else "REVIEW_REQUIRED",
            "round_dir": str(result.round_dir),
            "participants_answered": sorted(result.answers.keys()),
        }
        outcome = (groq_outcomes or {}).get(shot_id)
        if outcome is not None:
            row["groq_screen"] = {
                "ok": outcome.ok,
                "verdict": parse(outcome.text).verdict if outcome.ok else None,
                "detail": outcome.detail or None,
            }
        summary[shot_id] = row
    return summary
