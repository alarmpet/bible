from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

from jinja2 import Environment, StrictUndefined

from lib.aligned_prompt_compiler import compile_aligned_prompt, compile_nollam_prompt
from lib.fact_review_approval import validate_fact_review_gate
from lib.provenance import compute_file_sha256
from lib.visual_brief_cross_validation import (
    critique_visual_briefs,
    summarize_critique_results,
)
from lib.visual_brief_provider import (
    AntigravityCliVisualBriefProvider,
    CodexCliVisualBriefProvider,
    JsonFileVisualBriefProvider,
    build_fallback_brief,
)


_HANGUL = re.compile(r"[가-힣]")
_INTERNAL_ID = re.compile(r"(?:CLM|SRC|SPAN)-", re.IGNORECASE)
_DIRECT_DEPICTION_MODES = {
    "historical_reconstruction",
    "character_action",
    "place_establishing",
    "evidence_artifact",
}
_MOTIF_FAMILY_PATTERNS = {
    "archive_container": re.compile(
        r"\b(?:case|box|chest|scroll tube|record volume|archive volume)\b",
        re.IGNORECASE,
    ),
    "gate_boundary": re.compile(
        r"\b(?:gate|threshold|barrier|boundary|divider)\b",
        re.IGNORECASE,
    ),
    "balance_scale": re.compile(
        r"\b(?:balance|scale|weighing beam)\b",
        re.IGNORECASE,
    ),
    "path_route": re.compile(
        r"\b(?:path|road|route|rail|track)\b",
        re.IGNORECASE,
    ),
    "screen_curtain": re.compile(
        r"\b(?:screen|curtain|veil)\b",
        re.IGNORECASE,
    ),
    "bowl_vessel": re.compile(
        r"\b(?:bowl|vessel|cup)\b",
        re.IGNORECASE,
    ),
}
_IMAGE_FACING_FIELDS = (
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
    "safety_treatment",
)


_CHANNEL_PROFILES_PATH = Path(__file__).resolve().parents[1] / "config" / "channel_profiles.yaml"


def resolve_image_prompt_compiler_id(channel_profile_id: str | None) -> str:
    """Which image-prompt compiler a channel profile uses. Opt-in: without an
    explicit channel_profile_id this returns "aligned" (compile_aligned_prompt,
    today's unconditional default) unchanged, so existing callers that never
    pass --channel-profile (CLAUDE.md's documented EP02/doodle_seonbi_v1 flow)
    see no behavior change.

    Before this, compile_aligned_prompt() -- whose STYLE constant is literally
    "Korean editorial ink-doodle illustration..." -- was the only compiler
    generate_visual_briefs.py ever called, for every profile including
    nollam_file_v1, whose visual policy is photorealistic cinematic
    documentary. compile_nollam_prompt() (lib/aligned_prompt_compiler.py) was
    already built and tested (tests/test_nollam_prompt_profile.py) for exactly
    this, just never reachable from here (2026-09-15 overhaul plan Task 1
    item 3, §1.3).
    """
    if not channel_profile_id:
        return "aligned"
    try:
        import yaml

        data = yaml.safe_load(_CHANNEL_PROFILES_PATH.read_text(encoding="utf-8")) or {}
        profile = (data.get("profiles") or {}).get(channel_profile_id, {})
        return str(profile.get("image_prompt_compiler") or "aligned")
    except Exception:
        return "aligned"


_DEFAULT_HOST_RATIO = 0.10


def resolve_host_ratio(channel_profile_id: str | None) -> float:
    """Opt-in, matching resolve_image_prompt_compiler_id()'s pattern: without an
    explicit channel_profile_id this returns the historical hardcoded 0.10
    default unchanged. With one given, reads channel_profiles.yaml's
    visual.host_ratio (a plain float, or a [min, max] list -- the midpoint is
    used) and falls back to 0.10 only if the profile declares no host_ratio
    at all (an unknown/legacy profile), never if it explicitly declares 0.0."""
    if not channel_profile_id:
        return _DEFAULT_HOST_RATIO
    try:
        import yaml

        data = yaml.safe_load(_CHANNEL_PROFILES_PATH.read_text(encoding="utf-8")) or {}
        profile = (data.get("profiles") or {}).get(channel_profile_id, {})
        raw = (profile.get("visual") or {}).get("host_ratio")
        if raw is None:
            return _DEFAULT_HOST_RATIO
        if isinstance(raw, (list, tuple)) and len(raw) == 2:
            return (float(raw[0]) + float(raw[1])) / 2.0
        return float(raw)
    except Exception:
        return _DEFAULT_HOST_RATIO


