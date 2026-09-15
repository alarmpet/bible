"""The runner's job is to keep answers apart and make disagreement visible.

The tests that matter most are the containment ones: a review round that loses its
sandbox flag, or a Grok call that opens interactively and hangs, would both be found much
later and much more expensively than here.

Ported 2026-09-15 from D:\\all-manage\\tests\\orchestration\\test_run_round.py, adapted for
human_archive's run_consensus_round.py (3 default participants: claude/codex/grok, same as
the source; divergence text uses "--" instead of an em-dash for cp949 console safety, a
crash confirmed directly on this machine while authoring HARD_GATES.md).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import run_consensus_round as run_round  # noqa: E402
from run_consensus_round import (  # noqa: E402
    PARTICIPANTS, Outcome, Run, _attempt, _invoke, assign, check_model_drift, codex_cmd,
    diverge, escalate_claim, grok_cmd, is_transient, say,
)

SOUND = """## VERDICT
SOUND

## FINDINGS
- none

## NUMBERS
| metric | value | how obtained |
|---|---|---|
| scenes reviewed | 14 | len(shots) |

## UNCERTAINTY
none
"""

DEFECTIVE = """## VERDICT
DEFECTIVE

## FINDINGS
- [P0] scene reuses an unrelated image | evidence: x.py:12 | impact: narration/image mismatch

## NUMBERS
| metric | value | how obtained |
|---|---|---|
| scenes reviewed | 11 | recomputed after dedup |

## UNCERTAINTY
none
"""


def test_codex_model_is_pinned() -> None:
    """Inheriting the model from the global config makes a round incomparable with the
    one before it, and silently so."""
    cmd = codex_cmd(Path("out.md"))
    assert "-m" in cmd
    assert cmd[cmd.index("-m") + 1] == "gpt-5.6-luna"


def test_codex_round_is_always_read_only() -> None:
    cmd = codex_cmd(Path("out.md"))
    assert "-s" in cmd and cmd[cmd.index("-s") + 1] == "read-only"
    assert "--dangerously-bypass-approvals-and-sandbox" not in cmd
    assert "danger-full-access" not in cmd
    assert cmd[-1] == "-", "prompt must arrive on stdin, not as an argument"


def test_grok_round_is_never_interactive() -> None:
    cmd = grok_cmd(Path("p.txt"))
    assert "--prompt-file" in cmd, "a bare grok call hangs the round"
    assert "--always-approve" not in cmd
    assert "--bypassPermissions" not in cmd


def test_grok_can_actually_compute() -> None:
    cmd = grok_cmd(Path("p.txt"))
    assert cmd[cmd.index("--permission-mode") + 1] == "auto"
    assert "Bash" not in cmd, "denying Bash leaves the reviewer unable to compute a number"


def test_grok_has_room_to_finish() -> None:
    cmd = grok_cmd(Path("p.txt"))
    assert int(cmd[cmd.index("--max-turns") + 1]) >= 60


def test_grok_carries_no_bypassable_deny_rules() -> None:
    assert "--deny" not in grok_cmd(Path("p.txt"))


def test_roles_rotate_so_no_participant_owns_a_seat() -> None:
    seen = {p: set() for p in PARTICIPANTS}
    for rotation in range(3):
        for participant, role in assign(rotation).items():
            seen[participant].add(role)
    for participant, roles in seen.items():
        assert len(roles) == 3, f"{participant} never rotated through every role"


def test_each_round_assigns_three_distinct_roles() -> None:
    for rotation in range(5):
        assert len(set(assign(rotation).values())) == 3


def _round(tmp_path: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    return tmp_path


def test_diverge_flags_disagreement_as_unresolved(tmp_path: Path, capsys) -> None:
    d = _round(tmp_path, {"proposer.claude.md": SOUND, "adversary.codex.md": DEFECTIVE})
    assert diverge(argparse.Namespace(round=str(d))) == 0
    text = (d / "divergence.md").read_text(encoding="utf-8")
    assert "NO -- DEFECTIVE, SOUND" in text
    assert "UNRESOLVED" in text
    assert "human approval touchpoint" in text
    # the conflicting number has to be visible side by side, not averaged away
    assert "14" in text and "11" in text
    assert "**CONFLICT**" in text
    assert "Conflicts: **1**" in text


def test_diverge_does_not_call_agreement_evidence(tmp_path: Path) -> None:
    d = _round(tmp_path, {"proposer.claude.md": SOUND, "adversary.codex.md": SOUND})
    diverge(argparse.Namespace(round=str(d)))
    text = (d / "divergence.md").read_text(encoding="utf-8")
    assert "UNRESOLVED" not in text
    assert "agreement is not evidence" in text


ONLY_MINE = """## VERDICT
SOUND

## FINDINGS
- none

## NUMBERS
| metric | value | how obtained |
|---|---|---|
| something else entirely | 42 | counted |

