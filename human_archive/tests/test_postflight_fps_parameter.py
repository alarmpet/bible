# -*- coding: utf-8 -*-
"""Unit tests for ProductionProfile and target_fps parameter in postflight_release.py."""
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from postflight_release import ProductionProfile, verify_postflight


def test_production_profile_defaults():
    prof25 = ProductionProfile.from_fps(25)
    assert prof25.fps == 25
    assert prof25.samples_per_frame == 1920
    assert prof25.window_size == 25
    assert prof25.parity_tolerance_sec == 0.040

    prof30 = ProductionProfile.from_fps(30)
    assert prof30.fps == 30
    assert prof30.samples_per_frame == 1600
    assert prof30.window_size == 30
    assert abs(prof30.parity_tolerance_sec - 0.0333) < 0.001


def test_verify_postflight_30fps_compatibility(tmp_path):
    # Mock video file
    dummy_video = tmp_path / "dummy_30fps.mp4"
    dummy_video.write_bytes(b"dummy video content for testing")

    mock_meta = {
        "video": {
            "width": 1920,
            "height": 1080,
            "sample_aspect_ratio": "1:1",
            "field_order": "progressive",
            "r_frame_rate": "30/1",
            "avg_frame_rate": "30/1",
            "pix_fmt": "yuv420p",
            "color_space": "bt709",
            "color_primaries": "bt709",
            "color_trc": "bt709",
            "color_range": "tv",
        },
        "audio": {
            "codec_name": "aac",
            "sample_rate": "48000",
            "channels": 2,
        },
        "duration_sec": 973.167,
    }

    mock_loudness = {
        "integrated_lufs": -14.0,
        "true_peak_dbfs": -1.5,
    }

    with patch("postflight_release.probe_video_streams", return_value=mock_meta), \
         patch("postflight_release.measure_ebu_r128_loudness", return_value=mock_loudness), \
         patch("postflight_release.compute_file_sha256", return_value="A" * 64):

        ok, report = verify_postflight(dummy_video, target_fps=30)
        assert report["checks"]["framerate"]["status"] == "PASS"
        assert report["checks"]["framerate"]["target_fps"] == 30
        assert report["checks"]["framerate"]["r_frame_rate"] == "30/1"

        # Verify negative control: target_fps=25 on 30fps video fails
        ok_neg, report_neg = verify_postflight(dummy_video, target_fps=25)
        assert report_neg["checks"]["framerate"]["status"] == "FAIL"
        assert report_neg["checks"]["framerate"]["target_fps"] == 25
        assert any("Non-25 CFR detected" in err for err in report_neg["errors"])