def _brief_to_nollam_request_fields(
    brief: dict[str, Any],
    shot_inputs_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Adapt a CLI v5/v6-shaped brief (_IMAGE_FACING_FIELDS: focal_subject/action/
    place/era/...) into compile_nollam_prompt()'s expected input shape
    (subject/action/place/era/..., order, visual_claim_ids)."""
    shot_id = str(brief.get("shot_id", ""))
    shot_input = shot_inputs_by_id.get(shot_id, {})
    return {
        "shot_id": shot_id,
        "order": shot_input.get("order", 1),
        "visual_mode": brief.get("visual_mode", "historical_reconstruction"),
        "subject": brief.get("focal_subject", ""),
        "action": brief.get("action", ""),
        "place": brief.get("place", ""),
        "era": brief.get("era", ""),
        "semantic_anchors": brief.get("semantic_anchors", []),
        "visual_claim_ids": shot_input.get("claim_ids", []),
        "motion_profile": brief.get("motion_profile", "smooth_subpixel"),
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def select_host_shot_ids(
    shots: list[dict[str, Any]],
    *,
    ratio: float = 0.10,
    min_non_host_gap: int = 7,
) -> set[str]:
    """The 8-12% floor/cap band below is doodle_seonbi_v1's own host_ratio range
    (config/channel_profiles.yaml), not a universal minimum -- ratio<=0.0 (e.g.
    nollam_file_v1's host_ratio_min/max: 0.0, "호스트 아바타 완전 배제") must
    return zero host shots, not silently floor to `max(1, ceil(count*0.08))`
    like every other ratio does. Found live: a real codex+grok
    escalate_claim() smoke test (2026-09-16, audit/orchestration/
    2026-09-16-engine-smoke-test-codex-grok/) flagged that this function
    ignored a 0.0 ratio and always scheduled at least one host_chapter_hinge
    shot -- exactly the failure mode this competitive-verification engine
    exists to catch before it reaches a real nollam_file_v1 build.
    """
    if not shots:
        return set()
    if ratio <= 0.0:
        return set()
    count = len(shots)
    minimum = max(1, math.ceil(count * 0.08))
    maximum = max(minimum, math.floor(count * 0.12))
    requested = min(maximum, max(minimum, round(count * ratio)))
    minimum_separation = min_non_host_gap + 1
    capacity = 1 + (count - 1) // minimum_separation
    target = min(requested, capacity)
    if target == 1:
        positions = [0]
    else:
        positions = [
            round(index * (count - 1) / (target - 1)) for index in range(target)
        ]
    if any(
        right - left < minimum_separation
        for left, right in zip(positions, positions[1:])
    ):
        raise ValueError("host spacing cannot satisfy the configured ratio and gap")
    return {str(shots[position]["shot_id"]) for position in positions}


def validate_brief_sequence(
    shots: list[dict[str, Any]],
    briefs: list[dict[str, Any]],
) -> None:
    expected = [str(shot["shot_id"]) for shot in shots]
    actual = [str(brief.get("shot_id", "")) for brief in briefs]
    if actual != expected:
        raise ValueError(
            "visual brief shot IDs do not exactly match timing order: "
            f"expected {expected[:4]}...{expected[-4:]}, "
            f"got {actual[:4]}...{actual[-4:]}"
        )

    previous_mode = ""
    same_mode_streak = 0
    for brief in briefs:
        mode = str(brief.get("visual_mode", ""))
        if mode == previous_mode:
            same_mode_streak += 1
        else:
            previous_mode = mode
            same_mode_streak = 1
        if same_mode_streak > 2:
            raise ValueError(
                f"same visual mode streak exceeds 2 at {brief.get('shot_id')}: {mode}"
            )

    if len(briefs) < 10:
        return

    direct_count = sum(
        str(brief.get("visual_mode", "")) in _DIRECT_DEPICTION_MODES
        for brief in briefs
    )
    direct_ratio = direct_count / len(briefs)
    if direct_ratio < 0.60:
        raise ValueError(
            "direct depiction ratio is below 0.60: "
            f"{direct_count}/{len(briefs)}={direct_ratio:.4f}"
        )

    family_sets: list[set[str]] = []
    for brief in briefs:
        value = brief.get("prop_motifs", [])
        if isinstance(value, list):
            text = " ".join(str(item) for item in value)
        else:
            text = str(value)
        family_sets.append(
            {
                family
                for family, pattern in _MOTIF_FAMILY_PATTERNS.items()
                if pattern.search(text)
            }
        )
    for start in range(len(family_sets) - 9):
        counts = Counter(
            family
            for families in family_sets[start : start + 10]
            for family in families
        )
        overused = sorted(
            family for family, count in counts.items() if count > 2
        )
        if overused:
            raise ValueError(
                "motif family exceeds 2 occurrences in a 10-shot window "
                f"{start + 1}-{start + 10}: {overused}"
            )


def _ordered_sentence_ids(shot: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for span in shot.get("sentence_spans", []):
        sentence_id = str(span.get("sentence_id", ""))
        if sentence_id and sentence_id not in result:
            result.append(sentence_id)
    return result


def _build_shot_inputs(
    shots: list[dict[str, Any]],
    sentence_texts: dict[str, str],
    host_shot_ids: set[str],
) -> list[dict[str, Any]]:
    result = []
    for shot in shots:
        sentence_ids = _ordered_sentence_ids(shot)
        narration_digest = " ".join(
            sentence_texts[sentence_id] for sentence_id in sentence_ids
        ).strip()
        evidence_ids: list[str] = []
        for span in shot.get("sentence_spans", []):
            for evidence_id in span.get("evidence_span_ids", []):
                evidence_id = str(evidence_id)
                if evidence_id not in evidence_ids:
                    evidence_ids.append(evidence_id)
        result.append(
            {
                "shot_id": shot["shot_id"],
                "order": shot["order"],
                "chapter": shot.get("chapter", 1),
                "start_sec": shot["start_sec"],
                "end_sec": shot["end_sec"],
                "sentence_ids": sentence_ids,
                "narration_digest": narration_digest,
                "claim_ids": list(dict.fromkeys(shot.get("claim_ids", []))),
                "evidence_span_ids": evidence_ids,
                "host_required": shot["shot_id"] in host_shot_ids,
            }
        )
    return result


def _compact_claims(claim_inventory: dict[str, Any]) -> list[dict[str, Any]]:
    keys = (
        "claim_id",
        "statement",
        "type",
        "risk",
        "evidence_refs",
        "approved_paraphrases",
        "forbidden_wording",
    )
    return [
        {key: claim.get(key) for key in keys}
        for claim in claim_inventory.get("claims", [])
    ]


def _render_provider_prompt(
    template_path: Path,
    *,
    episode_id: str,
    shot_inputs: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    host_shot_ids: set[str],
    approved_reference_asset_ids: list[str],
) -> str:
    environment = Environment(
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )
    template = environment.from_string(
        Path(template_path).read_text(encoding="utf-8")
    )
    ordered_host_ids = [
        shot["shot_id"]
        for shot in shot_inputs
        if shot["shot_id"] in host_shot_ids
    ]
    return template.render(
        episode_id=episode_id,
        brief_count=len(shot_inputs),
        host_shot_ids_json=json.dumps(
            ordered_host_ids, ensure_ascii=False, indent=2
        ),
        approved_reference_asset_ids_json=json.dumps(
            approved_reference_asset_ids, ensure_ascii=False, indent=2
        ),
        claims_json=json.dumps(claims, ensure_ascii=False, indent=2),
        shots_json=json.dumps(shot_inputs, ensure_ascii=False, indent=2),
    )


def _validate_generated_briefs(
    shots: list[dict[str, Any]],
    shot_inputs: list[dict[str, Any]],
    briefs: list[dict[str, Any]],
    *,
    host_shot_ids: set[str],
    approved_reference_asset_ids: set[str],
    sentence_texts: dict[str, str],
) -> None:
    validate_brief_sequence(shots, briefs)
    expected_digest = {
        str(row["shot_id"]): str(row["narration_digest"]) for row in shot_inputs
    }
    for brief in briefs:
        shot_id = str(brief["shot_id"])
        if str(brief.get("narration_digest", "")) != expected_digest[shot_id]:
            raise ValueError(f"narration digest was rewritten: {shot_id}")
        is_host = str(brief.get("visual_mode", "")) == "host_chapter_hinge"
        if is_host != (shot_id in host_shot_ids):
            raise ValueError(f"host mode does not match scheduled host set: {shot_id}")

        rendered_fields = []
        for field in _IMAGE_FACING_FIELDS:
            value = brief.get(field, "")
            if isinstance(value, list):
                rendered_fields.extend(str(item) for item in value)
            else:
                rendered_fields.append(str(value))
        rendered = " ".join(rendered_fields)
        if _HANGUL.search(rendered):
            raise ValueError(f"image-facing brief contains Hangul: {shot_id}")
        if _INTERNAL_ID.search(rendered):
            raise ValueError(f"image-facing brief exposes internal IDs: {shot_id}")
        if len(brief.get("semantic_anchors", [])) < 3:
            raise ValueError(f"visual brief lacks concrete anchors: {shot_id}")

        unknown_assets = set(brief.get("reference_asset_ids", []))
        unknown_assets -= approved_reference_asset_ids
        if unknown_assets:
            raise ValueError(
                f"visual brief references unapproved assets {sorted(unknown_assets)}: "
                f"{shot_id}"
            )
        for overlay in brief.get("overlay_items", []):
            sentence_id = str(overlay.get("source_sentence_id", ""))
            text = str(overlay.get("text", ""))
            if sentence_id not in sentence_texts or text not in sentence_texts[sentence_id]:
                raise ValueError(f"overlay is not copied from approved narration: {shot_id}")


def _build_fallback_briefs(
    shots: list[dict[str, Any]],
    sentence_texts: dict[str, str],
    host_shot_ids: set[str],
) -> list[dict[str, Any]]:
    briefs = []
    for shot in shots:
        brief = build_fallback_brief(shot, sentence_texts)
        if shot["shot_id"] in host_shot_ids:
            brief["visual_mode"] = "host_chapter_hinge"
            brief["motion_profile"] = "host_hinge"
        briefs.append(brief)
    return briefs


def main() -> None:
    project_root = Path(__file__).parents[2]
    human_archive_root = Path(__file__).parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--timing", type=Path, required=True)
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--fact-report", type=Path, required=True)
    parser.add_argument("--persona-report", type=Path, required=True)
    parser.add_argument(
        "--fact-approval",
        type=Path,
        default=None,
        help="Human approval file recorded by record_fact_review_approval.py. "
        "Required when --fact-report's overall_status is REVIEW_REQUIRED; not "
        "required (and not read) when it is a clean PASS (zero blocking and "
        "zero review-required counts) -- there is nothing for a human to "
        "approve in that case, and record_fact_review_approval.py itself "
        "refuses to run against a PASS report.",
    )
    parser.add_argument(
        "--provider",
        choices=["antigravity-cli", "fallback", "codex-cli", "json-file"],
        default="antigravity-cli",
    )
    parser.add_argument("--response", type=Path)
    parser.add_argument("--response-output", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prompts", type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=human_archive_root
        / "schemas"
        / "visual_brief_response_v1.schema.json",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=human_archive_root
        / "templates"
        / "narration_visual_brief_prompt.j2",
    )
    parser.add_argument("--repo-root", type=Path, default=project_root)
    parser.add_argument("--model")
    parser.add_argument("--codex-model")
    parser.add_argument("--codex-reasoning")
    parser.add_argument(
        "--host-ratio",
        type=float,
        default=None,
        help="Fraction of shots forced to host_chapter_hinge. Opt-in: omitting it, "
        "with no --channel-profile given, keeps the historical 0.10 default "
        "unchanged. With --channel-profile given, resolves from that profile's "
        "channel_profiles.yaml visual.host_ratio (a plain float, or a [min, max] "
        "list -- the midpoint is used) -- e.g. nollam_file_v1 declares 0.0 "
        "(\"호스트 아바타 완전 배제\"), which select_host_shot_ids() now honors as "
        "genuinely zero host shots instead of flooring to at least one.",
    )
    parser.add_argument("--host-min-non-host-gap", type=int, default=7)
    parser.add_argument(
        "--cross-validate-scene-ids",
        default=None,
        help="Comma-separated shot_ids to cross-validate against codex+grok "
        "(escalate_claim) instead of the Studio path's 40-char narration "
        "truncation. Off by default: a full episode is 100-180 shots and this "
        "is a real 2-participant LLM round per shot (plan §5.5 cost guardrail).",
    )
    parser.add_argument(
        "--cross-validate-sample",
        type=int,
        default=0,
        help="If set and --cross-validate-scene-ids is not, cross-validate an "
        "evenly-spaced deterministic sample of this many shots instead of all.",
    )
    parser.add_argument("--cross-validate-timeout", type=int, default=480)
    parser.add_argument(
        "--cross-validate-include-groq",
        action="store_true",
        help="Additionally screen each cross-validated shot with Groq (a fast, "
        "free third opinion -- see lib/visual_brief_cross_validation.py's "
        "screen_with_groq()). Additive only: never changes the codex+grok "
        "escalate_claim() PASS/REVIEW_REQUIRED status, surfaced as a separate "
        "groq_screen field. Off by default. 2026-09-16 efficiency round: keep "
        "--cross-validate-sample at 8 (12 max) when this is on -- Groq's free "
        "tier is budgeted at 8000 tokens/min and one critique call measured "
        "~3259 tokens, so 8 calls costs ~3.3 minutes of that budget "
        "(audit/orchestration/2026-09-16-2026-09-16-groq-efficiency/).",
    )
    parser.add_argument(
        "--channel-profile",
        default=None,
        help="Channel profile id (e.g. nollam_file_v1). Selects the image-prompt "
        "compiler (compile_nollam_prompt for nollam_file_v1's photorealistic "
        "policy vs. compile_aligned_prompt's ink-doodle style) via "
        "channel_profiles.yaml's image_prompt_compiler field. Opt-in: omitting "
        "it keeps today's compile_aligned_prompt default unchanged.",
    )
    args = parser.parse_args()

    fact_gate = validate_fact_review_gate(
        approval_path=args.fact_approval,
        script_path=args.script,
        fact_report_path=args.fact_report,
        persona_report_path=args.persona_report,
        claim_inventory_path=args.claims,
        source_snapshot_path=args.sources,
    )
    script = _read_json(args.script)
    timing = _read_json(args.timing)
    claims = _read_json(args.claims)
    sentence_texts = {
        str(sentence["sentence_id"]): str(sentence.get("tts_text", ""))
        for sentence in script.get("sentences", [])
    }
    shots = timing["shots"]
    host_ratio = args.host_ratio if args.host_ratio is not None else resolve_host_ratio(args.channel_profile)
    host_shot_ids = select_host_shot_ids(
        shots,
        ratio=host_ratio,
        min_non_host_gap=args.host_min_non_host_gap,
    )
    shot_inputs = _build_shot_inputs(shots, sentence_texts, host_shot_ids)
    approved_reference_asset_ids: list[str] = []

    if args.provider == "fallback":
        briefs = _build_fallback_briefs(shots, sentence_texts, host_shot_ids)
        provider_name = "fallback"
        model_name = "deterministic-v1"
    else:
        prompt = _render_provider_prompt(
            args.template,
            episode_id=str(script.get("episode_id", "")),
            shot_inputs=shot_inputs,
            claims=_compact_claims(claims),
            host_shot_ids=host_shot_ids,
            approved_reference_asset_ids=approved_reference_asset_ids,
        )
        if args.provider in ["antigravity-cli", "antigravity"]:
            if args.response and Path(args.response).exists():
                provider = JsonFileVisualBriefProvider(args.response)
                provider_name = "antigravity-cli"
                model_name = "antigravity-response"
            else:
                provider = AntigravityCliVisualBriefProvider(
                    args.repo_root,
                    model=args.model,
                )
                provider_name = "antigravity-cli"
                model_name = args.model or "antigravity-default"
        elif args.provider == "codex-cli":
            provider = CodexCliVisualBriefProvider(
                args.repo_root,
                model=args.codex_model,
                reasoning_effort=args.codex_reasoning,
            )
            provider_name = "codex-cli"
            model_name = args.codex_model or "configured-default"
        else:
            if not args.response:
                raise ValueError("--provider json-file requires --response")
            provider = JsonFileVisualBriefProvider(args.response)
            provider_name = "json-file"
            model_name = "reviewed-response"
        response = provider.generate(prompt, args.schema)
        if args.response_output:
            _atomic_write_json(args.response_output, response)
        if str(response.get("episode_id", "")) != str(script.get("episode_id", "")):
            raise ValueError("visual brief response episode ID does not match script")
        briefs = response["briefs"]
        _validate_generated_briefs(
            shots,
            shot_inputs,
            briefs,
            host_shot_ids=host_shot_ids,
            approved_reference_asset_ids=set(approved_reference_asset_ids),
            sentence_texts=sentence_texts,
        )

    cross_validate_scene_ids = (
        [s.strip() for s in args.cross_validate_scene_ids.split(",") if s.strip()]
        if args.cross_validate_scene_ids
        else None
    )
    cross_validation_summary: dict[str, Any] = {}
    if cross_validate_scene_ids or args.cross_validate_sample:
        narration_by_shot = {si["shot_id"]: si["narration_digest"] for si in shot_inputs}
        results, groq_outcomes = critique_visual_briefs(
            briefs,
            narration_by_shot,
            scene_ids=cross_validate_scene_ids,
            sample_size=args.cross_validate_sample,
            timeout=args.cross_validate_timeout,
            round_dir_root=(args.output.parent / "cross_validation") if args.output else None,
            include_groq_screen=args.cross_validate_include_groq,
        )
        cross_validation_summary = summarize_critique_results(results, groq_outcomes)
        flagged = [sid for sid, r in cross_validation_summary.items() if r["status"] != "PASS"]
        if flagged:
            print(
                f"Cross-validation flagged {len(flagged)}/{len(cross_validation_summary)} "
                f"reviewed shot(s) as REVIEW_REQUIRED: {', '.join(flagged)}"
            )
        groq_flagged = [
            sid for sid, r in cross_validation_summary.items()
            if r.get("groq_screen", {}).get("verdict") not in (None, "SOUND")
        ]
        if groq_flagged:
            print(
                f"Groq screen additionally flagged {len(groq_flagged)}/{len(groq_outcomes)} "
                f"shot(s) (advisory, does not change PASS/REVIEW_REQUIRED): "
                f"{', '.join(groq_flagged)}"
            )

    brief_hash = hashlib.sha256(
        json.dumps(briefs, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    fact_approval_sha256 = (
        compute_file_sha256(args.fact_approval)
        if args.fact_approval is not None
        else fact_gate["fact_approval_sha256"]
    )
    manifest = {
        "schema_version": 2,
        "episode_id": script.get("episode_id", ""),
        "script_sha256": timing.get("script_sha256", ""),
        "timing_sha256": timing.get("timing_sha256", ""),
        "fact_approval_sha256": fact_approval_sha256,
        "fact_review_set_sha256": fact_gate["review_set_sha256"],
        "provider": provider_name,
        "model": model_name,
        "brief_manifest_sha256": brief_hash,
        "briefs": briefs,
        "cross_validation": cross_validation_summary,
    }
    compiler_id = resolve_image_prompt_compiler_id(args.channel_profile)
    if compiler_id == "nollam":
        shot_inputs_by_id = {si["shot_id"]: si for si in shot_inputs}
        requests = [
            compile_nollam_prompt(_brief_to_nollam_request_fields(brief, shot_inputs_by_id))
            for brief in briefs
        ]
    else:
        requests = [compile_aligned_prompt(brief) for brief in briefs]
    prompt_manifest = {
        "schema_version": 1,
        "episode_id": manifest["episode_id"],
        "requests": requests,
    }
    prompt_path = args.prompts or args.output.parent / "flow_image_prompts.json"
    _atomic_write_json(args.output, manifest)
    _atomic_write_json(prompt_path, prompt_manifest)
    print(
        f"Generated {len(briefs)} visual briefs with {len(host_shot_ids)} hosts "
        f"using {provider_name}"
    )


if __name__ == "__main__":
    main()
