# -*- coding: utf-8 -*-
"""Final 20-minute master assembly pipeline:
Hierarchical Concat of 56 motion clips + 48kHz master audio + ASS subtitles,
automated postflight QA, and canonical publication."""
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
MANIFEST_PATH = EP_DIR / "generation" / "master_1200s_manifest.json"
CANDIDATE_DIR = EP_DIR / "candidate"
CLIPS_DIR = CANDIDATE_DIR / "motion_clips"

AUDIO_PATH = CANDIDATE_DIR / "pilot_audio_1200s_master.wav"
ASS_PATH = CANDIDATE_DIR / "pilot_subtitles_1200s.ass"
OUTPUT_MASTER = CANDIDATE_DIR / "NOLLAM-HIMALAYA-MASTER-1200S-FINAL.mp4"
CANONICAL_MP4 = CANDIDATE_DIR / "NOLLAM-HIMALAYA-MASTER-1200S.mp4"

def main():
    print("=== Step 1: Validating Prerequisites for 20-Minute Master ===")
    assert MANIFEST_PATH.exists(), f"Missing manifest: {MANIFEST_PATH}"
    assert AUDIO_PATH.exists(), f"Missing master audio: {AUDIO_PATH}"
    assert ASS_PATH.exists(), f"Missing subtitles: {ASS_PATH}"

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    shots = manifest["shots"]
    print(f"Loaded {len(shots)} shots from manifest.")
    assert len(shots) == 56, f"Expected 56 shots, got {len(shots)}"

    # Concat playlist for all 56 motion clips
    concat_txt = CANDIDATE_DIR / "master_56_motion_concat.txt"
    concat_lines = []
    missing_clips = []
    for s in shots:
        clip_p = CLIPS_DIR / f"{s['shot_id']}_motion.mp4"
        if not clip_p.exists() or clip_p.stat().st_size < 100000:
            missing_clips.append(s["shot_id"])
        concat_lines.append(f"file '{clip_p.as_posix()}'")

    if missing_clips:
        raise FileNotFoundError(f"Missing {len(missing_clips)} motion clips: {missing_clips[:5]}...")

    concat_txt.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
    print(f"Concat playlist verified: {concat_txt} (56 entries)")

    probe_audio = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(AUDIO_PATH)], capture_output=True, text=True, check=True)
    audio_dur = float(json.loads(probe_audio.stdout)["format"]["duration"])
    print(f"Master audio measured duration: {audio_dur:.2f}s (20min ±30% window: 840s~1560s)")
    assert 840.0 <= audio_dur <= 1560.0, f"Audio duration {audio_dur:.2f}s is out of 20min ±30% bounds!"

    print(f"\n=== Step 2: Final Cinema Encoding via FFmpeg (Dynamic {audio_dur:.2f}s) ===")
    ass_escaped = ASS_PATH.as_posix().replace(":", r"\:")
    vf_filter = f"setpts=PTS-STARTPTS,fps=25,scale=1920:1080,format=yuv420p,ass='{ass_escaped}'"

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-f", "concat", "-safe", "0", "-i", str(concat_txt),
        "-i", str(AUDIO_PATH),
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "19",
        "-c:a", "aac",
        "-b:a", "256k",
        "-ar", "48000",
        "-t", f"{audio_dur:.3f}",
        "-movflags", "+faststart",
        str(OUTPUT_MASTER)
    ]

    t0 = time.time()
    print("Encoding master video with burned 2-line clean subtitles...")
    subprocess.run(cmd, check=True)
    dt = time.time() - t0
    print(f"Master encoding completed in {dt:.1f}s ({dt/60:.2f} min)!")

    print("\n=== Step 3: Running Postflight Technical QA (20min ±30% window: 840s~1560s) ===")
    report = postflight_video(OUTPUT_MASTER, min_duration=840.0, max_duration=1560.0)
    postflight_path = CANDIDATE_DIR / "render_postflight_master_1200s.json"
    postflight_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Postflight QA Status: {report['status']}")
    print(f"QA Report saved: {postflight_path}")

    if report["status"] != "PASS":
        raise RuntimeError(f"Postflight QA failed: {report}")

    print("\n=== Step 4: Updating Canonical Master Video ===")
    shutil.copy2(OUTPUT_MASTER, CANONICAL_MP4)
    print(f"Canonical master video updated: {CANONICAL_MP4}")

    # Snapshots across the 20 minutes
    snapshots_dir = CANDIDATE_DIR / "snapshots_master_1200s"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    sample_timestamps = [30.0, 150.0, 300.0, 500.0, 700.0, 950.0, 1150.0]
    for ts in sample_timestamps:
        out_jpg = snapshots_dir / f"frame_{int(ts):04d}s.jpg"
        cmd_snap = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", str(ts),
            "-i", str(OUTPUT_MASTER),
            "-vframes", "1",
            "-q:v", "2",
            str(out_jpg)
        ]
        subprocess.run(cmd_snap, check=True)
    print(f"Snapshots extracted: {snapshots_dir}")

    stat = OUTPUT_MASTER.stat()
    print("\nSUCCESS! 20-MINUTE MASTER DOCUMENTARY VIDEO IS COMPLETE!")
    print(f"File: {OUTPUT_MASTER}")
    print(f"Size: {stat.st_size / (1024*1024):.2f} MB")

if __name__ == "__main__":
    main()
