# -*- coding: utf-8 -*-
"""test_human_library_rank2_exact_physical_release.py

Automated Physical Release Gate Tests for Rank 2 1:1 Exact Replication:
- Title: "잊혀진 문명, 세계 최강이 사라진 이유" (YouTube o-x6sIGANPY, 1,440.000s / 24.00m)
- Verifies physical existence, byte sizes, durations, frame counts, sample frames, and SHA-256 chains of:
  - rank2_exact_master_documentary.mp4 (485MB, 43,200 frames @ 30fps CFR)
  - NOLLAM-HUMAN-LIBRARY-RANK2-EXACT-MASTER.mp4 (Output Mirror, 100% bit-exact SHA-256)
  - rank2_exact_master_audio_48k.wav (276MB, exactly 69,120,000 sample frames)
  - 128 2D Ligne Claire plates (2304x1296 Lanczos in images_2d_master/)
  - rank2_exact_master_subtitles.ass (958 strict 1-line events)
  - rank2_exact_release_manifest.json (Deterministic SHA-256 chain root)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.exact_release_verifier import (
    audit_ass_strict,
    audit_subcut_montage_plan,
    count_wav_sample_frames,
    validate_manifest_chain,
    validate_plate_manifest,
    validate_video_probe,
    validate_audio_probe,
)

EP_DIR = Path(r"D:\module\bible\human_archive\runs\human_library_replica\rank2_forgotten_civilization")
OUTPUT_MIRROR_MP4 = Path(r"D:\module\output\NOLLAM-HUMAN-LIBRARY-RANK2-EXACT-MASTER.mp4")
RELEASE_MANIFEST_PATH = EP_DIR / "metadata" / "rank2_exact_release_manifest.json"
MASTER_MP4 = EP_DIR / "rank2_exact_master_documentary.mp4"
RAW_MONTAGE_MP4 = EP_DIR / "video" / "rank2_exact_montage_raw.mp4"
MASTER_WAV = EP_DIR / "audio" / "rank2_exact_master_audio_48k.wav"
ASS_PATH = EP_DIR / "subtitles" / "rank2_exact_master_subtitles.ass"
PLATES_DIR = EP_DIR / "images_2d_master"
PLATES_PLAN_PATH = EP_DIR / "metadata" / "master_plates_composition_plan.json"
SUBCUT_PLAN_PATH = EP_DIR / "metadata" / "subcut_montage_plan.json"

TARGET_DURATION_SEC = 1440.000
TARGET_FRAMES = 43200
TARGET_SAMPLES = 69120000


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def get_ffprobe_info(media_path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=codec_type,codec_name,profile,width,height,r_frame_rate,avg_frame_rate,duration,sample_rate,channels,nb_frames,bit_rate",
        "-show_entries", "format=duration,size",
        "-of", "json",
        str(media_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def test_rank2_exact_release_manifest_integrity():
    assert RELEASE_MANIFEST_PATH.exists(), f"Release manifest missing: {RELEASE_MANIFEST_PATH}"
    manifest = json.loads(RELEASE_MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["release_id"] == "HL-RANK2-EXACT-CLONE-V1"
    assert manifest["status"] == "PROMOTED_MASTER"
    assert manifest["target_duration_sec"] == TARGET_DURATION_SEC
    assert manifest["total_frames"] == TARGET_FRAMES
    assert manifest["target_audio_sample_frames"] == TARGET_SAMPLES
    assert manifest["parity_delta_sec"] <= 0.033

    chain_check = validate_manifest_chain(manifest)
    assert chain_check["status"] == "PASS", "; ".join(chain_check.get("errors", []))

    # Check each artifact listed exists and matches declared SHA-256
    for art_id, art_info in manifest["artifacts"].items():
        art_path = Path(art_info["path"])
        assert art_path.exists(), f"Artifact {art_id} file missing: {art_path}"
        assert art_path.stat().st_size == art_info["size_bytes"]
        assert _sha256(art_path) == art_info["sha256"]


def test_rank2_master_mp4_physical_stream_integrity():
    assert MASTER_MP4.exists(), f"Master MP4 missing: {MASTER_MP4}"
    assert MASTER_MP4.stat().st_size > 400_000_000, f"Master MP4 size must be > 400MB: {MASTER_MP4.stat().st_size}"

    info = get_ffprobe_info(MASTER_MP4)
    v_stream = next(s for s in info["streams"] if s["codec_type"] == "video")
    a_stream = next(s for s in info["streams"] if s["codec_type"] == "audio")

    v_check = validate_video_probe(
        v_stream,
        target_frames=TARGET_FRAMES,
        target_fps="30/1",
        target_duration_sec=TARGET_DURATION_SEC,
        duration_tolerance_sec=0.033333,
    )
    assert v_check["status"] == "PASS", "; ".join(v_check["errors"])

    a_check = validate_audio_probe(a_stream)
    assert a_check["status"] == "PASS", "; ".join(a_check["errors"])

    v_dur = float(v_stream.get("duration", info["format"]["duration"]))
    a_dur = float(a_stream.get("duration", info["format"]["duration"]))
    assert abs(v_dur - a_dur) <= 0.033, f"AV Parity Delta {abs(v_dur - a_dur)}s > 0.033s"


def test_rank2_output_mirror_bit_exactness():
    assert OUTPUT_MIRROR_MP4.exists(), f"Output mirror MP4 missing: {OUTPUT_MIRROR_MP4}"
    assert OUTPUT_MIRROR_MP4.stat().st_size == MASTER_MP4.stat().st_size
    assert _sha256(OUTPUT_MIRROR_MP4) == _sha256(MASTER_MP4)


def test_rank2_all_128_master_plates_physical_contract():
    plan = json.loads(PLATES_PLAN_PATH.read_text(encoding="utf-8"))
    plate_check = validate_plate_manifest(plan["plates"], expected_count=128)
    assert plate_check["status"] == "PASS", "; ".join(plate_check["errors"])
    assert plate_check["plate_count"] == 128
    assert plate_check["unique_content_count"] == 128


def test_rank2_master_audio_exact_sample_frames():
    assert MASTER_WAV.exists(), f"Master WAV missing: {MASTER_WAV}"
    samples = count_wav_sample_frames(MASTER_WAV)
    assert samples == TARGET_SAMPLES, f"Expected {TARGET_SAMPLES} samples, got {samples}"


def test_rank2_subtitles_strict_contract():
    assert ASS_PATH.exists(), f"ASS subtitles missing: {ASS_PATH}"
    ass_check = audit_ass_strict(ASS_PATH, target_duration_sec=TARGET_DURATION_SEC)
    assert ass_check["status"] == "PASS", "; ".join(ass_check["errors"])
    assert ass_check["zero_start_events"] == 0
    assert ass_check["overlap_events"] == 0
    assert ass_check["multiline_events"] == 0


def test_rank2_subcut_montage_plan_no_aba_loops():
    assert SUBCUT_PLAN_PATH.exists(), f"Subcut montage plan missing: {SUBCUT_PLAN_PATH}"
    subcut_data = json.loads(SUBCUT_PLAN_PATH.read_text(encoding="utf-8"))
    cuts = subcut_data.get("cuts", [])
    check = audit_subcut_montage_plan(cuts)
    assert check["status"] == "PASS", "; ".join(check["errors"])
    assert check["aba_repeats"] == 0, f"Detected {check['aba_repeats']} ABA loops"
    assert check["role_reversals"] == 0, f"Detected {check['role_reversals']} role reversals"
    assert check["total_frames"] == TARGET_FRAMES
    assert 800 <= check["total_cuts"] <= 900
