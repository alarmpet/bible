from __future__ import annotations

import pytest

from lib.aligned_prompt_compiler import compile_nollam_prompt
from generate_video_prompts import compile_nollam_docu_prompts


def _brief(**overrides: object) -> dict[str, object]:
    brief: dict[str, object] = {
        "shot_id": "SHOT_004",
        "order": 4,
        "visual_mode": "historical_reconstruction",
        "subject": "네안데르탈인 사냥꾼과 매머드 발자국",
        "action": "눈 덮인 계곡에서 발자국을 추적한다",
        "place": "빙하기 유라시아 툰드라",
        "era": "후기 플라이스토세",
        "visual_claim_ids": ["CLAIM-001"],
    }
    brief.update(overrides)
    return brief


def test_nollam_historical_prompt_has_4_look_rotation_and_safe_zone() -> None:
    request = compile_nollam_prompt(_brief(order=4))

    assert request["look_id"] == "evidence_macro"
    assert request["asset_type"] == "FLOW_IMAGE"
    assert "bottom 18%" in request["submission_prompt"]
    assert "no subtitles" in request["submission_prompt"].lower()
    assert "선비" not in request["submission_prompt"]
    assert "ink-doodle" not in request["submission_prompt"].lower()
    assert len(request["request_sha256"]) == 64


def test_nollam_modern_prompt_keeps_topic_identity_without_legacy_palace_terms() -> None:
    request = compile_nollam_prompt(_brief(
        shot_id="SHOT_008",
        order=7,
        visual_mode="modern_scientific_explainer",
        subject="빙하호 붕괴를 관측하는 수문학 연구팀",
        action="위성 데이터와 현장 수위를 비교한다",
        place="히말라야 계곡의 관측소",
        era="현대",
    ))

    assert request["look_id"] == "data_observatory"
    assert "빙하호 붕괴" in request["positive_prompt"]
    assert "조선" not in request["submission_prompt"]
    assert "궁궐" not in request["submission_prompt"]
    assert request["negative"]["mode"] == "prompt_exclusion"


def test_nollam_prompt_rejects_legacy_seonbi_terms_instead_of_silently_contaminating_request() -> None:
    with pytest.raises(ValueError, match="legacy NOLLAM keyword"):
        compile_nollam_prompt(_brief(subject="선비가 기록을 읽는다"))


def test_nollam_media_modes_map_to_polymorphic_asset_contract() -> None:
    assert compile_nollam_prompt(_brief(visual_mode="bare_tip_hook"))["asset_type"] == "BARETIP_VIDEO"
    assert compile_nollam_prompt(_brief(visual_mode="hyperframes_hud"))["asset_type"] == "HYPERFRAMES_VIDEO"


def test_nollam_batch_entrypoint_binds_each_scene_to_the_canonical_request() -> None:
    compiled = compile_nollam_docu_prompts([
        _brief(shot_id="SHOT_001", order=1, visual_mode="bare_tip_hook"),
        _brief(shot_id="SHOT_002", order=2, visual_mode="historical_reconstruction"),
    ])
    assert [row["shot_id"] for row in compiled] == ["SHOT_001", "SHOT_002"]
    assert compiled[0]["asset_type"] == "BARETIP_VIDEO"
    assert compiled[1]["asset_type"] == "FLOW_IMAGE"
    assert all(row["exact_frames"] > 0 for row in compiled)
