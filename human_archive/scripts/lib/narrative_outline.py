"""Fact-scoped evidence packet and narrative outline validation for HA002 v4."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

CORE_ROLES = ("TRIGGER", "DECISION_CHANGE", "RECORDED_JUSTIFICATION", "FINAL_ORDER")
DEFAULT_BLOCKED = {"CLM-JH-003", "CLM-JH-006", "CLM-JH-007"}


def _load(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    value = yaml.safe_load(text) if path.suffix.lower() in {".yaml", ".yml"} else json.loads(text)
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def build_story_evidence_packet(source_snapshot_path: Path, claim_inventory_path: Path, policy_path: Path) -> dict[str, Any]:
    snapshot = _load(source_snapshot_path)
    claim_doc = _load(claim_inventory_path)
    policy = _load(policy_path) if policy_path.suffix.lower() == ".json" else {}
    claims = claim_doc.get("claims", [])
    blocked = set(policy.get("blocked_claim_ids", [])) | DEFAULT_BLOCKED
    normalized_claims = []
    for claim in claims:
        cid = claim.get("claim_id")
        if not cid:
            continue
        normalized_claims.append({**claim, "status": "BLOCKED" if cid in blocked else "SUPPORTED"})
    spans = []
    for source in snapshot.get("sources", []):
        spans.extend(source.get("evidence_spans", []))
    return {
        "episode_id": snapshot.get("episode_id") or claim_doc.get("episode_id") or "HA002",
        "claims": normalized_claims,
        "evidence_spans": spans,
        "sources": snapshot.get("sources", []),
        "blocked_claim_ids": sorted(cid for cid in (c.get("claim_id") for c in normalized_claims) if cid in blocked),
        "allowed_visual_modes": ["documented_event", "documented_object", "attributed_interpretation"],
        "policy": policy,
    }


def validate_promise_answerability(packet: dict[str, Any], outline: dict[str, Any]) -> list[str]:
    by_id = {c.get("claim_id"): c for c in packet.get("claims", [])}
    errors: list[str] = []
    promise_ids = outline.get("promise_claim_ids", [])
    if not promise_ids:
        errors.append("promise_answerability=SUPPORTED is required")
    for cid in promise_ids:
        claim = by_id.get(cid)
        if not claim or claim.get("status") != "SUPPORTED":
            errors.append(f"promise claim is not supported: {cid}")
    return errors


def validate_narrative_outline(outline: dict[str, Any], packet: dict[str, Any]) -> list[str]:
    errors = validate_promise_answerability(packet, outline)
    beats = outline.get("core_beats", [])
    roles = [b.get("narrative_role") for b in beats]
    if roles != list(CORE_ROLES):
        errors.append(f"core_beats must be exactly {list(CORE_ROLES)}")
    if outline.get("promise_answerability") != "SUPPORTED":
        errors.append("promise_answerability=SUPPORTED is required")
    for beat in beats:
        if beat.get("narrative_role") not in CORE_ROLES:
            errors.append("unknown narrative role")
        if not beat.get("claim_ids"):
            errors.append(f"beat missing claim_ids: {beat.get('narrative_role')}")
        for cid in beat.get("claim_ids", []):
            claim = next((c for c in packet.get("claims", []) if c.get("claim_id") == cid), None)
            if not claim or claim.get("status") != "SUPPORTED":
                errors.append(f"beat claim is not supported: {cid}")
    return sorted(set(errors))


def compile_narrative_outline(packet: dict[str, Any], output_path: Path) -> Path:
    supported = [c for c in packet.get("claims", []) if c.get("status") == "SUPPORTED"]
    if len(supported) < 4:
        raise ValueError("at least four supported claims are required")
    beats = [
        {"narrative_role": role, "claim_ids": [supported[i]["claim_id"]], "content_mode": "story"}
        for i, role in enumerate(CORE_ROLES)
    ]
    outline = {
        "schema_version": 1,
        "episode_id": packet.get("episode_id", "HA002"),
        "promise_answerability": "SUPPORTED",
        "promise_claim_ids": [b["claim_ids"][0] for b in beats],
        "loop_hook": {"question": "왜 이 결정은 그렇게 내려졌을까?", "claim_ids": beats[0]["claim_ids"]},
        "core_beats": beats,
        "edges": [
            {"from": CORE_ROLES[i], "to": CORE_ROLES[i + 1], "type": "causal"}
            for i in range(len(CORE_ROLES) - 1)
        ],
    }
    errors = validate_narrative_outline(outline, packet)
    if errors:
        raise ValueError("invalid outline: " + "; ".join(errors))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(outline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path
