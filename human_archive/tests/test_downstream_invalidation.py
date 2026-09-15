from __future__ import annotations

from lib.downstream_invalidation import (
    build_script_revision_invalidation_report,
    invalidate_downstream_artifacts,
)


def _shot(shot_id: str, text: str) -> dict[str, str]:
    return {"shot_id": shot_id, "display_text": text, "tts_text": text}


def test_report_identifies_only_revised_shots_and_all_downstream_stages() -> None:
    before = [_shot("S1", "원문"), _shot("S2", "그대로")]
    after = [_shot("S1", "팩트체크 수정문"), _shot("S2", "그대로")]

    report = build_script_revision_invalidation_report(before, after)

    assert report["changed_shot_ids"] == ["S1"]
    assert report["downstream_stages"] == [
        "sentence_audio",
        "shot_timing",
        "visual_brief",
        "image_request",
        "asset_manifest",
        "render",
    ]
    assert len(report["revision_sha256"]) == 64
    assert len(report["previous_revision_sha256"]) == 64


def test_invalidation_blocks_matching_rows_and_preserves_unaffected_rows() -> None:
    artifacts = {
        "sentence_audio": [
            {"shot_id": "S1", "status": "COMPLETED"},
            {"shot_id": "S2", "status": "COMPLETED"},
        ],
        "asset_manifest": [{"shot_id": "S1", "status": "COMPLETED"}],
    }

    updated = invalidate_downstream_artifacts(artifacts, ["S1"], reason="script_revision")

    assert updated["sentence_audio"][0]["status"] == "BLOCKED"
    assert updated["sentence_audio"][0]["stale"] is True
    assert updated["sentence_audio"][0]["previous_status"] == "COMPLETED"
    assert updated["sentence_audio"][0]["stale_reason"] == "script_revision"
    assert updated["sentence_audio"][1] == artifacts["sentence_audio"][1]
    assert updated["asset_manifest"][0]["status"] == "BLOCKED"
    assert artifacts["asset_manifest"][0]["status"] == "COMPLETED"


def test_revised_shot_detection_handles_tts_only_changes() -> None:
    report = build_script_revision_invalidation_report(
        [_shot("S1", "화면 문장")],
        [{"shot_id": "S1", "display_text": "화면 문장", "tts_text": "발화 문장"}],
    )
    assert report["changed_shot_ids"] == ["S1"]

