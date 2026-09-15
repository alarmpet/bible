# -*- coding: utf-8 -*-
"""Synthesize genuine Korean narration audio for the 20 pilot scenes using SuperTonic3 Engine."""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

# Add SuperTonic3 engine to sys.path
SUPERTONIC_ROOT = Path(r"C:\Users\shs\supertonic3-local-tts-20260517-r4\supertonic3-local-tts")
sys.path.insert(0, str(SUPERTONIC_ROOT / "src"))

from supertonic3_engine import Supertonic3Engine

EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
MANIFEST_PATH = EP_DIR / "generation" / "pilot_120s_scene_manifest.json"
OUT_DIR = EP_DIR / "audio" / "sentences"
OUT_DIR.mkdir(parents=True, exist_ok=True)

manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
scenes = manifest["scenes"]
print(f"Loaded {len(scenes)} scenes from {MANIFEST_PATH}")

engine = Supertonic3Engine(output_dir=OUT_DIR)
voice = "M2"
speed = 0.95
total_step = 10

print(f"Initializing SuperTonic3 Engine with Voice={voice}, Speed={speed}, Steps={total_step}...")

results = []
start_all = time.time()

for idx, scene in enumerate(scenes, 1):
    shot_id = scene["shot_id"]
    text = scene["narration"]
    target_wav = OUT_DIR / f"{shot_id}.wav"
    
    print(f"[{idx:02d}/20] Synthesizing {shot_id}: \"{text}\"")
    t0 = time.time()
    info = engine.synthesize_to_file(
        text=text,
        voice=voice,
        speed=speed,
        total_step=total_step,
        output_path=target_wav
    )
    elapsed = time.time() - t0
    dur = info["duration"]
    print(f"       -> Generated: {target_wav.name} ({dur:.2f}s audio in {elapsed:.2f}s)")
    results.append({
        "shot_id": shot_id,
        "text": text,
        "path": str(target_wav),
        "duration": dur,
        "scene_duration": scene["duration_sec"]
    })

print(f"\nAll 20 sentences synthesized in {time.time() - start_all:.2f}s!")
res_json = EP_DIR / "audio" / "raw_synthesis_summary.json"
res_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Summary saved to {res_json}")
