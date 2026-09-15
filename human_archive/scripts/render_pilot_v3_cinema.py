# -*- coding: utf-8 -*-
"""Final cinematic assembly for Pilot v3:
Combines 20 Ken Burns motion clips + 48kHz natural narration audio + ASS burn-in subtitles,
runs full postflight QA verification, and updates canonical pilot video."""
from __future__ import annotations
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Add project root
sys.path.insert(0, r"D:\module\bible\human_archive")
from flow_automation.native_host.render_runner import postflight_video

EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
MANIFEST_PATH = EP_DIR / "generation" / "pilot_120s_audio_bound_manifest.json"
CANDIDATE_DIR = EP_DIR / "candidate"
CLIPS_DIR = CANDIDATE_DIR / "motion_clips"

AUDIO_PATH = CANDIDATE_DIR / "pilot_audio_120s_v3.wav"
ASS_PATH = CANDIDATE_DIR / "pilot_subtitles_120s_v3.ass"
OUTPUT_V3 = CANDIDATE_DIR / "NOLLAM-HIMALAYA-OPENING-PILOT-120S-VERIFIED-v3.mp4"
CANONICAL_MP4 = CANDIDATE_DIR / "NOLLAM-HIMALAYA-OPENING-PILOT-120S.mp4"

def main():
    print("=== Step 1: Checking prerequisites ===")
    assert MANIFEST_PATH.exists(), f"Missing manifest: {MANIFEST_PATH}"
    assert AUDIO_PATH.exists(), f"Missing master audio: {AUDIO_PATH}"
    assert ASS_PATH.exists(), f"Missing subtitles: {ASS_PATH}"

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    shots = manifest["shots"]
    print(f"Loaded {len(shots)} shots from manifest.")

    # Concat file for motion clips
    concat_txt = CANDIDATE_DIR / "motion_clips_concat.txt"
    concat_lines = []
    for s in shots:
        clip_p = CLIPS_DIR / f"{s['shot_id']}_motion.mp4"
        assert clip_p.exists(), f"Missing motion clip: {clip_p}"
        concat_lines.append(f"file '{clip_p.as_posix()}'")

    concat_txt.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
    print(f"Concat playlist written to {concat_txt}")

    print("\n=== Step 2: Assembling Final Cinema Pilot (v3) with FFmpeg ===")
    ass_escaped = ASS_PATH.as_posix().replace(":", r"\:")
    vf_filter = f"setpts=PTS-STARTPTS,fps=25,scale=1920:1080,format=yuv420p,ass='{ass_escaped}'"

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-f", "concat", "-safe", "0", "-i", str(concat_txt),
        "-i", str(AUDIO_PATH),
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "256k",
        "-ar", "48000",
        "-t", "120.0",
        "-movflags", "+faststart",
        str(OUTPUT_V3)
    ]

    t0 = time.time()
    print("Running cinema render pipeline...")
    subprocess.run(cmd, check=True)
    print(f"Cinema render completed in {time.time() - t0:.1f}s!")

    print("\n=== Step 3: Running Automated Postflight QA ===")
    report = postflight_video(OUTPUT_V3)
    postflight_path = CANDIDATE_DIR / "render_postflight_verified_v3.json"
    postflight_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Postflight QA Status: {report['status']}")
    print(f"QA Report saved: {postflight_path}")

    if report["status"] != "PASS":
        raise RuntimeError(f"Postflight QA failed: {report}")

    print("\n=== Step 4: Updating Canonical Video ===")
    shutil.copy2(OUTPUT_V3, CANONICAL_MP4)
    print(f"Canonical pilot updated: {CANONICAL_MP4}")

    # Extract verification snapshots
    snapshots_dir = CANDIDATE_DIR / "snapshots_v3"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    timestamps = [2.0, 6.0, 18.0, 38.0, 60.0, 85.0, 110.0]
    for ts in timestamps:
        out_jpg = snapshots_dir / f"frame_{int(ts):03d}s.jpg"
        cmd_snap = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", str(ts),
            "-i", str(OUTPUT_V3),
            "-vframes", "1",
            "-q:v", "2",
            str(out_jpg)
        ]
        subprocess.run(cmd_snap, check=True)
    print(f"Snapshots extracted to {snapshots_dir}")

    stat = OUTPUT_V3.stat()
    print("\nSUCCESS! NOLLAM-HIMALAYA-OPENING-PILOT-120S-VERIFIED-v3 IS COMPLETE!")
    print(f"File: {OUTPUT_V3}")
    print(f"Size: {stat.st_size / (1024*1024):.2f} MB")

if __name__ == "__main__":
    main()
