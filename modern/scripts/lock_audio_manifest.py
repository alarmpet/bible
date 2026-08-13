# -*- coding: utf-8 -*-
"""Convert multi-voice TTS output into Hermes measured-and-locked scene_audio_manifest.

Hermes render-youtube-with-tts.mjs re-runs single-voice make-scenes-tts.py unless:
  manifest.status == "measured-and-locked" (or lock.status)
and requires:
  ok, scenes[{order, audio_path, duration, text, sha256}]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import wave
from datetime import datetime, timezone
from pathlib import Path


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        frames = w.getnframes()
        rate = w.getframerate() or 1
        return frames / float(rate)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True, help="Hermes job dir with scene_N.wav + draft.json")
    ap.add_argument("--backup", action="store_true", help="Backup previous manifest")
    args = ap.parse_args()
    job = Path(args.job).resolve()
    if not job.is_dir():
        raise SystemExit(f"job not found: {job}")

    draft_path = job / "draft.json"
    if not draft_path.exists():
        raise SystemExit("draft.json missing")
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    draft_scenes = {int(s["order"]): s for s in draft.get("scenes") or [] if "order" in s}

    old_manifest_path = job / "scene_audio_manifest.json"
    old = {}
    if old_manifest_path.exists():
        if args.backup:
            bak = job / f"scene_audio_manifest.prelock.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
            bak.write_text(old_manifest_path.read_text(encoding="utf-8"), encoding="utf-8")
            print("backed up", bak)
        try:
            old = json.loads(old_manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            old = {}

    # duration hints from multi-voice items[] if present
    duration_hint: dict[int, float] = {}
    for item in old.get("items") or []:
        if "order" in item and item.get("duration") is not None:
            duration_hint[int(item["order"])] = float(item["duration"])

    scenes = []
    cursor = 0.0
    orders = sorted(draft_scenes.keys())
    if not orders:
        # fallback: discover scene_N.wav
        orders = sorted(
            int(p.stem.split("_")[1])
            for p in job.glob("scene_*.wav")
            if p.stem.replace("scene_", "").isdigit()
        )

    for order in orders:
        wav = job / f"scene_{order}.wav"
        if not wav.exists():
            raise SystemExit(f"missing {wav.name}")
        try:
            duration = wav_duration(wav)
        except Exception:
            duration = duration_hint.get(order)
            if duration is None:
                # rough fallback from file size (pcm16 mono ~44.1k)
                duration = max(0.1, wav.stat().st_size / (44100 * 2))
        text = ""
        src = draft_scenes.get(order) or {}
        text = " ".join(str(src.get("narration") or src.get("text") or "").split())
        audio_path = str(wav.resolve()).replace("\\", "/")
        digest = sha256_file(wav)
        start = round(cursor, 3)
        end = round(cursor + duration, 3)
        scenes.append(
            {
                "order": order,
                "text": text,
                "audio_path": audio_path,
                "audioPath": audio_path,
                "duration": duration,
                "measuredDurationSeconds": duration,
                "startSeconds": start,
                "endSeconds": end,
                "sha256": digest,
            }
        )
        cursor = end

    scene_timings = [
        {
            "order": s["order"],
            "text": s["text"],
            "startSeconds": s["startSeconds"],
            "endSeconds": s["endSeconds"],
            "measuredDurationSeconds": s["measuredDurationSeconds"],
        }
        for s in scenes
    ]

    locked = {
        "ok": True,
        "schemaVersion": 2,
        "manifestVersion": int(old.get("manifestVersion") or 0) + 1,
        "status": "measured-and-locked",
        "engine": old.get("engine") or "supertonic3-multivoice",
        "source": "module_tts_multi_voice",
        "lockedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scene_count": len(scenes),
        "durationSeconds": round(cursor, 3),
        "targetSeconds": round(cursor, 3),
        "introDurationSeconds": 0,
        "lock": {
            "status": "measured-and-locked",
            "version": 1,
            "pointerPath": "scene_audio_manifest.json",
            "lockedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source": "module_tts_multi_voice",
        },
        "scenes": scenes,
        "sceneTimings": scene_timings,
        # keep multi-voice provenance lightly
        "multiVoice": True,
        "items_archived": bool(old.get("items")),
    }
    old_manifest_path.write_text(json.dumps(locked, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "path": str(old_manifest_path), "scenes": len(scenes), "durationSeconds": locked["durationSeconds"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
