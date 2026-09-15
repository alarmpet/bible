# -*- coding: utf-8 -*-
"""Task 1 follow-up (2026-09-15 overhaul plan, "의도적으로 다루지 않은 것"):
templates/nollam_script_prompt_v3.j2 (~line 83) instructs the LLM to tag every
sentence with one of six bare `phase` values (hook, roadmap, evidence,
paradigm_shift, insight, philosophical_outro), while
config/script_policy_v3.yaml's `story_phases` block declares a five-stage
chapter structure using `phase_N_name` keys (phase_1_hook ... phase_5_outro).
Task 1 fixed template/schema/policy *routing* only; nothing previously
cross-checked a generated script_candidate.json's sentence-level `phase`
values against story_phases' declared structure, so a script could silently
drift out of the intended 5-stage shape without anything catching it.

These tests exercise scripts/lib/phase_mapping.py's
validate_sentence_phases(), which is the actual drift check: it resolves each
bare sentence-phase value to its story_phases chapter(s) via
config/script_policy_v3.yaml's sentence_phase_map (falling back to the
hardcoded table in phase_mapping.py), and fails closed on an unknown phase
value, a phase whose mapped chapter isn't declared in policy.story_phases, a
script that doesn't open in phase_1_hook / close in phase_5_outro, or
sentences whose chapters regress out of order.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest
import yaml

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_HUMAN_ARCHIVE_ROOT = _PROJECT_ROOT / "human_archive"
_SCRIPTS_DIR = _HUMAN_ARCHIVE_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.phase_mapping import (  # noqa: E402
    SENTENCE_PHASE_VALUES,
    STORY_PHASE_ORDER,
    validate_sentence_phases,
)

_NOLLAM_POLICY = _HUMAN_ARCHIVE_ROOT / "config" / "script_policy_v3.yaml"
_NOLLAM_CANDIDATE = _TEST_DIR / "fixtures" / "nollam_script_candidate_v1.json"
_NOLLAM_TEMPLATE = _HUMAN_ARCHIVE_ROOT / "templates" / "nollam_script_prompt_v3.j2"


def _policy() -> dict:
    return yaml.safe_load(_NOLLAM_POLICY.read_text(encoding="utf-8"))


def _candidate_sentences() -> list[dict]:
    candidate = json.loads(_NOLLAM_CANDIDATE.read_text(encoding="utf-8"))
    return candidate["sentences"]


def test_policy_sentence_phase_map_covers_every_template_phase_value():
    """Every bare phase value the template instructs the LLM to use must have
    an entry in the policy's sentence_phase_map, and every chapter it maps to
    must actually be declared in story_phases -- otherwise the two artifacts
    are back to silently disagreeing."""
    policy = _policy()
    mapping = policy["sentence_phase_map"]
    story_phases = set(policy["story_phases"])

    assert set(mapping) == set(SENTENCE_PHASE_VALUES)
    for phase_value, chapters in mapping.items():
        assert chapters, f"{phase_value} maps to no chapters"
        for chapter in chapters:
            assert chapter in story_phases, (
                f"sentence_phase_map[{phase_value!r}] references undeclared "
                f"story_phases chapter {chapter!r}"
            )


def test_template_phase_instruction_still_lists_the_six_documented_values():
    """Guards against the template's line-83 enum silently drifting from the
    policy's sentence_phase_map (e.g. someone adds a 7th value to one file
    but not the other)."""
    text = _NOLLAM_TEMPLATE.read_text(encoding="utf-8")
    instruction_line = next(line for line in text.splitlines() if line.strip().startswith("4. 모든 문장은 phase"))
    for value in SENTENCE_PHASE_VALUES:
        assert value in instruction_line, f"template phase instruction is missing {value!r}"


def test_real_nollam_fixture_candidate_passes_phase_validation():
    """The realistic nollam-shaped fixture (hook -> roadmap -> evidence ->
    paradigm_shift -> philosophical_outro, in order) must validate cleanly
    against the declared story_phases structure."""
    result = validate_sentence_phases(_candidate_sentences(), policy=_policy())
    assert result["sentence_count"] == 5
    assert result["phase_counts"] == {
        "hook": 1,
        "roadmap": 1,
        "evidence": 1,
        "paradigm_shift": 1,
        "philosophical_outro": 1,
    }
    # evidence's chapter floor (phase_2_context) still counts toward both of
    # the chapters it can legitimately represent.
    assert result["chapter_counts"]["phase_3_evidence"] == 1
    assert result["chapter_counts"]["phase_5_outro"] == 1


def test_unknown_phase_value_is_rejected():
    """A generated script using a phase value that isn't in the template's
    enum (a typo, or an LLM inventing a new one) must fail closed instead of
    silently passing through unvalidated -- this is exactly the gap Task 1
    left open."""
    sentences = copy.deepcopy(_candidate_sentences())
    sentences[2]["phase"] = "supporting_context"  # not one of the six values
    with pytest.raises(ValueError, match="unknown phase"):
        validate_sentence_phases(sentences, policy=_policy())


def test_out_of_order_phase_regression_is_rejected():
    """If a later sentence reverts to an earlier chapter's phase (e.g. a
    paradigm_shift sentence followed by a hook-chapter sentence), that is
    exactly the kind of structural drift story_phases is meant to prevent."""
    sentences = copy.deepcopy(_candidate_sentences())
    sentences[3]["phase"] = "hook"  # was paradigm_shift; now regresses to phase_1_hook
    with pytest.raises(ValueError, match="comes after a later chapter"):
        validate_sentence_phases(sentences, policy=_policy())


def test_script_must_open_in_hook_chapter():
    sentences = copy.deepcopy(_candidate_sentences())
    # Move both hook-chapter sentences to "evidence" (rather than just the
    # first) so the monotonic-order check doesn't fire first -- this isolates
    # the "must open in phase_1_hook" check on its own.
    sentences[0]["phase"] = "evidence"
    sentences[1]["phase"] = "evidence"
    with pytest.raises(ValueError, match="first sentence phase must map to phase_1_hook"):
        validate_sentence_phases(sentences, policy=_policy())


def test_script_must_close_in_outro_chapter():
    sentences = copy.deepcopy(_candidate_sentences())
    sentences[-1]["phase"] = "paradigm_shift"
    with pytest.raises(ValueError, match="last sentence phase must map to phase_5_outro"):
        validate_sentence_phases(sentences, policy=_policy())


def test_phase_missing_from_policy_story_phases_is_rejected():
    """If a future policy edit drops a story_phases chapter (or renames it)
    without updating sentence_phase_map, sentences whose phase resolves to
    the now-missing chapter must fail instead of validating against a
    chapter that no longer exists."""
    policy = _policy()
    del policy["story_phases"]["phase_4_paradigm_shift"]
    with pytest.raises(ValueError, match="not declared in policy story_phases"):
        validate_sentence_phases(_candidate_sentences(), policy=policy)


def test_story_phase_order_matches_policy_declaration_order():
    """Sanity check that phase_mapping.py's hardcoded chapter order agrees
    with the order story_phases actually declares them in policy, so the
    monotonic-progression check enforces the real intended sequence."""
    policy = _policy()
    declared_order = list(policy["story_phases"])
    assert declared_order == sorted(STORY_PHASE_ORDER, key=lambda k: STORY_PHASE_ORDER[k])
