# -*- coding: utf-8 -*-
"""Fail-closed physical verification contracts for the rank1 exact release."""

import hashlib
import json
import sys
import wave
from pathlib import Path

import pytest
from PIL import Image

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from lib.exact_release_verifier import (  # noqa: E402
    audit_ass_strict,
    compute_sha256_chain,
    count_wav_sample_frames,
    validate_manifest_chain,
    validate_audio_probe,
    validate_plate_manifest,
    validate_video_probe,
)


def test_ass_strict_rejects_multiline_events_and_accepts_zero_overlap(tmp_path):
    ass = tmp_path / "subtitles.ass"
    ass.write_text(
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:01.00,0:00:02.00,DocuNarrator_Exact,,0,0,0,,한 줄\n"
        "Dialogue: 0,0:00:02.00,0:00:03.00,DocuNarrator_Exact,,0,0,0,,두 줄\\N금지\n",
        encoding="utf-8",
    )

    result = audit_ass_strict(ass, target_duration_sec=3.0)

    assert result["dialogue_events"] == 2
    assert result["zero_start_events"] == 0
    assert result["overlap_events"] == 0
    assert result["multiline_events"] == 1
    assert result["status"] == "FAIL"


def test_ass_strict_allows_one_centisecond_terminal_rounding(tmp_path):
    ass = tmp_path / "rounded.ass"
    ass.write_text(
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:01.00,0:16:13.17,DocuNarrator_Exact,,0,0,0,,끝\n",
        encoding="utf-8",
    )

    result = audit_ass_strict(ass, target_duration_sec=973.166667)

    assert result["status"] == "PASS"


def test_wav_sample_count_uses_riff_data_chunk(tmp_path):
    wav_path = tmp_path / "audio.wav"
    with wave.open(str(wav_path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(48_000)
        handle.writeframes(b"\x00\x00\x00\x00" * 7)

    assert count_wav_sample_frames(wav_path) == 7


def test_plate_manifest_requires_distinct_bound_2304x1296_assets(tmp_path):
    image_path = tmp_path / "SHOT_001_A.jpg"
    Image.new("RGB", (2304, 1296), (20, 30, 40)).save(image_path, quality=95)
    image_sha = hashlib.sha256(image_path.read_bytes()).hexdigest().upper()

    valid = validate_plate_manifest(
        [
            {
                "plate_id": "SHOT_001_A",
                "path": str(image_path),
                "sha256": image_sha,
                "width": 2304,
                "height": 1296,
            }
        ],
        expected_count=1,
    )
    assert valid["status"] == "PASS"
    assert valid["unique_content_count"] == 1

    invalid = validate_plate_manifest(
        [{"plate_id": "SHOT_001_B", "concept_kr": "missing binding"}],
        expected_count=1,
    )
    assert invalid["status"] == "FAIL"
    assert any("path" in error for error in invalid["errors"])


def test_video_probe_requires_exact_frame_count_and_cfr():
    valid = validate_video_probe(
        {
            "codec_name": "h264",
            "profile": "High",
            "width": 1920,
            "height": 1080,
            "r_frame_rate": "30/1",
            "avg_frame_rate": "30/1",
            "nb_frames": "29195",
            "duration": "973.166667",
        }
    )
    assert valid["status"] == "PASS"

    invalid = validate_video_probe(
        {
            "width": 1920,
            "height": 1080,
            "r_frame_rate": "30/1",
            "avg_frame_rate": "30/1",
            "nb_frames": "29194",
            "duration": "973.133333",
        }
    )
    assert invalid["status"] == "FAIL"
    assert any("frame" in error for error in invalid["errors"])


def test_audio_probe_requires_aac_48k_stereo():
    valid = validate_audio_probe(
        {"codec_name": "aac", "sample_rate": "48000", "channels": 2}
    )
    assert valid["status"] == "PASS"

    invalid = validate_audio_probe(
        {"codec_name": "pcm_s16le", "sample_rate": "44100", "channels": 1}
    )
    assert invalid["status"] == "FAIL"
    assert any("AAC" in error or "48000" in error or "stereo" in error for error in invalid["errors"])


def test_manifest_chain_requires_order_and_root_digest(tmp_path):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"artifact")
    artifact_sha = hashlib.sha256(artifact.read_bytes()).hexdigest().upper()
    entries = [{"artifact_id": "artifact", "sha256": artifact_sha}]

    manifest = {
        "sha256_chain": entries,
        "sha256_chain_root": compute_sha256_chain(entries),
    }
    assert validate_manifest_chain(manifest)["status"] == "PASS"

    missing_root = {"sha256_chain": entries}
    assert validate_manifest_chain(missing_root)["status"] == "FAIL"
