# -*- coding: utf-8 -*-
"""Render smooth 1080p 25fps square-pixel motion clips using subpixel floating-point Bicubic resampling to eliminate FFmpeg crop jitter."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from PIL import Image
from verify_visual_assets import verify_visual_build

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SHOT_MOTION_MAP = {
    "ch1_001": "kenburns_zoom_pan_in",
    "ch1_002": "pan_right",
    "ch1_003": "kenburns_hero_push",
    "ch1_004": "tilt_up",
    "ch1_005": "kenburns_wide_sweep",
    "ch1_006": "tilt_down",
    "ch1_007": "kenburns_hero_push",
    "ch1_008": "zoom_in",
    "ch1_009": "pan_left",
    "ch1_010": "tilt_up",
    "ch1_011": "kenburns_zoom_pan_out",
    "ch1_012": "kenburns_hero_push",
}


def render_subpixel_clip(
    img_path: Path,
    out_clip: Path,
    duration_sec: float,
    fps: int = 25,
    motion_type: str = "kenburns_zoom_pan_in",
):
    out_clip.parent.mkdir(parents=True, exist_ok=True)
    total_frames = max(1, int(round(duration_sec * fps)))

    with Image.open(img_path) as src_im:
        src_rgb = src_im.convert("RGB")
        orig_w, orig_h = src_rgb.size
        if orig_w != 1920 or orig_h != 1080:
            src_rgb = src_rgb.resize((1920, 1080), Image.Resampling.LANCZOS)
            orig_w, orig_h = 1920, 1080

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

    # Ultra-smooth subtle zoom (1.00 -> 1.035) with smooth cosine easing
    zoom_start = 1.00
    zoom_end = 1.035

    for frame_idx in range(total_frames):
        t = frame_idx / max(1, total_frames - 1)
        # Cosine smooth easing
        ease = (1.0 - math.cos(math.pi * t)) / 2.0

        current_zoom = zoom_start + (zoom_end - zoom_start) * ease

        crop_w = orig_w / current_zoom
        crop_h = orig_h / current_zoom

        max_dx = orig_w - crop_w
        max_dy = orig_h - crop_h

        if motion_type in ["kenburns_zoom_pan_in", "pan_right", "kenburns_hero_push"]:
            crop_x = max_dx * (0.3 + 0.4 * ease)
            crop_y = max_dy * (0.3 + 0.4 * ease)
        elif motion_type == "tilt_up":
            crop_x = max_dx * 0.5
            crop_y = max_dy * (1.0 - ease)
        elif motion_type == "tilt_down":
            crop_x = max_dx * 0.5
            crop_y = max_dy * ease
        elif motion_type in ["pan_left", "kenburns_zoom_pan_out", "kenburns_wide_sweep"]:
            crop_x = max_dx * (0.7 - 0.4 * ease)
            crop_y = max_dy * (0.7 - 0.4 * ease)
        else:
            crop_x = max_dx * 0.5
            crop_y = max_dy * 0.5

        box = (crop_x, crop_y, crop_x + crop_w, crop_y + crop_h)
        frame_img = src_rgb.resize((1920, 1080), resample=Image.Resampling.BICUBIC, box=box)
        proc.stdin.write(frame_img.tobytes())

    proc.stdin.close()
    proc.wait()


def build_motion_clips(
    build_dir: Path,
    limit: int | None = None,
) -> list[Path]:
    build_dir = Path(build_dir).resolve()
    visual_ok, visual_errors = verify_visual_build(build_dir=build_dir)
    if not visual_ok:
        detail = "; ".join(visual_errors[:5])
        raise SystemExit(f"Visual QA gate failed before motion rendering: {detail}")
    manifest_path = build_dir / "asset_manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = manifest_data.get("assets", [])

    audio_manifest_path = build_dir / "scene_audio_manifest.json"
    audio_durations = {}
    if audio_manifest_path.exists():
        audio_data = json.loads(audio_manifest_path.read_text(encoding="utf-8"))
        st_list = audio_data.get("shots", [])
        total_dur = audio_data.get("total_duration_sec", 0.0)
        for i, st in enumerate(st_list):
            if i + 1 < len(st_list):
                shot_dur = round(st_list[i + 1]["startSeconds"] - st["startSeconds"], 3)
            else:
                shot_dur = round(total_dur - st["startSeconds"], 3)
            audio_durations[st["shot_id"]] = max(0.5, shot_dur)

    images_dir = build_dir / "images"
    clips_dir = build_dir / "motion_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    rendered_clips = []
    fps = 25
    total_assets = len(assets)

    for idx, item in enumerate(assets):
        if limit and idx >= limit:
            break

        shot_id = item["shot_id"]
        img_name = item["file_path"]
        img_path = images_dir / img_name
        out_clip = clips_dir / f"{shot_id}_motion.mp4"

        if not img_path.exists():
            print(f"⚠️ Image missing for {shot_id}, skipping")
            continue

        motion_type = SHOT_MOTION_MAP.get(shot_id, ["kenburns_zoom_pan_in", "pan_right", "tilt_up", "kenburns_hero_push"][idx % 4])
        duration_sec = audio_durations.get(shot_id, 6.0)

        render_subpixel_clip(
            img_path=img_path,
            out_clip=out_clip,
            duration_sec=duration_sec,
            fps=fps,
            motion_type=motion_type,
        )

        rendered_clips.append(out_clip)
        print(f"[{idx + 1:02d}/{total_assets}] 🎬 Rendered Subpixel Ken Burns clip: {out_clip.name} ({duration_sec:.2f}s, effect={motion_type})")

    print(f"\n✅ Rendered {len(rendered_clips)} Subpixel Ken Burns motion clips in {clips_dir}")
    return rendered_clips


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    build_motion_clips(args.build, limit=args.limit)


if __name__ == "__main__":
    main()
