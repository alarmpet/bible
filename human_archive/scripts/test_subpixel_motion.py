# -*- coding: utf-8 -*-
"""Test subpixel bicubic affine motion generation with PIL to eliminate 1-pixel FFmpeg crop jitter."""
import math
import subprocess
import sys
import time
from pathlib import Path
from PIL import Image

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def render_subpixel_motion_clip(
    img_path: Path,
    out_clip: Path,
    duration_sec: float = 5.0,
    fps: int = 25,
    motion_type: str = "kenburns_zoom_pan_in",
):
    out_clip.parent.mkdir(parents=True, exist_ok=True)
    total_frames = max(1, int(round(duration_sec * fps)))

    with Image.open(img_path) as src_im:
        src_rgb = src_im.convert("RGB")
        orig_w, orig_h = src_rgb.size
        # Ensure we have a high-res base
        if orig_w != 1920 or orig_h != 1080:
            src_rgb = src_rgb.resize((1920, 1080), Image.Resampling.LANCZOS)
            orig_w, orig_h = 1920, 1080

    # We will pipe raw RGB24 frames to FFmpeg
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", "1920x1080",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-color_range", "tv",
        str(out_clip),
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

    # Subpixel transformation parameters
    # Subtle zoom 1.00 -> 1.04, subtle pan (15 pixels total across 5-25 seconds)
    zoom_start = 1.00
    zoom_end = 1.04

    for frame_idx in range(total_frames):
        t = frame_idx / max(1, total_frames - 1)
        # Cosine smooth easing: 0.0 -> 1.0 with smooth acceleration and deceleration
        ease = (1.0 - math.cos(math.pi * t)) / 2.0

        current_zoom = zoom_start + (zoom_end - zoom_start) * ease

        # Calculate exact floating-point crop box
        crop_w = orig_w / current_zoom
        crop_h = orig_h / current_zoom

        # Subtle pan drift in floating point
        max_dx = orig_w - crop_w
        max_dy = orig_h - crop_h

        if motion_type in ["kenburns_zoom_pan_in", "pan_right"]:
            crop_x = max_dx * (0.3 + 0.4 * ease)
            crop_y = max_dy * (0.3 + 0.4 * ease)
        elif motion_type in ["tilt_up"]:
            crop_x = max_dx * 0.5
            crop_y = max_dy * (1.0 - ease)
        elif motion_type in ["tilt_down"]:
            crop_x = max_dx * 0.5
            crop_y = max_dy * ease
        elif motion_type in ["pan_left", "kenburns_zoom_pan_out"]:
            crop_x = max_dx * (0.7 - 0.4 * ease)
            crop_y = max_dy * (0.7 - 0.4 * ease)
        else:
            crop_x = max_dx * 0.5
            crop_y = max_dy * 0.5

        # PIL transform with BICUBIC subpixel floating point resampling
        # Box tuple: (left, upper, right, lower)
        box = (crop_x, crop_y, crop_x + crop_w, crop_y + crop_h)
        frame_img = src_rgb.resize((1920, 1080), resample=Image.Resampling.BICUBIC, box=box)
        proc.stdin.write(frame_img.tobytes())

    proc.stdin.close()
    proc.wait()
    print(f"✅ Rendered subpixel butter-smooth clip: {out_clip} ({total_frames} frames, {duration_sec}s)")


if __name__ == "__main__":
    test_img = Path("human_archive/runs/ep02_jang_huibin/full-v2-001/images/jh_ch1_001.jpg")
    test_out = Path("human_archive/runs/ep02_jang_huibin/full-v2-001/motion_clips/test_subpixel.mp4")
    render_subpixel_motion_clip(test_img, test_out, duration_sec=5.0)
