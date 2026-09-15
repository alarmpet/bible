# -*- coding: utf-8 -*-
"""Probe media properties, stream formats, and loudness metrics."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def probe_video_streams(video_path: Path) -> dict[str, Any]:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_format",
        "-show_streams",
        "-of", "json",
        str(video_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)
    fmt = data.get("format", {})
    streams = data.get("streams", [])

    v_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

    return {
        "duration_sec": float(fmt.get("duration", 0.0)),
        "size_bytes": int(fmt.get("size", video_path.stat().st_size)),
        "video": {
            "codec_name": v_stream.get("codec_name"),
            "width": v_stream.get("width"),
            "height": v_stream.get("height"),
            "sample_aspect_ratio": v_stream.get("sample_aspect_ratio", "1:1"),
            "display_aspect_ratio": v_stream.get("display_aspect_ratio", "16:9"),
            "r_frame_rate": v_stream.get("r_frame_rate"),
            "avg_frame_rate": v_stream.get("avg_frame_rate"),
            "nb_frames": int(v_stream.get("nb_frames", 0) or 0),
            "pix_fmt": v_stream.get("pix_fmt"),
            "color_space": v_stream.get("color_space"),
            "color_primaries": v_stream.get("color_primaries"),
            "color_trc": v_stream.get("color_trc") or v_stream.get("color_transfer"),
            "color_range": v_stream.get("color_range"),
            "field_order": v_stream.get("field_order", "progressive"),
        },
        "audio": {
            "codec_name": a_stream.get("codec_name"),
            "sample_rate": int(a_stream.get("sample_rate", 0)),
            "channels": int(a_stream.get("channels", 0)),
        },
    }


def measure_ebu_r128_loudness(video_path: Path) -> dict[str, float]:
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-i", str(video_path),
        "-af", "loudnorm=print_format=json",
        "-f", "null",
        "-",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    err_text = res.stderr
    start_idx = err_text.rfind("{")
    end_idx = err_text.rfind("}")
    if start_idx != -1 and end_idx != -1:
        try:
            data = json.loads(err_text[start_idx : end_idx + 1])
            return {
                "input_i": float(data.get("input_i", -99.0)),
                "input_tp": float(data.get("input_tp", -99.0)),
                "input_lra": float(data.get("input_lra", 0.0)),
            }
        except Exception:
            pass
    return {"input_i": -99.0, "input_tp": -99.0, "input_lra": 0.0}
