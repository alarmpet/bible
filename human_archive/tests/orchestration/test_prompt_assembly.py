"""A prompt that reaches an agent without the hard gates is the failure this layer exists
to prevent, so assembly has to fail loudly rather than quietly drop them.

Ported 2026-09-15 from D:\\all-manage\\tests\\orchestration\\test_prompt_assembly.py,
adapted for human_archive's HARD_GATES.md and role wording.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_LIB_DIR = Path(__file__).resolve().parents[2] / "scripts" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from orchestration.prompt_assembly import (  # noqa: E402
    PLACEHOLDER, ROLES, DESIGN_ROLES, ALL_ROLES, GatesNotFound, assemble, hard_gates,
)


def test_gates_come_from_hard_gates_md() -> None:
    gates = hard_gates()
    assert "same underlying model in two seats" in gates
    assert "copied verbatim" in gates
    assert "another channel's real, specific video" in gates
    assert gates.count("\n1. ") + gates.startswith("1. ") >= 1


@pytest.mark.parametrize("role", ROLES)
def test_every_review_role_carries_the_gates(role: str) -> None:
    prompt = assemble(role, spec="Grade this claim.")
    assert PLACEHOLDER not in prompt, "placeholder survived assembly"
    assert "same underlying model in two seats" in prompt
    assert "## VERDICT" in prompt, "output contract missing"
    assert "Grade this claim." in prompt, "spec not appended"


@pytest.mark.parametrize("role", DESIGN_ROLES)
def test_every_design_role_carries_the_gates_without_review_contract(role: str) -> None:
    prompt = assemble(role, spec="Design a scene for this narration.")
    assert PLACEHOLDER not in prompt
    assert "same underlying model in two seats" in prompt
    assert "Design a scene for this narration." in prompt
    # design roles must not receive the review contract's own heading
    assert "SOUND | DEFECTIVE | CANNOT_DETERMINE" not in prompt


@pytest.mark.parametrize("role", ALL_ROLES)
def test_role_body_is_present(role: str) -> None:
    prompt = assemble(role, spec="s")
    assert f"# Role: {role.upper()}" in prompt


def test_replicator_is_told_not_to_read_the_proposer_first() -> None:
    assert "Do not read the proposer's answer" in assemble("replicator", spec="s")


def test_adversary_is_scored_on_finding_defects() -> None:
    prompt = assemble("adversary", spec="s")
    assert "You succeed by finding a defect" in prompt


def test_unknown_role_is_refused() -> None:
    with pytest.raises(ValueError):
        assemble("reviewer", spec="s")


def test_missing_gate_section_refuses_assembly(tmp_path: Path) -> None:
    fake = tmp_path / "HARD_GATES.md"
    fake.write_text("# HARD_GATES.md\n\n## Something else\n\nno gates here\n", encoding="utf-8")
    with pytest.raises(GatesNotFound):
        hard_gates(fake)


def test_truncated_gate_section_refuses_assembly(tmp_path: Path) -> None:
    fake = tmp_path / "HARD_GATES.md"
    fake.write_text("# Hard gates\n\n1. Do not fabricate.\n2. No silent fallback.\n",
                     encoding="utf-8")
    with pytest.raises(GatesNotFound, match="truncated"):
        hard_gates(fake)


def test_preamble_without_placeholder_refuses_assembly(tmp_path: Path) -> None:
    (tmp_path / "_preamble.md").write_text("no placeholder\n", encoding="utf-8")
    (tmp_path / "proposer.md").write_text("# Role: PROPOSER\n", encoding="utf-8")
    with pytest.raises(GatesNotFound, match="missing"):
        assemble("proposer", spec="s", prompts_dir=tmp_path)
