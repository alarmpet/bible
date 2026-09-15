# -*- coding: utf-8 -*-
"""Normalize raw generated intro video clips (SHOT_001 to SHOT_008)
into broadcast-grade 1080p 25fps constant frame rate clips with exact frame budget."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
RAW_INPUT_DIR = EP_DIR / "candidate" / "intro_raw_videos"
MOTION_CLIPS_DIR = EP_DIR / "candidate" / "motion_clips"
BACKUP_DIR = MOTION_CLIPS_DIR / "backup_kenburns"

# Exact target frame counts & durations for SHOT_001 through SHOT_008
SHOT_TARGET_SPECS: Dict[str, Dict[str, any]] = {
    "SHOT_001": {"frames": 86, "duration_sec": 3.440, "desc": "Sunny clear Himalayan sky, mountain serenity"},
    "SHOT_002": {"frames": 113, "duration_sec": 4.520, "desc": "Sudden violent tsunami surge, roaring debris"},
    "SHOT_003": {"frames": 94, "duration_sec": 3.760, "desc": "Dry riverbed under bright sunshine, no rain contrast"},
    "SHOT_004": {"frames": 130, "duration_sec": 5.200, "desc": "Confused villagers pointing at mountain flood"},
    "SHOT_005": {"frames": 139, "duration_sec": 5.560, "desc": "5,000m glacial peak high-altitude breach"},
    "SHOT_006": {"frames": 135, "duration_sec": 5.400, "desc": "Terminal moraine dam collapse, lake drainage"},
    "SHOT_007": {"frames": 135, "duration_sec": 5.400, "desc": "Torrential debris flood swallowing canyon"},
    "SHOT_008": {"frames": 132, "duration_sec": 5.280, "desc": "Glacial Lake Outburst Flood (GLOF) vista"},
}


def find_raw_file_for_shot(shot_id: str, raw_dir: Path) -> Optional[Path]:
    """Find input file matching shot ID with tolerant regex naming."""
    shot_num = int(shot_id.split("_")[1])
    patterns = [
        rf"^SHOT_?0*{shot_num}(?:_video)?\.(?:mp4|mov|mkv|webm)$",
        rf"^intro_?0*{shot_num}(?:_video)?\.(?:mp4|mov|mkv|webm)$",
        rf"^shot_?0*{shot_num}\.(?:mp4|mov|mkv|webm)$",
        rf"^0*{shot_num}\.(?:mp4|mov|mkv|webm)$",
    ]

    for p in raw_dir.iterdir():
        if not p.is_file():
            continue
        for pat in patterns:
            if re.match(pat, p.name, re.IGNORECASE):
                return p
    return None


def normalize_clip(
    raw_video: Path,
    output_clip: Path,
    target_frames: int,
    start_offset: float = 0.0,
    force_crop: bool = True,
) -> Tuple[bool, str]:
    """Normalize raw AI video clip to 1080p 25fps exact-frame stream without audio."""
    output_clip.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output_clip.with_suffix(".temp.mp4")

    # Filter chain:
    # 1. fps=25 conforming
    # 2. scale & crop to 1920x1080 (increase + center crop to avoid black pillar/letterboxes)
    # 3. setsar=1:1
    # 4. tpad=stop_mode=clone:stop_duration=5 ensures safety against short clips
    if force_crop:
        scale_filter = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1"
    else:
        scale_filter = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1"

    vf = f"fps=25,setpts=PTS-STARTPTS,{scale_filter},tpad=stop_mode=clone:stop_duration=5"

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
    ]
    if start_offset > 0.0:
        cmd.extend(["-ss", f"{start_offset:.3f}"])

    cmd.extend([
        "-i", str(raw_video),
        "-vf", vf,
        "-an",  # Strip AI audio
        "-frames:v", str(target_frames),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-color_range", "tv",
        "-g", "25",
        "-keyint_min", "25",
        "-movflags", "+faststart",
        str(temp_output),
    ])

    try:
        subprocess.run(cmd, check=True)
        if output_clip.exists():
            output_clip.unlink()
        temp_output.replace(output_clip)
        return True, f"Successfully normalized {raw_video.name} -> {output_clip.name} ({target_frames} frames)"
    except subprocess.CalledProcessError as e:
        if temp_output.exists():
            temp_output.unlink()
        return False, f"FFmpeg error on {raw_video.name}: {e}"


def run_normalization(
    raw_dir: Path = RAW_INPUT_DIR,
    out_dir: Path = MOTION_CLIPS_DIR,
    backup: bool = True,
    dry_run: bool = False,
) -> Dict[str, any]:
    """Process all available intro clips for SHOT_001 ~ SHOT_008."""
    print("=" * 70)
    print("🎬 Intro Video Ingestion & Normalization Engine (SHOT_001 ~ SHOT_008)")
    print(f"Drop directory:   {raw_dir}")
    print(f"Target directory: {out_dir}")
    print("=" * 70)

    if not raw_dir.exists():
        raw_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created input drop directory: {raw_dir}")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    summary = {
        "found": [],
        "missing": [],
        "normalized": [],
        "errors": [],
    }

    for shot_id, spec in SHOT_TARGET_SPECS.items():
        raw_file = find_raw_file_for_shot(shot_id, raw_dir)
        target_clip = out_dir / f"{shot_id}_motion.mp4"

        if not raw_file:
            summary["missing"].append(shot_id)
            print(f"⚠️ [{shot_id}] No raw video found in {raw_dir.name}. (Will keep existing clip)")
            continue

        summary["found"].append({"shot_id": shot_id, "raw_file": str(raw_file)})
        print(f"🔍 [{shot_id}] Matched: {raw_file.name} (Target: {spec['frames']} frames / {spec['duration_sec']:.3f}s)")

        if dry_run:
            continue

        # Backup existing Ken Burns clip if not already backed up
        if backup and target_clip.exists():
            bak_file = BACKUP_DIR / f"{shot_id}_motion_kenburns.mp4"
            if not bak_file.exists():
                shutil.copy2(target_clip, bak_file)
                print(f"  📦 Backed up Ken Burns clip to: {bak_file.name}")

        # Normalize
        success, msg = normalize_clip(
            raw_video=raw_file,
            output_clip=target_clip,
            target_frames=spec["frames"],
        )

        if success:
            summary["normalized"].append(shot_id)
            print(f"  ✅ {msg}")
        else:
            summary["errors"].append({"shot_id": shot_id, "error": msg})
            print(f"  ❌ {msg}")

    print("\n" + "=" * 70)
    print(f"Normalization Summary: {len(summary['normalized'])} normalized, {len(summary['missing'])} missing, {len(summary['errors'])} errors")
    print("=" * 70)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Normalize raw intro videos for Himalaya GLOF documentary")
    parser.add_argument("--raw-dir", type=Path, default=RAW_INPUT_DIR, help="Raw input drop folder")
    parser.add_argument("--out-dir", type=Path, default=MOTION_CLIPS_DIR, help="Output motion clips folder")
    parser.add_argument("--no-backup", action="store_true", help="Skip backing up existing motion clips")
    parser.add_argument("--dry-run", action="store_true", help="Scan and match files without converting")
    args = parser.parse_args()

    res = run_normalization(
        raw_dir=args.raw_dir,
        out_dir=args.out_dir,
        backup=not args.no_backup,
        dry_run=args.dry_run,
    )
    if res["errors"]:
        sys.exit(1)
