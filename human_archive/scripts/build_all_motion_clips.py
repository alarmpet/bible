# -*- coding: utf-8 -*-
"""Build cinematic 2.5D motion video clips for ALL 68 shots.

- Shots ch1_01~ch1_07: If AI video clips exist, skip (they take priority).
- Shots ch1_08~ch4_15: Generate motion clips with content-aware motion types.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def get_motion_type(shot_id: str, narration: str) -> str:
    """Assign cinematic motion type based on shot content keywords."""
    nar = narration.lower() if narration else ""

    # Content-aware motion assignment
    if any(k in nar for k in ["솟구", "화산", "분연", "기둥", "치솟", "솟아"]):
        return "tilt_up"
    elif any(k in nar for k in ["눈빛", "초상", "얼굴", "표정", "잔물결", "클로즈업", "마크로"]):
        return "zoom_in"
    elif any(k in nar for k in ["도시", "전경", "거리", "시장", "포럼", "항구", "해안", "성문"]):
        return "pan_right"
    elif any(k in nar for k in ["폐허", "매몰", "묻혀", "화산재", "파괴", "무너", "붕괴"]):
        return "zoom_out"
    elif any(k in nar for k in ["가족", "연인", "아이", "어머니", "포옹", "손을 맞잡", "품에"]):
        return "diagonal_drift"
    elif any(k in nar for k in ["저택", "연회", "귀족", "와인", "재건", "재산", "금화"]):
        return "zoom_in"
    elif any(k in nar for k in ["번개", "불", "열풍", "화쇄류", "충격파"]):
        return "tilt_up"
    elif any(k in nar for k in ["구조", "탈출", "도망", "뛰쳐", "몰려"]):
        return "pan_left"
    elif any(k in nar for k in ["발굴", "석고", "발견", "인부", "고고학"]):
        return "zoom_out"
    elif any(k in nar for k in ["기록", "역사", "질문", "교훈", "가치", "침묵"]):
        return "diagonal_drift"
    elif any(k in nar for k in ["하늘", "구름", "성층권", "우산", "퍼져"]):
        return "zoom_out"
    elif any(k in nar for k in ["시민", "사람", "군중", "토론", "검투사"]):
        return "pan_right"
    else:
        # Default: alternate between pan and zoom for variety
        shot_num = int(shot_id.split("_")[1])
        return ["pan_right", "zoom_in", "pan_left", "diagonal_drift"][shot_num % 4]


from smooth_subpixel_motion_engine import render_smooth_motion_clip


def generate_motion_clip(
    img_path: Path,
    audio_path: Path,
    out_clip_path: Path,
    duration: float,
    motion_type: str,
):
    """Generate high-quality 1080p 25fps subpixel motion video from still image + audio."""
    motion_map = {
        "tilt_up": "tilt_up",
        "tilt_down": "tilt_down",
        "pan_right": "pan_right",
        "pan_left": "pan_left",
        "zoom_in": "push_in",
        "zoom_out": "pull_out",
        "diagonal_drift": "push_in",
        "push_in": "push_in",
        "pull_out": "pull_out"
    }
    target_motion = motion_map.get(motion_type, "push_in")

    temp_video = out_clip_path.with_suffix(".temp_v.mp4")
    render_smooth_motion_clip(
        image_path=img_path,
        output_path=temp_video,
        duration=duration,
        motion=target_motion,
        fps=25,
        width=1920,
        height=1080
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(temp_video),
        "-i",
        str(audio_path),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(out_clip_path),
    ]

    subprocess.run(cmd, check=True)
    if temp_video.exists():
        temp_video.unlink()


def build_all_motion_clips(run_dir: Path):
    run_dir = Path(run_dir).resolve()
    manifest_path = run_dir / "scene_audio_manifest.json"
    images_dir = run_dir / "images"
    audio_dir = run_dir / "audio"
    clips_dir = run_dir / "video_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    shots = manifest_data.get("shots", [])

    # List of shot IDs that have AI-generated video clips (Phase 1)
    ai_video_shots = set()
    for f in clips_dir.glob("*_ai_video.mp4"):
        sid = f.stem.replace("_ai_video", "")
        if f.stat().st_size > 10000:  # At least 10KB to be valid
            ai_video_shots.add(sid)

    print(f"\n=== Generating Cinematic Motion Video Clips for ALL {len(shots)} Shots ===")
    if ai_video_shots:
        print(f"  (Skipping {len(ai_video_shots)} shots with AI video clips: {sorted(ai_video_shots)})\n")
    else:
        print(f"  (No AI video clips found. Generating motion for all shots.)\n")

    generated = 0
    skipped_ai = 0
    skipped_exists = 0

    for i, shot in enumerate(shots, 1):
        shot_id = shot["shot_id"]
        dur = float(shot["duration"])
        narration = shot.get("text", "")

        # Skip if AI video exists for this shot
        if shot_id in ai_video_shots:
            print(f"  [{i:02d}/{len(shots)}] ⏭️  {shot_id} -> AI Video exists, skipping motion")
            skipped_ai += 1
            continue

        img_path = images_dir / f"{shot_id}.jpg"
        if not img_path.exists():
            img_path = images_dir / f"{shot_id}.png"
        audio_path = audio_dir / f"{shot_id}.wav"
        out_clip = clips_dir / f"{shot_id}_motion.mp4"

        if not img_path.exists():
            print(f"  [{i:02d}/{len(shots)}] ⚠️  {shot_id} -> Image not found! Skipping")
            continue

        motion = get_motion_type(shot_id, narration)

        generate_motion_clip(img_path, audio_path, out_clip, dur, motion)
        generated += 1
        print(f"  [{i:02d}/{len(shots)}] 🎬 {shot_id} -> Motion ({motion}, {dur:.2f}s) [{narration[:30]}...]")

    print(f"\n=== Motion Clip Generation Complete ===")
    print(f"  Generated: {generated}")
    print(f"  Skipped (AI video): {skipped_ai}")
    print(f"  Total shots: {len(shots)}\n")


if __name__ == "__main__":
    build_all_motion_clips(Path("human_archive/runs/ep01_pompeii_18hours"))
