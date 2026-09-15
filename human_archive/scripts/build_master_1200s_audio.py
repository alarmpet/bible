# -*- coding: utf-8 -*-
"""Synthesize SuperTonic3 M2 TTS for 36 body shots (SHOT_021 ~ SHOT_056)
and assemble the full 56-shot 1,200.000s 48kHz master audio track with ASS subtitles."""
from __future__ import annotations
import json
import subprocess
import sys
import time
from pathlib import Path

SUPERTONIC_ROOT = Path(r"C:\Users\shs\supertonic3-local-tts-20260517-r4\supertonic3-local-tts")
sys.path.insert(0, str(SUPERTONIC_ROOT / "src"))
sys.path.insert(0, r"D:\module\bible\human_archive\scripts")

from supertonic3_engine import Supertonic3Engine
from lib.korean_phonetic_normalizer import robust_normalize_korean_tts

EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
MANIFEST_PATH = EP_DIR / "generation" / "master_1200s_manifest.json"
AUDIO_DIR = EP_DIR / "audio" / "sentences_v3"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
CANDIDATE_DIR = EP_DIR / "candidate"
CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)

def seconds_to_ass(s: float) -> str:
    cs = int(round(s * 100))
    m, cs = divmod(cs, 6000)
    h, m = divmod(m, 60)
    s_int, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s_int:02d}.{cs:02d}"

def get_wav_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())

def main():
    manifest_data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    shots = manifest_data["shots"]
    print(f"Loaded master manifest with {len(shots)} shots.")

    engine = Supertonic3Engine(output_dir=AUDIO_DIR)
    voice = "M2"
    speed = 1.075
    total_step = 10

    # 1. Synthesize missing body shots (SHOT_021 ~ SHOT_056)
    for s in shots:
        if s.get("is_pilot"):
            continue
        shot_id = s["shot_id"]
        target_wav = AUDIO_DIR / f"{shot_id}_v3.wav"
        raw_tts_text = s["tts_text"]
        normalized_text = robust_normalize_korean_tts(raw_tts_text)
        s["tts_text"] = normalized_text
        s["wav_path"] = str(target_wav)

        if not target_wav.exists() or target_wav.stat().st_size < 1000:
            print(f"Synthesizing [{shot_id}] ({len(normalized_text)} chars): {normalized_text[:35]}...")
            engine.synthesize_to_file(
                text=normalized_text,
                voice=voice,
                speed=speed,
                total_step=total_step,
                output_path=target_wav
            )
        dur = get_wav_duration(target_wav)
        s["speech_duration"] = round(dur, 3)
        # Speech starts 0.5s into the 30s shot
        s["speech_start"] = round(s["scene_start"] + 0.5, 3)
        s["speech_end"] = round(s["speech_start"] + dur, 3)
        print(f"[{shot_id}] Audio ready: {dur:.2f}s (ends at {s['speech_end']:.2f}s / {s['scene_end']:.2f}s)")

    # Save updated manifest with audio paths and durations
    MANIFEST_PATH.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated master manifest: {MANIFEST_PATH}")

    # 2. Build Master Audio Track (Bound to natural speech duration within 840s~1560s)
    total_target_dur = float(manifest_data.get("total_duration_sec", shots[-1]["scene_end"]))
    master_wav = CANDIDATE_DIR / "pilot_audio_1200s_master.wav"
    print(f"\nAssembling {total_target_dur:.1f}s 48kHz master audio track via FFmpeg...")

    inputs = []
    filter_parts = []
    for i, s in enumerate(shots):
        wav_p = Path(s["wav_path"])
        inputs.extend(["-i", str(wav_p)])
        delay_ms = int(round(s["speech_start"] * 1000))
        filter_parts.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[a{i}]")

    mix_inputs = "".join(f"[a{i}]" for i in range(len(shots)))
    filter_parts.append(f"{mix_inputs}amix=inputs={len(shots)}:dropout_transition=0:normalize=0[mixed]")
    
    # Broadcast documentary mastering filter: highpass 50, gentle bass warmth, presence boost, loudnorm
    docu_master = (
        "[mixed]highpass=f=50,lowpass=f=8000,"
        "equalizer=f=160:t=q:w=1:g=2.0,equalizer=f=3200:t=q:w=1:g=1.2,"
        "loudnorm=I=-16:TP=-1.5:LRA=11,"
        f"apad=whole_dur={total_target_dur:.3f}[outa]"
    )
    filter_parts.append(docu_master)
    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outa]",
        "-t", f"{total_target_dur:.3f}",
        "-ar", "48000",
        "-ac", "2",
        str(master_wav)
    ]
    t0 = time.time()
    subprocess.run(cmd, check=True)
    dt = time.time() - t0
    actual_dur = get_wav_duration(master_wav)
    print(f"Master audio generated in {dt:.1f}s: {master_wav} ({actual_dur:.3f}s)")

    # 3. Build ASS Subtitles
    ass_path = CANDIDATE_DIR / "pilot_subtitles_1200s.ass"
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: DocuNarrator,Malgun Gothic,46,&H00FFFFFF,&H000000FF,&H000C0C12,&H90000000,-1,0,0,0,100,100,0,0,1,4.5,2.5,2,140,140,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for item in shots:
        sub_start = max(0.0, item["speech_start"] - 0.05)
        sub_end = min(1200.0, item["speech_end"] + 0.20)
        start_ass = seconds_to_ass(sub_start)
        end_ass = seconds_to_ass(sub_end)
        text = item["display_text"].strip()
        # Word wrap for long subtitles
        if len(text) > 36 and " " in text:
            words = text.split()
            mid = len(words) // 2
            text = " ".join(words[:mid]) + r"\N" + " ".join(words[mid:])
        events.append(f"Dialogue: 0,{start_ass},{end_ass},DocuNarrator,,0,0,0,,{text}")

    full_ass = header + "\n".join(events) + "\n"
    ass_path.write_text(full_ass, encoding="utf-8-sig")
    print(f"ASS subtitles saved: {ass_path}")

if __name__ == "__main__":
    main()
