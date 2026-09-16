from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

PLACEHOLDER_MARKERS = (
    "narration-specific subject",
    "depict the narrated action directly",
    "historical people and setting",
    "period-dressed palace figures perform the single concrete action described by the narration",
    "specific joseon palace location implied by the narration",
)

_BASELINE_SHOT_COUNT_RANGE = (95, 120)
_BASELINE_HOST_RATIO_RANGE = (0.08, 0.12)


def _read_episode_contract(build: Path) -> dict:
    """Best-effort read of the episode contract, .json or the older .yaml
    shape (2026-09-16: nollam_file_v1 builds use episode_contract.json;
    pre-existing doodle_seonbi_v1/ep02 builds use episode_contract.yaml).
    Returns {} when neither exists so callers fall back to the historical
    hardcoded 20-minute-episode assumptions unchanged."""
    json_path = build / "source" / "episode_contract.json"
    if json_path.is_file():
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    for name in ("episode_contract.yaml", "episode_contract.yml"):
        yaml_path = build / "source" / name
        if yaml_path.is_file():
            try:
                import yaml

                return yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            except OSError:
                return {}
    return {}



# config/visual_pacing_profiles.yaml's nollam_decay_20m zones: cold_open's
# min_shot_sec (fastest cuts anywhere in the curve) and outro's
# hard_max_shot_sec (slowest). Shot count isn't linear in duration -- a short
# episode spends a larger fraction of its runtime in the fast early zones, so
# scaling the 1200s baseline count proportionally (e.g. 180/1200 * 95..120)
# under-predicts a real short build's shot count. Bounding by these global
# per-shot extremes instead is looser but never rejects what a linear scale
# would have wrongly flagged, and still catches genuinely degenerate counts.
_GLOBAL_MIN_SHOT_SEC = 3.0
_GLOBAL_MAX_SHOT_SEC = 18.0


def _expected_shot_count_range(contract: dict) -> tuple[int, int]:
    """95-120 is a real observed range, but only for the nominal 1200s
    trend_explainer_20m/standard_docu delivery -- it doesn't shrink for a
    quick_3m (~180s) episode. Bound it by the curve's own global per-shot
    duration extremes when the contract declares target_duration_sec;
    otherwise keep the historical hardcoded band unchanged (2026-09-16
    finding: a real 24-shot quick_3m build was rejected outright by this
    unconditional check)."""
    target = contract.get("target_duration_sec")
    if not target:
        return _BASELINE_SHOT_COUNT_RANGE
    target = float(target)
    low = max(1, math.floor(target / _GLOBAL_MAX_SHOT_SEC))
    high = max(low, math.ceil(target / _GLOBAL_MIN_SHOT_SEC))
    return (low, high)


def _expected_host_ratio_range(contract: dict) -> tuple[float, float]:
    """0.08-0.12 reflects doodle_seonbi_v1's host-avatar convention
    (CLAUDE.md section 2.2). nollam_file_v1 declares host_ratio: 0.0 (no host
    avatar at all -- channel_profiles.yaml, and the same 0% this session
    already fixed in select_host_shot_ids()); this check must accept that
    instead of rejecting every nollam build for having "too few" hosts.
    Any other/unknown profile keeps the historical band unchanged."""
    if contract.get("channel_profile") == "nollam_file_v1":
        return (0.0, 0.0)
    return _BASELINE_HOST_RATIO_RANGE


def validate(build: Path, *, include_groq_text_screen: bool = False) -> list[str]:
    data = json.loads((build / "flow_image_prompts.json").read_text(encoding="utf-8"))
    requests = data.get("requests", [])
    errors: list[str] = []
    if not requests:
        errors.append("no requests")
        return errors
    contract = _read_episode_contract(build)
    shot_count_low, shot_count_high = _expected_shot_count_range(contract)
    if not shot_count_low <= len(requests) <= shot_count_high:
        errors.append(
            f"shot count {len(requests)} outside {shot_count_low}-{shot_count_high}"
        )
    for index, request in enumerate(requests):
        if not request.get("semantic_anchors"):
            errors.append(f"{index}: missing semantic anchors")
        elif any(re.search(r"[가-힣]", str(anchor)) for anchor in request.get("semantic_anchors", [])):
            errors.append(f"{index}: hangul semantic anchor may induce generated text")
        prompt = str(request.get("submission_prompt", ""))
        lowered = prompt.lower()
        if any(marker in lowered for marker in PLACEHOLDER_MARKERS):
            errors.append(f"{index}: production placeholder prompt")
        if "1701" in prompt:
            errors.append(f"{index}: forbidden 1701")
        if index and request.get("visual_mode") == "host_chapter_hinge" and requests[index - 1].get("visual_mode") == "host_chapter_hinge":
            errors.append(f"{index}: consecutive hosts")
    host_ratio_low, host_ratio_high = _expected_host_ratio_range(contract)
    hosts = sum(request.get("visual_mode") == "host_chapter_hinge" for request in requests)
    host_ratio = hosts / len(requests)
    if not host_ratio_low <= host_ratio <= host_ratio_high:
        errors.append(f"host ratio {host_ratio:.3f}")

    if include_groq_text_screen:
        # 2026-09-16 groq-efficiency round finding, live-verified: a compact
        # (non-assemble()-wrapped) screen measured ~311 tokens/call, well
        # under the free tier's 8000-tokens/min budget -- sustains ~25
        # calls/min, so screening every request in a real 100-180-shot
        # episode finishes in well under 10 minutes (unlike the ~2.45
        # calls/min, 40-73-minute visual-brief critique screen). This catches
        # implied on-image text (a described inscription/placard/banner)
        # that _LABEL_LANGUAGE's English-only regex above cannot.
        from lib.prompt_lint import parse_text_policy_screen, screen_prompt_text_policy_with_groq

        for index, request in enumerate(requests):
            prompt = str(request.get("positive_prompt", ""))
            if not prompt:
                continue
            outcome = screen_prompt_text_policy_with_groq(prompt)
            if not outcome.ok:
                errors.append(f"{index}: groq text screen failed -- {outcome.detail}")
                continue
            flagged, reason = parse_text_policy_screen(outcome.text)
            if flagged:
                errors.append(f"{index}: groq flagged implied on-image text -- {reason}")
            elif flagged is None:
                errors.append(f"{index}: groq text screen response was malformed (treated as inconclusive, not clean)")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument(
        "--include-groq-text-screen",
        action="store_true",
        help="Additionally screen every request's positive_prompt with Groq "
        "for implied on-image text the regex check above cannot catch "
        "(a described inscription/placard/banner in any script, not just "
        "literal digits or English text-related words). Off by default. "
        "Measured ~311 tokens/call, well within Groq's free-tier budget for "
        "a full episode's shot count (see lib/prompt_lint.py's "
        "screen_prompt_text_policy_with_groq()).",
    )
    args = parser.parse_args()
    errors = validate(args.build, include_groq_text_screen=args.include_groq_text_screen)
    if errors:
        print("\n".join(errors))
        raise SystemExit(1)
    count = len(json.loads((args.build / "flow_image_prompts.json").read_text(encoding="utf-8"))["requests"])
    print(f"PASS: {count} requests")


if __name__ == "__main__":
    main()
