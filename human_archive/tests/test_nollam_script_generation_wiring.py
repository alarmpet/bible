# -*- coding: utf-8 -*-
"""Task 1 (pipeline convergence): build_prompt_context() hardcoded
templates/seonbi_script_prompt.j2 unconditionally, and generate_script_candidate()
hardcoded schemas/verified_script_v2.schema.json (a seonbi-shaped schema, wrong
persona/beat enums for nollam output) -- so nollam_file_v1 builds never actually
rendered templates/nollam_script_prompt_v3.j2 even though the nollam profile,
its policy (config/script_policy_v3.yaml), and its template all already existed
(2026-09-15 overhaul plan §1.1, Task 1).

Rendering the nollam template against the real script_policy_v3.yaml also
surfaced a second, independent bug while wiring this: the template references
policy.voice.prohibited_patterns / policy.voice.neutral_outro (the seonbi
policy's shape), but script_policy_v3.yaml had prohibited_patterns at the top
level and no voice block at all -- with jinja2.StrictUndefined this would have
raised the moment anyone actually tried to render it. Fixed by adding a
voice: block to script_policy_v3.yaml (aliased to the same prohibited_patterns
list, not duplicated). These tests would have caught both gaps.
"""
from __future__ import annotations

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

from lib.script_generation import (  # noqa: E402
    JsonFileProvider,
    build_prompt_context,
    generate_script_candidate,
    resolve_script_paths,
)

_NOLLAM_CONTRACT = _TEST_DIR / "fixtures" / "nollam_episode_contract_v1.yaml"
_NOLLAM_CANDIDATE = _TEST_DIR / "fixtures" / "nollam_script_candidate_v1.json"
_SEONBI_POLICY = _HUMAN_ARCHIVE_ROOT / "config" / "seonbi_narration_policy.yaml"
_NOLLAM_POLICY = _HUMAN_ARCHIVE_ROOT / "config" / "script_policy_v3.yaml"


def _nollam_inputs():
    contract = yaml.safe_load(_NOLLAM_CONTRACT.read_text(encoding="utf-8"))
    inventory = {
        "schema_version": 2,
        "episode_id": contract["episode_id"],
        "claims": [
            {
                "claim_id": "CLM-JWST-001",
                "statement": "초기 은하 성장 속도가 표준 모형 예측의 세 배였다.",
                "risk": "medium",
                "evidence_refs": ["SRC-JWST-01:SPAN-01"],
                "source": "JWST Early Release Science Survey (2023)",
                "allowed_wording": ["예측의 세 배"],
                "forbidden_wording": ["표준 모형이 완전히 틀렸다"],
            }
        ],
    }
    snapshots = {"schema_version": 2, "sources": []}
    policy = yaml.safe_load(_NOLLAM_POLICY.read_text(encoding="utf-8"))
    return contract, inventory, snapshots, policy


def test_resolve_script_paths_for_nollam_file_v1_returns_nollam_artifacts():
    template_path, schema_path, policy_path = resolve_script_paths("nollam_file_v1")
    assert template_path.name == "nollam_script_prompt_v3.j2"
    assert schema_path.name == "trend_verified_script_v1.schema.json"
    assert policy_path.name == "script_policy_v3.yaml"


def test_resolve_script_paths_for_doodle_seonbi_v1_keeps_seonbi_artifacts():
    template_path, schema_path, policy_path = resolve_script_paths("doodle_seonbi_v1")
    assert template_path.name == "seonbi_script_prompt.j2"
    assert schema_path.name == "verified_script_v2.schema.json"
    assert policy_path.name == "seonbi_narration_policy.yaml"


def test_resolve_script_paths_falls_back_to_seonbi_for_unknown_profile():
    template_path, schema_path, policy_path = resolve_script_paths("no_such_profile")
    assert template_path.name == "seonbi_script_prompt.j2"
    assert schema_path.name == "verified_script_v2.schema.json"


def test_nollam_profile_actually_renders_the_nollam_template():
    """The regression test Task 1 item 2 asks for: nollam_file_v1 must really
    render nollam_script_prompt_v3.j2 -- not just resolve its path. This is
    also where the policy.voice.* StrictUndefined bug would surface."""
    contract, inventory, snapshots, policy = _nollam_inputs()
    template_path, _schema_path, _policy_path = resolve_script_paths("nollam_file_v1")

    rendered = build_prompt_context(contract, inventory, snapshots, policy, template_path=template_path)

    assert "NOLLAM FILE" in rendered
    assert "8대 시각 모드" in rendered
    assert contract["core_question"] in rendered
    # The nollam template explicitly forbids the seonbi character persona by
    # naming it as a bad example ("캐릭터 페르소나(선비, ...)"), so "선비" alone
    # legitimately appears -- "쉽선비" (ShipSeonbi) is the actual persona name
    # and only ever appears in the seonbi template, never this one.
    assert "쉽선비" not in rendered


def test_nollam_profile_does_not_fall_back_to_seonbi_template_by_default_omission():
    """Sanity check on the other direction: build_prompt_context() with no
    template_path override still renders the historical seonbi template, so
    existing seonbi callers that never pass template_path see no behavior
    change."""
    contract, inventory, snapshots, policy = _nollam_inputs()
    # seonbi's own policy shape (voice.prohibited_patterns) is required by the
    # default template, so use it here rather than the nollam policy.
    seonbi_policy = yaml.safe_load(_SEONBI_POLICY.read_text(encoding="utf-8"))
    rendered = build_prompt_context(contract, inventory, snapshots, seonbi_policy)
    assert "선비" in rendered


def test_generate_script_candidate_with_nollam_profile_uses_nollam_schema_and_keeps_phase_and_visual_mode():
    contract, inventory, snapshots, policy = _nollam_inputs()
    provider = JsonFileProvider(_NOLLAM_CANDIDATE)

    candidate = generate_script_candidate(
        contract, inventory, snapshots, policy, provider, profile_id="nollam_file_v1"
    )

    assert candidate["format_id"] == "nollam_file_long"
    assert candidate["voice_lock_id"] == "M2_WARM"
    phases = {sentence["phase"] for sentence in candidate["sentences"]}
    assert phases == {"hook", "roadmap", "evidence", "paradigm_shift", "philosophical_outro"}
    assert all("visual_mode" in sentence for sentence in candidate["sentences"])


def test_generate_script_candidate_without_profile_id_rejects_nollam_shaped_output():
    """Proves the schema switch is load-bearing, not cosmetic: the exact same
    nollam-shaped fixture must fail validation against the default (seonbi)
    schema, because it lacks seonbi's required persona/beat/sentence shape."""
    contract, inventory, snapshots, policy = _nollam_inputs()
    provider = JsonFileProvider(_NOLLAM_CANDIDATE)

    with pytest.raises(ValueError, match="Schema validation failed"):
        generate_script_candidate(contract, inventory, snapshots, policy, provider)
