from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from lib.host_overlay import CANONICAL_HOST_ASSET, CANONICAL_HOST_COSTUME

STYLE = "Korean editorial ink-doodle illustration, clean black linework on ivory paper, sparse muted red blue and green accents, one coherent full-frame 16:9 scene, no photorealism"
BLANK_SURFACES = "all paper-like and sign-like surfaces completely blank and unmarked, no visible writing-like strokes"

NOLLAM_LOOKS = (
    ("documentary_35mm", "35mm documentary lens, grounded observational composition"),
    ("archival_wide", "wide environmental documentary frame, layered depth and restrained natural light"),
    ("data_observatory", "precise scientific observatory composition, tactile evidence foreground and deep context"),
    ("evidence_macro", "macro evidence detail, shallow depth of field with a readable physical focal anchor"),
)
NOLLAM_LEGACY_TERMS = ("조선", "선비", "궁궐", "ink-doodle", "seonbi")
NOLLAM_TEXT_GUARD = (
    "no subtitles",
    "no caption bar",
    "no burned-in captions",
    "no text overlays",
)


def _load_nollam_visual_policy() -> dict:
    policy_path = Path(__file__).resolve().parents[2] / "config" / "nollam_file_visual_policy.yaml"
    if not policy_path.exists():
        raise FileNotFoundError(f"NOLLAM visual policy is missing: {policy_path}")
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    if str(policy.get("policy_id", "")) != "nollam_file_visual_v1":
        raise ValueError("NOLLAM visual policy ID is invalid")
    return policy


