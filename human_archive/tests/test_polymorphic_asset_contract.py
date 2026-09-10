from __future__ import annotations

import pytest

from lib.asset_contract import validate_asset_record


def _base(asset_type: str) -> dict[str, object]:
    return {
        "asset_id": "SHOT_001",
        "shot_id": "SHOT_001",
        "asset_type": asset_type,
        "file_path": "SHOT_001.jpg",
        "sha256": "A" * 64,
        "bytes": 12_345,
        "status": "COMPLETED",
    }


def test_flow_image_requires_dimensions() -> None:
    record = _base("FLOW_IMAGE") | {"width": 1920, "height": 1080}
    assert validate_asset_record(record) == record


@pytest.mark.parametrize("asset_type", ["BARETIP_VIDEO", "HYPERFRAMES_VIDEO"])
def test_video_variants_require_duration_and_fps(asset_type: str) -> None:
    record = _base(asset_type) | {
        "file_path": "SHOT_001.mp4",
        "duration_sec": 8.5,
        "fps": 25,
    }
    assert validate_asset_record(record) == record


def test_unknown_asset_type_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unknown asset_type"):
        validate_asset_record(_base("UNKNOWN"))


def test_video_cannot_claim_image_extension() -> None:
    with pytest.raises(ValueError, match="video file"):
        validate_asset_record(_base("BARETIP_VIDEO") | {"duration_sec": 8.0, "fps": 25})


def test_asset_sha_must_be_hex() -> None:
    with pytest.raises(ValueError, match="hexadecimal"):
        validate_asset_record(_base("FLOW_IMAGE") | {"width": 1920, "height": 1080, "sha256": "Z" * 64})


@pytest.mark.parametrize("order,scene_role", [(1, "standard"), (2, "opening_group"), (1, "opening_group")])
def test_opening_strictly_disallows_baretip(order: int, scene_role: str) -> None:
    record = _base("BARETIP_VIDEO") | {
        "order": order,
        "scene_role": scene_role,
        "duration_sec": 8.0,
        "fps": 25,
        "file_path": "SHOT_001.mp4",
    }
    with pytest.raises(ValueError, match="BARETIP_VIDEO is strictly disallowed in opening"):
        validate_asset_record(record)


@pytest.mark.parametrize("visual_role", ["context_wide", "subject_action", "evidence_detail"])
def test_opening_group_accepts_valid_visual_roles(visual_role: str) -> None:
    record = _base("FLOW_IMAGE") | {
        "order": 1,
        "scene_role": "opening_group",
        "visual_role": visual_role,
        "width": 1920,
        "height": 1080,
    }
    validated = validate_asset_record(record)
    assert validated["visual_role"] == visual_role
    assert validated["scene_role"] == "opening_group"


def test_opening_group_rejects_invalid_visual_role() -> None:
    record = _base("FLOW_IMAGE") | {
        "order": 1,
        "scene_role": "opening_group",
        "visual_role": "invalid_role_name",
        "width": 1920,
        "height": 1080,
    }
    with pytest.raises(ValueError, match="Invalid visual_role for opening_group"):
        validate_asset_record(record)

