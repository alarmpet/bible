from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.aligned_prompt_compiler import compile_aligned_prompt
from lib.provenance import compute_file_sha256
from rewrite_policy_rejected_prompt import rewrite_policy_rejected


def _brief() -> dict:
    return {
        "shot_id": "shot-v6-001",
        "narration_digest": "The archive case remains in its excavation context.",
        "visual_mode": "evidence_artifact",
        "semantic_anchors": ["sealed archive case", "excavation context", "evidence object"],
        "focal_subject": "sealed archive case",
        "action": "the named sealed archive case rests in its real excavation context",
        "place": "royal archive excavation chamber",
        "era": "Joseon period",
        "shot_scale": "medium wide full-frame 16:9",
        "camera": "documentary observational framing",
        "foreground": "one narration-specific prop only",
        "midground": "the named evidence object",
        "background": "specific uncluttered archive architecture",
        "claim_ids": ["CLM-JH-001"],
        "semantic_anchor_ids": ["anchor-case", "anchor-context"],
        "required_semantic_anchor_ids": ["anchor-case"],
        "actors": [],
        "reference_asset_ids": [],
        "motion_profile": "artifact_close_push",
        "safety_treatment": "no sensational violence, no generated text",
    }


def _write_v6_retry_build(build: Path, *, flow_shape: str | None) -> dict:
    images = build / "images"
    images.mkdir(parents=True)
    brief = _brief()
    old_request = compile_aligned_prompt(brief)
    old_request.update(
        {
            "scene_id": "scene-v6-001",
            "shot_id": "shot-v6-001",
            "order": 1,
            "claim_ids": brief["claim_ids"],
            "place": brief["place"],
            "era": brief["era"],
        }
    )
    (build / "visual_brief_manifest.json").write_text(
        json.dumps({"schema_version": 1, "episode_id": "HA002", "briefs": [brief]}),
        encoding="utf-8",
    )
    flow_path = build / "flow_image_prompts.json"
    if flow_shape == "dict":
        flow_path.write_text(
            json.dumps({"schema_version": 1, "episode_id": "HA002", "requests": [old_request]}),
            encoding="utf-8",
        )
    elif flow_shape == "list":
        flow_path.write_text(
            json.dumps(
                [
                    {
                        "shot_id": "shot-v6-001",
                        "prompt": "stale legacy prompt",
                        "request_sha256": old_request["request_sha256"],
                    }
                ]
            ),
            encoding="utf-8",
        )
    request_manifest = {
        "schema_version": 2,
        "episode_id": "HA002",
        "contract_sha256": compute_file_sha256(flow_path) if flow_path.exists() else "MISSING-FLOW-CONTRACT",
        "requests": [old_request],
    }
    (build / "image_request_manifest.json").write_text(json.dumps(request_manifest), encoding="utf-8")
    (images / "shot-v6-001.jpg").write_bytes(b"failed-image-bytes")
    (build / "asset_manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "assets": [
                    {
                        "shot_id": "shot-v6-001",
                        "order": 1,
                        "status": "COMPLETED",
                        "file_path": "shot-v6-001.jpg",
                        "sha256": "OLD-IMAGE-HASH",
                        "prompt_sha256": old_request["request_sha256"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return old_request


def test_missing_flow_contract_fails_before_any_archive_or_manifest_mutation(tmp_path: Path):
    # Mutation caught: treating a missing Flow contract as optional and archiving before validation.
    build = tmp_path / "build"
    _write_v6_retry_build(build, flow_shape=None)
    protected_paths = [
        build / "visual_brief_manifest.json",
        build / "image_request_manifest.json",
        build / "asset_manifest.json",
        build / "images" / "shot-v6-001.jpg",
    ]
    before = {path: path.read_bytes() for path in protected_paths}
    error = None

    try:
        rewrite_policy_rejected(build, ["scene-v6-001"])
    except ValueError as caught:
        error = caught

    assert not (build / "rejected_policy_variants").exists()
    assert not (build / "policy_retry_manifest.json").exists()
    assert {path: path.read_bytes() for path in protected_paths} == before
    assert error is not None
    assert "Flow prompt contract" in str(error)


def test_legacy_list_flow_contract_is_replaced_exactly_and_rebound_to_its_file_hash(tmp_path: Path):
    # Mutation caught: merging a legacy row and retaining its stale prompt field in the new contract.
    build = tmp_path / "build"
    _write_v6_retry_build(build, flow_shape="list")

    [first_update] = rewrite_policy_rejected(build, ["scene-v6-001"])
    [second_update] = rewrite_policy_rejected(build, ["scene-v6-001"])
    [review_update] = rewrite_policy_rejected(build, ["scene-v6-001"])

    flow = json.loads((build / "flow_image_prompts.json").read_text(encoding="utf-8"))
    request_manifest = json.loads((build / "image_request_manifest.json").read_text(encoding="utf-8"))
    retried_request = request_manifest["requests"][0]
    assert flow == [retried_request]
    assert first_update["attempt"] == 1
    assert second_update["attempt"] == 2
    assert review_update["attempt"] == 3
    assert review_update["lifecycle"] == "REVIEW_REQUIRED"
    assert retried_request["policy_retry_attempt"] == 2
    assert retried_request["lifecycle"] == "REVIEW_REQUIRED"
    assert retried_request["request_sha256"] == second_update["new_request_sha256"]
    assert request_manifest["contract_sha256"] == compute_file_sha256(build / "flow_image_prompts.json")


def test_v5_v6_retry_lifecycle_uses_shot_keyed_briefs_and_immutable_archives(tmp_path: Path):
    # Mutation caught: reading only episode_visual_contract_v2 or mutating prior audit rows.
    build = tmp_path / "build"
    images = build / "images"
    images.mkdir(parents=True)
    brief = _brief()
    old_request = compile_aligned_prompt(brief)
    old_request.update(
        {
            "scene_id": "scene-v6-001",
            "shot_id": "shot-v6-001",
            "order": 1,
            "claim_ids": brief["claim_ids"],
            "place": brief["place"],
            "era": brief["era"],
        }
    )
    (build / "visual_brief_manifest.json").write_text(
        json.dumps({"schema_version": 1, "episode_id": "HA002", "briefs": [brief]}),
        encoding="utf-8",
    )
    (build / "image_request_manifest.json").write_text(
        json.dumps({"schema_version": 2, "episode_id": "HA002", "requests": [old_request]}),
        encoding="utf-8",
    )
    (build / "flow_image_prompts.json").write_text(
        json.dumps({"schema_version": 1, "episode_id": "HA002", "requests": [old_request]}),
        encoding="utf-8",
    )
    request_manifest = json.loads((build / "image_request_manifest.json").read_text(encoding="utf-8"))
    request_manifest["contract_sha256"] = compute_file_sha256(build / "flow_image_prompts.json")
    (build / "image_request_manifest.json").write_text(json.dumps(request_manifest), encoding="utf-8")
    failed_bytes = b"failed-image-bytes"
    (images / "shot-v6-001.jpg").write_bytes(failed_bytes)
    (build / "asset_manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "assets": [
                    {
                        "shot_id": "shot-v6-001",
                        "order": 1,
                        "status": "COMPLETED",
                        "file_path": "shot-v6-001.jpg",
                        "sha256": "OLD-IMAGE-HASH",
                        "prompt_sha256": old_request["request_sha256"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    [first_update] = rewrite_policy_rejected(
        build,
        ["scene-v6-001"],
        reason="provider_policy_rejected",
    )
    first_audit = json.loads((build / "policy_retry_manifest.json").read_text(encoding="utf-8"))["retries"][0]

    archived = build / first_update["archived_asset"]["file_path"]
    assert archived.read_bytes() == failed_bytes
    assert archived.parent == build / "rejected_policy_variants" / "shot-v6-001"
    assert first_update["attempt"] == 1
    assert first_update["transform"] == "safe_rephrase"
    assert first_update["old_request_sha256"] == old_request["request_sha256"]
    assert first_update["archived_request"]["sha256"] == old_request["request_sha256"]
    archived_request = build / first_update["archived_request"]["file_path"]
    assert json.loads(archived_request.read_text(encoding="utf-8")) == old_request
    updated_flow = json.loads((build / "flow_image_prompts.json").read_text(encoding="utf-8"))
    updated_request = json.loads((build / "image_request_manifest.json").read_text(encoding="utf-8"))
    assert updated_flow["requests"][0]["request_sha256"] == updated_request["requests"][0]["request_sha256"]
    assert updated_request["contract_sha256"] == compute_file_sha256(build / "flow_image_prompts.json")

    [second_update] = rewrite_policy_rejected(build, ["scene-v6-001"], reason="visual_mismatch")
    assert second_update["attempt"] == 2
    assert second_update["transform"] == "safe_abstraction"
    audit_after_second = json.loads((build / "policy_retry_manifest.json").read_text(encoding="utf-8"))["retries"]
    assert audit_after_second[0] == first_audit
    assert len(audit_after_second) == 2

    [review_update] = rewrite_policy_rejected(build, ["scene-v6-001"], reason="provider_policy_rejected")
    assert review_update["lifecycle"] == "REVIEW_REQUIRED"
    assert review_update["attempt"] == 3
    final_request = json.loads((build / "image_request_manifest.json").read_text(encoding="utf-8"))["requests"][0]
    assert final_request["scene_id"] == "scene-v6-001"
    assert final_request["shot_id"] == "shot-v6-001"
    assert final_request["lifecycle"] == "REVIEW_REQUIRED"
    assert len(json.loads((build / "policy_retry_manifest.json").read_text(encoding="utf-8"))["retries"]) == 2
    final_assets = json.loads((build / "asset_manifest.json").read_text(encoding="utf-8"))["assets"]
    assert final_assets[0]["status"] == "REVIEW_REQUIRED"
