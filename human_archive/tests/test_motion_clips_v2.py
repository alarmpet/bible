# -*- coding: utf-8 -*-
"""Test motion clip generation, square pixel ratio, 25fps CFR, and bt709 color tags."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import pytest
from PIL import Image

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.motion_plan import build_motion_filter
import build_motion_clips_v2


def test_motion_filter_includes_setsar_and_frame_formula():
    vf_pan = build_motion_filter("pan_right", duration_sec=5.0, fps=25)
    assert "setsar=1" in vf_pan
    assert "scale=2304:1296" in vf_pan
    assert "n/125" in vf_pan # 5.0s * 25fps = 125 frames

    vf_zoom = build_motion_filter("zoom_in", duration_sec=4.0, fps=25)
    assert "setsar=1" in vf_zoom
    assert "100" in vf_zoom # 4.0s * 25fps = 100 frames


def test_rendered_motion_clip_ffprobe_properties(tmp_path: Path):
    # Create single test image
    img_path = tmp_path / "test.jpg"
    img = Image.new("RGB", (1920, 1080), color=(100, 150, 200))
    img.save(img_path)

    out_mp4 = tmp_path / "motion.mp4"
    vf = build_motion_filter("pan_right", duration_sec=2.0, fps=25)

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-loop", "1",
        "-i", str(img_path),
        "-t", "2.0",
        "-r", "25",
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-color_range", "tv",
        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True)

    # Probe properties
    probe_cmd = [
        "ffprobe",
        "-v", "error",
        "-show_streams",
        "-of", "json",
        str(out_mp4),
    ]
    res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)
    v_stream = data["streams"][0]

    assert v_stream["width"] == 1920
    assert v_stream["height"] == 1080
    assert v_stream["sample_aspect_ratio"] in ["1:1", None]
    assert v_stream["r_frame_rate"] == "25/1"
    assert v_stream["pix_fmt"] == "yuv420p"
    assert v_stream["color_space"] == "bt709"


def test_motion_build_aborts_before_assets_when_visual_gate_fails(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(build_motion_clips_v2, "verify_visual_build", lambda **kwargs: (False, ["OCR failed"]), raising=False)
    with pytest.raises(SystemExit, match="Visual QA gate failed"):
        build_motion_clips_v2.build_motion_clips(tmp_path)
