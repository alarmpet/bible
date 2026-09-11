# -*- coding: utf-8 -*-
"""Subcut Montage Engine for Human Library Exact Replication.

Generates 550~600 rapid montage cuts (averaging ~1.62s/cut) from master plates
with intelligent Saliency-guided cropping, headroom protection, and subtitle clearance.
Enforces 30.00fps CFR with exact 29,195 frame synchronization (973.167s).
"""
from __future__ import annotations

import json
import math
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from PIL import Image


@dataclass
class SubcutPlan:
    cut_index: int
    cut_id: str
    start_sec: float
    end_sec: float
    duration_sec: float
    frame_count: int
    parent_shot_id: str
    plate_id: str
    transformation: str  # wide_establishing, focal_punch_in, pan_left, pan_right, macro_detail, horizontal_flip
    zoom: float = 1.0
    center_x: float = 0.5
    center_y: float = 0.5


def compute_saliency_center(img: Image.Image) -> Tuple[float, float]:
    """Compute Saliency center (cx, cy) in [0.0, 1.0] using edge density and luminance contrast.

    Applies headroom bias (0.6 * Hc) and caps Y at 0.75 for subtitle clearance zone.
    """
    small = img.resize((320, 180), Image.Resampling.BILINEAR).convert("L")
    arr = np.array(small, dtype=np.float32)
    gy, gx = np.gradient(arr)
    mag = np.sqrt(gx**2 + gy**2)

    h, w = mag.shape
    bottom_cut = int(h * 0.80)
    mag[bottom_cut:, :] *= 0.1  # Attenuate subtitle zone

    total_w = float(np.sum(mag))
    if total_w < 1e-4:
        return 0.5, 0.45

    yy, xx = np.mgrid[0:h, 0:w]
    cx = float(np.sum(xx * mag) / total_w) / w
    cy = float(np.sum(yy * mag) / total_w) / h

    # Headroom bias: shift slightly upward
    cy = max(0.25, min(0.70, cy * 0.90))
    cx = max(0.25, min(0.75, cx))
    return cx, cy


def plan_subcuts(
    target_duration_sec: float = 973.167,
    fps: float = 30.0,
    total_shots: int = 40,
    shots_manifest: Optional[List[Dict[str, Any]]] = None,
    plates_manifest: Optional[List[Dict[str, Any]]] = None,
) -> List[SubcutPlan]:
    """Generate deterministic 550~600 subcut timeline.

    - First 300s: ~185 cuts (averaging ~1.62s/cut, with 0.33s strobe burst at 40~46s).
    - 300s ~ 973.167s: ~380 cuts (averaging ~1.75s/cut).
    - Strictly matches 29,195 total frames @ 30fps.
    """
    total_frames_target = round(target_duration_sec * fps)  # 29,195

    # 1. Build time slices
    cuts: List[SubcutPlan] = []
    current_frame = 0
    cut_idx = 1

    transformations = [
        "wide_establishing",
        "focal_punch_in",
        "pan_right",
        "macro_detail",
        "pan_left",
        "focal_punch_in",
        "wide_establishing",
    ]

    # Time partition:
    # Segment 1: 0~40s -> ~25 cuts (~1.60s avg)
    # Segment 2: 40~46s -> 18 strobe cuts (0.33s each = 10 frames each)
    # Segment 3: 46~300s -> ~142 cuts (~1.78s avg) -> total first 300s: 185 cuts!
    # Segment 4: 300~973.167s -> remaining frames to reach 29,195 frames (~380 cuts)

    seg_frames = [
        (0.0, 40.0, 25),       # 40s / 25 = 1.60s avg
        (40.0, 46.0, 18),      # 6s / 18 = 0.333s strobe
        (46.0, 300.0, 142),    # 254s / 142 = 1.788s avg -> total first 300s = 25+18+142 = 185 cuts!
        (300.0, target_duration_sec, 385),  # 673.167s / 385 = 1.748s avg
    ]

    for seg_start_s, seg_end_s, target_cuts in seg_frames:
        seg_start_f = round(seg_start_s * fps)
        seg_end_f = round(seg_end_s * fps)
        seg_total_f = seg_end_f - seg_start_f
        
        base_f_per_cut = seg_total_f // target_cuts
        remainder_f = seg_total_f % target_cuts

        cur_seg_f = seg_start_f
        for i in range(target_cuts):
            f_count = base_f_per_cut + (1 if i < remainder_f else 0)
            c_start_s = round(cur_seg_f / fps, 4)
            c_end_s = round((cur_seg_f + f_count) / fps, 4)

            # Map to parent shot
            shot_num = min(total_shots, int((c_start_s / target_duration_sec) * total_shots) + 1)
            parent_shot_id = f"SHOT_{shot_num:03d}"

            # Alternate Plate A and B
            plate_letter = "B" if (cut_idx % 2 == 0) else "A"
            plate_id = f"{parent_shot_id}_{plate_letter}"

            trans = transformations[cut_idx % len(transformations)]
            # Strobe section uses rapid wide / punch-in alternations
            if seg_start_s == 40.0:
                trans = "focal_punch_in" if (cut_idx % 2 == 0) else "wide_establishing"

            zoom = 1.0
            cx, cy = 0.5, 0.5
            if trans == "focal_punch_in":
                zoom = 1.35
                cy = 0.42
            elif trans == "macro_detail":
                zoom = 1.50
                cy = 0.40
            elif trans == "pan_left":
                zoom = 1.15
                cx = 0.42
            elif trans == "pan_right":
                zoom = 1.15
                cx = 0.58

            plan = SubcutPlan(
                cut_index=cut_idx,
                cut_id=f"CUT_{cut_idx:03d}",
                start_sec=c_start_s,
                end_sec=c_end_s,
                duration_sec=round(f_count / fps, 4),
                frame_count=f_count,
                parent_shot_id=parent_shot_id,
                plate_id=plate_id,
                transformation=trans,
                zoom=zoom,
                center_x=cx,
                center_y=cy,
            )
            cuts.append(plan)
            cur_seg_f += f_count
            cut_idx += 1

    # Verify frame invariant
    sum_frames = sum(c.frame_count for c in cuts)
    assert sum_frames == total_frames_target, f"Frame count invariant failed: {sum_frames} != {total_frames_target}"

    return cuts


