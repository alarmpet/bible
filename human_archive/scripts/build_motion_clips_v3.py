# -*- coding: utf-8 -*-
"""Render overscanned, frame-exact motion clips for pilot builds."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
import sys
from PIL import Image

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from lib.motion_engine_v3 import trajectory


def render_clip(image_path: Path, output: Path, duration: float, motion: str = "push_in", fps: int = 25) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    frames = max(1, round(duration * fps))
    with Image.open(image_path) as image:
        src = image.convert("RGB")
        src.thumbnail((2304, 1296), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (2304, 1296), (0, 0, 0))
        canvas.paste(src, ((2304 - src.width) // 2, (1296 - src.height) // 2))
    proc = subprocess.Popen(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", str(output)], stdin=subprocess.PIPE)
    assert proc.stdin is not None
    for frame in range(frames):
        zoom, x, y = trajectory(frame, frames, motion)
        crop_w, crop_h = 1920 / zoom, 1080 / zoom
        left = (2304 - crop_w) * x
        top = (1296 - crop_h) * y
        rendered = canvas.resize((1920, 1080), Image.Resampling.BICUBIC, (left, top, left + crop_w, top + crop_h))
        proc.stdin.write(rendered.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {image_path}")
    return output


def build_pilot(build_dir: Path, output_dir: Path, limit: int = 3) -> list[Path]:
    manifest = json.loads((build_dir / "asset_manifest.json").read_text(encoding="utf-8"))
    audio = json.loads((build_dir / "scene_audio_manifest.json").read_text(encoding="utf-8"))
    starts = {item["shot_id"]: item["startSeconds"] for item in audio.get("shots", [])}
    total = float(audio.get("total_duration_sec", 0.0))
    assets = manifest.get("assets", [])[:limit]
    results = []
    for idx, asset in enumerate(assets):
        sid = asset["shot_id"]
        next_start = total
        if idx + 1 < len(manifest.get("assets", [])):
            next_id = manifest["assets"][idx + 1]["shot_id"]
            next_start = starts.get(next_id, next_start)
        duration = max(0.5, next_start - starts.get(sid, 0.0))
        image = build_dir / "images" / asset["file_path"]
        results.append(render_clip(image, output_dir / f"{sid}_motion.mp4", duration, ["push_in", "pan_right", "static"][idx % 3]))
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    build_pilot(args.build, args.output_dir, args.limit)
