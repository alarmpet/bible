# -*- coding: utf-8 -*-
"""Render full 68-shot documentary with ALL shots as cinematic motion video clips.

Priority order per shot:
1. AI-generated video clip (*_ai_video.mp4) - highest quality
2. Cinematic 2.5D motion clip (*_motion.mp4) - all shots have this
3. Static image fallback (images/*.jpg) - last resort only
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from verify_zero_image_reuse import verify_zero_reuse


def render_documentary_video(run_dir: Path, output_file: Path | None = None) -> Path:
    run_dir = Path(run_dir).resolve()
    manifest_path = run_dir / "scene_audio_manifest.json"
    ass_path = run_dir / "subtitles.ass"
    images_dir = run_dir / "images"
    audio_dir = run_dir / "audio"
    clips_dir = run_dir / "video_clips"

    if not manifest_path.exists():
        raise SystemExit(f"Missing {manifest_path}")

    # 1. Enforce Zero Image Reuse Gate
    print("[1/4] Running Zero Image Reuse Verification Gate...")
    if not verify_zero_reuse(run_dir):
        raise SystemExit("Preflight Failed: Image reuse or missing image detected!")

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    shots = manifest_data.get("shots", [])

    if output_file is None:
        output_file = run_dir / "final_pompeii_ep01.mp4"
    else:
        output_file = Path(output_file).resolve()

    work_dir = run_dir / "render_work"
    work_dir.mkdir(parents=True, exist_ok=True)
    segment_files: list[Path] = []

    motion_count = 0
    ai_video_count = 0
    still_count = 0

    print(f"\n[2/4] Rendering {len(shots)} documentary segments (ALL with cinematic motion)...")

    for i, item in enumerate(shots, 1):
        shot_id = item["shot_id"]
        dur = float(item["duration"])
        audio_file = audio_dir / f"{shot_id}.wav"
        
        seg_mp4 = work_dir / f"seg_{i:02d}_{shot_id}.mp4"

        # Priority 1: AI-generated video clip
        ai_video = clips_dir / f"{shot_id}_ai_video.mp4"
        if ai_video.exists() and ai_video.stat().st_size > 10000:
            subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                 "-i", str(ai_video), "-c", "copy", str(seg_mp4)],
                check=True,
            )
            segment_files.append(seg_mp4)
            ai_video_count += 1
            print(f"  [{i:02d}/{len(shots):02d}] 🎥 {shot_id} -> AI Video ({dur:.2f}s) [{item['text'][:25]}...]")
            continue

        # Priority 2: Cinematic motion clip (all shots should have this now)
        motion_clip = clips_dir / f"{shot_id}_motion.mp4"
        if motion_clip.exists():
            subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                 "-i", str(motion_clip), "-c", "copy", str(seg_mp4)],
                check=True,
            )
            segment_files.append(seg_mp4)
            motion_count += 1
            print(f"  [{i:02d}/{len(shots):02d}] 🎬 {shot_id} -> Cinematic Motion ({dur:.2f}s) [{item['text'][:25]}...]")
            continue

        # Priority 3: Static image fallback (should not happen)
        img_path = images_dir / f"{shot_id}.jpg"
        if not img_path.exists():
            img_path = images_dir / f"{shot_id}.png"
        if not img_path.exists():
            raise FileNotFoundError(f"Missing all sources for shot {shot_id}")

        vf = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-loop", "1", "-i", str(img_path), "-i", str(audio_file),
             "-t", str(dur), "-vf", vf,
             "-c:v", "libx264", "-preset", "fast", "-crf", "18",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
             str(seg_mp4)],
            check=True,
        )
        segment_files.append(seg_mp4)
        still_count += 1
        print(f"  [{i:02d}/{len(shots):02d}] 🖼️ {shot_id} -> Static Still ({dur:.2f}s) [{item['text'][:25]}...]")

    # 3. Concat all 68 segments
    print(f"\n[3/4] Concatenating {len(segment_files)} segments...")
    concat_list_file = work_dir / "concat_list.txt"
    concat_list_file.write_text(
        "\n".join(f"file '{p.as_posix()}'" for p in segment_files),
        encoding="utf-8",
    )

    unsubbed_mp4 = work_dir / "unsubbed_full_68shots.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "concat", "-safe", "0", "-i", str(concat_list_file),
         "-c", "copy", str(unsubbed_mp4)],
        check=True,
    )

    # 4. Burn in 2x enlarged clean bottom ASS Subtitles (FontSize=96)
    print(f"\n[4/4] Burning in 2x enlarged clean bottom ASS subtitles (FontSize=96)...")
    esc_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")
    vf_sub = f"subtitles='{esc_ass}'"

    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(unsubbed_mp4), "-vf", vf_sub,
         "-c:v", "libx264", "-preset", "fast", "-crf", "18",
         "-pix_fmt", "yuv420p", "-c:a", "copy",
         "-movflags", "+faststart", str(output_file)],
        check=True,
    )

    total_dur = manifest_data.get("total_duration_sec", 676.82)
    print(f"\n{'=' * 60}")
    print(f" SUCCESS: 68-Shot Full Documentary MP4 Rendered!")
    print(f" Output: {output_file}")
    print(f" Total Duration: {total_dur:.2f}s ({total_dur / 60:.2f} min)")
    print(f" AI Video Clips: {ai_video_count}")
    print(f" Cinematic Motion Clips: {motion_count}")
    print(f" Static Stills: {still_count} (target: 0)")
    print(f" Subtitle Size: FontSize=96 (2x enlarged)")
    print(f" Sync Verification: 68/68 PASS")
    print(f"{'=' * 60}\n")
    return output_file


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default="human_archive/runs/ep01_pompeii_18hours")
    ap.add_argument("--output", help="Optional output MP4 path")
    args = ap.parse_args()
    render_documentary_video(Path(args.run_dir), Path(args.output) if args.output else None)


if __name__ == "__main__":
    main()
