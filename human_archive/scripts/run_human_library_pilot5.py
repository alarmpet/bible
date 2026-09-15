# -*- coding: utf-8 -*-
"""run_human_library_pilot5.py

End-to-End Pilot-5 Pipeline for Human Library Replica (Rank 1 Race Adaptation):
- 5 Shots: SHOT_001 to SHOT_005 (total duration: 20.600s)
- Step 1: SuperTonic3 M2 Narration Audio Synthesis + 0.40s Roomtone Padding (48kHz Stereo)
- Step 2: Google Flow CDP 35mm Documentary Stills Generation + 1080p Normalization
- Step 3: Smooth Subpixel Motion Rendering (Push-in, Pan-right, Pull-out, Push-in, Pan-left)
- Step 4: 52pt Pretendard ASS Subtitles Compilation (<36 chars/line, 2-line pyramid)
- Step 5: Pre-Mux Strict AV Parity Gate (|delta| <= 0.040s)
- Step 6: Final Multiplex into pilot_5_master.mp4
- Step 7: Postflight Gate 8 Decoded Frame Analysis
- Step 8: Physical Release Manifest Generation (SHA-256)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np
from PIL import Image
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = Path(r"D:\module\bible\human_archive\scripts")
LIB_DIR = SCRIPTS_DIR / "lib"
REPO_ROOT = SCRIPTS_DIR.parent.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from lib.asset_contract import evaluate_frame_visibility_from_file
from lib.semantic_subtitle_engine import SemanticSubtitleEngine
from lib.tts_provider import SupertonicHttpProvider
from smooth_subpixel_motion_engine import render_smooth_motion_clip

# INTERNAL BENCHMARK RESEARCH ONLY — never publish this pipeline's output.
# See research/human_library_benchmark_internal_only/DO_NOT_PUBLISH.md.
EP_DIR = SCRIPTS_DIR.parent / "research" / "human_library_benchmark_internal_only" / "rank1_race_adaptation"
BUNDLE_PATH = EP_DIR / "metadata" / "pilot_5_bundle.json"

RAW_AUDIO_DIR = EP_DIR / "audio" / "raw"
PADDED_AUDIO_DIR = EP_DIR / "audio" / "padded"
IMAGES_DIR = EP_DIR / "images"
APPROVED_DIR = EP_DIR / "generation" / "downloads" / "approved"
CLIPS_DIR = EP_DIR / "video" / "clips"
SUBTITLES_DIR = EP_DIR / "subtitles"
CANDIDATE_DIR = EP_DIR / "candidate"
METADATA_DIR = EP_DIR / "metadata"

CDP_URL = "http://127.0.0.1:9222"
TTS_URL = "http://127.0.0.1:3093"


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def get_ffprobe_duration(media_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(media_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


# =========================================================================
# STEP 1: Audio Narration Synthesis & Padding
# =========================================================================

def synthesize_pilot_audio(shots: List[Dict[str, Any]]) -> Path:
    print("\n=======================================================")
    print(f"🎙️ [STEP 1] SuperTonic3 M2 Audio Synthesis ({len(shots)} Shots)")
    print("=======================================================")

    RAW_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    PADDED_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    tts_provider = SupertonicHttpProvider(base_url=TTS_URL, auto_start=True)
    padded_paths = []
    total_samples = 0
    sample_rate = 48000
    channels = 2  # Stereo 48kHz

    for idx, s in enumerate(shots, 1):
        shot_id = s["shot_id"]
        text = s["spoken_text"]
        target_dur = float(s["duration_sec"])

        raw_wav = RAW_AUDIO_DIR / f"{shot_id}.wav"
        padded_wav = PADDED_AUDIO_DIR / f"{shot_id}.wav"

        # 1. Synthesize if raw does not exist or is too small
        if not raw_wav.exists() or raw_wav.stat().st_size < 5000:
            print(f"[{idx}/{len(shots)}] Synthesizing {shot_id}: \"{text[:30]}...\"")
            tts_provider.synthesize_phrase(
                text=text,
                out_wav=raw_wav,
                speed=0.95,
                voice="M2",
                total_step=10,
            )
            print(f"   -> Raw audio saved ({raw_wav.stat().st_size:,} bytes)")
        else:
            print(f"[{idx}/{len(shots)}] Using cached raw audio for {shot_id}")

        # 2. Convert to 48kHz Stereo if needed and apply precision padding
        tmp_48k_stereo = RAW_AUDIO_DIR / f"{shot_id}_48k_stereo.wav"
        conv_cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(raw_wav),
            "-ar", "48000",
            "-ac", "2",
            "-c:a", "pcm_s16le",
            str(tmp_48k_stereo)
        ]
        subprocess.run(conv_cmd, check=True)

        with wave.open(str(tmp_48k_stereo), "rb") as crwf:
            c_frames = crwf.getnframes()
            speech_bytes = crwf.readframes(c_frames)
        tmp_48k_stereo.unlink(missing_ok=True)

        # 3. Calculate 0.40s head padding & frame-aligned trailing padding
        fps = 25
        samples_per_frame = sample_rate // fps  # 48000 // 25 = 1920
        bytes_per_sample = 2 * 2  # 16-bit stereo = 4 bytes per frame
        cur_samples = len(speech_bytes) // bytes_per_sample
        speech_dur = cur_samples / sample_rate

        head_samples = int(round(0.40 * sample_rate))  # 19200 samples = 10 frames
        min_required_samples = cur_samples + head_samples
        min_frames = math.ceil(min_required_samples / samples_per_frame)
        desired_frames = round(target_dur * fps)
        actual_frames = max(min_frames, desired_frames)

        target_samples = actual_frames * samples_per_frame
        tail_samples = target_samples - cur_samples - head_samples

        # Generate low-level roomtone for head padding (-48dB)
        head_roomtone = bytearray(head_samples * bytes_per_sample)
        amplitude = int(32767 * (10 ** (-48.0 / 20.0)))
        for frame_idx in range(head_samples):
            val = int(amplitude * (
                0.65 * math.sin(2.0 * math.pi * 97.0 * frame_idx / sample_rate)
                + 0.35 * math.sin(2.0 * math.pi * 131.0 * frame_idx / sample_rate)
            ))
            struct_bytes = struct.pack("<hh", val, val)
            head_roomtone[frame_idx * 4:(frame_idx + 1) * 4] = struct_bytes

        tail_roomtone = bytearray(tail_samples * bytes_per_sample)
        for frame_idx in range(tail_samples):
            val = int(amplitude * (
                0.65 * math.sin(2.0 * math.pi * 97.0 * frame_idx / sample_rate)
                + 0.35 * math.sin(2.0 * math.pi * 131.0 * frame_idx / sample_rate)
            ))
            struct_bytes = struct.pack("<hh", val, val)
            tail_roomtone[frame_idx * 4:(frame_idx + 1) * 4] = struct_bytes

        padded_data = head_roomtone + speech_bytes + tail_roomtone
        actual_padded_samples = len(padded_data) // bytes_per_sample
        actual_dur = actual_padded_samples / sample_rate

        with wave.open(str(padded_wav), "wb") as pwf:
            pwf.setnchannels(channels)
            pwf.setsampwidth(2)
            pwf.setframerate(sample_rate)
            pwf.writeframes(padded_data)

        # Back-propagate frame-exact duration to shot
        s["duration_sec"] = round(actual_dur, 3)
        print(f"   -> Padded {shot_id}: speech {speech_dur:.2f}s + head 0.40s + tail {tail_samples/sample_rate:.2f}s = {actual_dur:.3f}s ({actual_frames} frames)")
        padded_paths.append(padded_wav)
        total_samples += actual_padded_samples

    # Update timeline cumulatively across all shots
    cur_t = 0.0
    for s in shots:
        s["start_sec"] = round(cur_t, 3)
        cur_t += s["duration_sec"]
        s["end_sec"] = round(cur_t, 3)

    # 4. Stitch master voice audio
    master_voice_wav = EP_DIR / "audio" / "pilot_5_master_voice_48k.wav"
    with wave.open(str(master_voice_wav), "wb") as mwf:
        mwf.setnchannels(channels)
        mwf.setsampwidth(2)
        mwf.setframerate(sample_rate)
        for p in padded_paths:
            with wave.open(str(p), "rb") as in_f:
                mwf.writeframes(in_f.readframes(in_f.getnframes()))

    master_dur = total_samples / sample_rate
    print(f"\n✅ Master Voice Stitched: {master_voice_wav.name} ({master_dur:.3f}s, {master_voice_wav.stat().st_size:,} bytes)")
    return master_voice_wav


# =========================================================================
# STEP 2: Google Flow CDP Image Generation
# =========================================================================

async def generate_pilot_images(shots: List[Dict[str, Any]]) -> List[Path]:
    print("\n=======================================================")
    print(f"🎨 [STEP 2] Google Flow CDP Image Generation ({len(shots)} Shots)")
    print("=======================================================")

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    APPROVED_DIR.mkdir(parents=True, exist_ok=True)

    result_images = []

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        pages = [pg for ctx in browser.contexts for pg in ctx.pages if "flow" in pg.url or "labs.google" in pg.url]
        if not pages:
            raise RuntimeError("No Google Flow tab found on Chrome CDP port 9222")
        page = pages[0]
        print(f"Connected to Flow page: {page.url}")

        # Ensure we are in project canvas
        if "/project/" not in page.url:
            print("Navigating to project canvas...")
            first_proj = await page.query_selector("a[href*='/project/']")
            if first_proj:
                await first_proj.click()
                await page.wait_for_timeout(4000)

        for idx, s in enumerate(shots, 1):
            shot_id = s["shot_id"]
            prompt = s["visual"]["prompt_en"]
            out_img = IMAGES_DIR / f"{shot_id}.jpg"
            appr_img = APPROVED_DIR / f"{shot_id}.jpg"

            # 1. Idempotent check
            if out_img.exists() and out_img.stat().st_size > 50000:
                print(f"[{idx}/{len(shots)}] Image cached for {shot_id} ({out_img.stat().st_size:,} bytes). Skipping.")
                if not appr_img.exists():
                    shutil.copy2(out_img, appr_img)
                result_images.append(out_img)
                continue

            print(f"\n[{idx}/{len(shots)}] Submitting prompt for {shot_id}...")
            print(f"   Prompt: {prompt[:80]}...")

            # 2. Capture baseline images
            baseline_urls = set(await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('img')).map(i => i.src || i.currentSrc || '');
            }"""))

            # 3. Focus textbox and clear
            tb = await page.query_selector("div[role='textbox'], [contenteditable='true'], textarea")
            if not tb:
                raise RuntimeError("Flow prompt textbox not found")

            await tb.click(force=True)
            await page.wait_for_timeout(200)

            # Insert prompt via evaluate to prevent clipboard truncation
            await page.evaluate("""(p) => {
                const el = document.querySelector("div[role='textbox'], [contenteditable='true'], textarea");
                if (el) {
                    el.focus();
                    document.execCommand('selectAll', false, null);
                    document.execCommand('insertText', false, p);
                }
            }""", prompt)
            await page.wait_for_timeout(400)

            # 4. Submit via arrow_forward button or Enter
            submit_btn = await page.query_selector("button:has-text('arrow_forward'), button:has-text('만들기')")
            if submit_btn and await submit_btn.is_visible():
                await submit_btn.click(force=True)
            else:
                await page.keyboard.press("Enter")

            print("   Submitted! Polling for new generated image card...")

            # 5. Poll for new image card (up to 45s)
            start_time = time.time()
            new_img_url = None
            while time.time() - start_time < 45:
                await page.wait_for_timeout(2500)
                cur_imgs = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('img')).map(i => i.src || i.currentSrc || '');
                }""")
                candidates = [
                    u for u in cur_imgs
                    if (('googleusercontent.com' in u or 'flow-content.google' in u or 'labs.google/fx' in u)
                        and 'flower-placeholder' not in u and 'favicon' not in u
                        and u not in baseline_urls and len(u) > 20)
                ]
                if candidates:
                    new_img_url = candidates[-1]
                    break

            if not new_img_url:
                raise TimeoutError(f"Image generation timed out after 45s for {shot_id}")

            print(f"   Detected new image card: {new_img_url[:70]}...")

            # 6. Download and Lanczos normalize to 1920x1080 JPEG quality 95
            resp = await page.request.get(new_img_url)
            if resp.status != 200:
                raise RuntimeError(f"Failed to download image from {new_img_url}: HTTP {resp.status}")

            part_file = out_img.with_suffix(".jpg.part")
            part_file.write_bytes(await resp.body())

            with Image.open(part_file) as im:
                im_rgb = im.convert("RGB")
                if im_rgb.size != (1920, 1080):
                    im_rgb = im_rgb.resize((1920, 1080), Image.Resampling.LANCZOS)
                im_rgb.save(out_img, format="JPEG", quality=95)
            part_file.unlink(missing_ok=True)

            shutil.copy2(out_img, appr_img)
            print(f"   ✅ Saved {shot_id}.jpg: 1920x1080 ({out_img.stat().st_size:,} bytes)")

            # Gate 8 Visibility check
            eval_res = evaluate_frame_visibility_from_file(out_img)
            print(f"   Gate 8 Evaluation: passed={eval_res['passed']} (edge_density={eval_res['edge_density']}, non_bg_coverage={eval_res['non_bg_coverage']})")

            result_images.append(out_img)

            # Adaptive Jittered Cooldown (3.5s)
            await page.wait_for_timeout(3500)

    return result_images


# =========================================================================
# STEP 3: Subpixel Motion Video Clip Rendering
# =========================================================================

def render_pilot_motion_clips(shots: List[Dict[str, Any]], images: List[Path]) -> Path:
    print("\n=======================================================")
    print(f"🎬 [STEP 3] Smooth Subpixel Motion Clip Rendering ({len(shots)} Clips)")
    print("=======================================================")

    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    clip_paths = []

    motion_map = {
        "SHOT_001": "push_in",
        "SHOT_002": "pan_right",
        "SHOT_003": "pull_out",
        "SHOT_004": "push_in",
        "SHOT_005": "pan_left",
    }

    for idx, (s, img_path) in enumerate(zip(shots, images), 1):
        shot_id = s["shot_id"]
        dur = float(s["duration_sec"])
        motion = motion_map.get(shot_id, "push_in")
        out_clip = CLIPS_DIR / f"{shot_id}.mp4"

        print(f"[{idx}/{len(shots)}] Rendering {shot_id}.mp4: motion='{motion}', duration={dur:.2f}s, 1920x1080 @ 25fps...")
        render_smooth_motion_clip(
            image_path=img_path,
            output_path=out_clip,
            duration=dur,
            motion=motion,
            fps=25,
            width=1920,
            height=1080,
        )

        real_dur = get_ffprobe_duration(out_clip)
        print(f"   -> Rendered {out_clip.name}: {real_dur:.3f}s ({out_clip.stat().st_size:,} bytes)")
        clip_paths.append(out_clip)

    # Concatenate clips using FFmpeg concat demuxer
    concat_list = CLIPS_DIR / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{p.resolve().as_posix()}'\n")

    concat_video = EP_DIR / "video" / "pilot_5_concat_video.mp4"
    concat_video.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(concat_video)
    ]
    subprocess.run(cmd, check=True)

    concat_dur = get_ffprobe_duration(concat_video)
    print(f"\n✅ Concat Video Assembled: {concat_video.name} ({concat_dur:.3f}s, {concat_video.stat().st_size:,} bytes)")
    return concat_video


# =========================================================================
# STEP 4: ASS Subtitles Compilation
# =========================================================================

def compile_pilot_subtitles(shots: List[Dict[str, Any]]) -> Path:
    print("\n=======================================================")
    print("📝 [STEP 4] 52pt Pretendard ASS Subtitle Compilation")
    print("=======================================================")

    SUBTITLES_DIR.mkdir(parents=True, exist_ok=True)
    ass_path = SUBTITLES_DIR / "pilot_5.ass"

    engine = SemanticSubtitleEngine(font_size=52, max_line_chars=36, max_clause_chars=70)
    engine.compile_ass_subtitles(shots=shots, output_path=ass_path, title="Human Library Pilot-5")

    audit = engine.audit_ass_file(ass_path, max_line_chars=36)
    print(f"ASS Audit Result: status={audit['status']}, events={audit['dialogue_events']}, violations={audit['violations_count']}")
    if audit["status"] != "PASS":
        print(f"⚠️ Subtitle violations: {audit['violations']}")
        raise ValueError("Subtitle formatting violations detected!")

    print(f"✅ Subtitles Compiled & Audited: {ass_path.name}")
    return ass_path


# =========================================================================
# STEP 5 & 6: Pre-Mux Parity & Master Mux
# =========================================================================

def mux_pilot_master(concat_video: Path, master_audio: Path, ass_path: Path) -> Path:
    print("\n=======================================================")
    print("🎛️ [STEP 5 & 6] Pre-Mux Parity & Master Multiplexing")
    print("=======================================================")

    CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)
    master_mp4 = EP_DIR / "pilot_5_master.mp4"

    v_dur = get_ffprobe_duration(concat_video)
    a_dur = get_ffprobe_duration(master_audio)
    diff = abs(v_dur - a_dur)

    print(f"Pre-Mux Parity Check:")
    print(f"   Concat Video: {v_dur:.3f}s")
    print(f"   Master Audio: {a_dur:.3f}s")
    print(f"   Parity Delta: {diff:.4f}s (Tolerance <= 0.040s)")

    if diff > 0.040:
        raise ValueError(f"Pre-Mux Strict Parity Gate FAILED: Delta {diff:.4f}s > 0.040s")

    print("   -> Strict Parity Gate: PASSED ✅")

    # Mux with subtitle burning via sub filter for absolute visual fidelity
    ass_escaped = str(ass_path.resolve().as_posix()).replace(":", "\\:")
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(concat_video),
        "-i", str(master_audio),
        "-vf", f"subtitles='{ass_escaped}'",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "320k",
        "-ar", "48000",
        "-pix_fmt", "yuv420p",
        str(master_mp4)
    ]
    print(f"Executing FFmpeg Master Multiplex to {master_mp4.name}...")
    subprocess.run(cmd, check=True)

    master_dur = get_ffprobe_duration(master_mp4)
    print(f"✅ Final Master Rendered: {master_mp4} ({master_dur:.3f}s, {master_mp4.stat().st_size:,} bytes)")
    return master_mp4


# =========================================================================
# STEP 7: Gate 8 Decoded Frame Analysis
# =========================================================================

def verify_gate8_master(master_mp4: Path, shots: List[Dict[str, Any]]) -> Dict[str, Any]:
    print("\n=======================================================")
    print("🔍 [STEP 7] Gate 8 Physical Decoded Frame Verification")
    print("=======================================================")

    cap = cv2.VideoCapture(str(master_mp4))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open master video for decoding: {master_mp4}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap_dur = total_frames / max(1.0, fps)

    print(f"Decoded Stream Geometry: {width}x{height} @ {fps:.2f}fps, {total_frames} frames ({cap_dur:.3f}s)")

    if width != 1920 or height != 1080:
        raise ValueError(f"Geometry mismatch: expected 1920x1080, got {width}x{height}")

    boundary_evaluations = []
    for s in shots:
        shot_id = s["shot_id"]
        start_sec = float(s["start_sec"])
        target_frame = int(round(start_sec * fps))

        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        if not ret:
            raise RuntimeError(f"Could not read frame at t={start_sec}s (frame {target_frame})")

        from lib.asset_contract import evaluate_frame_visibility_gate
        eval_res = evaluate_frame_visibility_gate(frame)
        print(f"Shot Boundary [{shot_id}] at t={start_sec:.2f}s: passed={eval_res['passed']}, coverage={eval_res['non_bg_coverage']:.3f}, edge={eval_res['edge_density']:.3f}")
        boundary_evaluations.append({
            "shot_id": shot_id,
            "start_sec": start_sec,
            "frame": target_frame,
            "evaluation": eval_res
        })

    cap.release()
    all_passed = all(b["evaluation"]["passed"] for b in boundary_evaluations)
    print(f"Gate 8 Result: {'ALL BOUNDARIES PASSED ✅' if all_passed else 'SOME FAILED ❌'}")
    return {
        "passed": all_passed,
        "width": width,
        "height": height,
        "fps": fps,
        "duration_sec": cap_dur,
        "boundaries": boundary_evaluations
    }


# =========================================================================
# STEP 8: Release Manifest & Provenance Registration
# =========================================================================

def generate_release_manifest(
    master_mp4: Path,
    master_audio: Path,
    concat_video: Path,
    images: List[Path],
    shots: List[Dict[str, Any]],
    gate8_report: Dict[str, Any]
) -> Path:
    print("\n=======================================================")
    print("📜 [STEP 8] Release Manifest Generation (SHA-256 Chain)")
    print("=======================================================")

    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = METADATA_DIR / "pilot_5_release_manifest.json"

    manifest_data = {
        "schema_version": "1.0.0",
        "release_id": f"human_library_replica_pilot5_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "episode_id": "rank1_race_adaptation_pilot5",
        "target_duration_sec": 20.600,
        "measured_duration_sec": get_ffprobe_duration(master_mp4),
        "pre_mux_parity_difference_sec": abs(get_ffprobe_duration(concat_video) - get_ffprobe_duration(master_audio)),
        "master_video": {
            "path": str(master_mp4),
            "sha256": compute_sha256(master_mp4),
            "bytes": master_mp4.stat().st_size,
            "duration_sec": get_ffprobe_duration(master_mp4),
            "resolution": f"{gate8_report['width']}x{gate8_report['height']}",
            "fps": gate8_report["fps"],
        },
        "master_audio": {
            "path": str(master_audio),
            "sha256": compute_sha256(master_audio),
            "bytes": master_audio.stat().st_size,
            "duration_sec": get_ffprobe_duration(master_audio),
            "sample_rate": 48000,
            "channels": 2,
        },
        "gate8_verification": gate8_report,
        "shots": []
    }

    for s, img_p in zip(shots, images):
        shot_id = s["shot_id"]
        manifest_data["shots"].append({
            "shot_id": shot_id,
            "order": s["order"],
            "duration_sec": s["duration_sec"],
            "start_sec": s["start_sec"],
            "end_sec": s["end_sec"],
            "spoken_text": s["spoken_text"],
            "image": {
                "path": str(img_p),
                "sha256": compute_sha256(img_p),
                "bytes": img_p.stat().st_size,
            },
            "audio_raw": {
                "path": str(RAW_AUDIO_DIR / f"{shot_id}.wav"),
                "sha256": compute_sha256(RAW_AUDIO_DIR / f"{shot_id}.wav"),
            },
            "audio_padded": {
                "path": str(PADDED_AUDIO_DIR / f"{shot_id}.wav"),
                "sha256": compute_sha256(PADDED_AUDIO_DIR / f"{shot_id}.wav"),
            },
            "clip": {
                "path": str(CLIPS_DIR / f"{shot_id}.mp4"),
                "sha256": compute_sha256(CLIPS_DIR / f"{shot_id}.mp4"),
            }
        })

    manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Release Manifest Saved: {manifest_path}")
    return manifest_path


# =========================================================================
# MAIN ORCHESTRATOR
# =========================================================================

def main():
    print("=================================================================")
    print("🚀 LAUNCHING HUMAN LIBRARY PILOT-5 REPLICA GENERATION (20.6s)")
    print("=================================================================")

    if not BUNDLE_PATH.exists():
        raise FileNotFoundError(f"Bundle file missing at {BUNDLE_PATH}")

    bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    shots = bundle["shots"]
    print(f"Loaded {len(shots)} shots from {BUNDLE_PATH.name} (target: {bundle['target_duration_sec']}s)")

    # 1. Synthesize audio
    master_audio = synthesize_pilot_audio(shots)

    # 2. Generate Flow images
    images = asyncio.run(generate_pilot_images(shots))

    # 3. Render motion clips
    concat_video = render_pilot_motion_clips(shots, images)

    # 4. Compile subtitles
    ass_path = compile_pilot_subtitles(shots)

    # 5 & 6. Mux master video
    master_mp4 = mux_pilot_master(concat_video, master_audio, ass_path)

    # 7. Gate 8 verification
    gate8_report = verify_gate8_master(master_mp4, shots)

    # 8. Release manifest
    manifest_path = generate_release_manifest(master_mp4, master_audio, concat_video, images, shots, gate8_report)

    print("\n=================================================================")
    print("🎉 PILOT-5 GENERATION & PHYSICAL VERIFICATION COMPLETE!")
    print(f"Master Video:     {master_mp4} ({master_mp4.stat().st_size:,} bytes)")
    print(f"Release Manifest: {manifest_path}")
    print("=================================================================\n")


if __name__ == "__main__":
    main()
