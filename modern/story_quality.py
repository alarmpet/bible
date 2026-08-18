"""Deterministic quality gates for the modern story pipeline."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

import yaml


SENTENCE_SPLIT = re.compile(r"(?<=[.!?。！？])\s+|\n+")
CONFIG_DIR = Path(__file__).with_name("config")


class InsufficientStoryMaterial(ValueError):
    """Raised when a draft is shorter than its approved story contract."""


def split_sentence_units(text: str) -> list[str]:
    """Return trimmed, non-empty sentence-like units."""

    return [unit.strip() for unit in SENTENCE_SPLIT.split(text) if unit.strip()]


def check_filler_repetition(
    text: str,
    allowlist: Iterable[str] = (),
    warn_ratio: float = 0.90,
    block_ratio: float = 0.80,
) -> dict[str, object]:
    """Detect exact sentence loops and repeated three-sentence blocks."""

    allowed = {item.strip() for item in allowlist if item.strip()}
    all_units = [unit for unit in split_sentence_units(text) if unit not in allowed]
    units = [unit for unit in all_units if not unit.startswith(("\"", "“"))]
    counts = Counter(units)
    blocks: list[str] = []
    warns: list[str] = []

    repeated_sentences = [
        (sentence, count) for sentence, count in counts.items() if count >= 3
    ]
    for sentence, count in sorted(repeated_sentences, key=lambda item: -item[1]):
        blocks.append(
            f"FILLER_REPEAT_BLOCK: 동일 문장 {count}회: {sentence[:80]}"
        )

    windows = Counter(
        tuple(all_units[index : index + 3]) for index in range(len(all_units) - 2)
    )
    repeated_windows = [window for window, count in windows.items() if count >= 2]
    if repeated_windows:
        sample = " / ".join(repeated_windows[0])
        blocks.append(f"REPEATED_BLOCK: 3문장 블록 재등장: {sample[:160]}")

    unique_count = len(counts)
    unique_ratio = unique_count / len(units) if units else 1.0
    if units and unique_ratio < block_ratio:
        blocks.append(
            "FILLER_REPEAT_BLOCK: "
            f"고유 문장 비율 {unique_ratio:.3f} < {block_ratio:.2f}"
        )
    elif units and unique_ratio < warn_ratio:
        warns.append(
            f"WARN: 고유 문장 비율 {unique_ratio:.3f} < {warn_ratio:.2f}"
        )

    return {
        "ok": not blocks,
        "blocks": blocks,
        "warns": warns,
        "measures": {
            "sentence_units": len(all_units),
            "analyzed_non_dialogue_units": len(units),
            "unique_sentence_units": unique_count,
            "unique_sentence_ratio": round(unique_ratio, 3),
            "max_exact_repeat": max(counts.values(), default=0),
        },
    }


def require_story_material(text: str, minimum_chars: int) -> None:
    """Reject a short draft instead of padding it with repeated prose."""

    actual = len(text)
    if actual < minimum_chars:
        raise InsufficientStoryMaterial(
            "INSUFFICIENT_STORY_MATERIAL: "
            f"원고 {actual}자 < 승인된 최소 {minimum_chars}자"
        )


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML mapping with a stable validation error."""

    with Path(path).open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"YAML_MAPPING_REQUIRED: {path}")
    return value


def duration_bounds(config: Mapping[str, Any], tier: str) -> tuple[int, int]:
    """Return inclusive minute bounds for a configured duration tier."""

    tiers = config.get("tiers", {})
    if tier not in tiers:
        raise KeyError(tier)
    selected = tiers[tier]
    return int(selected["min_minutes"]), int(selected["max_minutes"])


