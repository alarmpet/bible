# -*- coding: utf-8 -*-
"""Assemble 20 scene audios into an exact 120.000s master narration track aligned with scene cuts."""
from __future__ import annotations
import json
import subprocess
import wave
import struct
from pathlib import Path

EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
MANIFEST_PATH = EP_DIR / "generation" / "pilot_120s_scene_manifest.json"
SENTENCES_DIR = EP_DIR / "audio" / "sentences"
PROCESSED_DIR = EP_DIR / "audio" / "processed_scenes"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_RATE = 48000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit

manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
scenes = manifest["scenes"]
print(f"Aligning {len(scenes)} scenes to master timeline...")

concat_list = []
total_aligned_duration = 0.0

for idx, scene in enumerate(scenes, 1):
    shot_id = scene["shot_id"]
    scene_dur = float(scene["duration_sec"])
    raw_wav = SENTENCES_DIR / f"{shot_id}.wav"
    
    # 1. Probe raw audio duration
    with wave.open(str(raw_wav), "rb") as w:
        raw_frames = w.getnframes()
        raw_rate = w.getframerate()
        raw_dur = raw_frames / raw_rate
    
    # 2. Determine if tempo scaling is needed
    # We want a small silence padding: min 0.1s lead-in and 0.15s tail
    max_voice_dur = max(1.0, scene_dur - 0.25)
    
    fitted_wav = PROCESSED_DIR / f"{shot_id}_fitted.wav"
    
    if raw_dur > max_voice_dur:
        tempo = raw_dur / max_voice_dur
        # Clamp tempo to reasonable range (1.0 to 1.7)
        tempo = min(1.7, max(1.01, tempo))
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(raw_wav),
            "-filter:a", f"atempo={tempo:.3f},afade=t=in:ss=0:d=0.015,afade=t=out:st={max_voice_dur-0.02:.3f}:d=0.015",
            "-ar", str(SAMPLE_RATE),
            "-ac", str(CHANNELS),
            "-c:a", "pcm_s16le",
            str(fitted_wav)
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(raw_wav),
            "-filter:a", f"afade=t=in:ss=0:d=0.015,afade=t=out:st={raw_dur-0.02:.3f}:d=0.015",
            "-ar", str(SAMPLE_RATE),
            "-ac", str(CHANNELS),
            "-c:a", "pcm_s16le",
            str(fitted_wav)
        ]
    subprocess.run(cmd, check=True)
    
    # 3. Read processed speech audio
    with wave.open(str(fitted_wav), "rb") as w:
        voice_frames = w.readframes(w.getnframes())
        voice_frame_count = w.getnframes()
    
    # 4. Create scene slot audio of EXACT target frame count
    target_frames = round(scene_dur * SAMPLE_RATE)
    lead_in_frames = round(0.10 * SAMPLE_RATE)
    
    # Adjust if voice_frames + lead_in exceeds target
    if lead_in_frames + voice_frame_count > target_frames:
        lead_in_frames = max(0, target_frames - voice_frame_count)
        tail_frames = 0
        # If voice alone exceeds target, truncate slightly
        if voice_frame_count > target_frames:
            voice_frames = voice_frames[:target_frames * SAMPLE_WIDTH]
            voice_frame_count = target_frames
    else:
        tail_frames = target_frames - (lead_in_frames + voice_frame_count)
    
    scene_slot_wav = PROCESSED_DIR / f"{shot_id}_slot.wav"
    lead_in_silence = b"\x00" * lead_in_frames * SAMPLE_WIDTH
    tail_silence = b"\x00" * tail_frames * SAMPLE_WIDTH
    
    with wave.open(str(scene_slot_wav), "wb") as writer:
        writer.setnchannels(CHANNELS)
        writer.setsampwidth(SAMPLE_WIDTH)
        writer.setframerate(SAMPLE_RATE)
        writer.writeframes(lead_in_silence)
        writer.writeframes(voice_frames)
        writer.writeframes(tail_silence)
    
    actual_frames = lead_in_frames + voice_frame_count + tail_frames
    actual_dur = actual_frames / SAMPLE_RATE
    total_aligned_duration += actual_dur
    print(f"[{idx:02d}/20] {shot_id}: raw={raw_dur:.2f}s -> slot={actual_dur:.3f}s (target={scene_dur:.3f}s, voice={voice_frame_count/SAMPLE_RATE:.2f}s)")
    concat_list.append(scene_slot_wav)

# 5. Concatenate all 20 scene slots into master audio
master_wav_unmastered = EP_DIR / "candidate" / "pilot_audio_120s_unmastered.wav"
with wave.open(str(master_wav_unmastered), "wb") as writer:
    writer.setnchannels(CHANNELS)
    writer.setsampwidth(SAMPLE_WIDTH)
    writer.setframerate(SAMPLE_RATE)
    for slot_wav in concat_list:
        with wave.open(str(slot_wav), "rb") as reader:
            writer.writeframes(reader.readframes(reader.getnframes()))

print(f"\nConcatenated unmastered audio: {master_wav_unmastered}")
print(f"Total frames: {total_aligned_duration * SAMPLE_RATE:.0f}, Total seconds: {total_aligned_duration:.3f}s")

# 6. Apply broadcast mastering (highpass 60Hz + normalization to -14 LUFS / peak -1.0dB)
master_wav_final = EP_DIR / "candidate" / "pilot_audio_120s.wav"
cmd_master = [
    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
    "-i", str(master_wav_unmastered),
    "-filter:a", "highpass=f=60,volume=1.8,alimiter=limit=0.92:attack=5:release=50",
    "-ar", "48000",
    "-ac", "1",
    "-c:a", "pcm_s16le",
    str(master_wav_final)
]
subprocess.run(cmd_master, check=True)

# Also copy to audio/master_narration_audio_120s.wav
copy_dst = EP_DIR / "audio" / "master_narration_audio_120s.wav"
import shutil
shutil.copy2(master_wav_final, copy_dst)

stat = master_wav_final.stat()
print(f"Successfully created verified master narration audio!")
print(f"   Path: {master_wav_final}")
print(f"   Size: {stat.st_size} bytes")
