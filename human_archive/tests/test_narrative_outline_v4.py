import json
from pathlib import Path

from human_archive.scripts.lib.narrative_outline import (
    build_story_evidence_packet,
    validate_narrative_outline,
)


def _write(tmp_path: Path, name: str, value: dict) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return p


def test_blocked_claim_cannot_be_promised(tmp_path):
    snapshot = _write(tmp_path, "snapshot.json", {"sources": []})
    claims = _write(tmp_path, "claims.json", {"claims": [{"claim_id": "CLM-JH-003", "type": "verified_fact"}]})
    policy = _write(tmp_path, "policy.json", {"blocked_claim_ids": ["CLM-JH-003"]})
    packet = build_story_evidence_packet(snapshot, claims, policy)
    outline = {"promise_claim_ids": ["CLM-JH-003"], "core_beats": []}
    assert validate_narrative_outline(outline, packet)


def test_outline_requires_supported_promise(tmp_path):
    snapshot = _write(tmp_path, "snapshot.json", {"sources": []})
    claims = _write(tmp_path, "claims.json", {"claims": []})
    policy = _write(tmp_path, "policy.json", {})
    packet = build_story_evidence_packet(snapshot, claims, policy)
    outline = {"promise_claim_ids": [], "core_beats": []}
    errors = validate_narrative_outline(outline, packet)
    assert "promise_answerability=SUPPORTED is required" in errors
