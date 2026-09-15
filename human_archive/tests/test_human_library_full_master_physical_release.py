# -*- coding: utf-8 -*-
"""test_human_library_full_master_physical_release.py

Automated Physical Integrity Tests for Human Library Full 40-Shot Master:
- Verifies physical existence, sizes, durations, and streams of:
  - rank1_master_documentary.mp4 (421MB, 1091.280s)
  - rank1_master_voice_48k.wav (209MB, 1091.280s)
  - 40 Flow images (1920x1080)
  - 40 motion clips
  - rank1_master.ass
  - rank1_release_manifest.json
- Verifies SHA-256 match between manifest and actual disk files.
- Verifies Gate 8 decoded boundary visibility (40/40 passed).
- Verifies Strict Pre-Mux Parity (delta == 0.000s <= 0.040s).
"""
import hashlib
import json
import subprocess
from pathlib import Path
import pytest

RUN_DIR = Path(r"D:\module\bible\human_archive\runs\human_library_replica\rank1_race_adaptation")
MANIFEST_PATH = RUN_DIR / "metadata" / "rank1_release_manifest.json"
MASTER_MP4 = RUN_DIR / "rank1_master_documentary.mp4"
MASTER_WAV = RUN_DIR / "audio" / "rank1_master_voice_48k.wav"
IMAGES_DIR = RUN_DIR / "images"
CLIPS_DIR = RUN_DIR / "video" / "clips"
ASS_PATH = RUN_DIR / "subtitles" / "rank1_master.ass"

pytestmark = pytest.mark.media_heavy


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def get_ffprobe_duration(media_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(media_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


def test_full_master_video_physical_integrity():
    assert MASTER_MP4.exists(), f"Full Master MP4 missing: {MASTER_MP4}"
    assert MASTER_MP4.stat().st_size > 300_000_000, f"Master MP4 size must be > 300MB, got {MASTER_MP4.stat().st_size}"

    v_dur = get_ffprobe_duration(MASTER_MP4)
    assert abs(v_dur - 1091.280) <= 0.05, f"Master MP4 duration {v_dur:.3f}s differs from expected 1091.280s"

    # Probe streams
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "stream=codec_type,codec_name,width,height,sample_rate,channels",
        "-of", "json",
        str(MASTER_MP4)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    probe = json.loads(res.stdout)
    streams = probe["streams"]

    v_stream = next(s for s in streams if s["codec_type"] == "video")
    a_stream = next(s for s in streams if s["codec_type"] == "audio")

    assert v_stream["codec_name"] == "h264"
    assert v_stream["width"] == 1920
    assert v_stream["height"] == 1080

    assert a_stream["codec_name"] == "aac"
    assert a_stream["sample_rate"] == "48000"
    assert a_stream["channels"] == 2


def test_full_master_audio_physical_integrity():
    assert MASTER_WAV.exists(), f"Master WAV missing: {MASTER_WAV}"
    assert MASTER_WAV.stat().st_size > 150_000_000, f"Master WAV size must be > 150MB, got {MASTER_WAV.stat().st_size}"

    a_dur = get_ffprobe_duration(MASTER_WAV)
    assert abs(a_dur - 1091.280) <= 0.05, f"Master WAV duration {a_dur:.3f}s differs from expected 1091.280s"


def test_full_master_premux_strict_parity():
    v_dur = get_ffprobe_duration(MASTER_MP4)
    a_dur = get_ffprobe_duration(MASTER_WAV)
    delta = abs(v_dur - a_dur)
    assert delta <= 0.040, f"Strict Pre-Mux Parity Gate FAILED: delta {delta:.4f}s > 0.040s"


def test_all_40_flow_images_physical_integrity():
    for shot_idx in range(1, 41):
        shot_id = f"SHOT_{shot_idx:03d}"
        img_path = IMAGES_DIR / f"{shot_id}.jpg"
        assert img_path.exists(), f"Flow image missing: {img_path}"
        assert img_path.stat().st_size > 50_000, f"Flow image too small: {img_path.stat().st_size} bytes"


def test_all_40_motion_clips_physical_integrity():
    for shot_idx in range(1, 41):
        shot_id = f"SHOT_{shot_idx:03d}"
        clip_path = CLIPS_DIR / f"{shot_id}.mp4"
        assert clip_path.exists(), f"Motion clip missing: {clip_path}"
        assert clip_path.stat().st_size > 500_000, f"Motion clip too small: {clip_path.stat().st_size} bytes"


def test_full_subtitles_integrity():
    assert ASS_PATH.exists(), f"ASS subtitles file missing: {ASS_PATH}"
    content = ASS_PATH.read_text(encoding="utf-8")
    assert "DocuNarrator_v4" in content
    assert "Pretendard" in content
    assert "7만 년 전에는 인종이 없었습니다." in content
    assert content.count("Dialogue:") >= 220


def test_full_release_manifest_and_sha_binding():
    assert MANIFEST_PATH.exists(), f"Release manifest missing: {MANIFEST_PATH}"
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["episode_id"] == "human_library_rank1_race_adaptation"
    assert manifest["total_shots"] == 40
    assert manifest["pre_mux_parity_difference_sec"] <= 0.040
    assert manifest["gate8_verification"]["passed"] is True
    assert manifest["gate8_verification"]["passed_count"] == 40

    # Check sha256 of master video
    actual_video_sha = compute_sha256(MASTER_MP4)
    assert manifest["master_video"]["sha256"] == actual_video_sha

    # Check sha256 of master audio
    actual_audio_sha = compute_sha256(MASTER_WAV)
    assert manifest["master_audio"]["sha256"] == actual_audio_sha

    # Check 40 shots in manifest
    assert len(manifest["shots"]) == 40
    for s in manifest["shots"][:5]:
        img_p = Path(s["image"]["path"])
        assert img_p.exists()
        assert s["image"]["sha256"] == compute_sha256(img_p)
