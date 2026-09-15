from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any

from lib.host_overlay import CANONICAL_HOST_ASSET, CANONICAL_HOST_COSTUME
from lib.prompt_lint import require_clean_image_request


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


_BASE_NEGATIVE = [
    "letters",
    "numerals",
    "captions",
    "signage",
    "speech bubbles",
    "watermark",
    "service mark",
    "poster layout",
    "empty infographic panel",
]


def _clean_generative_phrase(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"[\"'“”‘’]", "", text)
    text = re.sub(r"\d+", "", text)
    return " ".join(text.split()).strip(" ,.-")


def _generative_place(value: Any) -> str:
    place = _clean_generative_phrase(value)
    named_palace_tokens = ("chwiseondang", "tongmyeongjeon", "changgyeonggung", "changdeokgung", "gyeongbokgung")
    if any(token in place.lower() for token in named_palace_tokens):
        return "late Joseon palace quarters"
    return place


def _append_unique(target: list[str], values: list[Any]) -> None:
    for value in values:
        item = str(value)
        if item and item not in target:
            target.append(item)


_HOST_BASE_VIGNETTES = (
    "one small closed blank archive volume and a plain inkstone form an object-only historical vignette on the left",
    "one small empty palace gate and an unmarked lantern form an object-only historical vignette on the left",
    "one small rolled blank document and two smooth wooden tokens form an object-only historical vignette on the left",
    "one small empty courtyard pavilion and a closed blank volume form an object-only historical vignette on the left",
)

_EVIDENCE_OBJECT_VIGNETTES = (
    "one open blank bound record book rests beside one closed blank volume on a plain wooden table",
    "one rolled blank document tied with plain cord rests beside a smooth unmarked wooden token",
    "two closed blank archive volumes rest beside one unfolded blank sheet on a plain wooden table",
    "one closed blank record book rests beside three smooth unmarked stones on a plain wooden table",
)


def _variant_for_order(options: tuple[str, ...], scene: dict[str, Any]) -> str:
    order = max(1, int(scene.get("order", 1)))
    return options[(order - 1) % len(options)]


