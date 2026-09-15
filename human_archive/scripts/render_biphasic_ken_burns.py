# -*- coding: utf-8 -*-
"""Render 2-Stage Bi-Phasic Ken Burns motion clips (30.0s, 750 frames @ 25fps)
for the 36 body shots (SHOT_021 ~ SHOT_056) using PIL Bicubic subpixel interpolation."""
from __future__ import annotations
import json
import subprocess
import time
from pathlib import Path
from PIL import Image

EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
MANIFEST_PATH = EP_DIR / "generation" / "master_1200s_manifest.json"
CLIPS_DIR = EP_DIR / "candidate" / "motion_clips"
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

def render_biphasic_clip(
    image_path: Path,
    output_path: Path,
    duration: float = 30.0,
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
        
        # Bi-Phasic Timing Architecture:
        # Stage 1 (0.00 ~ 0.47, 0~14s): Slow panoramic drift / pull-out (zoom 1.00 -> 1.06)
        # Transition Cushion (0.47 ~ 0.53, 14~16s): Deceleration & focal lock (zoom 1.06)
        # Stage 2 (0.53 ~ 1.00, 16~30s): Accelerating forensic push-in (zoom 1.06 -> 1.25)
        if t < 0.47:
            u = t / 0.47
            e1 = 3.0 * (u ** 2) - 2.0 * (u ** 3)
            zoom = 1.00 + 0.06 * e1
            cx = 0.52 - 0.04 * e1
            cy = 0.50
        elif t < 0.53:
            zoom = 1.06
            cx = 0.48
            cy = 0.50
        else:
            w_norm = (t - 0.53) / 0.47
            e2 = 3.0 * (w_norm ** 2) - 2.0 * (w_norm ** 3)
            zoom = 1.06 + 0.19 * e2
            cx = 0.48 + 0.02 * e2
            cy = 0.50

        crop_w = w / zoom
        crop_h = h / zoom
        left = max(0.0, min(w - crop_w, (w - crop_w) * cx))
        top = max(0.0, min(h - crop_h, (h - crop_h) * cy))

        box = (left, top, left + crop_w, top + crop_h)
        frame_img = src.resize((w, h), Image.Resampling.BICUBIC, box)
        proc.stdin.write(frame_img.tobytes())

    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"FFmpeg motion clip rendering failed for {image_path}")
    return output_path

def main():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    shots = [s for s in manifest["shots"] if not s.get("is_pilot")]
    print(f"Starting Bi-Phasic Ken Burns rendering for {len(shots)} body shots...")

    t_start = time.time()
    for idx, s in enumerate(shots, 1):
        shot_id = s["shot_id"]
        out_mp4 = CLIPS_DIR / f"{shot_id}_motion.mp4"
        
        # Check if already rendered
        if out_mp4.exists() and out_mp4.stat().st_size > 100000:
            print(f"[{idx:02d}/36] {shot_id}: already rendered, skipping.")
            continue

        img_path = Path(s["image_path"])
        if not img_path.exists():
            print(f"[{idx:02d}/36] {shot_id}: image not found yet ({img_path.name}), waiting...")
            continue

        t0 = time.time()
        print(f"[{idx:02d}/36] Rendering {shot_id} (30.0s, 750 frames)...", end="", flush=True)
        render_biphasic_clip(img_path, out_mp4, duration=s["scene_duration"])
        dt = time.time() - t0
        print(f" done in {dt:.1f}s")

    print(f"\nBatch motion rendering cycle finished in {time.time() - t_start:.1f}s!")

if __name__ == "__main__":
    main()
