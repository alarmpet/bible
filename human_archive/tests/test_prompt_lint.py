from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import run_consensus_round  # noqa: E402
from lib.prompt_lint import (  # noqa: E402
    build_text_policy_screen_prompt,
    lint_image_request,
    parse_text_policy_screen,
    screen_prompt_text_policy_with_groq,
)


def test_lint_rejects_digits_and_generated_label_language():
    errors = lint_image_request({
        "visual_role": "historical_reconstruction",
        "positive_prompt": "A palace sign written with the date 1701",
        "host_reference_assets": [],
        "overlay_text": [],
    })
    assert any("digit" in error for error in errors)
    assert any("label" in error for error in errors)


def test_lint_rejects_host_reference_outside_host_role():
    errors = lint_image_request({
        "visual_role": "evidence_object",
        "positive_prompt": "A close view of a sealed document",
        "host_reference_assets": ["canonical_seonbi.png"],
        "overlay_text": [],
    })
    assert any("host reference" in error for error in errors)


def test_lint_accepts_clean_reconstruction_request():
    errors = lint_image_request({
        "visual_role": "historical_reconstruction",
        "positive_prompt": "Late Joseon royal council, historical actors discussing an order, hand drawn doodle",
        "host_reference_assets": [],
        "overlay_text": ["renderer only"],
    })
    assert errors == []


def test_build_text_policy_screen_prompt_embeds_the_positive_prompt():
    """The "## VERDICT" header (not a bare "VERDICT:" line) is required:
    run_consensus_round._attempt() marks any answer without a "##"-prefixed
    VERDICT/FINDINGS/NUMBERS/UNCERTAINTY section ok=False via
    orchestration.contract.has_contract(), even when the answer is otherwise
    perfectly parseable -- found live screening a real shot's prompt this
    session."""
    prompt = build_text_policy_screen_prompt("a stone tablet with an inscription")
    assert "a stone tablet with an inscription" in prompt
    assert "## VERDICT" in prompt
    assert "CLEAN or FLAGGED" in prompt


def test_parse_text_policy_screen_reads_flagged_and_reason():
    flagged, reason = parse_text_policy_screen(
        "## VERDICT\nFLAGGED\n\n## REASON\nimplies an inscribed monument plaque"
    )
    assert flagged is True
    assert reason == "implies an inscribed monument plaque"


def test_parse_text_policy_screen_reads_clean():
    flagged, reason = parse_text_policy_screen("## VERDICT\nCLEAN\n\n## REASON\n")
    assert flagged is False


def test_parse_text_policy_screen_malformed_response_is_inconclusive_not_clean():
    """2026-09-16 finding pattern reused here: a malformed/off-format answer
    must never be silently treated as a pass."""
    flagged, reason = parse_text_policy_screen("I think this looks fine overall.")
    assert flagged is None


def test_screen_prompt_text_policy_with_groq_skips_the_full_review_wrapper(monkeypatch):
    """2026-09-16 groq-efficiency finding: orchestration.prompt_assembly.assemble()'s
    full proposer/adversary wrapper measured ~84% of a visual-brief critique's
    prompt tokens. This screen is a narrow classification, not an adversarial
    review round, so it must send a compact prompt directly -- never call
    assemble()."""
    calls = []
    monkeypatch.setattr(run_consensus_round, "_invoke",
                         lambda *a, **kw: calls.append((a, kw)) or object())

    screen_prompt_text_policy_with_groq("a dated monument with an inscription", timeout=45)

    assert len(calls) == 1
    args, kwargs = calls[0]
    participant, role, prompt, round_dir, timeout = args
    assert participant == "groq"
    assert role == "proposer"
    assert "a dated monument with an inscription" in prompt
    # not wrapped in the full hard-gates/role-file preamble
    assert "Hard gates" not in prompt
    assert timeout == 45
    assert kwargs == {"retries": 3, "backoff": 25.0}
