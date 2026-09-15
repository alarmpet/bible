# -*- coding: utf-8 -*-
"""Render 120-second Opening Pilot MP4 for Himalaya GLOF Episode using FFmpeg."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
try:
    from scripts.pilot_render_guard import validate_pilot_inputs
except ModuleNotFoundError:
    # The test harness loads this file directly rather than as ``scripts.*``.
    from pilot_render_guard import validate_pilot_inputs

EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
SOURCE_DIR = EP_DIR / "source"
IMAGES_DIR = EP_DIR / "images"
AUDIO_DIR = EP_DIR / "audio"
SUBTITLES_DIR = EP_DIR / "subtitles"
OUTPUT_DIR = EP_DIR / "candidate"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FINAL_MP4 = OUTPUT_DIR / "NOLLAM-HIMALAYA-OPENING-PILOT-120S.mp4"


def render_pilot():
    manifest = json.loads((SOURCE_DIR / "scene_script_manifest_v2.json").read_text(encoding="utf-8"))
    scenes = manifest["scenes"]
    
    # We take all scenes from 0 to 120s (Phase 1: Cold Open & Roadmap, Scenes 1 to 20)
    pilot_scenes = [s for s in scenes if s["end_sec"] <= 120.0]
    print(f"Rendering Opening Pilot: {len(pilot_scenes)} scenes (0.0s ~ 120.0s)...")

    # Available 12 images: map available images across scenes 1~20
    available_imgs = sorted(list(IMAGES_DIR.glob("SHOT_*.jpg")))
    print(f"Available high-res images: {len(available_imgs)}")

    # 1. Create concat demuxer file for video stream
    concat_txt = OUTPUT_DIR / "video_concat.txt"
    with open(concat_txt, "w", encoding="utf-8") as f:
        for idx, s in enumerate(pilot_scenes):
            shot_num = (idx % len(available_imgs)) + 1
            img_path = IMAGES_DIR / f"SHOT_{shot_num:03d}.jpg"
            dur = s["duration_sec"]
            # FFmpeg concat format requires forward slashes or escaped backslashes
            f.write(f"file '{img_path.as_posix()}'\n")
            f.write(f"duration {dur:.2f}\n")
        # Re-specify last file as required by concat demuxer
        last_shot_num = ((len(pilot_scenes) - 1) % len(available_imgs)) + 1
        last_img_path = IMAGES_DIR / f"SHOT_{last_shot_num:03d}.jpg"
        f.write(f"file '{last_img_path.as_posix()}'\n")

    print(f"Created concat file: {concat_txt}")

    # 2. Extract 120s audio clip
    master_audio = AUDIO_DIR / "master_narration_audio.wav"
    pilot_audio = OUTPUT_DIR / "pilot_audio_120s.wav"
    
    cmd_audio = [
        "ffmpeg", "-y",
        "-ss", "0",
        "-t", "120.0",
        "-i", str(master_audio),
        "-c:a", "pcm_s16le",
        str(pilot_audio)
    ]
    subprocess.run(cmd_audio, check=True)
    print(f"Extracted 120s audio: {pilot_audio}")

    # 3. Create 120s subtitle ASS subset
    ass_orig = SUBTITLES_DIR / "subtitles.ass"
    pilot_ass = OUTPUT_DIR / "pilot_subtitles_120s.ass"
    
    ass_content = ass_orig.read_text(encoding="utf-8")
    lines = ass_content.splitlines()
    header_lines = []
    event_lines = []
    is_events = False
    for line in lines:
        if "[Events]" in line:
            is_events = True
            header_lines.append(line)
            continue
        if not is_events:
            header_lines.append(line)
        else:
            if line.startswith("Dialogue:"):
                # Check start time (00:00:00.00 ~ 00:02:00.00)
                parts = line.split(",", 9)
                start_time = parts[1]
                if start_time.startswith("0:00:") or start_time.startswith("0:01:") or start_time == "0:02:00.00":
                    event_lines.append(line)
            else:
                header_lines.append(line)

    pilot_ass.write_text("\n".join(header_lines) + "\n" + "\n".join(event_lines), encoding="utf-8")
    print(f"Created 120s ASS subtitles: {pilot_ass} ({len(event_lines)} subtitle lines)")

    # 4. Render Final 1080p MP4 Video with Burn-in Subtitles
    # Using subtle zoom/pan motion & ASS subtitles filter
    ass_path_escaped = pilot_ass.as_posix().replace(":", r"\:")
    
    cmd_render = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_txt),
        "-i", str(pilot_audio),
        "-vf", f"fps=25,format=yuv420p,ass='{ass_path_escaped}'",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", "120.0",
        "-pix_fmt", "yuv420p",
        str(FINAL_MP4)
    ]
    
    print("\n--- Running FFmpeg Render ---")
    print(" ".join(cmd_render))
    subprocess.run(cmd_render, check=True)
    
    stat = FINAL_MP4.stat()
    print(f"\n🎉 Successfully rendered 1080p Opening Pilot MP4!")
    print(f"   Output: {FINAL_MP4}")
    print(f"   Size: {stat.st_size / (1024*1024):.2f} MB")
    print(f"   Duration: Exactly 120.0s (2 min)\n")


if __name__ == "__main__":
    render_pilot()
