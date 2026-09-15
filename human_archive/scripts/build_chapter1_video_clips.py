# -*- coding: utf-8 -*-
"""Generate dynamic 1080p 25fps cinematic motion video clips for Chapter 1 (Shots 01 to 08)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def generate_motion_clip(
    img_path: Path,
    audio_path: Path,
    out_clip_path: Path,
    duration: float,
    motion_type: str,
):
    """Generate high-quality 1080p cinematic motion video from image + audio."""
    fps = 25
    total_frames = int(duration * fps)

    # Different cinematic motion curves for each shot
    if motion_type == "tilt_up":
        # Slow upward vertical tilt (Volcano eruption plume rising)
        vf = f"scale=2160:1215,crop=1920:1080:x='(iw-ow)/2':y='(ih-oh)*(1-n/{total_frames})'"
    elif motion_type == "pan_right":
        # Slow horizontal tracking pan (Ancient Pompeii city streets)
        vf = f"scale=2304:1296,crop=1920:1080:x='(iw-ow)*(n/{total_frames})':y='(ih-oh)/2'"
    elif motion_type == "zoom_in":
        # Slow dramatic push-in zoom (Pliny / Citizens)
        vf = f"scale=2160:1215,zoompan=z='min(zoom+0.0015,1.25)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}"
    elif motion_type == "zoom_out":
        # High altitude wide expansion (Stratosphere umbrella cloud)
        vf = f"scale=2160:1215,zoompan=z='if(lte(zoom,1.0),1.25,max(1.0,zoom-0.0015))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}"
    elif motion_type == "pan_left":
        # Forum market lively horizontal pan
        vf = f"scale=2304:1296,crop=1920:1080:x='(iw-ow)*(1-n/{total_frames})':y='(ih-oh)/2'"
    elif motion_type == "diagonal_drift":
        # Amphitheatre / Banquet diagonal cinematic drift
        vf = f"scale=2304:1296,crop=1920:1080:x='(iw-ow)*(n/{total_frames})':y='(ih-oh)*(n/{total_frames})'"
    else:
        # Default gentle cinematic push
        vf = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-loop",
        "1",
        "-i",
        str(img_path),
        "-i",
        str(audio_path),
        "-t",
        str(duration),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "17",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(out_clip_path),
    ]

    subprocess.run(cmd, check=True)
    print(f"  🎬 Generated dynamic video clip: {out_clip_path.name} ({duration:.2f}s, motion: {motion_type})")


def build_all_chapter1_video_clips(run_dir: Path):
    run_dir = Path(run_dir).resolve()
    manifest_path = run_dir / "scene_audio_manifest.json"
    images_dir = run_dir / "images"
    audio_dir = run_dir / "audio"
    clips_dir = run_dir / "video_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    shots = manifest_data.get("shots", [])

    # Motions assigned to Chapter 1 hook shots (shots 1 to 8, approx 74s)
    motion_map = {
        "ch1_01": "tilt_up",          # 30km 분연주 수직 상승
        "ch1_02": "pan_right",        # 폼페이 전경 와이드 트래킹
        "ch1_03": "diagonal_drift",   # 플리니우스 서한 기록 대각선 드리프트
        "ch1_04": "zoom_out",         # 성층권 우산구름 와이드 줌아웃
        "ch1_05": "zoom_in",          # 호기심 어린 시민들 슬로우 푸시인
        "ch1_06": "pan_left",         # 포럼 광장 시장 수평 패닝
        "ch1_07": "pan_right",        # 원형경기장 검투사 토론 트래킹
        "ch1_08": "zoom_in",          # 귀족 연회장 중앙 포커스 줌인
    }

    print(f"\n=== Generating Dynamic Video Clips for Chapter 1 (Shots 1~8) ===")
    for shot in shots:
        shot_id = shot["shot_id"]
        if shot_id not in motion_map:
            continue

        dur = float(shot["duration"])
        img_path = images_dir / f"{shot_id}.jpg"
        audio_path = audio_dir / f"{shot_id}.wav"
        out_clip = clips_dir / f"{shot_id}_motion.mp4"
        motion = motion_map[shot_id]

        if not img_path.exists():
            print(f"  Warning: Image {img_path} not found!")
            continue

        generate_motion_clip(img_path, audio_path, out_clip, dur, motion)

    print("=== Chapter 1 Dynamic Video Clips Generation Completed! ===\n")


if __name__ == "__main__":
    build_all_chapter1_video_clips(Path("human_archive/runs/ep01_pompeii_18hours"))
