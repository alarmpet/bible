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

from lib.aligned_prompt_compiler import compile_aligned_prompt
from lib.fact_review_approval import validate_fact_review_gate
from lib.provenance import compute_file_sha256
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
    if not shots:
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
    parser.add_argument("--fact-approval", type=Path, required=True)
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
    parser.add_argument("--host-ratio", type=float, default=0.10)
    parser.add_argument("--host-min-non-host-gap", type=int, default=7)
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
    host_shot_ids = select_host_shot_ids(
        shots,
        ratio=args.host_ratio,
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

    brief_hash = hashlib.sha256(
        json.dumps(briefs, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    manifest = {
        "schema_version": 2,
        "episode_id": script.get("episode_id", ""),
        "script_sha256": timing.get("script_sha256", ""),
        "timing_sha256": timing.get("timing_sha256", ""),
        "fact_approval_sha256": compute_file_sha256(args.fact_approval),
        "fact_review_set_sha256": fact_gate["review_set_sha256"],
        "provider": provider_name,
        "model": model_name,
        "brief_manifest_sha256": brief_hash,
        "briefs": briefs,
    }
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
