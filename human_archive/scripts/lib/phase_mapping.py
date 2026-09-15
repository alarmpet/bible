# -*- coding: utf-8 -*-
"""Nollam sentence-phase <-> story_phases chapter mapping and drift check.

2026-09-15 overhaul plan (docs/superpowers/plans/2026-09-15-human-archive-
nollam-script-visual-motion-multi-llm-overhaul-plan.md), Task 1 "의도적으로
다루지 않은 것": templates/nollam_script_prompt_v3.j2 (~line 83) instructs the
LLM to tag every sentence with one of six bare `phase` values (hook, roadmap,
evidence, paradigm_shift, insight, philosophical_outro), while
config/script_policy_v3.yaml's `story_phases` block declares a five-stage
chapter/time-range structure using `phase_N_name` keys (phase_1_hook,
phase_2_context, phase_3_evidence, phase_4_paradigm_shift, phase_5_outro).
Task 1 only fixed template/schema/policy *routing* (making sure the right
files get used for nollam_file_v1); it explicitly left this naming mismatch
between the two artifacts as a follow-up, and noted that nothing cross-checks
a generated script_candidate.json's sentence-level `phase` values against
story_phases' declared structure.

These are two different axes, not one enum with two spellings:

- story_phases (config/script_policy_v3.yaml) is the coarse, 5-chapter
  time-range/pacing structure of the 20-minute episode (used for cut-length
  policy, sub-chapter counts, etc.) -- and it already matches a real external
  consumer: scripts/generate_video_prompts.py's PHASE_LABELS dict uses the
  exact same five phase_N_name keys to render Korean chapter labels for a
  video-prompt compiler.
- The bare per-sentence `phase` tag the template asks the LLM to emit is a
  finer-grained rhetorical/functional tag: it splits the hook chapter into
  `hook` (cold open / first reversal) vs `roadmap` (the "what you'll learn"
  promise sentence), and splits the outro chapter into `insight` (modern
  implications) vs `philosophical_outro` (the closing signature line). It has
  no dedicated tag for phase_2_context; context-chapter sentences reuse the
  `evidence` tag, matching the template's own prose (Phase 2's "통념의 균열"
  section is itself evidence-driven -- it cites a 2019 university study --
  it just hasn't concluded yet).

Rather than force these into one flat enum (which would either lose the
finer per-sentence distinctions the template's prose clearly wants, or lose
the coarse chapter/time-range structure a real consumer already depends on),
this module documents the deterministic mapping between them and provides a
validator that actually catches drift: an unknown sentence-phase value, a
sentence-phase whose mapped chapter isn't declared in policy.story_phases, a
script that doesn't open in phase_1_hook or close in phase_5_outro, or
sentences whose chapters regress out of order.
"""
from __future__ import annotations

from typing import Any, Iterable

# The six bare per-sentence `phase` values nollam_script_prompt_v3.j2 (~line
# 83) instructs the LLM to tag every sentence with. Single source of truth for
# that enum so tests/validators don't hand-copy it and drift from the
# template's actual wording.
SENTENCE_PHASE_VALUES: tuple[str, ...] = (
    "hook",
    "roadmap",
    "evidence",
    "paradigm_shift",
    "insight",
    "philosophical_outro",
)

# Deterministic mapping from a sentence-level phase tag (fine-grained, one of
# SENTENCE_PHASE_VALUES) to the story_phases chapter key(s) -- config/
# script_policy_v3.yaml's coarse 5-stage time-range structure -- it may
# legitimately appear in. `evidence` maps to both phase_2_context and
# phase_3_evidence because the template gives context-chapter sentences no
# dedicated tag of their own. This mirrors script_policy_v3.yaml's own
# `sentence_phase_map` block (kept here too, not only in YAML, so pure-Python
# callers don't need to load+parse the policy file just to check a phase).
SENTENCE_PHASE_TO_STORY_PHASES: dict[str, tuple[str, ...]] = {
    "hook": ("phase_1_hook",),
    "roadmap": ("phase_1_hook",),
    "evidence": ("phase_2_context", "phase_3_evidence"),
    "paradigm_shift": ("phase_4_paradigm_shift",),
    "insight": ("phase_5_outro",),
    "philosophical_outro": ("phase_5_outro",),
}

