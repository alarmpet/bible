# -*- coding: utf-8 -*-
"""Build sentence-granular alignment manifest for 20-minute master documentary.
Maps shot-level master_1200s_manifest.json and source/scene_script_manifest_v2.json
into 105 sentence-level atoms (SHOT_xxx_Syy) with precise speech boundaries and audio tracking."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
MANIFEST_PATH = EP_DIR / "generation" / "master_1200s_manifest.json"
SCENE_MANIFEST = EP_DIR / "source" / "scene_script_manifest_v2.json"
AUDIO_DIR = EP_DIR / "audio" / "sentences_v3"
OUT_MANIFEST = EP_DIR / "generation" / "master_sentence_aligned_manifest.json"

BODY_SHOT_MAP = {
    'SHOT_021': ['SCN_021', 'SCN_022', 'SCN_023'],
    'SHOT_022': ['SCN_024', 'SCN_025', 'SCN_026'],
    'SHOT_023': ['SCN_027', 'SCN_028', 'SCN_029'],
    'SHOT_024': ['SCN_030', 'SCN_031', 'SCN_032', 'SCN_033'],
    'SHOT_025': ['SCN_034', 'SCN_035', 'SCN_036'],
    'SHOT_026': ['SCN_037', 'SCN_038', 'SCN_039'],
    'SHOT_027': ['SCN_040', 'SCN_041', 'SCN_042', 'SCN_043'],
    'SHOT_028': ['SCN_044', 'SCN_045', 'SCN_046'],
    'SHOT_029': ['SCN_047', 'SCN_048'],
    'SHOT_030': ['SCN_049', 'SCN_050'],
    'SHOT_031': ['SCN_051'],
    'SHOT_032': ['SCN_052', 'SCN_053'],
    'SHOT_033': ['SCN_054'],
    'SHOT_034': ['SCN_055'],
    'SHOT_035': ['SCN_056', 'SCN_057'],
    'SHOT_036': ['SCN_058'],
    'SHOT_037': ['SCN_059', 'SCN_060'],
    'SHOT_038': ['SCN_061', 'SCN_062'],
    'SHOT_039': ['SCN_063'],
    'SHOT_040': ['SCN_064'],
    'SHOT_041': ['SCN_065', 'SCN_066'],
    'SHOT_042': ['SCN_067', 'SCN_068'],
    'SHOT_043': ['SCN_069'],
    'SHOT_044': ['SCN_070'],
    'SHOT_045': ['SCN_071', 'SCN_072', 'SCN_073'],
    'SHOT_046': ['SCN_074', 'SCN_075', 'SCN_076'],
    'SHOT_047': ['SCN_077', 'SCN_078', 'SCN_079'],
    'SHOT_048': ['SCN_080', 'SCN_081', 'SCN_082'],
    'SHOT_049': ['SCN_083', 'SCN_084', 'SCN_085'],
    'SHOT_050': ['SCN_086', 'SCN_087', 'SCN_088'],
    'SHOT_051': ['SCN_089', 'SCN_090', 'SCN_091'],
    'SHOT_052': ['SCN_092', 'SCN_093', 'SCN_094'],
    'SHOT_053': ['SCN_095', 'SCN_096', 'SCN_097'],
    'SHOT_054': ['SCN_098', 'SCN_099', 'SCN_100'],
    'SHOT_055': ['SCN_101', 'SCN_102', 'SCN_103'],
    'SHOT_056': ['SCN_104', 'SCN_105'],
}

def get_wav_dur(p: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(p)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())

def main():
    manifest_data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    scene_data = json.loads(SCENE_MANIFEST.read_text(encoding="utf-8"))
    scenes_by_id = {s["scene_id"]: s for s in scene_data["scenes"]}
    shots = manifest_data["shots"]
    print(f"Loaded {len(shots)} shots from {MANIFEST_PATH.name}")

    sentence_items = []
    updated_shots = []

    for s in shots:
        sid = s["shot_id"]
        is_pilot = s.get("is_pilot", False)
        target_wav = AUDIO_DIR / f"{sid}_v3.wav"
        
        dur = get_wav_dur(target_wav)
        s["speech_duration"] = round(dur, 3)
        s["wav_path"] = str(target_wav)
        
        if is_pilot:
            s_start = s.get("speech_start", round(s["scene_start"] + 0.1, 3))
        else:
            s_start = round(s["scene_start"] + 0.5, 3)
            
        s["speech_start"] = s_start
        s["speech_end"] = round(s_start + dur, 3)
        updated_shots.append(s)

        if is_pilot:
            sent_id = f"{sid}_S1"
            sentence_items.append({
                "sentence_id": sent_id,
                "scene_id": f"SCN_{s['order']:03d}",
                "shot_id": sid,
                "order": len(sentence_items) + 1,
                "scene_start": s["scene_start"],
                "scene_end": s["scene_end"],
                "speech_start": s["speech_start"],
                "speech_end": s["speech_end"],
                "speech_duration": dur,
                "display_text": s["display_text"].strip(),
                "tts_text": s.get("tts_text", s["display_text"]).strip(),
                "wav_path": str(target_wav),
                "is_pilot": True
            })
        else:
            mapped_scns = BODY_SHOT_MAP[sid]
            scene_objs = [scenes_by_id[sc_id] for sc_id in mapped_scns]
            k_count = len(scene_objs)
            
            lens = [len(x["narration"]) for x in scene_objs]
            total_len = sum(lens)
            pause = 0.35
            avail_speech = max(dur - (k_count - 1) * pause, dur * 0.7)
            
            cur_t = s_start
            for idx, sc in enumerate(scene_objs):
                sent_id = f"{sid}_S{idx+1}"
                ratio = lens[idx] / total_len
                dur_k = round(avail_speech * ratio, 3)
                start_k = round(cur_t, 3)
                end_k = round(start_k + dur_k, 3)
                
                sentence_items.append({
                    "sentence_id": sent_id,
                    "scene_id": sc["scene_id"],
                    "shot_id": sid,
                    "order": len(sentence_items) + 1,
                    "scene_start": s["scene_start"],
                    "scene_end": s["scene_end"],
                    "speech_start": start_k,
                    "speech_end": end_k,
                    "speech_duration": dur_k,
                    "display_text": sc["narration"].strip(),
                    "tts_text": sc["narration"].strip(),
                    "wav_path": str(target_wav),
                    "is_pilot": False
                })
                cur_t = end_k + pause

    manifest_data["shots"] = updated_shots
    MANIFEST_PATH.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")

    sentence_manifest = {
        "schema_version": 2,
        "episode_id": "NOLLAM-20260902-HIMALAYA-GLOF-V1",
        "total_shots": len(shots),
        "total_sentences": len(sentence_items),
        "target_duration_sec": 1200.0,
        "sentences": sentence_items
    }
    OUT_MANIFEST.write_text(json.dumps(sentence_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated sentence-aligned manifest: {OUT_MANIFEST.name} ({len(sentence_items)} sentences)")

if __name__ == "__main__":
    main()