def _compile_role_aware(scene: dict[str, Any], provider: str) -> dict[str, Any]:
    for key in ("scene_id", "visual_role", "host_mode", "visual_beat", "place", "era_context"):
        if not scene.get(key):
            raise ValueError(f"scene missing required field: {key}")
    role = str(scene["visual_role"])
    host_mode = str(scene["host_mode"])
    host_refs = [str(item) for item in scene.get("host_reference_assets", []) if item]
    if role != "host_explainer" and host_refs:
        raise ValueError("host reference is allowed only for host_explainer")
    if role == "host_explainer" and host_mode != "full":
        raise ValueError("host_explainer requires host_mode=full")
    if role != "host_explainer" and host_mode != "absent":
        raise ValueError("non-host visual role requires host_mode=absent")

    subjects = [_clean_generative_phrase(value) for value in scene.get("historical_subjects", []) if value]
    action_values = scene.get("action", [])
    if isinstance(action_values, str):
        action_values = [action_values]
    action = ", ".join(filter(None, (_clean_generative_phrase(value) for value in action_values)))
    place = _generative_place(scene["place"])
    camera = _clean_generative_phrase(scene.get("camera", ""))
    composition = _clean_generative_phrase(scene.get("composition", ""))
    lighting = _clean_generative_phrase(scene.get("lighting", ""))
    style = _clean_generative_phrase(scene.get("style", "hand drawn doodle"))
    host_overlay: dict[str, Any] | None = None
    generation_profile = str(scene.get("_generation_profile", ""))
    context_phrase = "A single coherent Late Joseon Korean historical scene"

    if generation_profile == "ultra_minimal":
        context_phrase = "Two-dimensional Korean editorial doodle on warm off-white paper"
        subjects = []
        camera = "straight-on flat diagram view"
        composition = (
            "very sparse icon-like composition with one blank sheet and three smooth stones and broad empty space"
        )
        lighting = "no realistic lighting, no cast shadows, only a flat pale beige wash"
        style = (
            "hand-drawn black pen line art, intentionally simplified irregular outlines, flat minimal pale beige "
            "and gray fills, visible paper texture, no gradients, no depth, not a photograph, not photorealistic"
        )
    elif role == "host_explainer":
        subjects = []
        action = _variant_for_order(_HOST_BASE_VIGNETTES, scene) + ", no people, no hands, no human body parts"
        camera = "straight-on wide object vignette"
        composition = "single coherent vignette on the left with broad clean off-white negative space on the right"
        lighting = "flat pale paper wash with no realistic cast shadows"
        style = "two-dimensional hand-drawn black ink doodle with minimal flat pale pastel accents, no gradients"
    elif role == "evidence_object":
        subjects = []
        if generation_profile not in {"policy_object_only", "policy_minimal_objects"}:
            action = _variant_for_order(_EVIDENCE_OBJECT_VIGNETTES, scene) + ", no people, no hands, no human body parts"
        camera = "straight-on close object view"
        composition = "single coherent object-focused scene with one focal artifact, no split panels, no collage, no catalogue"
        lighting = "flat pale paper wash with no realistic cast shadows"
        style = "two-dimensional hand-drawn black ink doodle with minimal flat pale pastel accents, no gradients"

    if generation_profile == "ultra_minimal":
        role_phrase = (
            "An unoccupied plain wooden table, no people, no clothing display, no costumes, no crowns, "
            "no palace collage, no decorative border"
        )
    elif role == "host_explainer":
        role_phrase = (
            "An object-only historical vignette with the presenter absent from the generated base, "
            "no people, no hands, no human body parts, leaving the right side as clean off-white negative space "
            "for one fixed character overlay"
        )
        host_overlay = {
            "asset": CANONICAL_HOST_ASSET,
            "anchor": "right_bottom",
            "width_ratio": 0.38,
            "costume": CANONICAL_HOST_COSTUME,
        }
    elif role == "historical_reconstruction":
        role_phrase = "Historical actors reconstruct the narrated event with the presenter absent"
    elif role == "evidence_object":
        role_phrase = (
            "A single close study of narrated historical evidence, no people, no hands, no human body parts, "
            "no collage, no catalogue, no costume display, with the presenter absent"
        )
    elif role == "diagram_metaphor":
        role_phrase = "A simple visual metaphor made from objects and shapes with the presenter absent"
    elif role == "atmosphere":
        role_phrase = "A quiet atmospheric historical setting with the presenter absent"
    else:
        raise ValueError(f"unsupported visual role: {role}")

    parts = [
        context_phrase,
        role_phrase,
        ", ".join(subjects),
        action,
        place,
        camera,
        composition,
        lighting,
        style,
        "clean off-white paper and wide landscape composition",
    ]
    positive = ", ".join(part for part in parts if part)
    submission_prompt = (
        positive
        + ". All surfaces and papers remain completely blank. Do not draw alphabetic or Hangul characters, "
          "Arabic numerals, dates, labels, signs, captions, seals, watermarks, interface marks, or speech balloons. "
          "Do not include wall plaques, hanging scrolls, framed panels, or book covers facing the camera."
    )
    if re.search(r"\d", submission_prompt):
        raise ValueError("submission prompt contains a digit")
    negative_items: list[str] = []
    _append_unique(negative_items, _BASE_NEGATIVE)
    _append_unique(negative_items, [*scene.get("must_not", []), *scene.get("forbidden_implications", [])])
    if role != "host_explainer":
        _append_unique(negative_items, ["presenter", "black-gat host character", "seonbi mascot"])
    else:
        _append_unique(
            negative_items,
            [
                "generated presenter",
                "stick figure",
                "person wearing a black gat in the base image",
                "additional person",
                "woman presenter",
                "man presenter",
                "disembodied hand",
                "human body parts",
                "collage",
                "catalogue sheet",
            ],
        )
    if role == "evidence_object":
        _append_unique(
            negative_items,
            [
                "collage",
                "catalogue sheet",
                "costume display",
                "clothing reference board",
                "architecture reference board",
                "disembodied hand",
                "human body parts",
                "split panel",
                "photorealistic rendering",
            ],
        )
    if generation_profile == "ultra_minimal":
        _append_unique(
            negative_items,
            [
                "costume display",
                "crown",
                "collage",
                "decorative border",
                "ornamental chart",
                "photograph",
                "photorealistic rendering",
                "realistic room",
                "cinematic light",
                "gradients",
                "cast shadows",
                "three-dimensional render",
            ],
        )

    payload = {
        "scene_id": scene["scene_id"],
        "order": int(scene.get("order", 0)),
        "provider": provider,
        "visual_role": role,
        "host_mode": host_mode,
        "positive_prompt": positive,
        "submission_prompt": submission_prompt,
        "negative": {"mode": "prompt_exclusion", "items": negative_items, "source_items": negative_items.copy()},
        "reference_assets": scene.get("reference_assets", []),
        "host_reference_assets": host_refs,
        "overlay_text": [str(item) for item in scene.get("overlay_text", [])],
    }
    if host_overlay:
        payload["host_overlay"] = host_overlay
    require_clean_image_request(payload)
    payload["request_sha256"] = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest().upper()
    return payload


