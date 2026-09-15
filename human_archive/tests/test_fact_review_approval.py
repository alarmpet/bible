# -*- coding: utf-8 -*-
"""Tests for explicit human approval of fact-review-only findings."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


ALLOWED_WORDING_ISSUE = "Segment phrasing differs from approved paraphrase"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _write_fixture_bundle(root: Path) -> dict[str, Path]:
    paths = {
        "script": root / "script_candidate.json",
        "fact_report": root / "fact_check_report_v2.json",
        "persona_report": root / "persona_report_v2.json",
        "claims": root / "claim_inventory_v2.json",
        "sources": root / "source_snapshot_manifest_v2.json",
        "approval": root / "approvals" / "fact_review_approval_v1.json",
    }
    paths["script"].write_text(
        json.dumps(
            {
                "episode_id": "HA002",
                "sentences": [
                    {
                        "sentence_id": "S-001",
                        "tts_text": "기록의 침묵을 확인합니다.",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    paths["fact_report"].write_text(
        json.dumps(
            {
                "schema_version": 2,
                "overall_status": "REVIEW_REQUIRED",
                "fail_count": 0,
                "unsupported_count": 0,
                "forbidden_wording_count": 0,
                "unresolved_conflict_count": 0,
                "review_required_count": 2,
                "segment_evaluations": [
                    {
                        "sentence_id": "S-002",
                        "segment_index": 1,
                        "kind": "fact",
                        "claim_id": "CLM-002",
                        "status": "REVIEW_REQUIRED",
                        "issues": [ALLOWED_WORDING_ISSUE],
                    },
                    {
                        "sentence_id": "S-001",
                        "segment_index": 0,
                        "kind": "fact",
                        "claim_id": "CLM-001",
                        "status": "REVIEW_REQUIRED",
                        "issues": [ALLOWED_WORDING_ISSUE],
                    },
                    {
                        "sentence_id": "S-003",
                        "segment_index": 0,
                        "kind": "transition",
                        "claim_id": None,
                        "status": "PASS",
                        "issues": [],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    paths["persona_report"].write_text(json.dumps({"overall_status": "PASS"}), encoding="utf-8")
    paths["claims"].write_text(json.dumps({"claims": []}), encoding="utf-8")
    paths["sources"].write_text(json.dumps({"sources": []}), encoding="utf-8")
    return paths


def test_records_and_validates_exact_review_set(tmp_path: Path) -> None:
    try:
        from lib.fact_review_approval import (
            record_fact_review_approval,
            validate_fact_review_gate,
        )
    except ModuleNotFoundError:
        pytest.fail("fact review approval API is not implemented")

    paths = _write_fixture_bundle(tmp_path)
    approval = record_fact_review_approval(
        script_path=paths["script"],
        fact_report_path=paths["fact_report"],
        persona_report_path=paths["persona_report"],
        claim_inventory_path=paths["claims"],
        source_snapshot_path=paths["sources"],
        output_path=paths["approval"],
        reviewer_id="shs",
        approval_source="explicit_user_confirmation_in_codex_thread",
        approved_at_utc="2026-08-28T00:00:00+00:00",
    )

    assert paths["approval"].is_file()
    assert approval["decision"] == "approved"
    assert approval["reviewer_id"] == "shs"
    assert approval["review_scope"]["review_required_count"] == 2
    assert [row["review_id"] for row in approval["review_scope"]["items"]] == [
        "S-001:0",
        "S-002:1",
    ]
    assert approval["artifacts"] == {
        "script_sha256": _sha256(paths["script"]),
        "fact_report_sha256": _sha256(paths["fact_report"]),
        "persona_report_sha256": _sha256(paths["persona_report"]),
        "claim_inventory_sha256": _sha256(paths["claims"]),
        "source_snapshot_sha256": _sha256(paths["sources"]),
    }

    gate = validate_fact_review_gate(
        approval_path=paths["approval"],
        script_path=paths["script"],
        fact_report_path=paths["fact_report"],
        persona_report_path=paths["persona_report"],
        claim_inventory_path=paths["claims"],
        source_snapshot_path=paths["sources"],
    )
    assert gate == {
        "effective_status": "PASS",
        "approved_review_count": 2,
        "review_set_sha256": approval["review_scope"]["review_set_sha256"],
    }


def test_rejects_non_wording_review_issue(tmp_path: Path) -> None:
    from lib.fact_review_approval import record_fact_review_approval

    paths = _write_fixture_bundle(tmp_path)
    report = json.loads(paths["fact_report"].read_text(encoding="utf-8"))
    report["segment_evaluations"][0]["issues"] = [
        "Evidence span is not associated with the claim"
    ]
    paths["fact_report"].write_text(
        json.dumps(report, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="not approvable"):
        record_fact_review_approval(
            script_path=paths["script"],
            fact_report_path=paths["fact_report"],
            persona_report_path=paths["persona_report"],
            claim_inventory_path=paths["claims"],
            source_snapshot_path=paths["sources"],
            output_path=paths["approval"],
            reviewer_id="shs",
            approval_source="explicit_user_confirmation_in_codex_thread",
            approved_at_utc="2026-08-28T00:00:00+00:00",
        )


@pytest.mark.parametrize(
    "field",
    [
        "fail_count",
        "unsupported_count",
        "forbidden_wording_count",
        "unresolved_conflict_count",
    ],
)
def test_rejects_report_with_blocking_fact_failures(
    tmp_path: Path, field: str
) -> None:
    from lib.fact_review_approval import record_fact_review_approval

    paths = _write_fixture_bundle(tmp_path)
    report = json.loads(paths["fact_report"].read_text(encoding="utf-8"))
    report[field] = 1
    paths["fact_report"].write_text(
        json.dumps(report, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="blocking fact failures"):
        record_fact_review_approval(
            script_path=paths["script"],
            fact_report_path=paths["fact_report"],
            persona_report_path=paths["persona_report"],
            claim_inventory_path=paths["claims"],
            source_snapshot_path=paths["sources"],
            output_path=paths["approval"],
            reviewer_id="shs",
            approval_source="explicit_user_confirmation_in_codex_thread",
            approved_at_utc="2026-08-28T00:00:00+00:00",
        )


def test_rejects_review_count_mismatch(tmp_path: Path) -> None:
    from lib.fact_review_approval import record_fact_review_approval

    paths = _write_fixture_bundle(tmp_path)
    report = json.loads(paths["fact_report"].read_text(encoding="utf-8"))
    report["review_required_count"] = 87
    paths["fact_report"].write_text(
        json.dumps(report, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="review_required_count"):
        record_fact_review_approval(
            script_path=paths["script"],
            fact_report_path=paths["fact_report"],
            persona_report_path=paths["persona_report"],
            claim_inventory_path=paths["claims"],
            source_snapshot_path=paths["sources"],
            output_path=paths["approval"],
            reviewer_id="shs",
            approval_source="explicit_user_confirmation_in_codex_thread",
            approved_at_utc="2026-08-28T00:00:00+00:00",
        )


def test_rejects_duplicate_review_id(tmp_path: Path) -> None:
    from lib.fact_review_approval import record_fact_review_approval

    paths = _write_fixture_bundle(tmp_path)
    report = json.loads(paths["fact_report"].read_text(encoding="utf-8"))
    report["segment_evaluations"].append(
        dict(report["segment_evaluations"][0])
    )
    report["review_required_count"] = 3
    paths["fact_report"].write_text(
        json.dumps(report, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="duplicate review_id"):
        record_fact_review_approval(
            script_path=paths["script"],
            fact_report_path=paths["fact_report"],
            persona_report_path=paths["persona_report"],
            claim_inventory_path=paths["claims"],
            source_snapshot_path=paths["sources"],
            output_path=paths["approval"],
            reviewer_id="shs",
            approval_source="explicit_user_confirmation_in_codex_thread",
            approved_at_utc="2026-08-28T00:00:00+00:00",
        )


@pytest.mark.parametrize(
    ("reviewer_id", "approval_source", "approved_at_utc", "message"),
    [
        (
            "shs",
            "explicit_system",
            "2026-08-28T00:00:00+00:00",
            "approval_source",
        ),
        (
            "codex-agent",
            "explicit_user_confirmation_in_codex_thread",
            "2026-08-28T00:00:00+00:00",
            "reviewer_id",
        ),
        (
            "",
            "explicit_user_confirmation_in_codex_thread",
            "2026-08-28T00:00:00+00:00",
            "reviewer_id",
        ),
        (
            "shs",
            "explicit_user_confirmation_in_codex_thread",
            "2026-08-28T00:00:00",
            "approved_at_utc",
        ),
    ],
)
def test_rejects_non_human_approval_metadata(
    tmp_path: Path,
    reviewer_id: str,
    approval_source: str,
    approved_at_utc: str,
    message: str,
) -> None:
    from lib.fact_review_approval import record_fact_review_approval

    paths = _write_fixture_bundle(tmp_path)
    with pytest.raises(ValueError, match=message):
        record_fact_review_approval(
            script_path=paths["script"],
            fact_report_path=paths["fact_report"],
            persona_report_path=paths["persona_report"],
            claim_inventory_path=paths["claims"],
            source_snapshot_path=paths["sources"],
            output_path=paths["approval"],
            reviewer_id=reviewer_id,
            approval_source=approval_source,
            approved_at_utc=approved_at_utc,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", 2, "schema_version"),
        ("decision", "rejected", "decision"),
        ("reviewer_id", "system-agent", "reviewer_id"),
        ("approval_source", "explicit_system", "approval_source"),
        ("approved_at_utc", "2026-08-28T00:00:00", "approved_at_utc"),
        ("unresolved_issues", 1, "unresolved_issues"),
    ],
)
def test_gate_rejects_tampered_approval_envelope(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    from lib.fact_review_approval import (
        record_fact_review_approval,
        validate_fact_review_gate,
    )

    paths = _write_fixture_bundle(tmp_path)
    approval = record_fact_review_approval(
        script_path=paths["script"],
        fact_report_path=paths["fact_report"],
        persona_report_path=paths["persona_report"],
        claim_inventory_path=paths["claims"],
        source_snapshot_path=paths["sources"],
        output_path=paths["approval"],
        reviewer_id="shs",
        approval_source="explicit_user_confirmation_in_codex_thread",
        approved_at_utc="2026-08-28T00:00:00+00:00",
    )
    approval[field] = value
    paths["approval"].write_text(
        json.dumps(approval, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match=message):
        validate_fact_review_gate(
            approval_path=paths["approval"],
            script_path=paths["script"],
            fact_report_path=paths["fact_report"],
            persona_report_path=paths["persona_report"],
            claim_inventory_path=paths["claims"],
            source_snapshot_path=paths["sources"],
        )


def test_repeated_record_is_byte_idempotent(tmp_path: Path) -> None:
    from lib.fact_review_approval import record_fact_review_approval

    paths = _write_fixture_bundle(tmp_path)
    first = record_fact_review_approval(
        script_path=paths["script"],
        fact_report_path=paths["fact_report"],
        persona_report_path=paths["persona_report"],
        claim_inventory_path=paths["claims"],
        source_snapshot_path=paths["sources"],
        output_path=paths["approval"],
        reviewer_id="shs",
        approval_source="explicit_user_confirmation_in_codex_thread",
        approved_at_utc="2026-08-28T00:00:00+00:00",
    )
    original_bytes = paths["approval"].read_bytes()

    second = record_fact_review_approval(
        script_path=paths["script"],
        fact_report_path=paths["fact_report"],
        persona_report_path=paths["persona_report"],
        claim_inventory_path=paths["claims"],
        source_snapshot_path=paths["sources"],
        output_path=paths["approval"],
        reviewer_id="shs",
        approval_source="explicit_user_confirmation_in_codex_thread",
        approved_at_utc="2026-08-28T01:00:00+00:00",
    )

    assert second == first
    assert paths["approval"].read_bytes() == original_bytes


def test_gate_rejects_tampered_approval_review_count(tmp_path: Path) -> None:
    from lib.fact_review_approval import (
        record_fact_review_approval,
        validate_fact_review_gate,
    )

    paths = _write_fixture_bundle(tmp_path)
    approval = record_fact_review_approval(
        script_path=paths["script"],
        fact_report_path=paths["fact_report"],
        persona_report_path=paths["persona_report"],
        claim_inventory_path=paths["claims"],
        source_snapshot_path=paths["sources"],
        output_path=paths["approval"],
        reviewer_id="shs",
        approval_source="explicit_user_confirmation_in_codex_thread",
        approved_at_utc="2026-08-28T00:00:00+00:00",
    )
    approval["review_scope"]["review_required_count"] = 87
    paths["approval"].write_text(
        json.dumps(approval, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="review_required_count"):
        validate_fact_review_gate(
            approval_path=paths["approval"],
            script_path=paths["script"],
            fact_report_path=paths["fact_report"],
            persona_report_path=paths["persona_report"],
            claim_inventory_path=paths["claims"],
            source_snapshot_path=paths["sources"],
        )


def test_recorder_cli_writes_valid_approval(tmp_path: Path) -> None:
    paths = _write_fixture_bundle(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPTS_DIR / "record_fact_review_approval.py"),
            "--script",
            str(paths["script"]),
            "--fact-report",
            str(paths["fact_report"]),
            "--persona-report",
            str(paths["persona_report"]),
            "--claims",
            str(paths["claims"]),
            "--sources",
            str(paths["sources"]),
            "--output",
            str(paths["approval"]),
            "--reviewer-id",
            "shs",
            "--approval-source",
            "explicit_user_confirmation_in_codex_thread",
            "--approved-at-utc",
            "2026-08-28T00:00:00+00:00",
        ],
        cwd=_PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    approval = json.loads(paths["approval"].read_text(encoding="utf-8"))
    assert approval["review_scope"]["review_required_count"] == 2
    assert "2 fact review items" in result.stdout


def test_recorded_approval_matches_public_schema(tmp_path: Path) -> None:
    from lib.fact_review_approval import record_fact_review_approval
    from lib.schema_validation import load_schema, validate_json

    paths = _write_fixture_bundle(tmp_path)
    approval = record_fact_review_approval(
        script_path=paths["script"],
        fact_report_path=paths["fact_report"],
        persona_report_path=paths["persona_report"],
        claim_inventory_path=paths["claims"],
        source_snapshot_path=paths["sources"],
        output_path=paths["approval"],
        reviewer_id="shs",
        approval_source="explicit_user_confirmation_in_codex_thread",
        approved_at_utc="2026-08-28T00:00:00+00:00",
    )
    schema_path = (
        _PROJECT_ROOT
        / "human_archive"
        / "schemas"
        / "fact_review_approval_v1.schema.json"
    )
    if not schema_path.is_file():
        pytest.fail("fact review approval public schema is not implemented")

    validate_json(approval, load_schema(schema_path))


def test_visual_brief_cli_refuses_to_run_without_fact_approval(
    tmp_path: Path,
) -> None:
    paths = _write_fixture_bundle(tmp_path)
    timing_path = tmp_path / "shot_timing_manifest.json"
    output_path = tmp_path / "visual_brief_manifest.json"
    timing_path.write_text(
        json.dumps(
            {
                "script_sha256": _sha256(paths["script"]),
                "timing_sha256": "TIMING-SHA",
                "shots": [
                    {
                        "shot_id": "shot-001",
                        "order": 1,
                        "chapter": 1,
                        "start_sec": 0.0,
                        "end_sec": 4.0,
                        "sentence_spans": [
                            {
                                "sentence_id": "S-001",
                                "evidence_span_ids": [],
                            }
                        ],
                        "claim_ids": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPTS_DIR / "generate_visual_briefs.py"),
            "--script",
            str(paths["script"]),
            "--timing",
            str(timing_path),
            "--claims",
            str(paths["claims"]),
            "--provider",
            "fallback",
            "--output",
            str(output_path),
        ],
        cwd=_PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert result.returncode != 0
    assert "--fact-report" in result.stderr
    assert not output_path.exists()


def test_visual_brief_manifest_binds_valid_fact_approval(
    tmp_path: Path,
) -> None:
    from lib.fact_review_approval import record_fact_review_approval

    paths = _write_fixture_bundle(tmp_path)
    record_fact_review_approval(
        script_path=paths["script"],
        fact_report_path=paths["fact_report"],
        persona_report_path=paths["persona_report"],
        claim_inventory_path=paths["claims"],
        source_snapshot_path=paths["sources"],
        output_path=paths["approval"],
        reviewer_id="shs",
        approval_source="explicit_user_confirmation_in_codex_thread",
        approved_at_utc="2026-08-28T00:00:00+00:00",
    )
    approval = json.loads(paths["approval"].read_text(encoding="utf-8"))
    timing_path = tmp_path / "shot_timing_manifest.json"
    output_path = tmp_path / "visual_brief_manifest.json"
    prompts_path = tmp_path / "flow_image_prompts.json"
    timing_path.write_text(
        json.dumps(
            {
                "script_sha256": _sha256(paths["script"]),
                "timing_sha256": "TIMING-SHA",
                "shots": [
                    {
                        "shot_id": "shot-001",
                        "order": 1,
                        "chapter": 1,
                        "start_sec": 0.0,
                        "end_sec": 4.0,
                        "sentence_spans": [
                            {
                                "sentence_id": "S-001",
                                "evidence_span_ids": [],
                            }
                        ],
                        "claim_ids": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPTS_DIR / "generate_visual_briefs.py"),
            "--script",
            str(paths["script"]),
            "--timing",
            str(timing_path),
            "--claims",
            str(paths["claims"]),
            "--sources",
            str(paths["sources"]),
            "--fact-report",
            str(paths["fact_report"]),
            "--persona-report",
            str(paths["persona_report"]),
            "--fact-approval",
            str(paths["approval"]),
            "--provider",
            "fallback",
            "--output",
            str(output_path),
            "--prompts",
            str(prompts_path),
        ],
        cwd=_PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    manifest = json.loads(output_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 2
    assert manifest["fact_approval_sha256"] == _sha256(paths["approval"])
    assert (
        manifest["fact_review_set_sha256"]
        == approval["review_scope"]["review_set_sha256"]
    )
    from lib.schema_validation import load_schema, validate_json

    manifest_without_approval = dict(manifest)
    manifest_without_approval.pop("fact_approval_sha256")
    manifest_schema = load_schema(
        _PROJECT_ROOT
        / "human_archive"
        / "schemas"
        / "visual_brief_manifest.schema.json"
    )
    with pytest.raises(ValueError, match="fact_approval_sha256"):
        validate_json(manifest_without_approval, manifest_schema)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("sentence_id", "", "sentence_id"),
        ("segment_index", -1, "segment_index"),
        ("kind", "transition", "kind"),
        ("claim_id", None, "claim_id"),
    ],
)
def test_rejects_invalid_review_item_identity(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    from lib.fact_review_approval import record_fact_review_approval

    paths = _write_fixture_bundle(tmp_path)
    report = json.loads(paths["fact_report"].read_text(encoding="utf-8"))
    report["segment_evaluations"][0][field] = value
    paths["fact_report"].write_text(
        json.dumps(report, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match=message):
        record_fact_review_approval(
            script_path=paths["script"],
            fact_report_path=paths["fact_report"],
            persona_report_path=paths["persona_report"],
            claim_inventory_path=paths["claims"],
            source_snapshot_path=paths["sources"],
            output_path=paths["approval"],
            reviewer_id="shs",
            approval_source="explicit_user_confirmation_in_codex_thread",
            approved_at_utc="2026-08-28T00:00:00+00:00",
        )


@pytest.mark.parametrize(
    "artifact_key",
    ["script", "fact_report", "persona_report", "claims", "sources"],
)
def test_gate_rejects_stale_artifact_sha(
    tmp_path: Path, artifact_key: str
) -> None:
    from lib.fact_review_approval import (
        record_fact_review_approval,
        validate_fact_review_gate,
    )

    paths = _write_fixture_bundle(tmp_path)
    record_fact_review_approval(
        script_path=paths["script"],
        fact_report_path=paths["fact_report"],
        persona_report_path=paths["persona_report"],
        claim_inventory_path=paths["claims"],
        source_snapshot_path=paths["sources"],
        output_path=paths["approval"],
        reviewer_id="shs",
        approval_source="explicit_user_confirmation_in_codex_thread",
        approved_at_utc="2026-08-28T00:00:00+00:00",
    )
    paths[artifact_key].write_bytes(paths[artifact_key].read_bytes() + b" ")

    with pytest.raises(ValueError, match="artifact hashes"):
        validate_fact_review_gate(
            approval_path=paths["approval"],
            script_path=paths["script"],
            fact_report_path=paths["fact_report"],
            persona_report_path=paths["persona_report"],
            claim_inventory_path=paths["claims"],
            source_snapshot_path=paths["sources"],
        )


@pytest.mark.parametrize("mutation", ["missing", "extra", "duplicate"])
def test_gate_rejects_changed_approval_item_set(
    tmp_path: Path, mutation: str
) -> None:
    from lib.fact_review_approval import (
        record_fact_review_approval,
        validate_fact_review_gate,
    )

    paths = _write_fixture_bundle(tmp_path)
    approval = record_fact_review_approval(
        script_path=paths["script"],
        fact_report_path=paths["fact_report"],
        persona_report_path=paths["persona_report"],
        claim_inventory_path=paths["claims"],
        source_snapshot_path=paths["sources"],
        output_path=paths["approval"],
        reviewer_id="shs",
        approval_source="explicit_user_confirmation_in_codex_thread",
        approved_at_utc="2026-08-28T00:00:00+00:00",
    )
    items = approval["review_scope"]["items"]
    if mutation == "missing":
        items.pop()
    elif mutation == "extra":
        items.append(
            {
                "review_id": "S-999:0",
                "sentence_id": "S-999",
                "segment_index": 0,
                "kind": "fact",
                "claim_id": "CLM-999",
                "issues": [ALLOWED_WORDING_ISSUE],
            }
        )
    else:
        items.append(dict(items[0]))
    approval["review_scope"]["review_required_count"] = len(items)
    paths["approval"].write_text(
        json.dumps(approval, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(
        ValueError, match="review_required_count|items|set hash"
    ):
        validate_fact_review_gate(
            approval_path=paths["approval"],
            script_path=paths["script"],
            fact_report_path=paths["fact_report"],
            persona_report_path=paths["persona_report"],
            claim_inventory_path=paths["claims"],
            source_snapshot_path=paths["sources"],
        )


def test_existing_stale_approval_is_not_overwritten(tmp_path: Path) -> None:
    from lib.fact_review_approval import record_fact_review_approval

    paths = _write_fixture_bundle(tmp_path)
    record_fact_review_approval(
        script_path=paths["script"],
        fact_report_path=paths["fact_report"],
        persona_report_path=paths["persona_report"],
        claim_inventory_path=paths["claims"],
        source_snapshot_path=paths["sources"],
        output_path=paths["approval"],
        reviewer_id="shs",
        approval_source="explicit_user_confirmation_in_codex_thread",
        approved_at_utc="2026-08-28T00:00:00+00:00",
    )
    original_bytes = paths["approval"].read_bytes()
    paths["script"].write_bytes(paths["script"].read_bytes() + b" ")

    with pytest.raises(ValueError, match="artifact hashes"):
        record_fact_review_approval(
            script_path=paths["script"],
            fact_report_path=paths["fact_report"],
            persona_report_path=paths["persona_report"],
            claim_inventory_path=paths["claims"],
            source_snapshot_path=paths["sources"],
            output_path=paths["approval"],
            reviewer_id="shs",
            approval_source="explicit_user_confirmation_in_codex_thread",
            approved_at_utc="2026-08-28T01:00:00+00:00",
        )
    assert paths["approval"].read_bytes() == original_bytes


def test_gate_rejects_unknown_approval_fields(tmp_path: Path) -> None:
    from lib.fact_review_approval import (
        record_fact_review_approval,
        validate_fact_review_gate,
    )

    paths = _write_fixture_bundle(tmp_path)
    approval = record_fact_review_approval(
        script_path=paths["script"],
        fact_report_path=paths["fact_report"],
        persona_report_path=paths["persona_report"],
        claim_inventory_path=paths["claims"],
        source_snapshot_path=paths["sources"],
        output_path=paths["approval"],
        reviewer_id="shs",
        approval_source="explicit_user_confirmation_in_codex_thread",
        approved_at_utc="2026-08-28T00:00:00+00:00",
    )
    approval["agent_generated"] = True
    paths["approval"].write_text(
        json.dumps(approval, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Schema validation failed"):
        validate_fact_review_gate(
            approval_path=paths["approval"],
            script_path=paths["script"],
            fact_report_path=paths["fact_report"],
            persona_report_path=paths["persona_report"],
            claim_inventory_path=paths["claims"],
            source_snapshot_path=paths["sources"],
        )


@pytest.mark.parametrize(
    ("field", "mutation"),
    [
        ("fail_count", "missing"),
        ("unsupported_count", "missing"),
        ("forbidden_wording_count", "missing"),
        ("unresolved_conflict_count", "missing"),
        ("fail_count", "negative"),
    ],
)
def test_rejects_missing_or_invalid_blocking_counter(
    tmp_path: Path, field: str, mutation: str
) -> None:
    from lib.fact_review_approval import record_fact_review_approval

    paths = _write_fixture_bundle(tmp_path)
    report = json.loads(paths["fact_report"].read_text(encoding="utf-8"))
    if mutation == "missing":
        report.pop(field)
    else:
        report[field] = -1
    paths["fact_report"].write_text(
        json.dumps(report, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="blocking fact counter"):
        record_fact_review_approval(
            script_path=paths["script"],
            fact_report_path=paths["fact_report"],
            persona_report_path=paths["persona_report"],
            claim_inventory_path=paths["claims"],
            source_snapshot_path=paths["sources"],
            output_path=paths["approval"],
            reviewer_id="shs",
            approval_source="explicit_user_confirmation_in_codex_thread",
            approved_at_utc="2026-08-28T00:00:00+00:00",
        )


@pytest.mark.parametrize("status", ["FAIL", "UNKNOWN"])
def test_rejects_blocking_or_unknown_segment_status(
    tmp_path: Path, status: str
) -> None:
    from lib.fact_review_approval import record_fact_review_approval

    paths = _write_fixture_bundle(tmp_path)
    report = json.loads(paths["fact_report"].read_text(encoding="utf-8"))
    report["segment_evaluations"][2]["status"] = status
    paths["fact_report"].write_text(
        json.dumps(report, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="segment status"):
        record_fact_review_approval(
            script_path=paths["script"],
            fact_report_path=paths["fact_report"],
            persona_report_path=paths["persona_report"],
            claim_inventory_path=paths["claims"],
            source_snapshot_path=paths["sources"],
            output_path=paths["approval"],
            reviewer_id="shs",
            approval_source="explicit_user_confirmation_in_codex_thread",
            approved_at_utc="2026-08-28T00:00:00+00:00",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sentence_id", None),
        ("sentence_id", 123),
        ("segment_index", "1"),
        ("segment_index", 1.5),
        ("segment_index", True),
    ],
)
def test_rejects_coerced_review_item_identity(
    tmp_path: Path, field: str, value: object
) -> None:
    from lib.fact_review_approval import record_fact_review_approval

    paths = _write_fixture_bundle(tmp_path)
    report = json.loads(paths["fact_report"].read_text(encoding="utf-8"))
    report["segment_evaluations"][0][field] = value
    paths["fact_report"].write_text(
        json.dumps(report, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match=field):
        record_fact_review_approval(
            script_path=paths["script"],
            fact_report_path=paths["fact_report"],
            persona_report_path=paths["persona_report"],
            claim_inventory_path=paths["claims"],
            source_snapshot_path=paths["sources"],
            output_path=paths["approval"],
            reviewer_id="shs",
            approval_source="explicit_user_confirmation_in_codex_thread",
            approved_at_utc="2026-08-28T00:00:00+00:00",
        )


@pytest.mark.parametrize("value", ["2", 2.0, True, None])
def test_rejects_non_integer_review_required_count(
    tmp_path: Path, value: object
) -> None:
    from lib.fact_review_approval import record_fact_review_approval

    paths = _write_fixture_bundle(tmp_path)
    report = json.loads(paths["fact_report"].read_text(encoding="utf-8"))
    report["review_required_count"] = value
    paths["fact_report"].write_text(
        json.dumps(report, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="review_required_count"):
        record_fact_review_approval(
            script_path=paths["script"],
            fact_report_path=paths["fact_report"],
            persona_report_path=paths["persona_report"],
            claim_inventory_path=paths["claims"],
            source_snapshot_path=paths["sources"],
            output_path=paths["approval"],
            reviewer_id="shs",
            approval_source="explicit_user_confirmation_in_codex_thread",
            approved_at_utc="2026-08-28T00:00:00+00:00",
        )


@pytest.mark.parametrize("status", ["REVIEW_REQUIRED", "FAIL", None])
def test_rejects_nonpassing_persona_report(
    tmp_path: Path, status: str | None
) -> None:
    from lib.fact_review_approval import record_fact_review_approval

    paths = _write_fixture_bundle(tmp_path)
    persona = json.loads(paths["persona_report"].read_text(encoding="utf-8"))
    if status is None:
        persona.pop("overall_status")
    else:
        persona["overall_status"] = status
    paths["persona_report"].write_text(
        json.dumps(persona, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="persona report overall_status must be PASS"):
        record_fact_review_approval(
            script_path=paths["script"],
            fact_report_path=paths["fact_report"],
            persona_report_path=paths["persona_report"],
            claim_inventory_path=paths["claims"],
            source_snapshot_path=paths["sources"],
            output_path=paths["approval"],
            reviewer_id="shs",
            approval_source="explicit_user_confirmation_in_codex_thread",
            approved_at_utc="2026-08-28T00:00:00+00:00",
        )
