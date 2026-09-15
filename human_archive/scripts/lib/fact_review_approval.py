# -*- coding: utf-8 -*-
"""Explicit human approval binding for fact-review-only findings."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from lib.provenance import compute_file_sha256, compute_object_sha256
from lib.schema_validation import load_schema, validate_json


WORDING_REVIEW_ISSUE = "Segment phrasing differs from approved paraphrase"
EXPLICIT_APPROVAL_SOURCE = "explicit_user_confirmation_in_codex_thread"
NON_HUMAN_REVIEWER_MARKERS = (
    "agent",
    "automation",
    "bot",
    "claude",
    "codex",
    "gpt",
    "luna",
    "system",
)
APPROVAL_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "fact_review_approval_v1.schema.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _validate_human_metadata(
    *, reviewer_id: str, approval_source: str, approved_at_utc: str
) -> None:
    if approval_source != EXPLICIT_APPROVAL_SOURCE:
        raise ValueError("approval_source is not an explicit user confirmation")
    normalized_reviewer = reviewer_id.strip().casefold()
    if not normalized_reviewer or any(
        marker in normalized_reviewer for marker in NON_HUMAN_REVIEWER_MARKERS
    ):
        raise ValueError("reviewer_id must identify a human operator")
    try:
        parsed = datetime.fromisoformat(approved_at_utc.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("approved_at_utc is not valid ISO-8601") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("approved_at_utc must include a timezone")


def _validate_approval_envelope(approval: dict[str, Any]) -> None:
    if approval.get("schema_version") != 1:
        raise ValueError("fact review approval schema_version must be 1")
    if approval.get("decision") != "approved":
        raise ValueError("fact review approval decision is not approved")
    if approval.get("unresolved_issues") != 0:
        raise ValueError("fact review approval unresolved_issues must be 0")
    _validate_human_metadata(
        reviewer_id=str(approval.get("reviewer_id", "")),
        approval_source=str(approval.get("approval_source", "")),
        approved_at_utc=str(approval.get("approved_at_utc", "")),
    )


def _validate_report_is_approvable(report: dict[str, Any]) -> None:
    if report.get("schema_version") != 2:
        raise ValueError("fact report schema_version must be 2")
    blocking_fields = (
        "fail_count",
        "unsupported_count",
        "forbidden_wording_count",
        "unresolved_conflict_count",
    )
    for field in blocking_fields:
        value = report.get(field)
        if type(value) is not int or value != 0:
            raise ValueError(
                "blocking fact failures: "
                f"blocking fact counter {field} must be present as integer 0"
            )
    if report.get("overall_status") != "REVIEW_REQUIRED":
        raise ValueError("fact report is not in REVIEW_REQUIRED state")
    for row in report.get("segment_evaluations", []):
        status = row.get("status")
        if status not in {"PASS", "REVIEW_REQUIRED"}:
            raise ValueError(
                f"fact report segment status is blocking or invalid: {status}"
            )


def _validate_persona_report(persona_report: dict[str, Any]) -> None:
    if persona_report.get("overall_status") != "PASS":
        raise ValueError("persona report overall_status must be PASS")


def _review_items(report: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    seen_review_ids: set[str] = set()
    for row in report.get("segment_evaluations", []):
        if row.get("status") != "REVIEW_REQUIRED":
            continue
        sentence_id = row.get("sentence_id")
        if not isinstance(sentence_id, str) or not sentence_id.strip():
            raise ValueError("fact review item sentence_id is required")
        segment_index = row.get("segment_index")
        if type(segment_index) is not int or segment_index < 0:
            raise ValueError(
                "fact review item segment_index must be a non-negative integer"
            )
        kind = row.get("kind")
        if kind not in {"fact", "direct_quote"}:
            raise ValueError("fact review item kind is not factual")
        claim_id = row.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id.strip():
            raise ValueError("fact review item claim_id is required")
        review_id = f"{sentence_id}:{segment_index}"
        if review_id in seen_review_ids:
            raise ValueError(f"duplicate review_id: {review_id}")
        seen_review_ids.add(review_id)
        issues = list(row.get("issues", []))
        if issues != [WORDING_REVIEW_ISSUE]:
            raise ValueError(
                f"fact review item {sentence_id}:{segment_index} is not approvable"
            )
        items.append(
            {
                "review_id": review_id,
                "sentence_id": sentence_id,
                "segment_index": segment_index,
                "kind": kind,
                "claim_id": claim_id,
                "issues": issues,
            }
        )
    review_required_count = report.get("review_required_count")
    if type(review_required_count) is not int or review_required_count != len(items):
        raise ValueError(
            "fact report review_required_count does not match review items"
        )
    return sorted(items, key=lambda item: (item["sentence_id"], item["segment_index"]))


def _artifact_hashes(
    *,
    script_path: Path,
    fact_report_path: Path,
    persona_report_path: Path,
    claim_inventory_path: Path,
    source_snapshot_path: Path,
) -> dict[str, str]:
    return {
        "script_sha256": compute_file_sha256(script_path),
        "fact_report_sha256": compute_file_sha256(fact_report_path),
        "persona_report_sha256": compute_file_sha256(persona_report_path),
        "claim_inventory_sha256": compute_file_sha256(claim_inventory_path),
        "source_snapshot_sha256": compute_file_sha256(source_snapshot_path),
    }


def record_fact_review_approval(
    *,
    script_path: Path,
    fact_report_path: Path,
    persona_report_path: Path,
    claim_inventory_path: Path,
    source_snapshot_path: Path,
    output_path: Path,
    reviewer_id: str,
    approval_source: str,
    approved_at_utc: str,
) -> dict[str, Any]:
    _validate_human_metadata(
        reviewer_id=reviewer_id,
        approval_source=approval_source,
        approved_at_utc=approved_at_utc,
    )
    if output_path.exists():
        existing = _read_json(output_path)
        validate_fact_review_gate(
            approval_path=output_path,
            script_path=script_path,
            fact_report_path=fact_report_path,
            persona_report_path=persona_report_path,
            claim_inventory_path=claim_inventory_path,
            source_snapshot_path=source_snapshot_path,
        )
        if existing.get("reviewer_id") != reviewer_id:
            raise ValueError("existing fact review approval reviewer_id differs")
        return existing
    report = _read_json(fact_report_path)
    _validate_report_is_approvable(report)
    _validate_persona_report(_read_json(persona_report_path))
    items = _review_items(report)
    approval = {
        "schema_version": 1,
        "decision": "approved",
        "reviewer_id": reviewer_id,
        "role": "Human fact and editorial reviewer",
        "approved_at_utc": approved_at_utc,
        "approval_source": approval_source,
        "artifacts": _artifact_hashes(
            script_path=script_path,
            fact_report_path=fact_report_path,
            persona_report_path=persona_report_path,
            claim_inventory_path=claim_inventory_path,
            source_snapshot_path=source_snapshot_path,
        ),
        "review_scope": {
            "review_required_count": len(items),
            "review_set_sha256": compute_object_sha256(items),
            "items": items,
        },
        "unresolved_issues": 0,
        "notes": "Current fact-review-only wording findings explicitly approved by the human operator.",
    }
    validate_json(approval, load_schema(APPROVAL_SCHEMA_PATH))
    _atomic_write_json(output_path, approval)
    return approval


def validate_fact_review_gate(
    *,
    approval_path: Path,
    script_path: Path,
    fact_report_path: Path,
    persona_report_path: Path,
    claim_inventory_path: Path,
    source_snapshot_path: Path,
) -> dict[str, Any]:
    approval = _read_json(approval_path)
    validate_json(approval, load_schema(APPROVAL_SCHEMA_PATH))
    _validate_approval_envelope(approval)
    report = _read_json(fact_report_path)
    _validate_report_is_approvable(report)
    _validate_persona_report(_read_json(persona_report_path))
    items = _review_items(report)
    expected_artifacts = _artifact_hashes(
        script_path=script_path,
        fact_report_path=fact_report_path,
        persona_report_path=persona_report_path,
        claim_inventory_path=claim_inventory_path,
        source_snapshot_path=source_snapshot_path,
    )
    if approval.get("artifacts") != expected_artifacts:
        raise ValueError("fact review approval artifact hashes do not match current files")
    scope = approval.get("review_scope", {})
    if scope.get("review_required_count") != len(items):
        raise ValueError(
            "fact review approval review_required_count does not match current report"
        )
    if scope.get("items") != items:
        raise ValueError("fact review approval items do not match current report")
    expected_review_sha = compute_object_sha256(items)
    if scope.get("review_set_sha256") != expected_review_sha:
        raise ValueError("fact review approval set hash does not match current report")
    return {
        "effective_status": "PASS",
        "approved_review_count": len(items),
        "review_set_sha256": expected_review_sha,
    }
