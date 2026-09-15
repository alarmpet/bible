# -*- coding: utf-8 -*-
"""Synthesize genuine, natural Korean narration audio for the 20 pilot scenes using SuperTonic3 Engine,
with Korean phonetic normalization, uniform cadence (speed=1.075x), and measured audio-bound timing calculation."""
from __future__ import annotations
import json
import sys
import time
import subprocess
from pathlib import Path

# Add project paths
SUPERTONIC_ROOT = Path(r"C:\Users\shs\supertonic3-local-tts-20260517-r4\supertonic3-local-tts")
sys.path.insert(0, str(SUPERTONIC_ROOT / "src"))
sys.path.insert(0, r"D:\module\bible\human_archive\scripts")

from supertonic3_engine import Supertonic3Engine
from lib.korean_phonetic_normalizer import normalize_korean_phonetic_tts

EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
MANIFEST_PATH = EP_DIR / "generation" / "pilot_120s_scene_manifest.json"
APPROVED_ASSET_PATH = EP_DIR / "generation" / "approved_asset_manifest.json"
AUDIO_DIR = EP_DIR / "audio" / "sentences_v3"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
CANDIDATE_DIR = EP_DIR / "candidate"
CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)

CAMERA_MOTIONS = [
    "push_in",   # SHOT_001
    "push_in",   # SHOT_002
    "pan_right", # SHOT_003
    "push_in",   # SHOT_004
    "tilt_up",   # SHOT_005
    "push_in",   # SHOT_006
    "push_in",   # SHOT_007
    "push_in",   # SHOT_008
    "pan_left",  # SHOT_009
    "pull_out",  # SHOT_010
    "push_in",   # SHOT_011
    "push_in",   # SHOT_012
    "push_in",   # SHOT_013
    "pan_right", # SHOT_014
    "push_in",   # SHOT_015
    "pan_left",  # SHOT_016
    "tilt_down", # SHOT_017
    "push_in",   # SHOT_018
    "pan_right", # SHOT_019
    "pull_out",  # SHOT_020
]

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
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    approved_data = json.loads(APPROVED_ASSET_PATH.read_text(encoding="utf-8"))
    approved_map = {a["shot_id"]: a["approved_path"] for a in approved_data["assets"]}
    scenes = manifest["scenes"]
    print(f"Loaded {len(scenes)} scenes.")

    engine = Supertonic3Engine(output_dir=AUDIO_DIR)
    voice = "M2"
    speed = 1.075
    total_step = 10

    print(f"Synthesizing 20 scenes with Voice={voice}, Speed={speed}, Steps={total_step}...")
    sentence_records = []

    for idx, scene in enumerate(scenes, 1):
        shot_id = scene["shot_id"]
        raw_narration = scene["narration"]
        tts_text = normalize_korean_phonetic_tts(raw_narration)
        target_wav = AUDIO_DIR / f"{shot_id}_v3.wav"

        t0 = time.time()
        info = engine.synthesize_to_file(
            text=tts_text,
            voice=voice,
            speed=speed,
            total_step=total_step,
            output_path=target_wav
        )
        dur = get_wav_duration(target_wav)
        motion = CAMERA_MOTIONS[idx - 1]
        img_path = approved_map.get(shot_id)

        sentence_records.append({
            "order": idx,
            "shot_id": shot_id,
            "display_text": raw_narration,
            "tts_text": tts_text,
            "wav_path": str(target_wav),
            "image_path": img_path,
            "camera_motion": motion,
            "speech_duration": dur,
        })
        print(f"[{idx:02d}/20] {shot_id}: {dur:.3f}s | motion: {motion}")

    total_speech = sum(r["speech_duration"] for r in sentence_records)
    print(f"\nTotal raw speech duration at speed={speed}: {total_speech:.3f}s")

    TARGET_TOTAL = 120.000
    LEAD_IN = 0.400
    LEAD_OUT = 0.800
    num_gaps = len(sentence_records) - 1 # 19 gaps
    total_pause_budget = TARGET_TOTAL - total_speech - LEAD_IN - LEAD_OUT
    gap_duration = total_pause_budget / num_gaps
    print(f"Lead-in: {LEAD_IN:.3f}s, Lead-out: {LEAD_OUT:.3f}s")
    print(f"Calculated uniform breathing gap ({num_gaps} gaps): {gap_duration:.3f}s each")

    # If gap_duration is within 0.25s ~ 0.50s, this is an absolute sweet spot for human documentary speech.
    assert 0.20 <= gap_duration <= 0.60, f"Gap duration {gap_duration} outside natural range!"

    # Calculate exact timeline
    current_time = 0.0
    audio_events = []
    shot_timings = []

    # Lead-in silence
    current_time += LEAD_IN

    for idx, r in enumerate(sentence_records):
        speech_start = current_time
        speech_end = speech_start + r["speech_duration"]
        audio_events.append({
            "wav_path": r["wav_path"],
            "start": speech_start,
            "end": speech_end,
            "duration": r["speech_duration"]
        })

        # Scene visual cut points:
        # Scene 1 visual starts at 0.000
        # Subsequent scenes start at midpoint of breathing pause
        if idx == 0:
            scene_start = 0.000
        else:
            scene_start = speech_start - (gap_duration / 2.0)

        if idx == len(sentence_records) - 1:
            scene_end = TARGET_TOTAL
        else:
            scene_end = speech_end + (gap_duration / 2.0)

        scene_dur = scene_end - scene_start

        shot_timings.append({
            "order": r["order"],
            "shot_id": r["shot_id"],
            "scene_start": round(scene_start, 3),
            "scene_end": round(scene_end, 3),
            "scene_duration": round(scene_dur, 3),
            "speech_start": round(speech_start, 3),
            "speech_end": round(speech_end, 3),
            "speech_duration": round(r["speech_duration"], 3),
            "camera_motion": r["camera_motion"],
            "display_text": r["display_text"],
            "tts_text": r["tts_text"],
            "image_path": r["image_path"],
            "wav_path": r["wav_path"]
        })

        if idx < num_gaps:
            current_time = speech_end + gap_duration
        else:
            current_time = speech_end + LEAD_OUT

    # Adjust rounding in final shot so scene_durations sum EXACTLY to 120.000
    total_scene_dur = sum(s["scene_duration"] for s in shot_timings)
    diff = round(TARGET_TOTAL - total_scene_dur, 3)
    if diff != 0.0:
        shot_timings[-1]["scene_duration"] = round(shot_timings[-1]["scene_duration"] + diff, 3)
        shot_timings[-1]["scene_end"] = TARGET_TOTAL

    print("\n--- Audio-Bound Scene Timings ---")
    for s in shot_timings:
        print(f"[{s['shot_id']}] Visual: {s['scene_start']:6.2f}s ~ {s['scene_end']:6.2f}s ({s['scene_duration']:5.2f}s) | Audio: {s['speech_start']:6.2f}s ~ {s['speech_end']:6.2f}s | Motion: {s['camera_motion']}")

    # Save audio-bound manifest
    manifest_out = EP_DIR / "generation" / "pilot_120s_audio_bound_manifest.json"
    manifest_out.write_text(json.dumps({
        "total_duration_sec": TARGET_TOTAL,
        "total_shots": len(shot_timings),
        "lead_in_sec": LEAD_IN,
        "lead_out_sec": LEAD_OUT,
        "breathing_gap_sec": round(gap_duration, 3),
        "shots": shot_timings
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nManifest written: {manifest_out}")

    # Build Master Audio with FFmpeg
    # We mix each sentence at its exact delay, then apply documentary mastering EQ and limiter
    master_wav = CANDIDATE_DIR / "pilot_audio_120s_v3.wav"
    inputs = []
    filter_parts = []
    for i, s in enumerate(shot_timings):
        inputs.extend(["-i", s["wav_path"]])
        delay_ms = int(round(s["speech_start"] * 1000))
        filter_parts.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[a{i}]")

    mix_inputs = "".join(f"[a{i}]" for i in range(len(shot_timings)))
    filter_parts.append(f"{mix_inputs}amix=inputs={len(shot_timings)}:dropout_transition=0:normalize=0[mixed]")
    # Documentary broadcast warmth filter + soft limiter + pad to 120.0
    # Highpass 50Hz (cut sub rumble), warm bass boost (160Hz +2dB), presence boost (3.2kHz +1dB), gentle lowpass (8kHz)
    docu_master = (
        "[mixed]highpass=f=50,lowpass=f=8000,"
        "equalizer=f=160:t=q:w=1:g=2.0,equalizer=f=3200:t=q:w=1:g=1.2,"
        "loudnorm=I=-16:TP=-1.5:LRA=11,"
        "apad=whole_dur=120.0[outa]"
    )
    filter_parts.append(docu_master)
    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outa]",
        "-t", "120.0",
        "-ar", "48000",
        "-ac", "2",
        str(master_wav)
    ]
    print("\nMastering 120.0s 48kHz audio track with documentary filter...")
    subprocess.run(cmd, check=True)
    actual_audio_dur = get_wav_duration(master_wav)
    print(f"Master audio generated: {master_wav} ({actual_audio_dur:.3f}s)")

    # Build ASS Subtitles
    ass_path = CANDIDATE_DIR / "pilot_subtitles_120s_v3.ass"
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
    for item in shot_timings:
        # Subtitle appears 0.05s before speech and ends 0.15s after speech for readable persistence
        sub_start = max(0.0, item["speech_start"] - 0.05)
        sub_end = min(TARGET_TOTAL, item["speech_end"] + 0.15)
        start_ass = seconds_to_ass(sub_start)
        end_ass = seconds_to_ass(sub_end)
        text = item["display_text"].strip()
        if len(text) > 28 and " " in text:
            words = text.split()
            mid = len(words) // 2
            text = " ".join(words[:mid]) + r"\N" + " ".join(words[mid:])
        events.append(f"Dialogue: 0,{start_ass},{end_ass},DocuNarrator,,0,0,0,,{text}")

    full_ass = header + "\n".join(events) + "\n"
    ass_path.write_text(full_ass, encoding="utf-8-sig")
    print(f"ASS subtitles saved: {ass_path}")

if __name__ == "__main__":
    main()
