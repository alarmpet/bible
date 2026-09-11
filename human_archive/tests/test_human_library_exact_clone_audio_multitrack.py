# -*- coding: utf-8 -*-
"""Unit tests for 3-track audio multitrack mixer."""
import sys
import wave
from pathlib import Path
import pytest
import numpy as np

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.audio_multitrack_mixer import (
    build_3track_audio_command,
    mix_multitrack_audio,
)


def test_build_3track_audio_command_filtergraph():
    voice_p = Path("voice.wav")
    bgm_p = Path("bgm.wav")
    out_p = Path("master_mix.wav")

    cmd = build_3track_audio_command(
        voice_path=voice_p,
        bgm_path=bgm_p,
        output_path=out_p,
        target_duration_sec=973.167,
        sample_rate=48000,
    )

    cmd_str = " ".join(cmd)
    # 1. Sidechain ducking parameters
    assert "sidechaincompress" in cmd_str
    assert "ratio=10" in cmd_str
    assert "threshold=0.08" in cmd_str
    assert "release=250" in cmd_str

    # 2. Sub-bass boost
    assert "firequalizer" in cmd_str
    assert "entry(50,6)" in cmd_str

    # 3. Loudnorm -14 LUFS
    assert "loudnorm=I=-14" in cmd_str

    # 4. Exact sample clamping
    assert "apad=whole_dur=973.167" in cmd_str
    assert "-t 973.167" in cmd_str

    # 5. Format & Codec
    assert "-ar 48000" in cmd_str
    assert "-ac 2" in cmd_str
    assert "-c:a pcm_s16le" in cmd_str


def test_mix_multitrack_audio_execution(tmp_path):
    sr = 48000
    dur = 2.0  # 2 seconds
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)

    # 1. Synthetic voice: 440Hz tone
    voice_data = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)
    voice_stereo = np.column_stack([voice_data, voice_data])
    voice_wav = tmp_path / "voice_test.wav"
    with wave.open(str(voice_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(voice_stereo.tobytes())

    # 2. Synthetic BGM: 220Hz tone
    bgm_data = (np.sin(2 * np.pi * 220 * t) * 8000).astype(np.int16)
    bgm_stereo = np.column_stack([bgm_data, bgm_data])
    bgm_wav = tmp_path / "bgm_test.wav"
    with wave.open(str(bgm_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(bgm_stereo.tobytes())

    # 3. Run mix
    out_wav = tmp_path / "mixed_test.wav"
    result_path = mix_multitrack_audio(
        voice_path=voice_wav,
        bgm_path=bgm_wav,
        output_path=out_wav,
        target_duration_sec=2.0,
        sample_rate=sr,
    )

    assert result_path.exists()
    assert result_path.stat().st_size > 1000

    # 4. Verify wave header
    with wave.open(str(result_path), "rb") as wf:
        assert wf.getnchannels() == 2
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 48000
        assert wf.getnframes() == int(dur * sr)