# Chapter order index used for the monotonic-progression drift check below.
STORY_PHASE_ORDER: dict[str, int] = {
    "phase_1_hook": 1,
    "phase_2_context": 2,
    "phase_3_evidence": 3,
    "phase_4_paradigm_shift": 4,
    "phase_5_outro": 5,
}


def _sentence_phase_map(policy: dict[str, Any] | None) -> dict[str, tuple[str, ...]]:
    """Prefer policy['sentence_phase_map'] when the caller passed a loaded
    script_policy_v3.yaml, so a future policy edit is honored without a code
    change; fall back to the hardcoded table above when the policy doesn't
    define it (e.g. an older policy snapshot, or a caller that only has the
    sentences and no policy object)."""
    if not policy:
        return SENTENCE_PHASE_TO_STORY_PHASES
    raw = policy.get("sentence_phase_map")
    if not isinstance(raw, dict) or not raw:
        return SENTENCE_PHASE_TO_STORY_PHASES
    out: dict[str, tuple[str, ...]] = {}
    for key, value in raw.items():
        if isinstance(value, str):
            out[key] = (value,)
        elif isinstance(value, (list, tuple)):
            out[key] = tuple(value)
    return out or SENTENCE_PHASE_TO_STORY_PHASES


def validate_sentence_phases(
    sentences: Iterable[dict[str, Any]],
    *,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check a generated nollam script's per-sentence `phase` values against
    the declared 5-stage story_phases structure (config/script_policy_v3.yaml).

    This is the check the 2026-09-15 overhaul plan (Task 1, "의도적으로 다루지
    않은 것") flagged as missing: nothing previously cross-checked a generated
    script_candidate.json's sentence-level `phase` values against
    story_phases' declared structure, so a script could silently use an
    unknown phase value, or drift out of the intended 5-stage order, without
    anything catching it.

    Fail-closed (raises ValueError with a specific reason on the first
    problem found), matching lib/script_contract.py's style. Returns a small
    summary dict (phase_counts, chapter_counts) when the script is valid.
    """
    sentence_phase_map = _sentence_phase_map(policy)
    story_phases = set((policy or {}).get("story_phases") or {}) or set(STORY_PHASE_ORDER)

    rows = list(sentences)
    if not rows:
        raise ValueError("sentences must be a non-empty list")

    phase_counts: dict[str, int] = {}
    chapter_counts: dict[str, int] = {}
    last_floor = 0
    first_chapters: tuple[str, ...] | None = None
    last_chapters: tuple[str, ...] | None = None
    for row in rows:
        phase = row.get("phase")
        sentence_id = row.get("sentence_id", "?")
        if not isinstance(phase, str) or phase not in sentence_phase_map:
            raise ValueError(
                f"sentence {sentence_id}: unknown phase {phase!r} -- not in "
                f"sentence_phase_map ({sorted(sentence_phase_map)})"
            )
        chapters = sentence_phase_map[phase]
        unknown_chapters = [c for c in chapters if c not in story_phases]
        if unknown_chapters:
            raise ValueError(
                f"sentence {sentence_id}: phase {phase!r} maps to chapter(s) "
                f"{unknown_chapters} not declared in policy story_phases "
                f"({sorted(story_phases)})"
            )
        indices = [STORY_PHASE_ORDER[c] for c in chapters if c in STORY_PHASE_ORDER]
        floor = min(indices)
        if floor < last_floor:
            raise ValueError(
                f"sentence {sentence_id}: phase {phase!r} (chapter floor "
                f"{floor}) comes after a later chapter (floor {last_floor}) "
                "earlier in the script -- sentences must progress through "
                "story_phases in order"
            )
        last_floor = floor
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
        for chapter in chapters:
            chapter_counts[chapter] = chapter_counts.get(chapter, 0) + 1
        if first_chapters is None:
            first_chapters = chapters
        last_chapters = chapters

    if first_chapters is not None and "phase_1_hook" not in first_chapters:
        raise ValueError(
            f"first sentence phase must map to phase_1_hook, got chapters {first_chapters}"
        )
    if last_chapters is not None and "phase_5_outro" not in last_chapters:
        raise ValueError(
            f"last sentence phase must map to phase_5_outro, got chapters {last_chapters}"
        )

    return {
        "sentence_count": len(rows),
        "phase_counts": phase_counts,
        "chapter_counts": chapter_counts,
    }
