from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from lib.doodle_visual_roles import classify_visual_role


KNOWN_SUBJECTS = (
    "장희빈",
    "숙종",
    "숙빈 최씨",
    "인현왕후",
    "대신",
    "나인",
    "기록관",
)

EVIDENCE_TERMS = ("실록", "승정원일기", "기록", "문서", "사료", "교지", "명령")
PLACE_RULES = (
    (("취선당", "신당"), "Chwiseondang palace quarters"),
    (("통명전",), "Tongmyeongjeon palace courtyard"),
    (("조정", "대신", "간언"), "Joseon royal council hall"),
    (("실록", "기록관", "사료"), "royal archive room"),
    (("궁", "왕실", "숙종"), "late Joseon royal palace"),
)

CAMERAS_BY_ROLE = {
    "host_explainer": ("medium presenter framing", "wide presenter and context"),
    "historical_reconstruction": (
        "wide establishing view",
        "medium character action",
        "over shoulder documentary view",
        "close object anchored view",
    ),
    "evidence_object": (
        "evidence close-up",
        "overhead document view",
        "hands and artifact detail",
        "shelf and archive context",
    ),
    "diagram_metaphor": ("balanced diagram composition", "top-down symbolic layout"),
    "atmosphere": ("wide atmospheric view", "quiet architectural detail"),
}


def _claim_ids(sentence: dict[str, Any]) -> tuple[str, ...]:
    values: list[str] = []
    for segment in sentence.get("segments", []):
        claim_id = segment.get("claim_id")
        if claim_id and claim_id not in values:
            values.append(str(claim_id))
    return tuple(values)


