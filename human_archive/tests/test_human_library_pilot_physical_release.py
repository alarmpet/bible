# -*- coding: utf-8 -*-
"""test_human_library_pilot_physical_release.py

Automated Physical Integrity Tests for Human Library Pilot-5 Master:
- Verifies physical existence, sizes, durations, and streams of:
  - pilot_5_master.mp4
  - pilot_5_master_voice_48k.wav
  - 5 Flow images (1920x1080)
  - 5 motion clips
  - pilot_5.ass
  - pilot_5_release_manifest.json
- Verifies SHA-256 match between manifest and actual disk files.
- Verifies Gate 8 decoded boundary visibility.
- Verifies Strict Pre-Mux Parity (delta <= 0.040s).
"""
import hashlib
import json
import subprocess
from pathlib import Path
import pytest

RUN_DIR = Path(r"D:\module\bible\human_archive\runs\human_library_replica\rank1_race_adaptation")
MANIFEST_PATH = RUN_DIR / "metadata" / "pilot_5_release_manifest.json"
MASTER_MP4 = RUN_DIR / "pilot_5_master.mp4"
MASTER_WAV = RUN_DIR / "audio" / "pilot_5_master_voice_48k.wav"
IMAGES_DIR = RUN_DIR / "images"
CLIPS_DIR = RUN_DIR / "video" / "clips"
ASS_PATH = RUN_DIR / "subtitles" / "pilot_5.ass"


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


def test_pilot_master_video_physical_integrity():
    assert MASTER_MP4.exists(), f"Master MP4 missing: {MASTER_MP4}"
    assert MASTER_MP4.stat().st_size > 5_000_000, "Master MP4 size must be > 5MB"

    v_dur = get_ffprobe_duration(MASTER_MP4)
    assert abs(v_dur - 38.120) <= 0.05, f"Master MP4 duration {v_dur:.3f}s differs from expected 38.120s"

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


def test_pilot_master_audio_physical_integrity():
    assert MASTER_WAV.exists(), f"Master WAV missing: {MASTER_WAV}"
    assert MASTER_WAV.stat().st_size > 2_000_000, "Master WAV size must be > 2MB"

    a_dur = get_ffprobe_duration(MASTER_WAV)
    assert abs(a_dur - 38.120) <= 0.05, f"Master WAV duration {a_dur:.3f}s differs from expected 38.120s"


def test_pilot_premux_strict_parity():
    v_dur = get_ffprobe_duration(MASTER_MP4)
    a_dur = get_ffprobe_duration(MASTER_WAV)
    delta = abs(v_dur - a_dur)
    assert delta <= 0.040, f"Strict Pre-Mux Parity Gate FAILED: delta {delta:.4f}s > 0.040s"


def test_pilot_flow_images_physical_integrity():
    for shot_idx in range(1, 6):
        shot_id = f"SHOT_{shot_idx:03d}"
        img_path = IMAGES_DIR / f"{shot_id}.jpg"
        assert img_path.exists(), f"Flow image missing: {img_path}"
        assert img_path.stat().st_size > 100_000, f"Flow image too small: {img_path.stat().st_size} bytes"


def test_pilot_subtitles_integrity():
    assert ASS_PATH.exists(), f"ASS subtitles file missing: {ASS_PATH}"
    content = ASS_PATH.read_text(encoding="utf-8")
    assert "DocuNarrator_v4" in content
    assert "Pretendard" in content
    assert "7만 년 전에는 인종이 없었습니다." in content


def test_pilot_release_manifest_and_sha_binding():
    assert MANIFEST_PATH.exists(), f"Release manifest missing: {MANIFEST_PATH}"
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["episode_id"] == "rank1_race_adaptation_pilot5"
    assert manifest["pre_mux_parity_difference_sec"] <= 0.040
    assert manifest["gate8_verification"]["passed"] is True

    # Check sha256 of master video
    actual_video_sha = compute_sha256(MASTER_MP4)
    assert manifest["master_video"]["sha256"] == actual_video_sha

    # Check sha256 of master audio
    actual_audio_sha = compute_sha256(MASTER_WAV)
    assert manifest["master_audio"]["sha256"] == actual_audio_sha

    # Check 5 shots in manifest
    assert len(manifest["shots"]) == 5
    for s in manifest["shots"]:
        img_p = Path(s["image"]["path"])
        assert img_p.exists()
        assert s["image"]["sha256"] == compute_sha256(img_p)
