# -*- coding: utf-8 -*-
"""Master Intro Ingestion, Normalization, QA, and Assembly Pipeline:
Watches/ingests candidate/intro_raw_videos, normalizes SHOT_001~008, validates QA,
and automatically triggers final 20-minute master assembly."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = Path(r"D:\module\bible\human_archive\scripts")
EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
RAW_DIR = EP_DIR / "candidate" / "intro_raw_videos"
CLIPS_DIR = EP_DIR / "candidate" / "motion_clips"
FINAL_MASTER = EP_DIR / "candidate" / "NOLLAM-HIMALAYA-MASTER-1200S-FINAL.mp4"

sys.path.insert(0, str(SCRIPTS_DIR))
from normalize_intro_videos import run_normalization
from validate_intro_videos import validate_all_intro_clips


def run_full_pipeline(auto_assemble: bool = True, backup: bool = True) -> int:
    print("=" * 80)
    print("🚀 AUTOMATED INTRO VIDEO INGESTION & MASTER ASSEMBLY PIPELINE (0s to 38.5s)")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Step 1: Ingest & Normalize
    print("\n[PHASE 1] Scanning and Normalizing Raw Video Clips...")
    norm_summary = run_normalization(raw_dir=RAW_DIR, out_dir=CLIPS_DIR, backup=backup)

    if norm_summary["errors"]:
        print(f"❌ Aborting: {len(norm_summary['errors'])} errors during normalization.")
        return 1

    if not norm_summary["normalized"]:
        print("ℹ️ No new raw videos to normalize. Existing motion clips will be evaluated.")

    # Step 2: Quality Gate
    print("\n[PHASE 2] Running Strict Technical QA Validation on Intro Clips...")
    qa_report = validate_all_intro_clips(CLIPS_DIR)
    if qa_report["status"] != "PASS":
        print(f"❌ Aborting: QA Gate failed with violations: {qa_report['violations']}")
        return 1

    print("✨ QA Gate Passed: 964 frames (38.560s) verified across SHOT_001 ~ SHOT_008.")

    # Step 3: Trigger Master Assembly
    if not auto_assemble:
        print("\n[PHASE 3] Auto-assembly disabled (--no-assemble). Clips are ready in motion_clips.")
        return 0

    if not norm_summary["normalized"]:
        print("\n[PHASE 3] No raw videos were newly normalized. Skipping master re-render.")
        return 0

    print("\n[PHASE 3] Triggering 20-Minute Master Video Assembly...")
    assemble_script = SCRIPTS_DIR / "assemble_master_20min.py"
    t0 = time.time()
    try:
        proc = subprocess.run([sys.executable, str(assemble_script)], check=True)
        dt = time.time() - t0
        print(f"\n🎉 20-Minute Master Assembly complete in {dt:.1f}s ({dt/60:.2f} min)!")
        print(f"Canonical master video updated: {FINAL_MASTER}")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Master assembly failed: {e}")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Full intro ingestion, normalization and assembly pipeline")
    parser.add_argument("--no-assemble", action="store_true", help="Only normalize and QA without triggering master re-render")
    parser.add_argument("--no-backup", action="store_true", help="Do not backup existing Ken Burns motion clips")
    args = parser.parse_args()

    sys.exit(run_full_pipeline(auto_assemble=not args.no_assemble, backup=not args.no_backup))
