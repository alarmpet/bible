from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from generate_flow_batch import pending_requests
from lib.provenance import compute_file_sha256
from materialize_semantic_image_reuse import (
    MaterializationError,
    _copy_files_atomically,
    materialize_semantic_image_reuse,
)


HOST_COSTUME = "white dopo with full torso, sleeves, collar, and waist tie"


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _make_image(path: Path, color: tuple[int, int, int]) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1920, 1080), color)
    draw = ImageDraw.Draw(image)
    for x in range(0, 1920, 24):
        draw.line((x, 0, 1919 - x // 2, 1079), fill=(255 - color[0], 90, 40), width=2)
    image.save(path, format="JPEG", quality=95)
    return {
        "sha256": compute_file_sha256(path),
        "bytes": path.stat().st_size,
        "width": 1920,
        "height": 1080,
    }


def _request(shot_id: str, order: int, digest: str, *, host: bool = False) -> dict:
    row = {
        "scene_id": shot_id,
        "shot_id": shot_id,
        "order": order,
        "visual_mode": "host_chapter_hinge" if host else "historical_reconstruction",
        "visual_role": "host_explainer" if host else "historical_reconstruction",
        "semantic_anchors": [f"anchor-{digest}-a", f"anchor-{digest}-b", f"anchor-{digest}-c"],
        "positive_prompt": f"scene prompt {digest}",
        "negative": {"mode": "prompt_exclusion", "items": ["text", "digits"]},
        "submission_prompt": f"scene prompt {digest}; no text or digits",
        "motion_profile": "host_hinge" if host else "reenactment_push",
        "provider": "flow",
    }
    if host:
        row["host_overlay"] = {
            "asset": "human_archive/assets/doodle_seonbi_v1.png",
            "costume": HOST_COSTUME,
            "width_ratio": 0.38,
        }
    return row


def _write_contract(build: Path, requests: list[dict]) -> str:
    flow_requests = []
    for row in requests:
        payload = {
            "shot_id": row["scene_id"],
            "visual_mode": row["visual_mode"],
            "semantic_anchors": row["semantic_anchors"],
            "positive_prompt": row["positive_prompt"],
            "negative": row["negative"],
            "submission_prompt": row["submission_prompt"],
            "motion_profile": row["motion_profile"],
            "provider": row["provider"],
        }
        if row.get("host_overlay"):
            payload["host_overlay"] = row["host_overlay"]
        payload["request_sha256"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest().upper()
        row["request_sha256"] = payload["request_sha256"]
        flow_requests.append(payload)
    flow = {
        "schema_version": 1,
        "episode_id": "HA002",
        "requests": flow_requests,
    }
    flow_path = build / "flow_image_prompts.json"
    _write_json(flow_path, flow)
    contract_sha = compute_file_sha256(flow_path)
    _write_json(
        build / "image_request_manifest.json",
        {
            "schema_version": 2,
            "episode_id": "HA002",
            "contract_sha256": contract_sha,
            "requests": requests,
        },
    )
    return contract_sha


def _source_asset(
    build: Path,
    request: dict,
    color: tuple[int, int, int],
    *,
    host: bool = False,
) -> dict:
    file_path = f"{request['scene_id']}.jpg"
    evidence = _make_image(build / "images" / file_path, color)
    row = {
        "shot_id": request["scene_id"],
        "order": request["order"],
        "card_id": f"FLOW-{request['scene_id']}-{evidence['sha256'][:8]}",
        "prompt_sha256": request["request_sha256"],
        "file_path": file_path,
        **evidence,
        "status": "COMPLETED",
    }
    if host:
        project_root = Path(__file__).resolve().parents[2]
        overlay_path = project_root / "human_archive" / "assets" / "doodle_seonbi_v1.png"
        row["postprocess"] = {
            "type": "canonical_host_overlay",
            "overlay_sha256": compute_file_sha256(overlay_path),
            "output_sha256": evidence["sha256"],
            "anchor": "right_bottom",
            "width_ratio": 0.38,
            "costume": HOST_COSTUME,
            "raw_file": f"raw/{file_path}",
        }
    return row


def _fixture(tmp_path: Path) -> dict:
    source = (tmp_path / "source-v5").resolve()
    target = (tmp_path / "target-v6").resolve()
    source.mkdir()
    target.mkdir()

    source_requests = [
        _request("SRC-HOST", 1, "1", host=True),
        _request("SRC-REVIEW", 2, "2"),
    ]
    target_requests = [
        _request("TGT-HOST", 1, "3", host=True),
        _request("TGT-REVIEW", 2, "4"),
        _request("TGT-NEW", 3, "5"),
    ]
    _write_contract(source, source_requests)
    target_contract_sha = _write_contract(target, target_requests)

    source_assets = [
        _source_asset(source, source_requests[0], (20, 80, 130), host=True),
        _source_asset(source, source_requests[1], (110, 50, 30)),
    ]
    _write_json(
        source / "asset_manifest.json",
        {"schema_version": 2, "build_id": source.name, "assets": source_assets},
    )

    plan = {
        "schema_version": 1,
        "source_build": str(source),
        "target_build": str(target),
        "summary": {"auto_reuse": 1, "review_candidate": 1, "generate_new": 1},
        "decisions": [
            {
                "target_shot_id": "TGT-HOST",
                "target_order": 1,
                "target_host_required": True,
                "decision": "auto_reuse",
                "source_shot_id": "SRC-HOST",
                "source_visual_mode": "host_chapter_hinge",
                "source_asset_file_path": source_assets[0]["file_path"],
                "source_asset_sha256": source_assets[0]["sha256"],
            },
            {
                "target_shot_id": "TGT-REVIEW",
                "target_order": 2,
                "target_host_required": False,
                "decision": "review_candidate",
                "source_shot_id": "SRC-REVIEW",
                "source_visual_mode": "historical_reconstruction",
                "source_asset_file_path": source_assets[1]["file_path"],
                "source_asset_sha256": source_assets[1]["sha256"],
            },
            {
                "target_shot_id": "TGT-NEW",
                "target_order": 3,
                "target_host_required": False,
                "decision": "generate_new",
            },
        ],
    }
    plan_path = target / "image_reuse_plan.json"
    _write_json(plan_path, plan)
    plan_sha = compute_file_sha256(plan_path)
    approval = {
        "schema_version": 1,
        "decision": "approved",
        "approved_at_utc": "2026-08-28T03:00:00+00:00",
        "reviewer_id": "operator-shs",
        "approval_source": "explicit_user_confirmation_in_codex_thread",
        "plan_sha256": plan_sha,
        "request_contract_sha256": target_contract_sha,
        "reviews": [
            {
                "target_shot_id": "TGT-REVIEW",
                "source_shot_id": "SRC-REVIEW",
                "source_asset_sha256": source_assets[1]["sha256"],
                "decision": "reuse",
            }
        ],
    }
    approval_path = target / "image_reuse_review_approval.json"
    _write_json(approval_path, approval)
    return {
        "source": source,
        "target": target,
        "plan_path": plan_path,
        "approval_path": approval_path,
        "plan_sha": plan_sha,
        "target_contract_sha": target_contract_sha,
        "source_assets": source_assets,
        "source_requests": source_requests,
        "target_requests": target_requests,
    }


def _run(case: dict, **kwargs) -> dict:
    return materialize_semantic_image_reuse(
        case["source"],
        case["target"],
        case["plan_path"],
        case["approval_path"],
        **kwargs,
    )


def test_materializes_auto_and_approved_review_with_bound_provenance(tmp_path):
    case = _fixture(tmp_path)

    report = _run(case)

    manifest = json.loads((case["target"] / "asset_manifest.json").read_text(encoding="utf-8"))
    rows = {row["shot_id"]: row for row in manifest["assets"]}
    assert report["copied_shot_ids"] == ["TGT-HOST", "TGT-REVIEW"]
    assert report["pending_generation_shot_ids"] == ["TGT-NEW"]
    assert set(rows) == {"TGT-HOST", "TGT-REVIEW"}
    for target_id, source_index, decision in (
        ("TGT-HOST", 0, "auto_reuse"),
        ("TGT-REVIEW", 1, "approved_review_reuse"),
    ):
        row = rows[target_id]
        source_row = case["source_assets"][source_index]
        assert row["status"] == "COMPLETED"
        assert row["sha256"] == source_row["sha256"]
        assert row["prompt_sha256"] == case["target_requests"][source_index]["request_sha256"]
        assert row["file_path"].startswith(f"reused/{target_id}-")
        assert compute_file_sha256(case["target"] / "images" / row["file_path"]) == row["sha256"]
        assert row["provenance"]["decision"] == decision
        assert row["provenance"]["plan_sha256"] == case["plan_sha"]
        assert row["provenance"]["request_contract_sha256"] == case["target_contract_sha"]
    assert rows["TGT-HOST"]["postprocess"]["type"] == "canonical_host_overlay"
    assert "raw_file" not in rows["TGT-HOST"]["postprocess"]


@pytest.mark.parametrize("mutation", ["missing", "stale"])
def test_review_candidates_require_current_complete_approval_before_writes(tmp_path, mutation):
    case = _fixture(tmp_path)
    if mutation == "missing":
        case["approval_path"].unlink()
    else:
        approval = json.loads(case["approval_path"].read_text(encoding="utf-8"))
        approval["reviews"] = []
        _write_json(case["approval_path"], approval)

    with pytest.raises(MaterializationError, match="approval|review"):
        _run(case)

    assert not (case["target"] / "asset_manifest.json").exists()
    assert not (case["target"] / "images").exists()


def test_source_sha_mismatch_fails_before_target_writes(tmp_path):
    case = _fixture(tmp_path)
    source_file = case["source"] / "images" / case["source_assets"][0]["file_path"]
    source_file.write_bytes(source_file.read_bytes() + b"tampered")

    with pytest.raises(MaterializationError, match="SHA"):
        _run(case)

    assert not (case["target"] / "asset_manifest.json").exists()
    assert not (case["target"] / "images").exists()


def test_host_reuse_requires_canonical_postprocess_evidence(tmp_path):
    case = _fixture(tmp_path)
    manifest_path = case["source"] / "asset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"][0].pop("postprocess")
    _write_json(manifest_path, manifest)

    with pytest.raises(MaterializationError, match="host|canonical"):
        _run(case)

    assert not (case["target"] / "asset_manifest.json").exists()


def test_plan_host_requirement_must_match_current_target_contract(tmp_path):
    case = _fixture(tmp_path)
    requests = list(case["target_requests"])
    requests[0] = _request("TGT-HOST", 1, "3", host=False)
    contract_sha = _write_contract(case["target"], requests)
    approval = json.loads(case["approval_path"].read_text(encoding="utf-8"))
    approval["request_contract_sha256"] = contract_sha
    _write_json(case["approval_path"], approval)

    with pytest.raises(MaterializationError, match="host"):
        _run(case)

    assert not (case["target"] / "asset_manifest.json").exists()


def test_dry_run_is_read_only(tmp_path):
    case = _fixture(tmp_path)

    report = _run(case, dry_run=True)

    assert report["would_materialize_shot_ids"] == ["TGT-HOST", "TGT-REVIEW"]
    assert report["copied_shot_ids"] == []
    assert not (case["target"] / "asset_manifest.json").exists()
    assert not (case["target"] / "images").exists()


def test_repeated_materialization_is_byte_identical_noop(tmp_path):
    case = _fixture(tmp_path)
    _run(case)
    manifest_path = case["target"] / "asset_manifest.json"
    before_manifest = manifest_path.read_bytes()
    before_images = {
        path.relative_to(case["target"]): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in (case["target"] / "images").rglob("*")
        if path.is_file()
    }

    report = _run(case)

    assert report["copied_shot_ids"] == []
    assert report["already_materialized_shot_ids"] == ["TGT-HOST", "TGT-REVIEW"]
    assert manifest_path.read_bytes() == before_manifest
    assert {
        path.relative_to(case["target"]): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in (case["target"] / "images").rglob("*")
        if path.is_file()
    } == before_images


def test_stale_asset_row_is_archived_without_overwriting_old_file(tmp_path):
    case = _fixture(tmp_path)
    old_file = case["target"] / "images" / "legacy" / "TGT-HOST-old.jpg"
    old_evidence = _make_image(old_file, (200, 130, 10))
    _write_json(
        case["target"] / "asset_manifest.json",
        {
            "schema_version": 2,
            "build_id": case["target"].name,
            "assets": [
                {
                    "shot_id": "TGT-HOST",
                    "order": 1,
                    "card_id": "FLOW-OLD",
                    "prompt_sha256": "E" * 64,
                    "file_path": "legacy/TGT-HOST-old.jpg",
                    **old_evidence,
                    "status": "COMPLETED",
                }
            ],
        },
    )

    _run(case)

    manifest = json.loads((case["target"] / "asset_manifest.json").read_text(encoding="utf-8"))
    assert old_file.exists()
    assert manifest["asset_history"][0]["file_path"] == "legacy/TGT-HOST-old.jpg"
    assert manifest["asset_history"][0]["archive_reason"] == "stale_request_hash"
    assert {row["shot_id"] for row in manifest["assets"]} == {"TGT-HOST", "TGT-REVIEW"}


def test_current_same_prompt_different_asset_fails_closed(tmp_path):
    case = _fixture(tmp_path)
    current_file = case["target"] / "images" / "existing" / "TGT-HOST.jpg"
    current = _make_image(current_file, (220, 20, 20))
    current_postprocess = {
        "type": "canonical_host_overlay",
        "overlay_sha256": "B" * 64,
        "output_sha256": current["sha256"],
        "anchor": "right_bottom",
        "width_ratio": 0.38,
        "costume": HOST_COSTUME,
    }
    _write_json(
        case["target"] / "asset_manifest.json",
        {
            "schema_version": 2,
            "assets": [
                {
                    "shot_id": "TGT-HOST",
                    "order": 1,
                    "card_id": "FLOW-CONFLICT",
                    "prompt_sha256": case["target_requests"][0]["request_sha256"],
                    "file_path": "existing/TGT-HOST.jpg",
                    **current,
                    "status": "COMPLETED",
                    "postprocess": current_postprocess,
                }
            ],
        },
    )

    with pytest.raises(MaterializationError, match="conflict"):
        _run(case)

    assert current_file.exists()
    assert not (case["target"] / "images" / "reused").exists()


def test_orphan_destination_file_fails_closed(tmp_path):
    case = _fixture(tmp_path)
    source_row = case["source_assets"][0]
    orphan = (
        case["target"]
        / "images"
        / "reused"
        / f"TGT-HOST-{source_row['sha256'][:12]}.jpg"
    )
    orphan.parent.mkdir(parents=True)
    orphan.write_bytes(
        (case["source"] / "images" / source_row["file_path"]).read_bytes()
    )

    with pytest.raises(MaterializationError, match="orphan"):
        _run(case)

    assert not (case["target"] / "asset_manifest.json").exists()


def test_flow_contract_mutation_fails_before_writes(tmp_path):
    case = _fixture(tmp_path)
    with (case["target"] / "flow_image_prompts.json").open("a", encoding="utf-8") as handle:
        handle.write("\n")

    with pytest.raises(MaterializationError, match="contract"):
        _run(case)

    assert not (case["target"] / "asset_manifest.json").exists()
    assert not (case["target"] / "images").exists()


def test_target_image_request_payload_must_exactly_match_flow_contract(tmp_path):
    case = _fixture(tmp_path)
    manifest_path = case["target"] / "image_request_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["requests"][0]["positive_prompt"] = "tampered prompt after contract build"
    _write_json(manifest_path, manifest)

    with pytest.raises(MaterializationError, match="Flow/image request|payload"):
        _run(case)

    assert not (case["target"] / "asset_manifest.json").exists()
    assert not (case["target"] / "images").exists()


def test_declared_request_sha_must_match_recomputed_flow_payload(tmp_path):
    case = _fixture(tmp_path)
    flow_path = case["target"] / "flow_image_prompts.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8"))
    flow["requests"][0]["request_sha256"] = "F" * 64
    _write_json(flow_path, flow)
    contract_sha = compute_file_sha256(flow_path)

    request_path = case["target"] / "image_request_manifest.json"
    request_manifest = json.loads(request_path.read_text(encoding="utf-8"))
    request_manifest["contract_sha256"] = contract_sha
    request_manifest["requests"][0]["request_sha256"] = "F" * 64
    _write_json(request_path, request_manifest)

    approval = json.loads(case["approval_path"].read_text(encoding="utf-8"))
    approval["request_contract_sha256"] = contract_sha
    _write_json(case["approval_path"], approval)

    with pytest.raises(MaterializationError, match="request SHA"):
        _run(case)

    assert not (case["target"] / "asset_manifest.json").exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("approval_source", "explicit_system"),
        ("reviewer_id", "automation-bot-agent"),
    ],
)
def test_review_approval_rejects_synthetic_identity_markers(tmp_path, field, value):
    case = _fixture(tmp_path)
    approval = json.loads(case["approval_path"].read_text(encoding="utf-8"))
    approval[field] = value
    _write_json(case["approval_path"], approval)

    with pytest.raises(MaterializationError, match="approval|reviewer|human"):
        _run(case)

    assert not (case["target"] / "asset_manifest.json").exists()


