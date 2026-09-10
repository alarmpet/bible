from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from render_episode_v2 import build_mux_command
from run_neanderthal_full_pipeline import (
    AVDurationMismatchError,
    PreflightServiceUnavailableError,
    build_neanderthal_master_mux_command,
    probe_required_external_services,
    validate_premux_av_parity,
)


def test_mux_command_contains_canonical_subtitle_and_bgm_ducking_contract(tmp_path: Path) -> None:
    command = build_mux_command(
        tmp_path / "visual.mp4",
        tmp_path / "voice.wav",
        tmp_path / "subtitles.ass",
        tmp_path / "candidate.part",
        bgm_file=tmp_path / "bgm.wav",
    )
    joined = " ".join(command)
    assert "-filter_complex" in command
    assert "volume=-18dB" in joined
    assert "sidechaincompress" in joined
    assert "[vout]" in joined and "[aout]" in joined
    assert "subtitles='" in joined
    assert "-stream_loop -1" in joined


def test_mux_without_bgm_preserves_legacy_two_input_path(tmp_path: Path) -> None:
    command = build_mux_command(
        tmp_path / "visual.mp4",
        tmp_path / "voice.wav",
        tmp_path / "subtitles.ass",
        tmp_path / "candidate.part",
    )
    assert "-filter_complex" not in command
    assert "-vf" in command
    assert "-map" in command


def test_neanderthal_master_mux_does_not_truncate_audio_to_video(tmp_path: Path) -> None:
    command = build_neanderthal_master_mux_command(
        tmp_path / "video.mp4",
        tmp_path / "audio.wav",
        tmp_path / "subtitles.ass",
        tmp_path / "master.mp4",
    )
    assert "-shortest" not in command
    assert "-map" in command


def test_neanderthal_master_mux_physical_parity_with_lavfi_sources(tmp_path: Path) -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg or ffprobe not installed in environment")

    # Generate 2.0s synthetic video
    video_path = tmp_path / "synthetic_video.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=25:duration=2.0",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(video_path)
    ], check=True)

    # Generate 2.0s synthetic audio
    audio_path = tmp_path / "synthetic_audio.wav"
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2.0:sample_rate=48000",
        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
        str(audio_path)
    ], check=True)

    # Validate Pre-Mux Parity Gate
    v_dur, a_dur, diff = validate_premux_av_parity(video_path, audio_path, max_tolerance_sec=0.040)
    assert diff <= 0.040

    # Minimal ASS subtitle
    ass_path = tmp_path / "test.ass"
    ass_path.write_text(
        "[Script Info]\nTitle: Test\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:00.00,0:00:01.50,Default,,0,0,0,,Test Subtitle\n",
        encoding="utf-8"
    )

    master_path = tmp_path / "master.mp4"
    cmd = build_neanderthal_master_mux_command(video_path, audio_path, ass_path, master_path)
    subprocess.run(cmd, check=True)

    assert master_path.is_file() and master_path.stat().st_size > 0

    # Probe output streams for parity
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=codec_type,duration",
        "-of", "json",
        str(master_path)
    ]
    res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    streams = json.loads(res.stdout)["streams"]
    v_s = next(s for s in streams if s["codec_type"] == "video")
    a_s = next(s for s in streams if s["codec_type"] == "audio")
    v_out_dur = float(v_s.get("duration", 0))
    a_out_dur = float(a_s.get("duration", 0))
    assert abs(v_out_dur - a_out_dur) <= 0.040, f"Mux output parity mismatch: V={v_out_dur}, A={a_out_dur}"


def test_premux_parity_gate_rejects_asymmetric_av_durations(tmp_path: Path) -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not installed")

    # 1.0s video vs 3.0s audio
    video_path = tmp_path / "short_video.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=25:duration=1.0",
        "-c:v", "libx264", str(video_path)
    ], check=True)

    audio_path = tmp_path / "long_audio.wav"
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3.0:sample_rate=48000",
        "-c:a", "pcm_s16le", str(audio_path)
    ], check=True)

    with pytest.raises(AVDurationMismatchError) as exc_info:
        validate_premux_av_parity(video_path, audio_path, max_tolerance_sec=0.040)
    assert "Pre-Mux Strict Parity Gate FAILED" in str(exc_info.value)


def test_preflight_probe_fails_closed_when_external_service_offline() -> None:
    # Port 3093 (SuperTonic3) is offline in current environment; require_tts must fail-closed
    with pytest.raises(PreflightServiceUnavailableError) as exc_info:
        probe_required_external_services(require_tts=True)
    assert "SuperTonic3 TTS service is OFFLINE" in str(exc_info.value)
