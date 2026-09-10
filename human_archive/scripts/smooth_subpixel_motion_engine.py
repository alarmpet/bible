# -*- coding: utf-8 -*-
"""Smooth Subpixel Motion Engine (Ken Burns Overhaul).

Eliminates 1-pixel stair-step judder and jerky linear movement:
1. Scales source image to a 2304x1296 (120% overscan) canvas using Lanczos.
2. Evaluates Cosine S-curve easing: smooth_t = 0.5 * (1.0 - math.cos(math.pi * t)).
3. Computes continuous floating-point crop boxes without integer quantization.
4. Performs subpixel Bicubic resampling in PIL with box=(left, top, right, bottom).
5. Pipes raw RGB frames into FFmpeg libx264 for artifact-free broadcast delivery.
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path
from typing import Tuple
from PIL import Image


def cosine_easing(t: float) -> float:
    """Compute S-curve ease-in-out using cosine.
    
    t in [0.0, 1.0] -> returns smooth_t in [0.0, 1.0] with zero derivative at endpoints.
    """
    clamped_t = max(0.0, min(1.0, float(t)))
    return 0.5 * (1.0 - math.cos(math.pi * clamped_t))


def compute_trajectory(
    frame: int,
    total_frames: int,
    motion: str = "push_in"
) -> Tuple[float, float, float]:
    """Return continuous floating-point (zoom, center_x, center_y) for the given frame.
    
    All coordinates are normalized in [0.0, 1.0], zoom is >= 1.0.
    """
    if motion in {"biphasic_ken_burns", "biphasic_push_in"}:
        return compute_biphasic_trajectory(frame, total_frames, "push_in")
    if motion in {"layer3_perceptual_cut", "perceptual_cut"}:
        return compute_perceptual_cut_trajectory(frame, total_frames)
    if motion == "static" or total_frames <= 1:
        return 1.0, 0.5, 0.5

    linear_t = max(0.0, min(1.0, frame / float(total_frames - 1)))
    st = cosine_easing(linear_t)

    if motion == "push_in":
        zoom = 1.0 + 0.12 * st
        return zoom, 0.5, 0.5
    elif motion == "pull_out":
        zoom = 1.12 - 0.12 * st
        return zoom, 0.5, 0.5
    elif motion == "pan_left":
        zoom = 1.08
        x = 0.65 - 0.30 * st
        return zoom, x, 0.5
    elif motion == "pan_right":
        zoom = 1.08
        x = 0.35 + 0.30 * st
        return zoom, x, 0.5
    elif motion == "tilt_up":
        zoom = 1.08
        y = 0.65 - 0.30 * st
        return zoom, 0.5, y
    elif motion == "tilt_down":
        zoom = 1.08
        y = 0.35 + 0.30 * st
        return zoom, 0.5, y
    else:
        zoom = 1.0 + 0.08 * st
        return zoom, 0.5, 0.5


def compute_biphasic_trajectory(
    frame: int,
    total_frames: int,
    motion: str = "push_in",
    phase_ratio: float = 0.5,
) -> Tuple[float, float, float]:
    """Return a two-stage trajectory: ambient composition, then focal push-in.

    Stage one preserves spatial context with the requested movement.  Stage
    two settles at the visual center and gradually increases scale, making a
    long narration shot feel alive without introducing a hard cut.
    """
    if total_frames <= 1:
        return 1.0, 0.5, 0.5
    ratio = max(0.2, min(0.8, float(phase_ratio)))
    normalized = max(0.0, min(1.0, frame / float(total_frames - 1)))
    if normalized <= ratio:
        local_t = normalized / ratio
        eased = cosine_easing(local_t)
        if motion == "pan_left":
            return 1.04, 0.65 - 0.15 * eased, 0.5
        if motion == "pan_right":
            return 1.04, 0.35 + 0.15 * eased, 0.5
        if motion == "tilt_up":
            return 1.04, 0.5, 0.65 - 0.15 * eased
        if motion == "tilt_down":
            return 1.04, 0.5, 0.35 + 0.15 * eased
        return 1.0 + 0.04 * eased, 0.5, 0.5

    local_t = (normalized - ratio) / (1.0 - ratio)
    eased = cosine_easing(local_t)
    return 1.04 + 0.12 * eased, 0.5, 0.5


def compute_perceptual_cut_trajectory(
    frame: int,
    total_frames: int,
    fps: int = 25,
    cut_time_sec: float = 5.0,
) -> Tuple[float, float, float]:
    """Layer 3 Perceptual Cut trajectory: wide master before 5.0s, jump-cut close-up at 5.0s."""
    cut_frame = int(round(cut_time_sec * fps))
    if total_frames <= cut_frame:
        linear_t = max(0.0, min(1.0, frame / float(max(1, total_frames - 1))))
        return 1.0 + 0.10 * cosine_easing(linear_t), 0.5, 0.5

    if frame < cut_frame:
        local_t = frame / float(cut_frame)
        st = cosine_easing(local_t)
        return 1.02 + 0.04 * st, 0.5, 0.5
    else:
        rem_frames = total_frames - cut_frame
        local_t = (frame - cut_frame) / float(max(1, rem_frames - 1))
        st = cosine_easing(local_t)
        return 1.18 + 0.05 * st, 0.5, 0.45


def compute_crop_box(
    canvas_w: float,
    canvas_h: float,
    target_w: float,
    target_h: float,
    zoom: float,
    norm_x: float,
    norm_y: float
) -> Tuple[float, float, float, float]:
    """Calculate subpixel crop box (left, top, right, bottom) as floating-point floats."""
    crop_w = target_w / zoom
    crop_h = target_h / zoom
    left = (canvas_w - crop_w) * norm_x
    top = (canvas_h - crop_h) * norm_y
    right = left + crop_w
    bottom = top + crop_h
    return left, top, right, bottom


def prepare_overscan_canvas(
    image_path: Path,
    canvas_w: int = 2304,
    canvas_h: int = 1296
) -> Image.Image:
    """Load and center image onto overscan canvas using high quality Lanczos filter."""
    with Image.open(image_path) as img:
        src = img.convert("RGB")
        # Resize to fit inside or fill overscan canvas maintaining aspect ratio
        src_aspect = src.width / src.height
        canvas_aspect = canvas_w / canvas_h
        
        if abs(src_aspect - canvas_aspect) < 1e-3:
            scaled = src.resize((canvas_w, canvas_h), Image.Resampling.LANCZOS)
            return scaled
        else:
            # Aspect fill
            if src_aspect > canvas_aspect:
                new_h = canvas_h
                new_w = int(round(canvas_h * src_aspect))
            else:
                new_w = canvas_w
                new_h = int(round(canvas_w / src_aspect))
            scaled = src.resize((new_w, new_h), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
            offset_x = (canvas_w - new_w) // 2
            offset_y = (canvas_h - new_h) // 2
            canvas.paste(scaled, (offset_x, offset_y))
            return canvas


def render_smooth_motion_clip(
    image_path: Path,
    output_path: Path,
    duration: float,
    motion: str = "push_in",
    fps: int = 25,
    width: int = 1920,
    height: int = 1080
) -> Path:
    """Render an ultra-smooth subpixel Ken Burns video clip with zero pixel judder."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames = max(1, round(duration * fps))

    canvas_w = int(round(width * 1.2))
    canvas_h = int(round(height * 1.2))
    canvas = prepare_overscan_canvas(image_path, canvas_w=canvas_w, canvas_h=canvas_h)

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-color_range", "tv",
        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        str(output_path)
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None

    for f in range(frames):
        zoom, norm_x, norm_y = compute_trajectory(f, frames, motion)
        left, top, right, bottom = compute_crop_box(
            canvas_w=float(canvas_w),
            canvas_h=float(canvas_h),
            target_w=float(width),
            target_h=float(height),
            zoom=zoom,
            norm_x=norm_x,
            norm_y=norm_y
        )
        rendered = canvas.resize(
            (width, height),
            resample=Image.Resampling.BICUBIC,
            box=(left, top, right, bottom)
        )
        proc.stdin.write(rendered.tobytes())

    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"FFmpeg failed while rendering smooth clip for {image_path}")

    return output_path
