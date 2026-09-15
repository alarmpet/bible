# -*- coding: utf-8 -*-
"""Synthesize documentary audio using SuperTonic3 M4 voice and build 48k normalized audio master."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.audio_timeline import get_wav_duration, normalize_master_audio
from lib.tts_provider import ToneFixtureProvider, SupertonicHttpProvider, validate_audio_provenance

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def generate_silence_wav(duration_sec: float, out_wav: Path):
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=mono:d={duration_sec:.3f}",
        "-c:a", "pcm_s16le", str(out_wav),
    ]
    subprocess.run(cmd, check=True)


def build_audio_master(
    build_dir: Path,
    audio_mode: str = "supertonic3",
    tts_url: str | None = None,
) -> Path:
    build_dir = Path(build_dir).resolve()
    contract_path = build_dir.parent / "source" / "shot_contract_v4.json"
    if not contract_path.exists():
        contract_path = build_dir.parent / "source" / "shot_contract.json"
    if not contract_path.exists():
        raise SystemExit(f"Contract not found: {contract_path}")

    contract_data = json.loads(contract_path.read_text(encoding="utf-8"))
    shots = contract_data.get("shots", [])

    audio_dir = build_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    if audio_mode == "supertonic3":
        try:
            provider = SupertonicHttpProvider(tts_url or "http://127.0.0.1:3093")
        except Exception:
            provider = ToneFixtureProvider()
    else:
        provider = ToneFixtureProvider()

    manifest_shots = []
    current_time = 0.0
    gap_sec = 0.35

    silence_wav = audio_dir / "silence_gap.wav"
    generate_silence_wav(gap_sec, silence_wav)

    wav_concat_list = []

    for idx, s in enumerate(shots):
        sid = s["shot_id"]
        text = s.get("tts_text", s.get("display_text", ""))
        shot_wav = audio_dir / f"{sid}.wav"

        if isinstance(provider, SupertonicHttpProvider):
            prov_info = provider.synthesize_phrase(text, shot_wav, speed=0.86, voice="M4")
        else:
            prov_info = provider.synthesize_phrase(text, shot_wav, speed=0.96)
        dur = get_wav_duration(shot_wav)

        start_s = round(current_time, 3)
        end_s = round(current_time + dur, 3)

        manifest_shots.append({
            "order": s["order"],
            "shot_id": sid,
            "chapter": s["chapter"],
            "display_text": s["display_text"],
            "tts_text": text,
            "duration": dur,
            "startSeconds": start_s,
            "endSeconds": end_s,
            "audio_file": shot_wav.name,
            "provenance": prov_info,
        })
        wav_concat_list.append(shot_wav)
        current_time = end_s

        # Insert gap if not last shot
        if idx < len(shots) - 1:
            wav_concat_list.append(silence_wav)
            current_time += gap_sec

    # Concat raw master
    concat_txt = audio_dir / "audio_concat.txt"
    concat_txt.write_text("\n".join(f"file '{p.name}'" for p in wav_concat_list), encoding="utf-8")

    raw_master = audio_dir / "raw_master.wav"
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_txt),
        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1",
        str(raw_master)
    ], cwd=audio_dir, check=True)

    # Normalize master to -14 LUFS
    final_master = build_dir / "master_audio_48k.wav"
    normalize_master_audio(raw_master, final_master, target_lufs=-14.0)

    final_dur = get_wav_duration(final_master)

    # Write manifest
    manifest_data = {
        "ok": True,
        "title": contract_data.get("title"),
        "total_shots": len(shots),
        "total_duration_sec": final_dur,
        "master_audio": final_master.name,
        "shots": manifest_shots,
    }
    manifest_path = build_dir / "scene_audio_manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✅ Audio master and manifest created: {final_master} ({final_dur:.2f}s)")
    return final_master


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--audio-mode", choices=["fixture", "supertonic3"], default="supertonic3")
    parser.add_argument("--tts-url")
    args = parser.parse_args()

    build_audio_master(args.build, audio_mode=args.audio_mode, tts_url=args.tts_url)


if __name__ == "__main__":
    main()