def validate_project_contract(
    contract: Mapping[str, Any],
    source_packet: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    """Validate truth labeling, disclosure, duration, and source readiness."""

    blocks: list[str] = []
    warns: list[str] = []
    truth_config = load_yaml(CONFIG_DIR / "truth_modes.yaml")
    duration_config = load_yaml(CONFIG_DIR / "duration_matrix.yaml")
    lane_config = load_yaml(CONFIG_DIR / "content_lanes.yaml")
    modes = truth_config["modes"]

    truth_mode = contract.get("truth_mode")
    if not truth_mode:
        blocks.append("TRUTH_MODE_REQUIRED: truth_mode 누락")
    elif truth_mode not in modes:
        blocks.append(f"TRUTH_MODE_INVALID: {truth_mode}")

    lane = contract.get("lane")
    lanes = lane_config["lanes"]
    if not lane:
        blocks.append("CONTENT_LANE_REQUIRED: lane 누락")
    elif lane not in lanes:
        blocks.append(f"CONTENT_LANE_INVALID: {lane}")
    elif truth_mode in modes and truth_mode not in lanes[lane]["truth_modes"]:
        blocks.append(f"LANE_TRUTH_MISMATCH: {lane} cannot use {truth_mode}")

    tier = contract.get("duration_tier")
    if tier not in duration_config["tiers"]:
        blocks.append(f"DURATION_TIER_INVALID: {tier}")
    else:
        minimum, maximum = duration_bounds(duration_config, str(tier))
        target = contract.get("target_duration_min")
        if not isinstance(target, (int, float)) or not minimum <= target <= maximum:
            blocks.append(
                "DURATION_TARGET_OUT_OF_RANGE: "
                f"{target} not in {minimum}~{maximum}"
            )

    if tier == "special":
        special_ready = (
            int(contract.get("active_subplots", 0)) >= 2
            and int(contract.get("goal_state_changes", 0)) >= 3
            and int(contract.get("independent_act_goals", 0)) >= 3
            and contract.get("pilot_approved") is True
        )
        if not special_ready:
            blocks.append(
                "SPECIAL_APPROVAL_REQUIRED: 보조선2·목표변화3·독립3막·파일럿 승인 필요"
            )

    if lane == "L4_MAKJANG":
        intensity = int(contract.get("makjang_intensity", 3))
        if intensity >= 5:
            blocks.append(f"MAKJANG_INTENSITY_BLOCK: {intensity}")

    disclosure = str(contract.get("content_disclosure", "")).strip()
    if truth_mode in {"INSPIRED_COMPOSITE", "FICTION_REALISTIC", "FICTION_HEIGHTENED"}:
        if not disclosure or not any(word in disclosure for word in ("허구", "창작")):
            blocks.append("DISCLOSURE_REQUIRED: 허구·창작 고지 누락")

    if truth_mode in {"TRUE_VERIFIED", "TRUE_PERMISSIONED"}:
        if source_packet is None:
            blocks.append("SOURCE_PACKET_REQUIRED: 실화 모드 출처 패킷 누락")
        else:
            claims = source_packet.get("core_claims")
            if not isinstance(claims, list) or not claims:
                blocks.append("SOURCE_CLAIMS_REQUIRED: 핵심 주장 누락")
            else:
                for claim in claims:
                    urls = claim.get("source_urls", []) if isinstance(claim, dict) else []
                    if not urls:
                        blocks.append("SOURCE_URL_REQUIRED: 핵심 주장 출처 URL 누락")
                        break
            people = source_packet.get("people", {})
            consent = people.get("consent_status") if isinstance(people, dict) else None
            if consent not in {"obtained", "not_required"}:
                blocks.append(f"CONSENT_UNRESOLVED: {consent}")
            if truth_mode == "TRUE_PERMISSIONED" and consent != "obtained":
                blocks.append("PERMISSION_REQUIRED: 당사자 동의가 필요함")
            if source_packet.get("review_status") != "approved":
                blocks.append("SOURCE_REVIEW_REQUIRED: 출처 패킷 미승인")
            if not source_packet.get("reviewer"):
                blocks.append("SOURCE_REVIEWER_REQUIRED: 검토자 누락")

    return {
        "ok": not blocks,
        "blocks": blocks,
        "warns": warns,
        "measures": {"truth_mode": truth_mode, "duration_tier": tier},
    }


def validate_topic_cards(
    cards: list[Mapping[str, Any]], expected_count: int = 8
) -> dict[str, object]:
    """Validate batch-level premise diversity before a topic is selected."""

    blocks: list[str] = []
    warns: list[str] = []
    if len(cards) != expected_count:
        blocks.append(f"TOPIC_CARD_COUNT: {len(cards)} != {expected_count}")

    lanes = {str(card.get("lane", "")) for card in cards if card.get("lane")}
    if len(lanes) < 4:
        blocks.append(f"LANE_DIVERSITY: 서로 다른 레인 {len(lanes)}개 < 4개")

    roles: Counter[str] = Counter()
    missing_execution = 0
    for card in cards:
        protagonist = card.get("protagonist", {})
        role = protagonist.get("role") if isinstance(protagonist, Mapping) else None
        if role:
            roles[str(role)] += 1
        else:
            blocks.append(f"PROTAGONIST_ROLE_REQUIRED: {card.get('card_id', 'unknown')}")
        execution = card.get("execution_dna", {})
        if not isinstance(execution, Mapping) or not execution.get("pov") or not execution.get("chronology"):
            missing_execution += 1

    for role, count in roles.items():
        if count > 2:
            blocks.append(f"ROLE_OVERUSE: {role} {count}개 > 2개")
    if missing_execution:
        blocks.append(f"EXECUTION_DNA_REQUIRED: {missing_execution}개 카드 누락")

    return {
        "ok": not blocks,
        "blocks": blocks,
        "warns": warns,
        "measures": {
            "card_count": len(cards),
            "lane_count": len(lanes),
            "role_counts": dict(roles),
        },
    }


def audit_portfolio(episodes: list[Mapping[str, Any]]) -> dict[str, object]:
    """Audit the most recent 20 episodes for categorical repetition."""

    recent = episodes[-20:]
    blocks: list[str] = []
    warns: list[str] = []
    lane_counts = Counter(str(item.get("lane", "")) for item in recent if item.get("lane"))

    for index in range(len(recent) - 2):
        window = recent[index : index + 3]
        pairs = [
            (str(item.get("pov", "")), str(item.get("chronology", "")))
            for item in window
        ]
        if pairs[0] == pairs[1] == pairs[2] and all(pairs[0]):
            ids = ",".join(str(item.get("episode_id", "?")) for item in window)
            blocks.append(
                f"EXECUTION_PAIR_STREAK: 동일 POV+시간구조 3편 연속 ({ids})"
            )

    recent_ten_counts = Counter(
        str(item.get("lane", "")) for item in recent[-10:] if item.get("lane")
    )
    for lane, count in recent_ten_counts.items():
        if count > 3:
            warns.append(f"WARN: LANE_OVERREPRESENTED 최근 10편 {lane}={count}")

    return {
        "ok": not blocks,
        "blocks": blocks,
        "warns": warns,
        "measures": {
            "episode_count": len(recent),
            "lane_counts": dict(lane_counts),
        },
    }


def validate_clue_ledger(
    project_contract: Mapping[str, Any], clues: list[Mapping[str, Any]]
) -> dict[str, object]:
    """Require three seeded clues for each core L3 twist."""

    blocks: list[str] = []
    warns: list[str] = []
    if project_contract.get("lane") == "L3_TWIST":
        core_twists = int(project_contract.get("core_twists", 0))
        if core_twists < 1:
            blocks.append("CORE_TWIST_REQUIRED: L3는 핵심 반전이 필요함")
        for index in range(1, core_twists + 1):
            twist_id = f"TW{index:02d}"
            clue_count = sum(1 for clue in clues if clue.get("twist_id") == twist_id)
            if clue_count < 3:
                blocks.append(f"CLUE_COUNT: {twist_id} 단서 {clue_count}개 < 3개")

    return {
        "ok": not blocks,
        "blocks": blocks,
        "warns": warns,
        "measures": {"clue_count": len(clues)},
    }