@pytest.mark.parametrize("missing_field", ["overlay_sha256", "anchor", "width_ratio"])
def test_host_reuse_requires_complete_canonical_metadata(tmp_path, missing_field):
    case = _fixture(tmp_path)
    manifest_path = case["source"] / "asset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"][0]["postprocess"].pop(missing_field)
    _write_json(manifest_path, manifest)

    with pytest.raises(MaterializationError, match="host|canonical"):
        _run(case)

    assert not (case["target"] / "asset_manifest.json").exists()


def test_nonhost_visual_mode_and_role_must_match_source(tmp_path):
    case = _fixture(tmp_path)
    source_request = case["source_requests"][1]
    source_request["visual_mode"] = "evidence_artifact"
    source_request["visual_role"] = "evidence_object"
    _write_contract(case["source"], case["source_requests"])

    source_manifest_path = case["source"] / "asset_manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    source_manifest["assets"][1]["prompt_sha256"] = source_request["request_sha256"]
    _write_json(source_manifest_path, source_manifest)

    plan = json.loads(case["plan_path"].read_text(encoding="utf-8"))
    plan["decisions"][1]["source_visual_mode"] = "evidence_artifact"
    _write_json(case["plan_path"], plan)
    approval = json.loads(case["approval_path"].read_text(encoding="utf-8"))
    approval["plan_sha256"] = compute_file_sha256(case["plan_path"])
    _write_json(case["approval_path"], approval)

    with pytest.raises(MaterializationError, match="visual mode|visual role"):
        _run(case)

    assert not (case["target"] / "asset_manifest.json").exists()