def compile_nollam_prompt(brief: dict, provider: str = "flow") -> dict:
    """Compile the canonical NOLLAM visual request for any documentary topic."""
    shot_id = str(brief.get("shot_id", "")).strip()
    if not shot_id:
        raise ValueError("NOLLAM prompt requires shot_id")
    source_text = " ".join(str(brief.get(key, "")) for key in ("subject", "action", "place", "era", "visual_mode"))
    lowered = source_text.casefold()
    found_legacy = next((term for term in NOLLAM_LEGACY_TERMS if term.casefold() in lowered), None)
    if found_legacy:
        raise ValueError(f"legacy NOLLAM keyword is forbidden: {found_legacy}")
    policy = _load_nollam_visual_policy()
    policy_sha256 = hashlib.sha256(
        json.dumps(policy, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest().upper()

    try:
        order = max(1, int(brief.get("order", 1)))
    except (TypeError, ValueError):
        order = 1
    look_id, look_description = NOLLAM_LOOKS[(order - 1) % len(NOLLAM_LOOKS)]
    mode = str(brief.get("visual_mode", "historical_reconstruction"))
    asset_type = (
        "BARETIP_VIDEO" if "bare_tip" in mode
        else "HYPERFRAMES_VIDEO" if "hyperframes" in mode
        else "FLOW_IMAGE"
    )
    scene = "; ".join(
        f"{label}: {str(brief.get(key, '')).strip()}"
        for label, key in (("subject", "subject"), ("action", "action"), ("place", "place"), ("era", "era"))
        if str(brief.get(key, "")).strip()
    )
    positive = (
        "NOLLAM documentary visual policy, 16:9 landscape, realistic physical detail, "
        f"{look_description}; {scene}; no text in image; "
        "keep the bottom 18% of the frame visually clear for later subtitles"
    )
    negative = [*NOLLAM_TEXT_GUARD, "watermark", "logo", "modern signage", "graphic UI clutter"]
    asset_id = str(brief.get("asset_id") or shot_id).strip()
    payload = {
        "shot_id": shot_id,
        "asset_id": asset_id,
        "order": order,
        "visual_mode": mode,
        "visual_claim_ids": list(brief.get("visual_claim_ids", [])),
        "look_id": look_id,
        "asset_type": asset_type,
        "positive_prompt": positive,
        "negative": {"mode": "prompt_exclusion", "items": negative},
        "submission_prompt": positive + ". Strict exclusions: " + "; ".join(negative),
        "motion_profile": str(brief.get("motion_profile", "smooth_subpixel")),
        "provider": provider,
        "policy_id": str(policy["policy_id"]),
        "policy_sha256": policy_sha256,
        "canvas": {
            "width": int(policy.get("width", 1920)),
            "height": int(policy.get("height", 1080)),
            "fps": int(policy.get("fps", 25)),
        },
    }
    if brief.get("visual_role"):
        payload["visual_role"] = str(brief["visual_role"])
    payload["request_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest().upper()
    return payload


def compile_opening_flow_prompts(brief: dict, provider: str = "flow") -> list[dict]:
    """Compile 3-Cut Visible FLOW Opening prompts (context_wide -> subject_action -> evidence_detail)."""
    shot_id = str(brief.get("shot_id", "SHOT_001")).strip()
    era = str(brief.get("era", "후기 플라이스토세 빙하기"))
    place = str(brief.get("place", "유라시아 혹한 절벽"))

    cut_specs = [
        {
            "asset_id": f"{shot_id}_cut01",
            "visual_role": "context_wide",
            "subject": f"광활한 설원과 깎아지른 바위 절벽 파노라마 전경, {place}",
            "action": "혹독한 눈보라와 매서운 겨울 바람이 계곡을 휩쓴다",
            "duration": 3.0,
        },
        {
            "asset_id": f"{shot_id}_cut02",
            "visual_role": "subject_action",
            "subject": f"동굴 앞 모피를 입은 네안데르탈인 사냥꾼 무리의 생존 행동, {place}",
            "action": "매서운 추위 속에서 창을 쥐고 주변을 경계하며 이동한다",
            "duration": 3.5,
        },
        {
            "asset_id": f"{shot_id}_cut03",
            "visual_role": "evidence_detail",
            "subject": f"동굴 바닥의 4만 년 전 네안데르탈인 두개골 화석 및 투창기 유물 클로즈업, {place}",
            "action": "빙하기 석기와 화석 단서가 사실적인 질감으로 선명히 드러난다",
            "duration": 4.5,
        },
    ]

    results = []
    for spec in cut_specs:
        cut_brief = dict(brief)
        cut_brief.update({
            "shot_id": shot_id,
            "asset_id": spec["asset_id"],
            "order": 1,
            "visual_mode": "historical_reconstruction",
            "scene_role": "opening_group",
            "visual_role": spec["visual_role"],
            "subject": spec["subject"],
            "action": spec["action"],
            "era": era,
            "place": place,
            "duration": spec["duration"],
        })
        compiled = compile_nollam_prompt(cut_brief, provider=provider)
        compiled["duration"] = spec["duration"]
        results.append(compiled)

    return results


def compile_aligned_prompt(brief: dict, provider: str = "flow") -> dict:
    anchors = ", ".join(brief.get("semantic_anchors", []))
    mode = str(brief["visual_mode"])
    host = mode == "host_chapter_hinge"
    scene = "; ".join(filter(None, [str(brief.get("focal_subject", "")), str(brief.get("action", "")), str(brief.get("place", "")), str(brief.get("era", "")), str(brief.get("camera", ""))]))
    if host:
        scene = f"background plate only, no people, no human figures, no hands, no body parts; narration-specific vignette confined to the left 55 percent; right 40 percent clean open ivory space for later host overlay; {scene}"
    else:
        scene = f"no presenter, no pointing scholar, no mascot, no direct-to-camera figure; {scene}"
    positive = f"{STYLE}; {scene}; required visible anchors: {anchors}; {BLANK_SURFACES}"
    negative = [
        "letters, digits, numbers, years, captions, labels, handwriting, calligraphy, signatures, seals, watermark, logo, star or diamond service mark",
        "open manuscript, open book, written scroll, written map, generic desk, repeated books or papers",
        "collage, split panel, catalog sheet, cutaway collection, empty room, cropped body, malformed hands or limbs",
        "presenter, pointing scholar, mascot, direct eye contact outside canonical host overlay",
    ]
    payload = {
        "shot_id": brief["shot_id"], "visual_mode": mode, "semantic_anchors": brief.get("semantic_anchors", []),
        "positive_prompt": positive, "negative": {"mode": "prompt_exclusion", "items": negative},
        "submission_prompt": positive + ". Strict exclusions: " + "; ".join(negative) + ".",
        "motion_profile": brief.get("motion_profile", "reenactment_push"), "provider": provider,
    }
    if host:
        payload["host_overlay"] = {"asset": CANONICAL_HOST_ASSET, "costume": CANONICAL_HOST_COSTUME, "width_ratio": 0.38}
    payload["request_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest().upper()
    return payload