def _evidence_ids(sentences: Iterable[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for sentence in sentences:
        for segment in sentence.get("segments", []):
            for evidence_id in segment.get("evidence_span_ids", []):
                if evidence_id not in values:
                    values.append(str(evidence_id))
    return values


def _group_sentences(sentences: list[dict[str, Any]], target_chars: int) -> list[list[dict[str, Any]]]:
    if target_chars <= 1:
        return [[sentence] for sentence in sentences]
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_chars = 0
    current_key: tuple[Any, ...] | None = None
    for sentence in sentences:
        key = (sentence.get("chapter", 1), sentence.get("beat", "body"), _claim_ids(sentence))
        text_len = len(str(sentence.get("tts_text", "")))
        boundary = current and (key != current_key or current_chars + text_len > target_chars)
        if boundary:
            groups.append(current)
            current = []
            current_chars = 0
        current.append(sentence)
        current_chars += text_len
        current_key = key
    if current:
        groups.append(current)
    total_chars = sum(len(str(sentence.get("tts_text", ""))) for sentence in sentences)
    scene_ceiling = max(12, min(len(sentences), round(total_chars / target_chars)))
    while len(groups) > scene_ceiling:
        best_index = min(
            range(len(groups) - 1),
            key=lambda index: (
                1 if groups[index][0].get("chapter") != groups[index + 1][0].get("chapter") else 0,
                1 if groups[index][0].get("beat") != groups[index + 1][0].get("beat") else 0,
                sum(len(str(sentence.get("tts_text", ""))) for sentence in groups[index] + groups[index + 1]),
            ),
        )
        groups[best_index] = groups[best_index] + groups[best_index + 1]
        del groups[best_index + 1]
    return groups


def extract_historical_subjects(text: str) -> list[str]:
    subjects = [subject for subject in KNOWN_SUBJECTS if subject in text]
    if "대신들" in text and "대신" not in subjects:
        subjects.append("대신")
    return subjects


def _infer_place(text: str) -> str:
    for terms, place in PLACE_RULES:
        if any(term in text for term in terms):
            return place
    return "late Joseon historical setting"


def _visual_action(text: str, role: str, subjects: list[str]) -> str:
    actors = " and ".join(subjects) if subjects else "historical figures"
    if role == "host_explainer":
        return "the presenter points toward a simple symbolic vignette"
    if role == "diagram_metaphor":
        return "a balance made from simple palace objects compares two interpretations"
    if role == "atmosphere":
        return "an empty palace courtyard settles into a quiet closing moment"
    if any(term in text for term in ("실록", "승정원일기", "기록", "사료", "문서")):
        return "hands examine blank bound archive volumes and unmarked papers"
    if any(term in text for term in ("신당", "흉물", "발견")):
        return f"{actors} inspect ritual objects inside palace quarters"
    if any(term in text for term in ("간언", "조정", "대신", "정치", "왕권")):
        return f"{actors} take part in a restrained royal council debate"
    if any(term in text for term in ("명령", "자진", "사약", "처분")):
        return f"{actors} receive a blank rolled royal order in a palace corridor"
    if any(term in text for term in ("고변", "보고", "알리")):
        return f"{actors} report a concern to palace attendants"
    return f"{actors} perform the central narrated historical action without posing for the viewer"


def _role_for_group(group: list[dict[str, Any]], text: str):
    beat = str(group[0].get("beat", "body"))
    if beat == "analogy":
        return "diagram_metaphor", "absent", "analogy is visualized without the presenter"
    if beat == "outro":
        return "atmosphere", "absent", "outro uses a quiet closing image"
    decision = classify_visual_role({"beat": beat})
    if decision.role == "historical_reconstruction" and any(term in text for term in EVIDENCE_TERMS):
        return "evidence_object", "absent", "narration centers a record or artifact"
    return decision.role, decision.host_mode, decision.rationale


def _select_host_indices(role_candidates: list[tuple[str, str, str]], total_scenes: int) -> set[int]:
    candidates = [index for index, (role, _mode, _reason) in enumerate(role_candidates) if role == "host_explainer"]
    if not candidates:
        return set()
    desired = max(math.ceil(total_scenes * 0.15), round(total_scenes * 0.20))
    desired = min(desired, math.floor(total_scenes * 0.25), len(candidates))
    if desired <= 0:
        return set()
    if desired == 1:
        return {candidates[len(candidates) // 2]}
    ranks = [round(position * (len(candidates) - 1) / (desired - 1)) for position in range(desired)]
    return {candidates[rank] for rank in ranks}


def plan_scenes(
    sentences: list[dict[str, Any]],
    claims: dict[str, Any] | None = None,
    *,
    target_chars: int = 55,
) -> list[dict[str, Any]]:
    del claims  # Reserved for richer claim-linked planning without changing the interface.
    ordered = sorted(sentences, key=lambda item: (int(item.get("order", 0)), str(item.get("sentence_id", ""))))
    groups = _group_sentences(ordered, target_chars)
    group_texts = [" ".join(str(sentence.get("tts_text", "")).strip() for sentence in group).strip() for group in groups]
    role_candidates = [_role_for_group(group, text) for group, text in zip(groups, group_texts)]
    selected_host_indices = _select_host_indices(role_candidates, len(groups))
    scenes: list[dict[str, Any]] = []
    recent_triplets: list[tuple[str, tuple[str, ...], str]] = []

    for index, (group, text, role_candidate) in enumerate(zip(groups, group_texts, role_candidates), 1):
        role, host_mode, rationale = role_candidate
        if role == "host_explainer" and index - 1 not in selected_host_indices:
            role = "evidence_object" if any(term in text for term in EVIDENCE_TERMS) else "historical_reconstruction"
            host_mode = "absent"
            rationale = f"host-eligible beat demoted to {role} to satisfy episode quota"
        subjects = extract_historical_subjects(text)
        cameras = CAMERAS_BY_ROLE[role]
        camera = cameras[(index - 1) % len(cameras)]
        triplet = (role, tuple(subjects), camera)
        if triplet in recent_triplets[-3:]:
            camera = cameras[index % len(cameras)]
            triplet = (role, tuple(subjects), camera)

        must_not = ["letters", "numerals", "captions", "signage", "speech bubbles", "watermark"]
        if role != "host_explainer":
            must_not.extend(["host character", "black-gat presenter"])

        scene = {
            "scene_id": f"jh_v4_scene_{index:03d}",
            "order": index,
            "chapter": int(group[0].get("chapter", 1)),
            "beat": str(group[0].get("beat", "body")),
            "sentence_ids": [str(sentence["sentence_id"]) for sentence in group],
            "narration_text": text,
            "visual_role": role,
            "host_mode": host_mode,
            "historical_subjects": subjects,
            "evidence_ids": _evidence_ids(group),
            "era_context": "late Joseon royal court",
            "overlay_text": [],
            "must_not": must_not,
            "place": _infer_place(text),
            "visual_beat": text,
            "action": [_visual_action(text, role, subjects)],
            "camera": camera,
            "composition": "filled editorial doodle composition with one clear focal action",
            "lighting": "soft flat candlelight",
            "style": "hand-drawn black ink doodle with minimal flat pastel accents",
            "rationale": rationale,
        }
        scenes.append(scene)
        recent_triplets.append(triplet)

    covered = [sid for scene in scenes for sid in scene["sentence_ids"]]
    expected = [str(sentence["sentence_id"]) for sentence in ordered]
    if covered != expected:
        raise ValueError("scene planning must cover every sentence exactly once and in order")
    return scenes