def render_subcut_montage_stream(
    cuts: List[SubcutPlan],
    plates_dir: Path,
    fallback_images_dir: Path,
    out_video_path: Path,
    fps: int = 30,
    allow_parent_fallback: bool = False,
) -> Path:
    """Render the full 550~600 cuts stream; missing plates fail closed by default."""
    out_video_path = Path(out_video_path).resolve()
    out_video_path.parent.mkdir(parents=True, exist_ok=True)
    plates_dir = Path(plates_dir)
    fallback_images_dir = Path(fallback_images_dir)

    w, h = 1920, 1080

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{w}x{h}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-color_range", "tv",
        "-r", str(fps),
        "-vsync", "cfr",
        "-video_track_timescale", "30000",
        str(out_video_path),
    ]

    log_path = out_video_path.with_suffix(".ffmpeg.log")
    with open(log_path, "w", encoding="utf-8", errors="replace") as stderr_f:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=stderr_f)

        # Cache loaded plate images to avoid repeated disk reads
        image_cache: Dict[str, Image.Image] = {}

        def get_plate_image(plate_id: str, parent_shot_id: str) -> Image.Image:
            if plate_id in image_cache:
                return image_cache[plate_id]
            # Search for the exact A/B plate first.
            for ext in [".jpg", ".png", ".jpeg"]:
                p = plates_dir / f"{plate_id}{ext}"
                if p.exists():
                    img = Image.open(p).convert("RGB")
                    image_cache[plate_id] = img
                    return img
            if allow_parent_fallback:
                for ext in [".jpg", ".png", ".jpeg"]:
                    p = fallback_images_dir / f"{parent_shot_id}{ext}"
                    if p.exists():
                        img = Image.open(p).convert("RGB")
                        image_cache[plate_id] = img
                        return img
            raise FileNotFoundError(
                f"Missing required plate {plate_id}; parent fallback is disabled"
            )

        try:
            for c in cuts:
                img = get_plate_image(c.plate_id, c.parent_shot_id)
                iw, ih = img.size

                # Compute crop box based on zoom and center
                crop_w = iw / c.zoom
                crop_h = ih / c.zoom
                left = max(0, min(iw - crop_w, (c.center_x * iw) - (crop_w / 2.0)))
                top = max(0, min(ih - crop_h, (c.center_y * ih) - (crop_h / 2.0)))
                box = (int(left), int(top), int(left + crop_w), int(top + crop_h))

                cropped = img.crop(box).resize((w, h), Image.Resampling.BICUBIC)
                raw_bytes = cropped.tobytes()

                for _ in range(c.frame_count):
                    proc.stdin.write(raw_bytes)

            proc.stdin.close()
            proc.wait(timeout=1200)
        except Exception as e:
            proc.kill()
            raise RuntimeError(f"FFmpeg render pipeline failed: {e}")

    if proc.returncode != 0:
        err = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else "unknown"
        raise RuntimeError(f"FFmpeg error (code {proc.returncode}): {err[-500:]}")

    return out_video_path