def compile_scene_request(scene: dict[str, Any], *, provider: str = "flow") -> dict[str, Any]:
    if scene.get("visual_role"):
        return _compile_role_aware(scene, provider)
    for key in ("scene_id", "visual_beat", "action", "place", "era"):
        if not scene.get(key):
            raise ValueError(f"scene missing required field: {key}")
    subjects = [str(v) for v in scene.get("subject_refs", []) if v]
    parts = [
        ", ".join(subjects),
        str(scene["visual_beat"]),
        ", ".join(str(v) for v in scene.get("action", [])),
        str(scene["place"]),
        str(scene["era"]),
        str(scene.get("camera", "")),
        str(scene.get("composition", "")),
        str(scene.get("lighting", "")),
        str(scene.get("style", "")),
        str(scene.get("subtitle_safe_area", "")),
    ]
    positive = ", ".join(part for part in parts if part)
    negative_items = []
    for item in [*scene.get("must_not", []), *scene.get("forbidden_implications", [])]:
        if item and item not in negative_items:
            negative_items.append(str(item))
    payload = {
        "scene_id": scene["scene_id"], "provider": provider,
        "positive_prompt": positive,
        "negative": {"mode": "prompt_exclusion", "items": negative_items, "source_items": negative_items.copy()},
        "reference_assets": scene.get("reference_assets", []),
    }
    payload["request_sha256"] = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest().upper()
    return payload


SAFE_ABSTRACTION_BY_MODE = {
    "event_reconstruction": "same named actors as distant non-graphic silhouettes performing the same action in the same place",
    "place_establishing": "the same place after the event, with environmental traces but no harmed person",
    "route_map": "the same unlabeled route map with a single highlighted path",
    "mechanism_diagram": "the same causal relationship as neutral unlabeled shapes and arrows",
    "evidence_artifact": "the same named evidence object in its real archive or excavation context",
    "modern_analogy": "the same single analogy using neutral everyday objects",
    "atmosphere_transition": "the same place and time as an unoccupied atmospheric view",
    "host_chapter_hinge": "the same contextual base with no generated person and canonical host overlay metadata",
}

_RETRY_MODE_ALIASES = {
    "historical_reconstruction": "event_reconstruction",
    "character_action": "event_reconstruction",
    "place_establishing": "place_establishing",
    "route_pan": "route_map",
    "diagram_metaphor": "mechanism_diagram",
    "analogy_explainer": "modern_analogy",
    "evidence_object": "evidence_artifact",
    "atmosphere": "atmosphere_transition",
    "host_explainer": "host_chapter_hinge",
}


def _retry_text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item)
    return str(value or "")


