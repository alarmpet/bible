# -*- coding: utf-8 -*-
"""Render smooth, jitter-free 25fps Ken Burns motion clips (1920x1080 H.264)
for all 20 documentary scenes using PIL Bicubic subpixel interpolation."""
from __future__ import annotations
import json
import subprocess
import time
from pathlib import Path
from PIL import Image

EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
MANIFEST_PATH = EP_DIR / "generation" / "pilot_120s_audio_bound_manifest.json"
CLIPS_DIR = EP_DIR / "candidate" / "motion_clips"
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

def render_motion_clip(
    image_path: Path,
    output_path: Path,
    duration: float,
    motion: str,
    fps: int = 25,
    w: int = 1920,
    h: int = 1080
) -> Path:
    total_frames = max(1, round(duration * fps))
    with Image.open(image_path) as im:
        src = im.convert("RGB")
        if src.size != (w, h):
            src = src.resize((w, h), Image.Resampling.LANCZOS)
    
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{w}x{h}",
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

    for frame in range(total_frames):
        t = frame / max(1, total_frames - 1)
        # Smooth hermite easing
        s = 3.0 * (t ** 2) - 2.0 * (t ** 3)

        if motion == "push_in":
            zoom = 1.00 + 0.08 * s
            crop_w = w / zoom
            crop_h = h / zoom
            left = (w - crop_w) * 0.5
            top = (h - crop_h) * 0.5
        elif motion == "pull_out":
            zoom = 1.08 - 0.08 * s
            crop_w = w / zoom
            crop_h = h / zoom
            left = (w - crop_w) * 0.5
            top = (h - crop_h) * 0.5
        elif motion == "pan_right":
            zoom = 1.10
            crop_w = w / zoom
            crop_h = h / zoom
            left = (w - crop_w) * (0.10 + 0.80 * s)
            top = (h - crop_h) * 0.5
        elif motion == "pan_left":
            zoom = 1.10
            crop_w = w / zoom
            crop_h = h / zoom
            left = (w - crop_w) * (0.90 - 0.80 * s)
            top = (h - crop_h) * 0.5
        elif motion == "tilt_up":
            zoom = 1.10
            crop_w = w / zoom
            crop_h = h / zoom
            left = (w - crop_w) * 0.5
            top = (h - crop_h) * (0.90 - 0.80 * s)
        elif motion == "tilt_down":
            zoom = 1.10
            crop_w = w / zoom
            crop_h = h / zoom
            left = (w - crop_w) * 0.5
            top = (h - crop_h) * (0.10 + 0.80 * s)
        else: # static fallback
            crop_w = w
            crop_h = h
            left = 0.0
            top = 0.0

        box = (left, top, left + crop_w, top + crop_h)
        frame_img = src.resize((w, h), Image.Resampling.BICUBIC, box)
        proc.stdin.write(frame_img.tobytes())

    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"FFmpeg motion clip rendering failed for {image_path}")
    return output_path

def main():
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    shots = manifest["shots"]
    print(f"Starting Ken Burns rendering for {len(shots)} shots...")

    t_start = time.time()
    rendered_clips = []
    for s in shots:
        shot_id = s["shot_id"]
        motion = s["camera_motion"]
        duration = float(s["scene_duration"])
        img_path = Path(s["image_path"])
        out_mp4 = CLIPS_DIR / f"{shot_id}_motion.mp4"

        t0 = time.time()
        print(f"Rendering {shot_id} [{motion}] ({duration:.2f}s, {round(duration*25)} frames)...", end="", flush=True)
        render_motion_clip(img_path, out_mp4, duration, motion)
        dt = time.time() - t0
        print(f" done in {dt:.1f}s")
        rendered_clips.append({
            "shot_id": shot_id,
            "clip_path": str(out_mp4),
            "motion": motion,
            "duration": duration,
            "frames": round(duration * 25)
        })

    summary_file = CLIPS_DIR / "motion_clips_summary.json"
    summary_file.write_text(json.dumps(rendered_clips, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nAll {len(shots)} motion clips successfully rendered in {time.time() - t_start:.1f}s!")
    print(f"Summary written to {summary_file}")

if __name__ == "__main__":
    main()
