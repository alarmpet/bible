"""Polymorphic media asset contract for NOLLAM shot manifests."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

ASSET_TYPES = {"FLOW_IMAGE", "BARETIP_VIDEO", "HYPERFRAMES_VIDEO"}
VIDEO_TYPES = {"BARETIP_VIDEO", "HYPERFRAMES_VIDEO"}
OPENING_SCENE_ROLES = {"opening_group"}
OPENING_DISALLOWED_ASSET_TYPES = {"BARETIP_VIDEO"}
OPENING_VISUAL_ROLES = {"context_wide", "subject_action", "evidence_detail"}


def validate_asset_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return one asset record without coercing its provenance."""
    asset_type = str(record.get("asset_type", ""))
    if asset_type not in ASSET_TYPES:
        raise ValueError(f"Unknown asset_type: {asset_type}")
    for key in ("asset_id", "shot_id", "file_path", "sha256", "status"):
        if not str(record.get(key, "")).strip():
            raise ValueError(f"Asset field is required: {key}")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", str(record["sha256"])):
        raise ValueError("Asset sha256 must be 64 hexadecimal characters")
    if int(record.get("bytes", 0)) <= 0:
        raise ValueError("Asset bytes must be positive")

    order = record.get("order")
    scene_role = record.get("scene_role")
    is_opening = (order == 1) or (scene_role in OPENING_SCENE_ROLES)
    if is_opening and asset_type in OPENING_DISALLOWED_ASSET_TYPES:
        raise ValueError(
            f"BARETIP_VIDEO is strictly disallowed in opening (order={order}, scene_role={scene_role}). "
            "Gate 8 requires visible FLOW_IMAGE."
        )

    if scene_role in OPENING_SCENE_ROLES:
        if asset_type != "FLOW_IMAGE":
            raise ValueError(f"opening_group requires FLOW_IMAGE, got {asset_type}")
        visual_role = record.get("visual_role")
        if visual_role is not None and visual_role not in OPENING_VISUAL_ROLES:
            raise ValueError(
                f"Invalid visual_role for opening_group: {visual_role}. "
                f"Must be one of {sorted(OPENING_VISUAL_ROLES)}"
            )

    path = str(record["file_path"]).lower()
    if asset_type == "FLOW_IMAGE":
        if not path.endswith((".jpg", ".jpeg", ".png", ".webp")):
            raise ValueError("FLOW_IMAGE requires an image file")
        if int(record.get("width", 0)) <= 0 or int(record.get("height", 0)) <= 0:
            raise ValueError("FLOW_IMAGE requires positive width and height")
    elif asset_type in VIDEO_TYPES:
        if not path.endswith((".mp4", ".webm", ".mov")):
            raise ValueError(f"{asset_type} requires a video file")
        if float(record.get("duration_sec", 0.0)) <= 0:
            raise ValueError(f"{asset_type} requires positive duration_sec")
        if float(record.get("fps", 0.0)) <= 0:
            raise ValueError(f"{asset_type} requires positive fps")
    return dict(record)


def evaluate_frame_visibility_gate(image_bgr: Any) -> dict[str, Any]:
    """Gate 8: Multi-dimensional first-frame visibility verification with special scene defenses."""
    import cv2
    import numpy as np

    if image_bgr is None or not isinstance(image_bgr, np.ndarray) or image_bgr.size == 0:
        raise ValueError("Invalid image array for visibility gate")

    h, w = image_bgr.shape[:2]
    total_pixels = float(h * w)

    # 1. Histogram & environment detection (Low-Key / High-Key)
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    mean_val = float(np.mean(gray))

    is_extreme_low_key = mean_val < 35.0   # Cave / Night scene
    is_extreme_high_key = mean_val > 220.0 # Snow / Blizzard scene

    # 2. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced_gray = clahe.apply(gray)

    # 3. Adaptive Canny Edge Detection
    med = float(np.median(enhanced_gray))
    t_low = int(max(15, (1.0 - 0.4) * med))
    t_high = int(min(220, (1.0 + 0.4) * med))
    edges = cv2.Canny(enhanced_gray, t_low, t_high)
    edge_density = float(np.count_nonzero(edges)) / total_pixels

    # 4. Lab luminance local variance for non-background coverage
    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
    l_chan = lab[:, :, 0].astype(np.float32)
    blur_l = cv2.GaussianBlur(l_chan, (5, 5), 0)
    local_var = cv2.GaussianBlur(l_chan**2, (5, 5), 0) - blur_l**2

    # Solid whiteboard canvas has local_var < 3.0; natural scenes have local_var >= 6.0
    info_mask = (local_var >= 6.0) | (edges > 0)
    non_bg_coverage = float(np.count_nonzero(info_mask)) / total_pixels

    # 5. Connected Component Saliency Clustering for Focal Bounding Box
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    dilated = cv2.dilate(edges, kernel, iterations=2)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    max_bbox_ratio = 0.0
    if contours:
        largest_c = max(contours, key=cv2.contourArea)
        bx, by, bw, bh = cv2.boundingRect(largest_c)
        max_bbox_ratio = float(bw * bh) / total_pixels

    # 6. Environmental threshold adjustment
    min_edge_density = 0.020 if (is_extreme_low_key or is_extreme_high_key) else 0.035
    min_coverage = 0.10 if is_extreme_low_key else 0.15
    min_bbox = 0.08

    passed = (
        edge_density >= min_edge_density and
        non_bg_coverage >= min_coverage and
        max_bbox_ratio >= min_bbox
    )

    return {
        "passed": bool(passed),
        "edge_density": round(edge_density, 4),
        "non_bg_coverage": round(non_bg_coverage, 4),
        "focal_bbox_ratio": round(max_bbox_ratio, 4),
        "environment": "low_key" if is_extreme_low_key else ("high_key" if is_extreme_high_key else "standard")
    }


def evaluate_frame_visibility_from_file(file_path: str | Path, scene_role: str = "opening_group") -> dict[str, Any]:
    """Load image from disk and evaluate Gate 8 visibility."""
    import cv2
    from pathlib import Path

    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {file_path}")
    img = cv2.imread(str(p))
    if img is None:
        raise ValueError(f"Failed to decode image: {file_path}")
    res = evaluate_frame_visibility_gate(img)
    res["scene_role"] = scene_role
    return res

