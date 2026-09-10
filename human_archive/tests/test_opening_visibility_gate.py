from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np
import pytest

from lib.asset_contract import (
    evaluate_frame_visibility_gate,
    evaluate_frame_visibility_from_file,
    validate_asset_record,
)


def test_sparse_baretip_frame_fails_visibility_gate() -> None:
    """A sparse bare-tip ivory frame must fail Gate 8 visibility."""
    img = np.full((1080, 1920, 3), (215, 235, 245), dtype=np.uint8)
    cv2.line(img, (500, 400), (700, 450), (20, 20, 20), 2)
    cv2.circle(img, (600, 420), 30, (20, 20, 20), 2)

    result = evaluate_frame_visibility_gate(img)
    assert result["passed"] is False
    assert result["non_bg_coverage"] < 0.15
    assert result["edge_density"] < 0.035


def test_rich_photographic_frame_passes_visibility_gate() -> None:
    """A rich photographic frame with scenery, texture, and subject passes."""
    np.random.seed(42)
    img = np.zeros((1080, 1920, 3), dtype=np.uint8)
    for y in range(1080):
        img[y, :, :] = (int(50 + y * 0.1), int(80 + y * 0.05), int(100 + y * 0.08))
    noise = np.random.randint(-15, 15, img.shape, dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    cv2.rectangle(img, (400, 200), (1200, 750), (220, 190, 150), -1)
    cv2.putText(img, "NEANDERTHAL EVIDENCE", (450, 400), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (20, 20, 20), 4)
    for i in range(10):
        cv2.line(img, (420, 450 + i * 25), (1150, 450 + i * 25), (10, 10, 80), 3)

    result = evaluate_frame_visibility_gate(img)
    assert result["passed"] is True
    assert result["non_bg_coverage"] >= 0.15
    assert result["edge_density"] >= 0.035
    assert result["focal_bbox_ratio"] >= 0.08


def test_extreme_low_key_cave_scene_passes_with_defense() -> None:
    """An extreme low-key scene must adapt and pass if texture and edges exist."""
    np.random.seed(123)
    img = np.random.randint(15, 30, (1080, 1920, 3), dtype=np.uint8)
    cv2.circle(img, (960, 540), 220, (60, 80, 120), -1)
    for r in range(50, 200, 15):
        cv2.circle(img, (960, 540), r, (120, 160, 220), 2)

    result = evaluate_frame_visibility_gate(img)
    assert result["environment"] == "low_key"
    assert result["passed"] is True


def test_extreme_high_key_snow_scene_passes_with_defense() -> None:
    """An extreme high-key snow scene must adapt and pass with local texture variance."""
    np.random.seed(456)
    img = np.random.randint(225, 245, (1080, 1920, 3), dtype=np.uint8)
    cv2.rectangle(img, (300, 300), (1300, 800), (180, 190, 200), -1)
    for y in range(320, 780, 15):
        cv2.line(img, (310, y), (1290, y + 10), (120, 130, 140), 2)

    result = evaluate_frame_visibility_gate(img)
    assert result["environment"] == "high_key"
    assert result["passed"] is True


def test_real_neanderthal_shot001_photo_passes() -> None:
    """Verify real Neanderthal SHOT_001.jpg passes Gate 8 if file exists."""
    target = Path(r"human_archive/runs/nollam_file/2026-09-09/iceage-neanderthal-sapiens-extinction/images/SHOT_001.jpg")
    if target.exists():
        res = evaluate_frame_visibility_from_file(str(target))
        assert res["passed"] is True
        assert res["edge_density"] >= 0.035
        assert res["non_bg_coverage"] >= 0.15


def test_contract_opening_bare_tip_fail_closed() -> None:
    """validate_asset_record strictly rejects BARETIP_VIDEO in opening."""
    record = {
        "asset_id": "SHOT_001",
        "shot_id": "SHOT_001",
        "asset_type": "BARETIP_VIDEO",
        "file_path": "clips/SHOT_001.mp4",
        "sha256": "c" * 64,
        "bytes": 1048576,
        "status": "COMPLETED",
        "order": 1,
        "duration_sec": 11.0,
        "fps": 25.0,
    }
    with pytest.raises(ValueError, match="BARETIP_VIDEO is strictly disallowed in opening"):
        validate_asset_record(record)
