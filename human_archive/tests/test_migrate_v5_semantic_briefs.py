from __future__ import annotations

import hashlib
import json
from pathlib import Path

from migrate_v5_semantic_briefs import migrate_semantic_briefs


def test_semantic_migration_replaces_only_generic_brief_and_preserves_old_asset(tmp_path: Path):
    generic_digest = "여기서 사건 자체를 완전한 조작이라 단정할 수는 없습니다."
    script = {
        "episode_id": "HA002",
        "sentences": [
            {"sentence_id": "S0", "tts_text": "실록에도 승정원일기에도 난동 기록은 없습니다"},
            {"sentence_id": "S1", "tts_text": generic_digest},
        ],
    }
    timing = {
        "script_sha256": "SCRIPT",
        "timing_sha256": "TIMING",
        "shots": [
            {"shot_id": "KEEP", "order": 1, "chapter": 1, "start_sec": 0.0, "end_sec": 5.0, "duration_sec": 5.0, "sentence_spans": [{"sentence_id": "S0"}]},
            {"shot_id": "CHANGE", "order": 2, "chapter": 1, "start_sec": 5.0, "end_sec": 10.0, "duration_sec": 5.0, "sentence_spans": [{"sentence_id": "S1"}]},
        ],
    }
    old_briefs = {
        "schema_version": 1,
        "episode_id": "HA002",
        "briefs": [
            {"shot_id": "KEEP", "semantic_anchors": ["sealed archive case"], "action": "specific scene"},
            {"shot_id": "CHANGE", "semantic_anchors": ["여기서", "사건", "자체를"], "action": "period-dressed palace figures perform the single concrete action described by the narration"},
        ],
    }
    keep_request = {
        "shot_id": "KEEP", "request_sha256": "KEEP-HASH", "ocr_retry_attempt": 1,
        "visual_mode": "evidence_artifact", "semantic_anchors": ["sealed archive case"],
        "submission_prompt": "one sealed archive case", "positive_prompt": "one sealed archive case",
        "negative": {"mode": "prompt_exclusion", "items": []},
    }
    change_request = {"shot_id": "CHANGE", "request_sha256": "OLD-CHANGE-HASH"}
    flow = {"schema_version": 1, "episode_id": "HA002", "requests": [keep_request, change_request]}
    (tmp_path / "source").mkdir()
    (tmp_path / "images").mkdir()
    old_image = tmp_path / "images" / "CHANGE.jpg"
    old_image.write_bytes(b"generic-image")
    image_sha = hashlib.sha256(old_image.read_bytes()).hexdigest().upper()
    assets = {"generation_scope": "all", "assets": [{
        "shot_id": "CHANGE", "order": 2, "status": "COMPLETED", "file_path": "CHANGE.jpg",
        "sha256": image_sha, "prompt_sha256": "OLD-CHANGE-HASH",
    }]}
    script_path = tmp_path / "source" / "script_candidate.json"
    timing_path = tmp_path / "shot_timing_manifest.json"
    script_path.write_text(json.dumps(script), encoding="utf-8")
    timing_path.write_text(json.dumps(timing), encoding="utf-8")
    (tmp_path / "visual_brief_manifest.json").write_text(json.dumps(old_briefs), encoding="utf-8")
    (tmp_path / "flow_image_prompts.json").write_text(json.dumps(flow), encoding="utf-8")
    (tmp_path / "asset_manifest.json").write_text(json.dumps(assets), encoding="utf-8")

    result = migrate_semantic_briefs(tmp_path, script_path=script_path, timing_path=timing_path)
    updated_flow = json.loads((tmp_path / "flow_image_prompts.json").read_text(encoding="utf-8"))
    by_id = {row["shot_id"]: row for row in updated_flow["requests"]}
    updated_briefs = json.loads((tmp_path / "visual_brief_manifest.json").read_text(encoding="utf-8"))
    brief_by_id = {row["shot_id"]: row for row in updated_briefs["briefs"]}
    updated_assets = json.loads((tmp_path / "asset_manifest.json").read_text(encoding="utf-8"))

    assert result["changed_ids"] == ["CHANGE"]
    assert by_id["KEEP"] == keep_request
    assert by_id["CHANGE"]["request_sha256"] != "OLD-CHANGE-HASH"
    assert not any(any("가" <= char <= "힣" for char in anchor) for anchor in by_id["CHANGE"]["semantic_anchors"])
    assert brief_by_id["CHANGE"]["focal_subject"] == "partly uncovered wrapped bundle"
    archives = list((tmp_path / "rejected_visual_variants" / "semantic-fallback-002" / "CHANGE").glob("variant-*.jpg"))
    assert len(archives) == 1
    assert archives[0].read_bytes() == b"generic-image"
    assert updated_assets["asset_history"][0]["archive_reason"] == "generic_semantic_fallback"
