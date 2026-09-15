from __future__ import annotations

from lib.semantic_image_reuse import plan_semantic_image_reuse


def _shot(shot_id, order, sentence_ids):
    return {
        "shot_id": shot_id,
        "order": order,
        "chapter": 1,
        "sentence_spans": [
            {"sentence_id": sentence_id} for sentence_id in sentence_ids
        ],
    }


def test_reuse_planner_auto_reuses_only_exact_sentence_groups():
    source_timing = {
        "shots": [
            _shot("OLD-1", 1, ["S1", "S2"]),
            _shot("OLD-2", 2, ["S3"]),
        ]
    }
    target_timing = {
        "shots": [
            _shot("NEW-1", 1, ["S1", "S2"]),
            _shot("NEW-2", 2, ["S2", "S3"]),
            _shot("NEW-3", 3, ["S3", "V6-N1"]),
        ]
    }
    source_briefs = {
        "briefs": [
            {
                "shot_id": "OLD-1",
                "narration_digest": "첫 장면",
                "visual_mode": "historical_reconstruction",
                "semantic_anchors": ["royal hall", "king", "ministers"],
            },
            {
                "shot_id": "OLD-2",
                "narration_digest": "둘째 장면",
                "visual_mode": "evidence_artifact",
                "semantic_anchors": ["sealed case", "archive shelf", "empty tray"],
            },
        ]
    }
    source_assets = {
        "assets": [
            {
                "shot_id": "OLD-1",
                "status": "COMPLETED",
                "file_path": "OLD-1.jpg",
                "sha256": "A" * 64,
            },
            {
                "shot_id": "OLD-2",
                "status": "COMPLETED",
                "file_path": "OLD-2.jpg",
                "sha256": "B" * 64,
            },
        ]
    }

    result = plan_semantic_image_reuse(
        source_timing,
        target_timing,
        source_briefs,
        source_assets,
        base_sentence_ids={"S1", "S2", "S3"},
    )
    by_id = {row["target_shot_id"]: row for row in result["decisions"]}

    assert by_id["NEW-1"]["decision"] == "auto_reuse"
    assert by_id["NEW-1"]["source_shot_id"] == "OLD-1"
    assert by_id["NEW-1"]["match_basis"] == "exact_sentence_group"
    assert by_id["NEW-2"]["decision"] == "review_candidate"
    assert by_id["NEW-3"]["decision"] == "generate_new"
    assert result["summary"] == {
        "auto_reuse": 1,
        "review_candidate": 1,
        "generate_new": 1,
    }


def test_reuse_planner_rejects_exact_match_without_completed_asset():
    source_timing = {"shots": [_shot("OLD", 1, ["S1"])]}
    target_timing = {"shots": [_shot("NEW", 1, ["S1"])]}
    briefs = {"briefs": [{"shot_id": "OLD", "narration_digest": "장면"}]}
    assets = {
        "assets": [
            {
                "shot_id": "OLD",
                "status": "SUBMITTED",
                "file_path": "",
                "sha256": "",
            }
        ]
    }

    result = plan_semantic_image_reuse(
        source_timing,
        target_timing,
        briefs,
        assets,
        base_sentence_ids={"S1"},
    )

    assert result["decisions"][0]["decision"] == "generate_new"
    assert result["decisions"][0]["reason"] == "exact_match_asset_unavailable"


def test_reuse_planner_rejects_exact_match_when_host_mode_changes():
    source_timing = {"shots": [_shot("OLD", 1, ["S1"])]}
    target_timing = {"shots": [_shot("NEW", 1, ["S1"])]}
    briefs = {
        "briefs": [
            {
                "shot_id": "OLD",
                "narration_digest": "장면",
                "visual_mode": "historical_reconstruction",
            }
        ]
    }
    assets = {
        "assets": [
            {
                "shot_id": "OLD",
                "status": "COMPLETED",
                "file_path": "OLD.jpg",
                "sha256": "A" * 64,
            }
        ]
    }

    result = plan_semantic_image_reuse(
        source_timing,
        target_timing,
        briefs,
        assets,
        base_sentence_ids={"S1"},
        target_host_shot_ids={"NEW"},
    )

    assert result["decisions"][0]["decision"] == "generate_new"
    assert result["decisions"][0]["reason"] == "visual_mode_host_mismatch"


def test_reuse_planner_demotes_request_mode_or_role_mismatches():
    source_timing = {
        "shots": [
            _shot("OLD-EXACT", 1, ["S1"]),
            _shot("OLD-PARTIAL", 2, ["S2", "S3"]),
        ]
    }
    target_timing = {
        "shots": [
            _shot("NEW-EXACT", 1, ["S1"]),
            _shot("NEW-PARTIAL", 2, ["S2"]),
        ]
    }
    source_briefs = {
        "briefs": [
            {
                "shot_id": "OLD-EXACT",
                "visual_mode": "historical_reconstruction",
            },
            {
                "shot_id": "OLD-PARTIAL",
                "visual_mode": "evidence_artifact",
            },
        ]
    }
    source_assets = {
        "assets": [
            {
                "shot_id": "OLD-EXACT",
                "status": "COMPLETED",
                "file_path": "OLD-EXACT.jpg",
                "sha256": "A" * 64,
            },
            {
                "shot_id": "OLD-PARTIAL",
                "status": "COMPLETED",
                "file_path": "OLD-PARTIAL.jpg",
                "sha256": "B" * 64,
            },
        ]
    }
    source_requests = {
        "requests": [
            {
                "scene_id": "OLD-EXACT",
                "visual_mode": "historical_reconstruction",
                "visual_role": "historical_reconstruction",
            },
            {
                "scene_id": "OLD-PARTIAL",
                "visual_mode": "evidence_artifact",
                "visual_role": "evidence_object",
            },
        ]
    }
    target_requests = {
        "requests": [
            {
                "scene_id": "NEW-EXACT",
                "visual_mode": "evidence_artifact",
                "visual_role": "evidence_object",
            },
            {
                "scene_id": "NEW-PARTIAL",
                "visual_mode": "evidence_artifact",
                "visual_role": "historical_reconstruction",
            },
        ]
    }

    result = plan_semantic_image_reuse(
        source_timing,
        target_timing,
        source_briefs,
        source_assets,
        base_sentence_ids={"S1", "S2", "S3"},
        source_request_manifest=source_requests,
        target_request_manifest=target_requests,
    )
    by_id = {row["target_shot_id"]: row for row in result["decisions"]}

    assert by_id["NEW-EXACT"]["decision"] == "generate_new"
    assert by_id["NEW-EXACT"]["reason"] == "source_target_visual_mode_mismatch"
    assert by_id["NEW-PARTIAL"]["decision"] == "generate_new"
    assert by_id["NEW-PARTIAL"]["reason"] == "source_target_visual_role_mismatch"
    assert result["summary"] == {
        "auto_reuse": 0,
        "review_candidate": 0,
        "generate_new": 2,
    }
