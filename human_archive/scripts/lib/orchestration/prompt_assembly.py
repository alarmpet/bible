"""Assemble a role prompt from the preamble, the live hard gates, and the role file.

The gates are not copied into the prompt files. They are lifted out of `HARD_GATES.md` at
assembly time, so editing that file changes what every delegated agent is told and there
is no second copy to drift out of date. If the section cannot be found, assembly raises
rather than sending a prompt with the constraints missing -- a delegation without gates is
the one failure mode this whole layer exists to prevent.

Ported 2026-09-15 from D:\\all-manage\\tools\\orchestration\\prompt_assembly.py, adapted
for human_archive: `AGENTS.md` -> `docs/orchestration/HARD_GATES.md` as part of
docs/superpowers/plans/2026-09-15-human-archive-nollam-script-visual-motion-multi-llm-overhaul-plan.md
Task 2.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # .../human_archive
HARD_GATES_FILE = ROOT / "docs" / "orchestration" / "HARD_GATES.md"
PROMPTS = ROOT / "docs" / "orchestration" / "prompts"
ROLES = ("proposer", "adversary", "replicator")
# The propose mode has its own two roles. They share the preamble -- the hard gates
# apply to an agent writing a proposal exactly as they do to one checking a number --
# but not the VERDICT/FINDINGS contract, which has nothing to say about an idea.
DESIGN_ROLES = ("designer", "critic")
ALL_ROLES = ROLES + DESIGN_ROLES
PLACEHOLDER = "{{HARD_GATES}}"

_GATES_HEADING = re.compile(r"^#{1,2}\s+Hard gates\b.*$", re.MULTILINE)
_NEXT_HEADING = re.compile(r"^#{1,2}\s+", re.MULTILINE)
_NUMBERED = re.compile(r"^\d+\.\s+\S", re.MULTILINE)


class GatesNotFound(RuntimeError):
    """HARD_GATES.md did not yield a usable hard-gate section."""


def hard_gates(gates_file: Path | None = None) -> str:
    """The numbered gate list from HARD_GATES.md, verbatim."""
    path = gates_file or HARD_GATES_FILE
    text = path.read_text(encoding="utf-8")
    start = _GATES_HEADING.search(text)
    if start is None:
        raise GatesNotFound(f"no '## Hard gates' / '# Hard gates' heading in {path}")
    rest = text[start.end():]
    end = _NEXT_HEADING.search(rest)
    section = (rest[: end.start()] if end else rest).strip()
    found = len(_NUMBERED.findall(section))
    if found < 5:
        raise GatesNotFound(
            f"hard-gate section in {path} has only {found} numbered gates; refusing to "
            "assemble a prompt with constraints that look truncated"
        )
    return section


def assemble(role: str, spec: str, gates_file: Path | None = None,
             prompts_dir: Path | None = None) -> str:
    """Full prompt text for one role: preamble (gates injected), role, then the spec."""
    if role not in ALL_ROLES:
        raise ValueError(f"unknown role {role!r}; expected one of {ALL_ROLES}")
    directory = prompts_dir or PROMPTS
    preamble = (directory / "_preamble.md").read_text(encoding="utf-8")
    if PLACEHOLDER not in preamble:
        raise GatesNotFound(f"{PLACEHOLDER} missing from _preamble.md; gates would be dropped")
    preamble = preamble.replace(PLACEHOLDER, hard_gates(gates_file))
    if role in DESIGN_ROLES:
        # The preamble ends with the review contract (VERDICT/FINDINGS/NUMBERS), which
        # has nothing to say about a proposal. Leaving both in would give the agent two
        # contradictory output formats and let it pick.
        head, marker, _tail = preamble.partition("## Output contract")
        if marker:
            preamble = head + "## Output contract\n\nThe role below defines it.\n"
    body = (directory / f"{role}.md").read_text(encoding="utf-8")
    heading = "Problem for this round" if role in DESIGN_ROLES else "Specification for this round"
    return f"{preamble}\n\n---\n\n{body}\n\n---\n\n# {heading}\n\n{spec}\n"


if __name__ == "__main__":  # pragma: no cover - manual inspection
    import argparse

    parser = argparse.ArgumentParser(description="Print an assembled role prompt.")
    parser.add_argument("role", choices=ROLES)
    parser.add_argument("--spec", default="(spec goes here)")
    args = parser.parse_args()
    print(assemble(args.role, args.spec))
