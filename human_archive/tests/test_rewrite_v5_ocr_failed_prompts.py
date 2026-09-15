from __future__ import annotations

import hashlib
import json
from pathlib import Path

from rewrite_v5_ocr_failed_prompts import rewrite_ocr_failed


def _request(shot_id: str) -> dict:
    row = {
        "shot_id": shot_id,
        "visual_mode": "historical_reconstruction",
        "semantic_anchors": ["palace"],
        "positive_prompt": "one clean palace scene",
        "negative": {"mode": "prompt_exclusion", "items": ["letters"]},
        "submission_prompt": "one clean palace scene. Strict exclusions: letters.",
        "motion_profile": "reenactment_push",
        "provider": "flow",
    }
    row["request_sha256"] = hashlib.sha256(
        json.dumps(row, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest().upper()
    return row


def test_ocr_retry_preserves_old_asset_and_rebuilds_only_selected_request(tmp_path: Path):
    selected = _request("S1")
    untouched = _request("S2")
    old_selected_sha = selected["request_sha256"]
    old_untouched_sha = untouched["request_sha256"]
    flow = {"episode_id": "HA002", "requests": [selected, untouched]}
    timing = {"shots": [
        {"shot_id": "S1", "order": 1, "start_sec": 0.0, "end_sec": 5.0, "duration_sec": 5.0},
        {"shot_id": "S2", "order": 2, "start_sec": 5.0, "end_sec": 10.0, "duration_sec": 5.0},
    ]}
    (tmp_path / "images").mkdir()
    old_image = tmp_path / "images" / "S1.jpg"
    old_image.write_bytes(b"old-image")
    manifest = {"assets": [{
        "shot_id": "S1", "status": "COMPLETED", "file_path": "S1.jpg",
        "sha256": hashlib.sha256(old_image.read_bytes()).hexdigest().upper(),
        "prompt_sha256": old_selected_sha,
    }]}
    (tmp_path / "flow_image_prompts.json").write_text(json.dumps(flow), encoding="utf-8")
    (tmp_path / "shot_timing_manifest.json").write_text(json.dumps(timing), encoding="utf-8")
    (tmp_path / "asset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    result = rewrite_ocr_failed(tmp_path, ["S1"])
    updated = json.loads((tmp_path / "flow_image_prompts.json").read_text(encoding="utf-8"))
    updated_by_id = {row["shot_id"]: row for row in updated["requests"]}
    image_requests = json.loads((tmp_path / "image_request_manifest.json").read_text(encoding="utf-8"))
    updated_assets = json.loads((tmp_path / "asset_manifest.json").read_text(encoding="utf-8"))

    assert result["changed_ids"] == ["S1"]
    assert updated_by_id["S1"]["request_sha256"] != old_selected_sha
    assert updated_by_id["S1"]["ocr_retry_attempt"] == 1
    assert "text-like" in updated_by_id["S1"]["submission_prompt"]
    assert updated_by_id["S2"]["request_sha256"] == old_untouched_sha
    assert image_requests["contract_sha256"]
    assert next(row for row in image_requests["requests"] if row["scene_id"] == "S1")["request_sha256"] == updated_by_id["S1"]["request_sha256"]
    archives = list((tmp_path / "rejected_visual_variants" / "ocr-detected-001" / "S1").glob("*.jpg"))
    assert len(archives) == 1
    assert archives[0].read_bytes() == b"old-image"
    assert len(updated_assets["asset_history"]) == 1
    assert updated_assets["asset_history"][0]["prompt_sha256"] == old_selected_sha
    assert updated_assets["asset_history"][0]["archive_reason"] == "embedded_text_detected"
    assert updated_assets["asset_history"][0]["archived_file_path"].endswith("variant-001.jpg")


def test_ocr_retry_rejects_unknown_scene_id(tmp_path: Path):
    flow = {"episode_id": "HA002", "requests": [_request("S1")]}
    timing = {"shots": [{"shot_id": "S1", "order": 1, "start_sec": 0.0, "end_sec": 5.0, "duration_sec": 5.0}]}
    (tmp_path / "flow_image_prompts.json").write_text(json.dumps(flow), encoding="utf-8")
    (tmp_path / "shot_timing_manifest.json").write_text(json.dumps(timing), encoding="utf-8")

    import pytest
    with pytest.raises(ValueError, match="unknown"):
        rewrite_ocr_failed(tmp_path, ["MISSING"])


def test_second_ocr_retry_switches_to_ultra_minimal_composition(tmp_path: Path):
    flow = {"episode_id": "HA002", "requests": [_request("S1")]}
    timing = {"shots": [{"shot_id": "S1", "order": 1, "start_sec": 0.0, "end_sec": 5.0, "duration_sec": 5.0}]}
    (tmp_path / "flow_image_prompts.json").write_text(json.dumps(flow), encoding="utf-8")
    (tmp_path / "shot_timing_manifest.json").write_text(json.dumps(timing), encoding="utf-8")

    rewrite_ocr_failed(tmp_path, ["S1"])
    rewrite_ocr_failed(tmp_path, ["S1"])
    updated = json.loads((tmp_path / "flow_image_prompts.json").read_text(encoding="utf-8"))
    request = updated["requests"][0]

    assert request["ocr_retry_attempt"] == 2
    assert "Ultra-minimal OCR-safe retry" in request["submission_prompt"]
    assert "grids and lattice" in request["submission_prompt"]