## UNCERTAINTY
none
"""


def test_a_number_only_one_reviewer_reported_is_not_agreement(tmp_path: Path) -> None:
    d = _round(tmp_path, {"proposer.claude.md": SOUND, "adversary.codex.md": ONLY_MINE})
    diverge(argparse.Namespace(round=str(d)))
    text = (d / "divergence.md").read_text(encoding="utf-8")
    assert "unconfirmed" in text
    assert "Cross-confirmed metrics: **0**" in text
    assert "No number was independently confirmed" in text


def test_a_number_two_reviewers_agree_on_is_confirmed(tmp_path: Path) -> None:
    d = _round(tmp_path, {"proposer.claude.md": SOUND, "adversary.codex.md": SOUND})
    diverge(argparse.Namespace(round=str(d)))
    text = (d / "divergence.md").read_text(encoding="utf-8")
    assert "**confirmed**" in text
    assert "Cross-confirmed metrics: **1**" in text


def test_a_failed_reviewer_makes_the_round_incomplete(tmp_path: Path) -> None:
    d = _round(tmp_path, {"proposer.claude.md": SOUND,
                          "adversary.codex.FAILED.md": "timed out after 900s"})
    diverge(argparse.Namespace(round=str(d)))
    text = (d / "divergence.md").read_text(encoding="utf-8")
    assert "Incomplete round" in text
    assert "codex" in text
    assert "without the adversary is not an adversarial result" in text


def test_diverge_ignores_scratch_and_failure_files(tmp_path: Path) -> None:
    d = _round(tmp_path, {
        "proposer.claude.md": SOUND,
        "spec.md": "the question",
        "_adversary.claude.prompt.md": "prompt text",
        "adversary.grok.FAILED.md": "timed out after 900s",
    })
    diverge(argparse.Namespace(round=str(d)))
    text = (d / "divergence.md").read_text(encoding="utf-8")
    assert "claude (proposer)" in text
    assert "grok" not in text.split("## Findings")[0].replace("divergence", "")


def test_diverge_reports_when_nothing_to_compare(tmp_path: Path) -> None:
    assert diverge(argparse.Namespace(round=str(tmp_path))) == 1


def test_status_output_never_raises_on_a_narrow_codepage(capsys) -> None:
    """A plain em-dash in a markdown file raised UnicodeEncodeError through this exact
    code path on this machine (2026-09-15, while authoring HARD_GATES.md), confirming why
    `say()` exists."""

    class Cp949Stdout:
        encoding = "cp949"

        def __init__(self) -> None:
            self.written: list[str] = []

        def write(self, text: str) -> None:
            text.encode("cp949")  # raises if say() let anything unencodable through
            self.written.append(text)

    stream, original = Cp949Stdout(), sys.stdout
    sys.stdout = stream  # type: ignore[assignment]
    try:
        say("FAILED \u2014 provider at capacity \uc2e4\ud328")
    finally:
        sys.stdout = original
    assert stream.written, "nothing was written"


@pytest.mark.parametrize("detail", [
    "ERROR: Selected model is at capacity. Please try a different model.",
    "429 Too Many Requests",
    "upstream overloaded",
    "timed out after 900s",
])
def test_upstream_failures_are_retried(detail: str) -> None:
    assert is_transient(detail)


@pytest.mark.parametrize("detail", [
    "exit 1; no output",
    "FileNotFoundError: grok is not on PATH",
    "",
])
def test_real_failures_are_not_retried(detail: str) -> None:
    assert not is_transient(detail)


NARRATION = ("I'll start from the spec and the claim inventory, then draft the scene. "
             "Next I'll read the rest of it.")


def test_narration_without_an_answer_is_not_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(run_round, "_run_grok",
                        lambda *a, **k: Run(True, NARRATION, "", ""))
    run = _attempt("grok", "proposer", "prompt", tmp_path, 60)
    assert not run.ok
    assert "stopped before answering" in run.detail
    assert run.text == NARRATION, "the partial output must survive classification"


def test_a_real_answer_still_succeeds(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(run_round, "_run_grok", lambda *a, **k: Run(True, SOUND, "", ""))
    assert _attempt("grok", "proposer", "prompt", tmp_path, 60).ok


def test_stderr_survives_a_successful_call(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(run_round, "_run_grok",
                        lambda *a, **k: Run(True, SOUND, "", "warning: slow tool call"))
    outcome = _invoke("grok", "proposer", "prompt", tmp_path, 60, retries=0)
    assert outcome.ok
    assert "slow tool call" in outcome.stderr


def test_a_capacity_error_on_stderr_is_retried(tmp_path: Path, monkeypatch) -> None:
    calls: list[int] = []

    def flaky(*_a, **_k):
        calls.append(1)
        if len(calls) == 1:
            return Run(True, NARRATION, "", "ERROR: Selected model is at capacity.")
        return Run(True, SOUND, "", "")

    monkeypatch.setattr(run_round, "_run_grok", flaky)
    outcome = _invoke("grok", "proposer", "prompt", tmp_path, 60, retries=1, backoff=0)
    assert len(calls) == 2, "a capacity error reported only on stderr was not retried"
    assert outcome.ok


def test_malformed_answer_is_surfaced_not_counted_clean(tmp_path: Path) -> None:
    d = _round(tmp_path, {"proposer.claude.md": SOUND,
                          "adversary.codex.md": "it all looks fine to me"})
    diverge(argparse.Namespace(round=str(d)))
    text = (d / "divergence.md").read_text(encoding="utf-8")
    assert "(unparsed)" in text
    assert "no '## SECTION' headings found" in text


# --- check_model_drift -----------------------------------------------------------

def test_matching_model_banner_is_not_drift() -> None:
    assert check_model_drift("some log\nmodel: gpt-5.6-luna\nmore log") == ""


def test_mismatched_model_banner_is_reported() -> None:
    """On this machine (2026-09-15) codex silently served gpt-6-astra for four whole
    rounds when the intended gpt-5.6-luna wasn't honored, per
    C:\\Users\\shs\\Downloads\\tf\\portable-setup.md section 3 -- nobody noticed until the
    user asked. That is exactly the failure this check exists to catch immediately."""
    warning = check_model_drift("model: gpt-6-astra\n")
    assert "MODEL DRIFT" in warning
    assert "gpt-5.6-luna" in warning
    assert "gpt-6-astra" in warning


def test_no_banner_at_all_is_not_flagged_as_drift() -> None:
    """codex's `-o file` capture doesn't always carry the banner (only seen on stderr in
    some runs); absence of the banner is not itself evidence of drift."""
    assert check_model_drift("no banner here") == ""


# --- escalate_claim (mocked -- no real codex/grok invocation) ---------------------

def test_escalate_claim_agrees_when_both_verdicts_match(tmp_path: Path, monkeypatch) -> None:
    def fake_invoke(participant, role, prompt, round_dir, timeout):
        return Outcome(participant, role, True, SOUND, 1.0)

    monkeypatch.setattr(run_round, "_invoke", fake_invoke)
    result = escalate_claim("test-claim", "spec text", round_dir=tmp_path)
    assert result.ok
    assert result.agreed
    assert result.verdict == "SOUND"
    assert set(result.answers) == {"codex", "grok"}


def test_escalate_claim_does_not_agree_on_verdict_mismatch(tmp_path: Path, monkeypatch) -> None:
    def fake_invoke(participant, role, prompt, round_dir, timeout):
        text = SOUND if participant == "codex" else DEFECTIVE
        return Outcome(participant, role, True, text, 1.0)

    monkeypatch.setattr(run_round, "_invoke", fake_invoke)
    result = escalate_claim("test-claim", "spec text", round_dir=tmp_path)
    assert result.ok, "both participants answered, so the round itself is complete"
    assert not result.agreed, "disagreeing verdicts must never be silently resolved"
    assert result.verdict is None


def test_escalate_claim_is_incomplete_when_one_participant_fails(tmp_path: Path, monkeypatch) -> None:
    def fake_invoke(participant, role, prompt, round_dir, timeout):
        if participant == "grok":
            return Outcome(participant, role, False, "", 1.0, detail="timed out after 480s")
        return Outcome(participant, role, True, SOUND, 1.0)

    monkeypatch.setattr(run_round, "_invoke", fake_invoke)
    result = escalate_claim("test-claim", "spec text", round_dir=tmp_path)
    assert not result.ok, "a round without the adversary is not adversarial"
    assert not result.agreed
    assert "codex" in result.answers
    assert "grok" not in result.answers


def test_escalate_claim_rejects_a_malformed_answer_as_disagreement(tmp_path: Path, monkeypatch) -> None:
    """A malformed answer must not silently count as a SOUND vote just because it parsed
    to an empty verdict alongside a real one."""
    def fake_invoke(participant, role, prompt, round_dir, timeout):
        text = SOUND if participant == "codex" else "I looked at it and it's fine."
        return Outcome(participant, role, True, text, 1.0)

    monkeypatch.setattr(run_round, "_invoke", fake_invoke)
    result = escalate_claim("test-claim", "spec text", round_dir=tmp_path)
    assert not result.ok
    assert not result.agreed
    assert "grok" not in result.answers, "a malformed answer must not be counted as a vote"


def test_escalate_claim_persists_assignment_and_answer_files(tmp_path: Path, monkeypatch) -> None:
    def fake_invoke(participant, role, prompt, round_dir, timeout):
        return Outcome(participant, role, True, SOUND, 1.0)

    monkeypatch.setattr(run_round, "_invoke", fake_invoke)
    result = escalate_claim("test-claim", "spec text", round_dir=tmp_path)
    assert (tmp_path / "assignment.json").exists()
    assert (tmp_path / "spec.md").read_text(encoding="utf-8") == "spec text"
    assert any(tmp_path.glob("*.codex.md"))
    assert any(tmp_path.glob("*.grok.md"))
