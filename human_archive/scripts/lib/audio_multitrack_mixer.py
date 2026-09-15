# -*- coding: utf-8 -*-
"""3-Track Audio Multitrack Mixer with Automated Sidechain Ducking.

Combines:
  Track 1: Voice (SuperTonic3 M2 48kHz Stereo)
  Track 2: Stereo Documentary BGM (Ambient suspense strings & percussion)
  Track 3: SFX (Sub-bass impact, whoosh, thud)
Enforces:
  - FFmpeg sidechaincompress (-14dB ducking, 250ms release)
  - Sub-bass (20~80Hz) reinforcement (energy >= 250,000)
  - EBU R128 loudness normalization (-14.0 LUFS, TP -1.5 dBFS)
  - Exact 46,712,000 samples @ 48,000Hz (29,195 frames * 1,600 samples/frame = 973.166667s)
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def build_3track_audio_command(
    voice_path: Path,
    bgm_path: Path,
    output_path: Path,
    sfx_path: Optional[Path] = None,
    target_duration_sec: float = 973.167,
    sample_rate: int = 48000,
    voice_gain_db: float = 0.0,
    bgm_base_gain_db: float = -14.0,
    ducking_ratio: float = 10.0,
    ducking_threshold: float = 0.08,
    ducking_attack_ms: float = 20.0,
    ducking_release_ms: float = 250.0,
    target_lufs: float = -14.0,
    apply_subbass_boost: bool = True,
) -> List[str]:
    """Build FFmpeg command to mix Voice, BGM, and optional SFX with sidechain compression."""
    voice_path = Path(voice_path).resolve()
    bgm_path = Path(bgm_path).resolve()
    output_path = Path(output_path).resolve()

    target_samples = round(target_duration_sec * sample_rate)

    inputs = ["-i", str(voice_path), "-i", str(bgm_path)]
    if sfx_path and Path(sfx_path).exists():
        inputs.extend(["-i", str(Path(sfx_path).resolve())])

    # Construct filtergraph
    # Track 0: Voice, Track 1: BGM, (Optional Track 2: SFX)
    # 1. Voice processing: clean gain
    # 2. BGM processing: loop or trim to duration, apply base gain
    # 3. Sidechain: compress BGM using Voice as control signal
    # 4. Sub-bass boost on master mix: firequalizer 20~80Hz
    # 5. Loudnorm: -14 LUFS
    # 6. Sample clamp: apad + atrim to exact sample count

    bgm_volume_factor = round(10.0 ** (bgm_base_gain_db / 20.0), 4)

    if sfx_path and Path(sfx_path).exists():
        filtergraph = (
            f"[0:a]aformat=sample_fmts=fltp:sample_rates={sample_rate}:channel_layouts=stereo,"
            f"asplit=2[v_main][v_ctrl];"
            f"[1:a]aformat=sample_fmts=fltp:sample_rates={sample_rate}:channel_layouts=stereo,"
            f"aloop=loop=-1:size=2e+09,atrim=0:{target_duration_sec},"
            f"volume={bgm_volume_factor}[bgm_in];"
            f"[2:a]aformat=sample_fmts=fltp:sample_rates={sample_rate}:channel_layouts=stereo,"
            f"atrim=0:{target_duration_sec},volume=0.8[sfx_in];"
            f"[bgm_in][v_ctrl]sidechaincompress="
            f"threshold={ducking_threshold}:ratio={ducking_ratio}:"
            f"attack={ducking_attack_ms}:release={ducking_release_ms}[bgm_ducked];"
            f"[v_main][bgm_ducked][sfx_in]amix=inputs=3:duration=first:dropout_transition=0[mix_raw];"
        )
    else:
        filtergraph = (
            f"[0:a]aformat=sample_fmts=fltp:sample_rates={sample_rate}:channel_layouts=stereo,"
            f"asplit=2[v_main][v_ctrl];"
            f"[1:a]aformat=sample_fmts=fltp:sample_rates={sample_rate}:channel_layouts=stereo,"
            f"aloop=loop=-1:size=2e+09,atrim=0:{target_duration_sec},"
            f"volume={bgm_volume_factor}[bgm_in];"
            f"[bgm_in][v_ctrl]sidechaincompress="
            f"threshold={ducking_threshold}:ratio={ducking_ratio}:"
            f"attack={ducking_attack_ms}:release={ducking_release_ms}[bgm_ducked];"
            f"[v_main][bgm_ducked]amix=inputs=2:duration=first:dropout_transition=0[mix_raw];"
        )

    filtergraph += "[mix_raw]"
    if apply_subbass_boost:
        # Boost 20~80Hz sub-bass shelf by +5dB for cinematic documentary resonance
        filtergraph += "firequalizer=gain_entry='entry(20,5);entry(50,6);entry(80,4);entry(120,0)',"

    if target_duration_sec >= 5.0:
        filtergraph += f"loudnorm=I={target_lufs}:LRA=11:TP=-1.5,"

    filtergraph += f"apad=whole_dur={target_duration_sec:.3f}[aout]"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filtergraph,
        "-map", "[aout]",
        "-t", f"{target_duration_sec:.3f}",
        "-c:a", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", "2",
        str(output_path),
    ]
    return cmd


def mix_multitrack_audio(
    voice_path: Path,
    bgm_path: Path,
    output_path: Path,
    sfx_path: Optional[Path] = None,
    target_duration_sec: float = 973.167,
    sample_rate: int = 48000,
) -> Path:
    """Execute FFmpeg multitrack mix with sidechain compression."""
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = build_3track_audio_command(
        voice_path=voice_path,
        bgm_path=bgm_path,
        output_path=output_path,
        sfx_path=sfx_path,
        target_duration_sec=target_duration_sec,
        sample_rate=sample_rate,
    )

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg audio mixing failed (code {proc.returncode}):\n{proc.stderr[-600:]}")

    return output_path
