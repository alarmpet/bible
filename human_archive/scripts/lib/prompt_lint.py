from __future__ import annotations

import re
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from run_consensus_round import Outcome


_LABEL_LANGUAGE = re.compile(r"\b(text|caption|label|sign|signage|written|date)\b", re.IGNORECASE)


def lint_image_request(request: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    positive = str(request.get("positive_prompt", ""))
    role = str(request.get("visual_role", ""))
    host_references = [item for item in request.get("host_reference_assets", []) if item]

    if re.search(r"\d", positive):
        errors.append("positive prompt contains a digit")
    if _LABEL_LANGUAGE.search(positive):
        errors.append("positive prompt contains generated label language")
    if role != "host_explainer" and host_references:
        errors.append("host reference is allowed only for host_explainer")
    for overlay in request.get("overlay_text", []):
        if overlay and str(overlay) in positive:
            errors.append("renderer overlay text leaked into positive prompt")
    return errors


def require_clean_image_request(request: dict[str, Any]) -> None:
    errors = lint_image_request(request)
    if errors:
        raise ValueError("; ".join(errors))


# ---------------------------------------------------------------------------------
# Optional Groq-based screen for IMPLIED on-image text that _LABEL_LANGUAGE's
# English-only regex cannot catch: a described object that would visually carry
# text (a stone tablet with an inscription, a palace placard/현판, an era-name
# banner/연호, a dated monument/비석) even when the prompt spells out no literal
# digits or English text-related words. 2026-09-16 groq-efficiency round
# (audit/orchestration/2026-09-16-2026-09-16-groq-efficiency/): deliberately does
# NOT use orchestration.prompt_assembly.assemble()'s full proposer/adversary
# review-round wrapper -- that measured ~84% of a visual-brief critique's prompt
# tokens -- because this is a narrow yes/no classification, not an adversarial
# design review, and a compact prompt keeps real per-shot throughput inside the
# free tier's 8000-tokens/min budget. Opt-in and additive only, like
# screen_with_groq() for visual briefs: never blocks on its own, never replaces
# lint_image_request()'s deterministic regex check.
# ---------------------------------------------------------------------------------

def build_text_policy_screen_prompt(positive_prompt: str) -> str:
    # The "## VERDICT" header (not a bare "VERDICT:" line) is required, not
    # stylistic: run_consensus_round._attempt() runs every participant's
    # answer through orchestration.contract.has_contract(), which only
    # recognizes a markdown "##"-prefixed VERDICT/FINDINGS/NUMBERS/UNCERTAINTY
    # section. A bare "VERDICT: CLEAN" response is a perfectly good answer
    # that _attempt() nonetheless marks ok=False ("stopped before answering")
    # purely because of the missing "##" -- found live screening a real
    # shot's prompt this session (Outcome.ok was False despite a correctly
    # parsed CLEAN/FLAGGED answer in Outcome.text). One "## VERDICT" line is
    # sufficient for has_contract() -- it does not require FINDINGS/NUMBERS/
    # UNCERTAINTY too, so the rest of the format stays compact.
    return (
        "You are screening an AI image-generation prompt for a documentary "
        "channel that forbids ANY rendered text, letters, digits, dates, "
        "years, era names, inscriptions, signage, or captions appearing in "
        "the generated image -- in ANY language or script (Latin, Hangul, "
        "Hanja/Chinese characters, etc.), even if only implied rather than "
        "spelled out. A separate regex check already catches literal digits "
        "and the English words text/caption/label/sign/signage/written/date. "
        "Your job is to catch what that regex cannot: a described object "
        "that would visually carry text even though no literal letters are "
        "spelled out in the prompt -- e.g. a stone tablet with an "
        "inscription, a palace placard, an era-name banner, a dated "
        "monument, a newspaper headline, a calendar page, a name plate.\n\n"
        "Prompt to screen:\n"
        f"{positive_prompt}\n\n"
        "Answer in exactly this format, nothing else:\n"
        "## VERDICT\n"
        "CLEAN or FLAGGED\n\n"
        "## REASON\n"
        "<one sentence; empty if CLEAN>"
    )


def parse_text_policy_screen(text: str) -> tuple[bool | None, str]:
    """Returns (flagged, reason). flagged is None if the response didn't
    follow the expected VERDICT CLEAN/FLAGGED format at all (treat as
    inconclusive, not as CLEAN -- a malformed answer is not a pass)."""
    verdict_match = re.search(r"VERDICT\s*\n?\s*(CLEAN|FLAGGED)", text, re.IGNORECASE)
    reason_match = re.search(r"REASON\s*\n?\s*(.*)", text, re.IGNORECASE | re.DOTALL)
    reason = reason_match.group(1).strip() if reason_match else ""
    if not verdict_match:
        return None, reason
    return verdict_match.group(1).upper() == "FLAGGED", reason


def screen_prompt_text_policy_with_groq(
    positive_prompt: str, *, timeout: int = 60,
) -> "Outcome":
    """Fast, cheap Groq screen for implied on-image text that
    lint_image_request()'s regex cannot catch. No round_dir/audit-trail file
    is written (unlike screen_with_groq() for visual briefs) -- this is meant
    to run inline per-shot during request validation, not as a recorded
    cross-verification round; round_dir is unused by _run_groq's code path in
    _attempt() so a placeholder is safe to pass through _invoke()."""
    from run_consensus_round import _invoke

    prompt = build_text_policy_screen_prompt(positive_prompt)
    return _invoke("groq", "proposer", prompt, Path("."), timeout, retries=3, backoff=25.0)
