# -*- coding: utf-8 -*-
"""Synthesize documentary audio using SuperTonic3 M4 voice and generate aligned ASS subtitles."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Setup paths
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_BH_SCRIPTS = _PROJECT_ROOT / "bible_healing" / "scripts"
_MODERN_SCRIPTS = _PROJECT_ROOT / "modern" / "scripts"
for p in [_BH_SCRIPTS, _MODERN_SCRIPTS]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

try:
    from paths_bh import TTS_ROOT, FFMPEG
except Exception:
    TTS_ROOT = Path(os.environ.get("HERMES_TTS_ROOT", Path.home() / "supertonic3-local-tts-20260517-r4" / "supertonic3-local-tts"))
    FFMPEG = "ffmpeg"


def seconds_to_ass(s: float) -> str:
    cs = int(round(s * 100))
    m, cs = divmod(cs, 6000)
    h, m = divmod(m, 60)
    s_int, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s_int:02d}.{cs:02d}"


def get_audio_duration(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


def synthesize_shot_audio(text: str, out_wav: Path, engine) -> float:
    # Synthesize M4 voice (documentary narrator)
    # Speed: 0.94, total_step: 10
    raw_wav = out_wav.parent / f"raw_{out_wav.name}"
    engine.synthesize_to_file(
        text=text,
        output_path=raw_wav,
        voice="M4",
        lang="ko",
        speed=0.94,
        total_step=10,
        silence_duration=0.35,
        max_chunk_length=120,
        verbose=False,
    )

    # Apply documentary broadcast audio filter (warm lowpass 7500, bass warmth)
    af = "highpass=f=50,lowpass=f=7500,equalizer=f=160:t=q:w=1:g=2.5,equalizer=f=3000:t=q:w=1:g=1.2"
    cmd = [
        str(FFMPEG),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(raw_wav),
        "-af",
        af,
        "-c:a",
        "pcm_s16le",
        str(out_wav),
    ]
    subprocess.run(cmd, check=True)
    if raw_wav.exists():
        raw_wav.unlink()

    return get_audio_duration(out_wav)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default="human_archive/runs/ep01_pompeii_18hours")
    args = ap.parse_args()

    run_dir = Path(args.run_dir).resolve()
    prompts_file = run_dir / "full_script_68shots.json"
    if not prompts_file.exists():
        prompts_file = run_dir / "full_script_36shots.json"
    if not prompts_file.exists():
        prompts_file = run_dir / "flow_image_prompts.json"
    if not prompts_file.exists():
        raise SystemExit(f"Missing script file in {run_dir}")

    data = json.loads(prompts_file.read_text(encoding="utf-8"))
    shots = data.get("shots", [])

    audio_dir = run_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    # Initialize SuperTonic3 Engine
    sys.path.insert(0, str(TTS_ROOT / "src"))
    from supertonic3_engine import Supertonic3Engine

    engine = Supertonic3Engine(model_dir=TTS_ROOT / "models")

    manifest_shots = []
    current_time = 0.0

    print(f"Synthesizing {len(shots)} shots for {data.get('title')}...")

    for i, shot in enumerate(shots, 1):
        shot_id = shot["shot_id"]
        text = shot["narration_ko"]
        out_wav = audio_dir / f"{shot_id}.wav"

        dur = synthesize_shot_audio(text, out_wav, engine)
        start_s = round(current_time, 3)
        end_s = round(current_time + dur, 3)
        current_time = end_s

        manifest_shots.append({
            "order": i,
            "shot_id": shot_id,
            "chapter": shot.get("chapter", 1),
            "text": text,
            "audio_file": str(out_wav),
            "duration": dur,
            "startSeconds": start_s,
            "endSeconds": end_s,
        })
        print(f"[{i:02d}/{len(shots):02d}] {shot_id}: {dur:.2f}s | {text[:28]}...")

    # Write Manifest
    manifest_path = run_dir / "scene_audio_manifest.json"
    manifest_data = {
        "ok": True,
        "title": data.get("title"),
        "total_shots": len(shots),
        "total_duration_sec": round(current_time, 2),
        "shots": manifest_shots,
    }
    manifest_path.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nManifest saved: {manifest_path} (Total duration: {current_time:.2f}s)")

    # Build ASS subtitles
    ass_path = run_dir / "subtitles.ass"
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: DocuNarrator,Malgun Gothic,48,&H00FFFFFF,&H000000FF,&H000A0A10,&HB0000000,-1,0,0,0,100,100,0,0,1,5,3,2,140,140,85,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for item in manifest_shots:
        start_ass = seconds_to_ass(item["startSeconds"])
        end_ass = seconds_to_ass(item["endSeconds"])
        text = item["text"].strip()
        if len(text) > 26 and " " in text:
            words = text.split()
            mid = len(words) // 2
            text = " ".join(words[:mid]) + r"\N" + " ".join(words[mid:])
        events.append(f"Dialogue: 0,{start_ass},{end_ass},DocuNarrator,,0,0,0,,{text}")

    full_ass = header + "\n".join(events) + "\n"
    ass_path.write_text(full_ass, encoding="utf-8-sig")
    print(f"ASS subtitles saved: {ass_path}")


if __name__ == "__main__":
    main()