@pytest.mark.parametrize("malformed_order", ["not-an-integer", 1.9])
def test_malformed_plan_number_is_controlled_materialization_error(
    tmp_path,
    malformed_order,
):
    case = _fixture(tmp_path)
    plan = json.loads(case["plan_path"].read_text(encoding="utf-8"))
    plan["decisions"][0]["target_order"] = malformed_order
    _write_json(case["plan_path"], plan)
    approval = json.loads(case["approval_path"].read_text(encoding="utf-8"))
    approval["plan_sha256"] = compute_file_sha256(case["plan_path"])
    _write_json(case["approval_path"], approval)

    with pytest.raises(MaterializationError, match="order|integer"):
        _run(case)

    assert not (case["target"] / "asset_manifest.json").exists()


def test_materialized_completed_rows_are_skipped_by_flow_pending_logic(tmp_path):
    case = _fixture(tmp_path)
    _run(case)
    manifest = json.loads(
        (case["target"] / "asset_manifest.json").read_text(encoding="utf-8")
    )

    pending = pending_requests(case["target_requests"], manifest["assets"])

    assert [row["scene_id"] for row in pending] == ["TGT-NEW"]


def test_atomic_copy_refuses_destination_created_after_preflight(tmp_path):
    source = tmp_path / "source.jpg"
    source.write_bytes(b"source-content")
    destination = tmp_path / "target" / "images" / "reused" / "asset.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"concurrent-writer-content")

    with pytest.raises(MaterializationError, match="destination|exists|concurrent"):
        _copy_files_atomically(
            [(source, destination, compute_file_sha256(source))]
        )

    assert destination.read_bytes() == b"concurrent-writer-content"


def test_existing_materialization_lock_blocks_without_asset_writes(tmp_path):
    case = _fixture(tmp_path)
    lock_path = case["target"] / ".semantic-image-reuse.lock"
    lock_path.write_text("concurrent-run", encoding="utf-8")

    with pytest.raises(MaterializationError, match="lock|concurrent|running"):
        _run(case)

    assert lock_path.read_text(encoding="utf-8") == "concurrent-run"
    assert not (case["target"] / "asset_manifest.json").exists()
    assert not (case["target"] / "images").exists()
