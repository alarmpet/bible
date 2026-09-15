from __future__ import annotations

import json
from pathlib import Path

from lib.prompt_compiler import compile_policy_safe_retry, compile_scene_request
from migrate_coherent_scene_requests import migrate_requests


def _scene(scene_id: str, order: int, role: str, action: str) -> dict:
    return {
        "scene_id": scene_id,
        "order": order,
        "visual_role": role,
        "host_mode": "full" if role == "host_explainer" else "absent",
        "historical_subjects": ["historical person"],
        "visual_beat": "test beat",
        "action": [action],
        "place": "late Joseon historical setting",
        "era_context": "late Joseon",
        "overlay_text": [],
        "must_not": [],
        "forbidden_implications": [],
        "camera": "medium view",
        "composition": "filled editorial doodle composition",
        "lighting": "soft flat candlelight",
        "style": "hand-drawn doodle",
    }


def _old_request(scene: dict, marker: str) -> dict:
    request = compile_scene_request(scene)
    request["positive_prompt"] = f"old {marker} prompt"
    request["submission_prompt"] = f"old {marker} prompt"
    request["request_sha256"] = marker
    return request


def test_migration_rewrites_only_normal_host_and_evidence_and_archives_current_assets(tmp_path: Path):
    build = tmp_path / "build"
    images = build / "images"
    raw = images / "raw"
    raw.mkdir(parents=True)
    host = _scene("host-scene", 1, "host_explainer", "the presenter points toward a vignette")
    evidence = _scene("evidence-scene", 2, "evidence_object", "hands examine blank documents")
    reconstruction = _scene("reconstruction-scene", 3, "historical_reconstruction", "actors exchange a scroll")
    policy_scene = _scene("policy-scene", 4, "evidence_object", "hands examine blank documents")
    old_host = _old_request(host, "OLD-HOST")
    old_evidence = _old_request(evidence, "OLD-EVIDENCE")
    current_reconstruction = compile_scene_request(reconstruction)
    policy_request = compile_policy_safe_retry(policy_scene, 2, reason="visual_mismatch")
    requests = [old_host, old_evidence, current_reconstruction, policy_request]
    (build / "episode_visual_contract_v2.json").write_text(
        json.dumps({"scenes": [host, evidence, reconstruction, policy_scene]}), encoding="utf-8"
    )
    (build / "image_request_manifest.json").write_text(json.dumps({"requests": requests}), encoding="utf-8")
    (build / "flow_image_prompts.json").write_text(
        json.dumps([{"shot_id": request["scene_id"], "prompt": request["positive_prompt"], "request_sha256": request["request_sha256"]} for request in requests]),
        encoding="utf-8",
    )
    asset_rows = []
    for request in requests:
        scene_id = request["scene_id"]
        (images / f"{scene_id}.jpg").write_bytes(f"image-{scene_id}".encode())
        asset_rows.append({
            "shot_id": scene_id,
            "status": "COMPLETED",
            "prompt_sha256": request["request_sha256"],
            "file_path": f"{scene_id}.jpg",
        })
    (raw / "host-scene.jpg").write_bytes(b"raw-host")
    (build / "asset_manifest.json").write_text(json.dumps({"assets": asset_rows}), encoding="utf-8")

    audit = migrate_requests(build)

    assert audit["changed_ids"] == ["host-scene", "evidence-scene"]
    assert audit["skipped_policy_safe_ids"] == ["policy-scene"]
    migrated = json.loads((build / "image_request_manifest.json").read_text(encoding="utf-8"))
    by_id = {item["scene_id"]: item for item in migrated["requests"]}
    assert by_id["host-scene"]["request_sha256"] != "OLD-HOST"
    assert by_id["evidence-scene"]["request_sha256"] != "OLD-EVIDENCE"
    assert by_id["reconstruction-scene"] == current_reconstruction
    assert by_id["policy-scene"] == policy_request
    archive = build / "rejected_visual_variants" / "pre-coherent-scene-001"
    assert (archive / "images" / "host-scene.jpg").read_bytes() == b"image-host-scene"
    assert (archive / "images" / "evidence-scene.jpg").read_bytes() == b"image-evidence-scene"
    assert (archive / "raw" / "host-scene.jpg").read_bytes() == b"raw-host"
    assert not (archive / "images" / "reconstruction-scene.jpg").exists()
    assert not (archive / "images" / "policy-scene.jpg").exists()
    archived_requests = json.loads((archive / "metadata" / "image_request_manifest_before.json").read_text(encoding="utf-8"))
    archived_assets = json.loads((archive / "metadata" / "asset_manifest_before.json").read_text(encoding="utf-8"))
    archived_compatibility = json.loads((archive / "metadata" / "flow_image_prompts_before.json").read_text(encoding="utf-8"))
    assert {item["request_sha256"] for item in archived_requests["requests"]} >= {"OLD-HOST", "OLD-EVIDENCE"}
    assert len(archived_assets["assets"]) == 4
    assert len(archived_compatibility) == 4
    compatibility = json.loads((build / "flow_image_prompts.json").read_text(encoding="utf-8"))
    compatibility_by_id = {item["shot_id"]: item for item in compatibility}
    assert compatibility_by_id["host-scene"]["request_sha256"] == by_id["host-scene"]["request_sha256"]
    assert compatibility_by_id["evidence-scene"]["request_sha256"] == by_id["evidence-scene"]["request_sha256"]