def _retry_identity(scene: dict[str, Any]) -> tuple[str, str, str, str, str, str, str]:
    scene_id = str(scene.get("scene_id") or scene.get("shot_id") or "")
    shot_id = str(scene.get("shot_id") or scene_id)
    if not scene_id or not shot_id:
        raise ValueError("scene missing required identity: scene_id or shot_id")
    original_mode = str(scene.get("visual_mode") or scene.get("visual_role") or "")
    canonical_mode = _RETRY_MODE_ALIASES.get(original_mode, original_mode)
    if canonical_mode not in SAFE_ABSTRACTION_BY_MODE:
        raise ValueError(f"unsupported visual mode for policy retry: {original_mode}")
    actors = _retry_text(scene.get("actors") or scene.get("historical_subjects") or scene.get("subjects"))
    action = _retry_text(scene.get("action") or scene.get("visual_beat"))
    place = _retry_text(scene.get("place"))
    era = _retry_text(scene.get("era") or scene.get("era_context"))
    return scene_id, shot_id, original_mode, canonical_mode, actors, action, place + "|" + era


def compile_policy_safe_retry(
    scene: dict[str, Any],
    attempt: int,
    provider: str = "flow",
    reason: str = "provider_policy_rejected",
    previous_request_sha256: str | None = None,
) -> dict[str, Any]:
    """Compile a semantic-preserving policy retry for a narrated image request."""
    if int(attempt) < 1 or int(attempt) > 2:
        raise ValueError("maximum of two automatic policy retries")

    retry_scene = deepcopy(scene)
    retry_scene.pop("request_sha256", None)
    scene_id, shot_id, original_mode, canonical_mode, actors, action, place_era = _retry_identity(retry_scene)
    place, era = place_era.split("|", 1)
    semantic_anchors = [str(item) for item in retry_scene.get("semantic_anchors", []) if item]
    anchor_ids = retry_scene.get("required_semantic_anchor_ids") or retry_scene.get("semantic_anchor_ids") or []
    claim_ids = [str(item) for item in retry_scene.get("claim_ids", []) if item]
    abstraction = SAFE_ABSTRACTION_BY_MODE[canonical_mode]
    if int(attempt) == 1:
        transform = "safe_rephrase"
        retry_instruction = (
            "safe rephrase: the same narrated scene is shown calmly, non-graphic, non-sensational, "
            "and educational while retaining the original actors, action, place, era, and required anchors"
        )
    else:
        transform = "safe_abstraction"
        retry_instruction = abstraction

    prompt_parts = [
        f"visual mode: {original_mode}",
        f"actors: {actors}" if actors else "no generated actors beyond the specified abstraction",
        f"action: {action}",
        f"place: {place}",
        f"era: {era}",
        f"semantic anchors: {', '.join(semantic_anchors)}",
        f"required semantic anchor IDs: {', '.join(str(item) for item in anchor_ids)}",
        retry_instruction,
        "calm, non-graphic, educational historical image; all surfaces blank and unmarked; no captions, labels, or watermarks",
    ]
    payload = retry_scene
    payload.update(
        {
            "scene_id": scene_id,
            "shot_id": shot_id,
            "provider": provider,
            "visual_mode": retry_scene.get("visual_mode", original_mode),
            "semantic_anchors": semantic_anchors,
            "claim_ids": claim_ids,
            "positive_prompt": ", ".join(part for part in prompt_parts if part),
            "submission_prompt": ", ".join(part for part in prompt_parts if part),
            "negative": {
                "mode": "prompt_exclusion",
                "items": [
                    "graphic harm",
                    "sensational violence",
                    "letters",
                    "digits",
                    "captions",
                    "labels",
                    "watermark",
                    "generic wooden table",
                ],
            },
            "policy_safe_retry": True,
            "policy_retry_attempt": int(attempt),
            "policy_retry_transform": transform,
            "policy_retry_reason": reason,
            "previous_request_sha256": previous_request_sha256,
            "policy_retry_mode": canonical_mode,
        }
    )
    if canonical_mode == "host_chapter_hinge" and "host_overlay" not in payload:
        payload["host_overlay"] = {
            "asset": CANONICAL_HOST_ASSET,
            "costume": CANONICAL_HOST_COSTUME,
            "width_ratio": 0.38,
        }
    payload["request_sha256"] = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest().upper()
    return payload
