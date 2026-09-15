# -*- coding: utf-8 -*-
"""Audio timeline builder, trimming, normalization, and WAV master generation."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import re
import subprocess
from typing import Any

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def get_wav_duration(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


def normalize_master_audio(input_wav: Path, output_wav: Path, target_lufs: float = -16.0) -> dict[str, Any]:
    """Perform 2-pass EBU R128 loudness normalization to ensure -16 LUFS, TP <= -1dBTP."""
    # Pass 1: Measure
    measure_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-i", str(input_wav),
        "-af", f"loudnorm=I={target_lufs}:TP=-1.0:LRA=11:print_format=json",
        "-f", "null",
        "-",
    ]
    res = subprocess.run(measure_cmd, capture_output=True, text=True)
    # Find JSON block in stderr
    err_text = res.stderr
    start_idx = err_text.rfind("{")
    end_idx = err_text.rfind("}")
    measure_data = {}
    if start_idx != -1 and end_idx != -1:
        try:
            measure_data = json.loads(err_text[start_idx : end_idx + 1])
        except Exception:
            pass

    # Pass 2: Apply
    if measure_data:
        m_i = measure_data.get("input_i", "-24")
        m_tp = measure_data.get("input_tp", "-2")
        m_lra = measure_data.get("input_lra", "7")
        m_thresh = measure_data.get("input_thresh", "-34")
        af = f"loudnorm=I={target_lufs}:TP=-1.0:LRA=11:measured_I={m_i}:measured_TP={m_tp}:measured_LRA={m_lra}:measured_thresh={m_thresh}:linear=true"
    else:
        af = f"loudnorm=I={target_lufs}:TP=-1.0:LRA=11"

    apply_cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-i", str(input_wav),
        "-af", af,
        "-c:a", "pcm_s16le",
        "-ar", "48000",
        "-ac", "1",
        str(output_wav),
    ]
    subprocess.run(apply_cmd, check=True)
    return measure_data

def measure_active_bounds(path: Path, threshold_db: float = -45.0, min_silence_sec: float = 0.10) -> dict[str, float]:
    cmd = ["ffmpeg", "-hide_banner", "-i", str(path), "-af", f"silencedetect=noise={threshold_db}dB:d={min_silence_sec}", "-f", "null", "-"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    text = result.stderr
    events = [
        (match.group(1), float(match.group(2)))
        for match in re.finditer(r"silence_(start|end): ([0-9.]+)", text)
    ]
    duration = get_wav_duration(path)
    start = 0.0
    if events and events[0][0] == "start" and events[0][1] <= 0.05:
        leading_end = next((value for kind, value in events[1:] if kind == "end"), None)
        if leading_end is not None:
            start = leading_end

    end = duration
    if events and events[-1][0] == "start" and events[-1][1] >= start:
        end = events[-1][1]
    return {"start_sec": round(start, 3), "end_sec": round(end, 3), "duration_sec": round(duration, 3)}


def trim_outer_silence(path: Path, out_path: Path, keep_lead_sec: float = 0.08, keep_tail_sec: float = 0.10) -> dict[str, float]:
    bounds = measure_active_bounds(path)
    start = max(0.0, bounds["start_sec"] - keep_lead_sec)
    end = min(bounds["duration_sec"], bounds["end_sec"] + keep_tail_sec)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(path), "-af", f"atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1", str(out_path)]
    subprocess.run(cmd, check=True)
    return {**bounds, "trim_start_sec": round(start, 3), "trim_end_sec": round(end, 3), "trimmed_duration_sec": round(get_wav_duration(out_path), 3)}


