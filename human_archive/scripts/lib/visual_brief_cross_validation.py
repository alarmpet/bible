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
    from run_consensus_round import EscalationResult

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
) -> dict[str, EscalationResult]:
    """Critique a selection of already-generated briefs. Returns shot_id -> EscalationResult
    only for the shots actually selected; callers decide how to act on REVIEW_REQUIRED
    (disagreement) or DEFECTIVE verdicts -- this function never raises on a bad brief,
    matching execute_fact_check()'s "flag, don't silently block" philosophy (Task 3).
    """
    selected = select_scenes_for_critique(briefs, scene_ids=scene_ids, sample_size=sample_size)
    results: dict[str, EscalationResult] = {}
    for brief in selected:
        shot_id = brief.get("shot_id", "unknown_shot")
        narration = sentence_texts_by_shot.get(shot_id, "")
        rd = (round_dir_root / shot_id) if round_dir_root else None
        results[shot_id] = critique_visual_brief(brief, narration, timeout=timeout, round_dir=rd)
    return results


def summarize_critique_results(results: dict[str, EscalationResult]) -> dict[str, Any]:
    """Compact, JSON-serializable summary suitable for embedding in the brief manifest."""
    summary: dict[str, Any] = {}
    for shot_id, result in results.items():
        summary[shot_id] = {
            "ok": result.ok,
            "agreed": result.agreed,
            "verdict": result.verdict,
            "status": "PASS" if (result.agreed and result.verdict == "SOUND")
            else "REVIEW_REQUIRED",
            "round_dir": str(result.round_dir),
            "participants_answered": sorted(result.answers.keys()),
        }
    return summary
