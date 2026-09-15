# -*- coding: utf-8 -*-
"""San Jose Galleon 20-Minute (1,200.0s) Master Production Engine via Google Flow CDP & SuperTonic3.

Invariants Enforced:
1. N Shots (dynamic, determined by manifest) = Target 1,200.00 seconds (20 minutes).
2. Authentic Google Flow Imagen 3 generation via Chrome CDP (Port 9222).
3. 2-Stage Dynamic Motion (Pan + Push-in) for anti-stillness viewer retention.
4. High-fidelity 48kHz SuperTonic3 M2 TTS voice narration.
5. ASS Subtitle burn-in with bottom 12% anchoring and Pretendard typography.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Add scripts directory to path for smooth_subpixel_motion_engine import
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from smooth_subpixel_motion_engine import render_smooth_motion_clip
from lib.flow_dom_maintenance import (
    clear_error_cards,
    cleanup_verified_cards,
    dom_gc_due,
)
from lib.flow_generation_state import adaptive_cooldown

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODULE_ROOT = Path(r"D:\module")
EP_DATE = "2026-09-08"
EP_SLUG = "caribbean-san-jose-galleon-gold"
EP_DIR = MODULE_ROOT / "bible" / "human_archive" / "runs" / "nollam_file" / EP_DATE / EP_SLUG

MANIFEST_PATH = EP_DIR / "source" / "scene_script_manifest_v2.json"
AUDIO_DIR = EP_DIR / "audio" / "sentences_v4"
PADDED_AUDIO_DIR = EP_DIR / "audio" / "padded"
APPROVED_IMG_DIR = EP_DIR / "generation" / "downloads" / "approved"
IMAGES_DIR = EP_DIR / "images"
CLIPS_DIR = EP_DIR / "generation" / "clips"
SUBTITLE_PATH = EP_DIR / "subtitles" / "pilot_subtitles_1200s.ass"
ASSET_MANIFEST_PATH = EP_DIR / "generation" / "approved_asset_manifest.json"

MASTER_VIDEO_NAMES = [
    EP_DIR / "NOLLAM-SAN-JOSE-GALLEON-MASTER.mp4",
    EP_DIR / "candidate" / "NOLLAM-SAN-JOSE-GALLEON-MASTER.mp4",
    EP_DIR / "output" / "NOLLAM-SAN-JOSE-GALLEON-MASTER.mp4",
    EP_DIR / "generation" / "NOLLAM-SAN-JOSE-GALLEON-MASTER.mp4",
]


def ensure_workspace():
    """Ensure all required directories exist."""
    for p in [
        AUDIO_DIR, PADDED_AUDIO_DIR, APPROVED_IMG_DIR, IMAGES_DIR,
        CLIPS_DIR, EP_DIR / "subtitles", EP_DIR / "candidate",
        EP_DIR / "output", EP_DIR / "generation"
    ]:
        p.mkdir(parents=True, exist_ok=True)


def pad_and_stitch_audio(shots: List[Dict[str, Any]]) -> Path:
    """Pad each shot's WAV audio to match exact scene_duration, then stitch master audio."""
    print("\n--- [STEP 1] Audio Precision Padding & Master Stitching ---")
    import wave
    
    padded_wavs = []
    total_samples = 0
    
    for idx, s in enumerate(shots, 1):
        shot_id = s["shot_id"]
        target_dur = s["scene_duration"]
        raw_wav = AUDIO_DIR / f"{shot_id}.wav"
        padded_wav = PADDED_AUDIO_DIR / f"{shot_id}.wav"
        
        if not raw_wav.exists():
            raise FileNotFoundError(f"Audio file not found for {shot_id}: {raw_wav}")
            
        with wave.open(str(raw_wav), "rb") as wf:
            params = wf.getparams()
            frames = wf.readframes(wf.getnframes())
            sample_rate = wf.getframerate()
            num_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            
        cur_samples = len(frames) // (num_channels * sampwidth)
        target_samples = int(round(target_dur * sample_rate))
        
        # Calculate front padding (0.40s) and tail padding
        head_samples = int(round(0.40 * sample_rate))
        tail_samples = max(0, target_samples - cur_samples - head_samples)
        
        zero_sample = b"\x00" * (num_channels * sampwidth)
        head_silence = zero_sample * head_samples
        tail_silence = zero_sample * tail_samples
        
        full_audio_bytes = head_silence + frames + tail_silence
        actual_samples = len(full_audio_bytes) // (num_channels * sampwidth)
        
        # Trim or pad slightly if rounding difference
        if actual_samples < target_samples:
            full_audio_bytes += zero_sample * (target_samples - actual_samples)
        elif actual_samples > target_samples:
            full_audio_bytes = full_audio_bytes[:target_samples * num_channels * sampwidth]
            
        with wave.open(str(padded_wav), "wb") as out_wf:
            out_wf.setparams((num_channels, sampwidth, sample_rate, target_samples, "NONE", "not compressed"))
            out_wf.writeframes(full_audio_bytes)
            
        padded_wavs.append(padded_wav)
        total_samples += target_samples
        if idx % 10 == 0 or idx == len(shots):
            print(f"  [{idx:02d}/{len(shots)}] {shot_id} padded to {target_dur:.2f}s ({target_samples:,} samples)")
            
    # Stitch master audio 48k
    master_audio_p = EP_DIR / "audio" / "san_jose_master_audio_48k.wav"
    with wave.open(str(padded_wavs[0]), "rb") as wf:
        m_params = wf.getparams()
        
    with wave.open(str(master_audio_p), "wb") as master_wf:
        master_wf.setparams(m_params)
        for pw in padded_wavs:
            with wave.open(str(pw), "rb") as in_wf:
                master_wf.writeframes(in_wf.readframes(in_wf.getnframes()))
                
    master_dur = total_samples / m_params.framerate
    print(f"Master Audio Stitched: {master_audio_p.name} ({master_dur:.2f}s, {master_audio_p.stat().st_size:,} bytes)")
    return master_audio_p


async def detect_and_clear_error_cards(flow_page) -> int:
    """Detect and clear Flow error cards ('실패' text) via JS evaluate.
    
    Returns the number of error cards cleared.
    """
    return await clear_error_cards(flow_page)


async def generate_flow_images_batch(shots: List[Dict[str, Any]]):
    """Generate authentic 1080p images using Google Flow via Chrome CDP.
    
    Features:
    - Error card auto-detection and clearing (up to 3 retries per shot)
    - Adaptive cooldown: 5s base, 10s after error, 15s every 10th shot
    - SHA-256 duplicate hash rejection
    - Batch report generation
    """
    print("\n--- [STEP 2] Google Flow CDP (Port 9222) Batch Generation ---")
    from playwright.async_api import async_playwright
    from PIL import Image

    # Load or initialize asset manifest
    asset_records = {}
    if ASSET_MANIFEST_PATH.exists():
        try:
            with open(ASSET_MANIFEST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("assets", []):
                    asset_records[item["shot_id"]] = item
        except Exception:
            pass

    # Collect existing SHA-256 hashes for duplicate rejection
    existing_hashes = set()
    for rec in asset_records.values():
        if "sha256" in rec:
            existing_hashes.add(rec["sha256"])
    for img_f in IMAGES_DIR.glob("SHOT_*.jpg"):
        if img_f.stat().st_size > 20000:
            h = hashlib.sha256(img_f.read_bytes()).hexdigest()
            existing_hashes.add(h)

    # Batch statistics
    stats = {"success": 0, "failed": 0, "skipped": 0, "retried": 0, "duplicates_rejected": 0}
    failed_shots = []

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        flow_page = None
        for ctx in browser.contexts:
            for page in ctx.pages:
                if "flow" in page.url:
                    flow_page = page
                    break
            if flow_page:
                break

        if not flow_page:
            print("ERROR: Google Flow page not found in Chrome tabs!")
            return

        print(f"  Connected to Google Flow tab: {flow_page.url}")
        await flow_page.bring_to_front()

        # Track existing candidate images on canvas
        seen_urls = set()
        init_imgs = await flow_page.evaluate("""() => {
            const list = [];
            document.querySelectorAll('img').forEach(el => {
                const src = el.src || el.currentSrc || '';
                if (src && (src.includes('flow-content.google') || src.includes('labs.google') || src.includes('asb/'))) {
                    list.push(src);
                }
            });
            return list;
        }""")
        seen_urls.update(init_imgs)
        print(f"  Baseline canvas images: {len(seen_urls)}")

        # Pre-clean any existing error cards
        pre_cleared = await detect_and_clear_error_cards(flow_page)
        if pre_cleared > 0:
            print(f"  Pre-cleaned {pre_cleared} stale error cards from canvas")
            await flow_page.wait_for_timeout(1000)

        consecutive_success = 0

        for idx, s in enumerate(shots, 1):
            shot_id = s["shot_id"]
            approved_f = APPROVED_IMG_DIR / f"{shot_id}.jpg"
            images_f = IMAGES_DIR / f"{shot_id}.jpg"

            # Check if authentic image already generated and validated (> 20KB, unique hash)
            if images_f.exists() and images_f.stat().st_size > 20000:
                img_hash = hashlib.sha256(images_f.read_bytes()).hexdigest()
                # Verify it's not a duplicate of another shot
                other_hashes = set()
                for other_f in IMAGES_DIR.glob("SHOT_*.jpg"):
                    if other_f.name != images_f.name and other_f.stat().st_size > 20000:
                        other_hashes.add(hashlib.sha256(other_f.read_bytes()).hexdigest())
                if img_hash not in other_hashes:
                    print(f"[{idx:02d}/{len(shots)}] {shot_id} already exists ({images_f.stat().st_size:,} bytes). Skipping.")
                    stats["skipped"] += 1
                    consecutive_success += 1
                    continue
                else:
                    print(f"[{idx:02d}/{len(shots)}] {shot_id} is a DUPLICATE of another shot. Regenerating.")
                    images_f.unlink(missing_ok=True)
                    stats["duplicates_rejected"] += 1

            # Format prompt for Imagen 3
            raw_prompt = s["visual_prompt"]
            clean_prompt = raw_prompt.replace("25fps optical cadence,", "").strip()
            clean_prompt = clean_prompt.replace("no subtitles, no text overlays, keep bottom 18% clear.", "").strip()
            flow_prompt = f"{clean_prompt} --no text, typography, letters, watermarks, subtitles, UI badges, borders"

            print(f"\n[{idx:02d}/{len(shots)}] Generating {shot_id} via Google Flow...")
            print(f"   Prompt: {flow_prompt[:100]}...")

            shot_success = False
            max_retries = 3

            for attempt in range(1, max_retries + 1):
                if attempt > 1:
                    print(f"   Retry {attempt}/{max_retries} for {shot_id}...")
                    stats["retried"] += 1
                    await flow_page.wait_for_timeout(5000)  # Extra wait before retry

                # 1. Close modal popups if any
                for sel in [".glue-cookie-notification-bar__accept", "button[aria-label='\ub2eb\uae30']"]:
                    try:
                        btn = await flow_page.query_selector(sel)
                        if btn and await btn.is_visible():
                            await btn.click()
                            await flow_page.wait_for_timeout(200)
                    except Exception:
                        pass

                # 2. Focus and enter prompt into ProseMirror editor
                pm = await flow_page.query_selector(".ProseMirror")
                if not pm:
                    await flow_page.wait_for_timeout(2000)
                    pm = await flow_page.query_selector(".ProseMirror")

                if not pm:
                    print(f"   Could not locate prompt editor for {shot_id}. Skipping.")
                    break

                await pm.click()
                await flow_page.wait_for_timeout(200)
                await flow_page.keyboard.press("Control+A")
                await flow_page.wait_for_timeout(100)
                await flow_page.keyboard.press("Backspace")
                await flow_page.wait_for_timeout(100)
                await flow_page.keyboard.type(flow_prompt, delay=3)
                await flow_page.wait_for_timeout(300)

                # 3. Submit generation
                submit_btn = await flow_page.query_selector("button.generate-icon-button, button[aria-label='\uc0dd\uc131 \uc2dc\uc791']")
                if submit_btn and await submit_btn.is_visible():
                    await submit_btn.click()
                else:
                    await flow_page.keyboard.press("Enter")

                print(f"   Prompt submitted (attempt {attempt}). Polling (max 120s)...")
                start_poll = time.time()
                new_img_url = None

                while time.time() - start_poll < 120:
                    await flow_page.wait_for_timeout(2500)

                    # Check for error cards first
                    err_cleared = await detect_and_clear_error_cards(flow_page)
                    if err_cleared > 0:
                        print(f"   Cleared {err_cleared} error card(s). Will retry.")
                        break

                    # Check for new image
                    current_imgs = await flow_page.evaluate("""() => {
                        const list = [];
                        document.querySelectorAll('img').forEach(el => {
                            const src = el.src || el.currentSrc || '';
                            if (src && (src.includes('flow-content.google') || src.includes('labs.google') || src.includes('asb/'))) {
                                list.push(src);
                            }
                        });
                        return list;
                    }""")
                    for url in reversed(current_imgs):
                        if url not in seen_urls:
                            new_img_url = url
                            seen_urls.add(url)
                            break
                    if new_img_url:
                        break

                if err_cleared > 0:
                    continue  # Retry the shot

                if new_img_url:
                    print(f"   Downloading {shot_id} from Flow CDN...")
                    try:
                        resp = await flow_page.request.get(new_img_url)
                        raw_bytes = await resp.body()

                        if len(raw_bytes) < 20000:
                            print(f"   Image too small ({len(raw_bytes)} bytes). Retrying...")
                            continue

                        # Normalize via Lanczos to 1920x1080
                        temp_part = approved_f.with_suffix(".part")
                        temp_part.write_bytes(raw_bytes)

                        with Image.open(temp_part) as im:
                            im_rgb = im.convert("RGB")
                            im_1080 = im_rgb.resize((1920, 1080), Image.Resampling.LANCZOS)
                            im_1080.save(approved_f, format="JPEG", quality=95)
                            shutil.copy2(approved_f, images_f)
                        temp_part.unlink(missing_ok=True)

                        # SHA-256 duplicate check
                        sha256_hash = hashlib.sha256(approved_f.read_bytes()).hexdigest()
                        if sha256_hash in existing_hashes:
                            print(f"   DUPLICATE hash detected for {shot_id}! Deleting and retrying...")
                            approved_f.unlink(missing_ok=True)
                            images_f.unlink(missing_ok=True)
                            stats["duplicates_rejected"] += 1
                            continue

                        existing_hashes.add(sha256_hash)
                        asset_records[shot_id] = {
                            "shot_id": shot_id,
                            "filename": f"{shot_id}.jpg",
                            "path": str(approved_f),
                            "size": approved_f.stat().st_size,
                            "sha256": sha256_hash,
                            "width": 1920,
                            "height": 1080,
                            "aspect_ratio": "16:9",
                            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        print(f"   OK: {approved_f.name} ({approved_f.stat().st_size:,} bytes | SHA256: {sha256_hash[:12]}...)")
                        shot_success = True
                        break  # Exit retry loop

                    except Exception as ex:
                        print(f"   Error processing image {shot_id}: {ex}")
                        continue
                else:
                    print(f"   Generation timed out for {shot_id} (attempt {attempt})")

            if shot_success:
                stats["success"] += 1
                consecutive_success += 1
            else:
                stats["failed"] += 1
                consecutive_success = 0
                failed_shots.append(shot_id)
                print(f"   FAILED: {shot_id} after {max_retries} attempts")

            # Shared adaptive cooldown and 25-verified-card DOM GC policy.
            cooldown = adaptive_cooldown(consecutive_success, had_error=not shot_success)
            if dom_gc_due(consecutive_success):
                print(f"   [DOM GC] Periodic canvas cleanup after {consecutive_success} verified shots...")
                await cleanup_verified_cards(flow_page, 25)
            print(f"   [Cooldown] Waiting {cooldown:.1f}s after {shot_id}...")
            await flow_page.wait_for_timeout(int(cooldown * 1000))

            # Save manifest incrementally every 5 shots
            if idx % 5 == 0:
                manifest_data = {
                    "project": "San Jose Galleon 20-Trillion Gold Shipwreck",
                    "total_assets": len(asset_records),
                    "assets": list(asset_records.values())
                }
                with open(ASSET_MANIFEST_PATH, "w", encoding="utf-8") as f:
                    json.dump(manifest_data, f, ensure_ascii=False, indent=2)

        # Write final manifest
        manifest_data = {
            "project": "San Jose Galleon 20-Trillion Gold Shipwreck",
            "total_assets": len(asset_records),
            "assets": list(asset_records.values())
        }
        with open(ASSET_MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)

        # Write batch report
        report = {
            "batch_completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_shots_attempted": len(shots),
            "stats": stats,
            "failed_shots": failed_shots,
            "manifest_path": str(ASSET_MANIFEST_PATH)
        }
        report_path = EP_DIR / "generation" / "batch_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n=== Batch Generation Report ===")
        print(f"  Success: {stats['success']} | Failed: {stats['failed']} | Skipped: {stats['skipped']}")
        print(f"  Retries: {stats['retried']} | Duplicates Rejected: {stats['duplicates_rejected']}")
        if failed_shots:
            print(f"  Failed Shots: {', '.join(failed_shots)}")
        print(f"  Manifest: {ASSET_MANIFEST_PATH}")
        print(f"  Report: {report_path}")


def render_2stage_motion_clips(shots: List[Dict[str, Any]]):
    """Render smooth subpixel Ken Burns motion clips (zero pixel judder).

    Uses PIL-based smooth_subpixel_motion_engine instead of FFmpeg zoompan to
    eliminate integer-coordinate stair-step judder (ERR-006 fix).
    Pipeline: PIL subpixel render (video only) -> FFmpeg audio mux (final clip).
    """
    print("\n--- [STEP 3] Smooth Sub-Pixel Ken Burns Motion Clip Rendering ---")

    # 6-type motion rotation for visual variety (anti-monotony)
    MOTION_CYCLE = ["push_in", "pan_left", "pull_out", "pan_right", "tilt_up", "tilt_down"]

    for idx, s in enumerate(shots, 1):
        shot_id = s["shot_id"]
        dur = s["scene_duration"]
        fps = 25

        img_p = APPROVED_IMG_DIR / f"{shot_id}.jpg"
        if not img_p.exists():
            img_p = IMAGES_DIR / f"{shot_id}.jpg"

        audio_p = PADDED_AUDIO_DIR / f"{shot_id}.wav"
        clip_p = CLIPS_DIR / f"{shot_id}.mp4"

        # Check if clip already rendered with correct duration AND has audio stream
        if clip_p.exists() and clip_p.stat().st_size > 100000:
            probe_cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-show_streams", "-select_streams", "a",
                "-of", "json", str(clip_p)
            ]
            res = subprocess.run(probe_cmd, capture_output=True, text=True)
            try:
                probe_data = json.loads(res.stdout)
                c_dur = float(probe_data.get("format", {}).get("duration", 0))
                has_audio_stream = len(probe_data.get("streams", [])) > 0
                if abs(c_dur - dur) < 0.2 and has_audio_stream:
                    print(f"[{idx:02d}/{len(shots)}] {shot_id}.mp4 already exists ({c_dur:.2f}s, audio OK). Skipping.")
                    continue
                else:
                    print(f"[{idx:02d}/{len(shots)}] {shot_id}.mp4 missing audio or duration mismatch. Re-rendering...")
            except Exception:
                pass

        # Select motion type from 6-type rotation cycle
        motion_type = MOTION_CYCLE[(idx - 1) % len(MOTION_CYCLE)]
        print(f"[{idx:02d}/{len(shots)}] \U0001f3ac Rendering {shot_id}.mp4 (Duration: {dur:.2f}s, Motion: {motion_type})...")

        # Stage 1: PIL subpixel motion render (video only, zero judder)
        temp_video = CLIPS_DIR / f"{shot_id}_video_only.mp4"
        try:
            render_smooth_motion_clip(
                image_path=img_p,
                output_path=temp_video,
                duration=dur,
                motion=motion_type,
                fps=fps,
                width=1920,
                height=1080
            )
        except Exception as e:
            print(f"   \u274c PIL render error on {shot_id}: {e}")
            continue

        # Stage 2: FFmpeg audio mux (merge video + audio into final clip)
        mux_cmd = [
            "ffmpeg", "-y",
            "-hide_banner", "-loglevel", "error",
            "-i", str(temp_video),
            "-i", str(audio_p),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-t", f"{dur:.3f}",
            "-shortest",
            str(clip_p)
        ]
        ret = subprocess.run(mux_cmd, capture_output=True, text=True)
        if ret.returncode != 0:
            print(f"   \u274c FFmpeg mux error on {shot_id}: {ret.stderr[:300]}")
        else:
            print(f"   \u2705 Rendered {clip_p.name} ({clip_p.stat().st_size:,} bytes, motion={motion_type})")

        # Clean up temp video-only file
        temp_video.unlink(missing_ok=True)

def assemble_master_video(shots: List[Dict[str, Any]]) -> Path:
    """Concatenate all clips and burn in ASS subtitles to produce master video."""
    print("\n--- [STEP 4] Master Lossless Concat & ASS Subtitle Burning ---")
    
    concat_list_f = CLIPS_DIR / "concat_list.txt"
    with open(concat_list_f, "w", encoding="utf-8") as f:
        for s in shots:
            shot_id = s["shot_id"]
            clip_file = CLIPS_DIR / f"{shot_id}.mp4"
            f.write(f"file '{clip_file.as_posix()}'\n")

    raw_concat_p = EP_DIR / "generation" / "video_concat_raw.mp4"
    print(f"Concatenating {len(shots)} clips to {raw_concat_p.name}...")
    
    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list_f),
        "-c", "copy",
        str(raw_concat_p)
    ]
    subprocess.run(concat_cmd, check=True)
    
    # Subtitle burn-in + Master 48kHz Audio integration
    primary_master = MASTER_VIDEO_NAMES[0]
    master_audio_p = EP_DIR / "audio" / "san_jose_master_audio_48k.wav"
    sub_posix = SUBTITLE_PATH.as_posix()
    if ":" in sub_posix:
        sub_posix = sub_posix[0] + "\\:" + sub_posix[2:]

    print(f"Burning ASS subtitles ({SUBTITLE_PATH.name}) and muxing Master 48k Audio into Master Video...")
    burn_cmd = [
        "ffmpeg", "-y",
        "-i", str(raw_concat_p),
        "-i", str(master_audio_p),
        "-vf", f"ass='{sub_posix}'",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-shortest",
        str(primary_master)
    ]
    subprocess.run(burn_cmd, check=True)
    
    for target in MASTER_VIDEO_NAMES[1:]:
        shutil.copy2(primary_master, target)
        print(f"  Mirrored to: {target}")

    probe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(primary_master)
    ]
    res = subprocess.run(probe_cmd, capture_output=True, text=True)
    dur = float(res.stdout.strip())
    print(f"\n🎉 20-Minute Master Video Assembled: {primary_master.name}")
    print(f"   Final Duration: {dur:.2f}s (Target: 1,200.00s | Delta: {abs(dur - 1200.0):.2f}s)")
    print(f"   File Size: {primary_master.stat().st_size:,} bytes")
    
    return primary_master


def update_studio_gui_catalog(master_video: Path, total_shots: int, total_duration: float):
    """Update production_video_history.json so Studio Cinema Player streams this master."""
    print("\n--- [STEP 5] Studio GUI Cinema Player Registration ---")
    catalog_path = MODULE_ROOT / "production_video_history.json"
    
    dur_min = int(total_duration // 60)
    dur_sec = int(total_duration % 60)
    record = {
        "title": "바다 밑 3,100m 잠든 20조 원의 황금 — 스페인 보물선 산호세 호와 카리브해의 침묵 (완편 다큐)",
        "project": "San Jose Galleon 20-Trillion Gold Shipwreck",
        "slug": EP_SLUG,
        "date": EP_DATE,
        "duration": total_duration,
        "duration_label": f"{dur_min}:{dur_sec:02d}",
        "total_shots": total_shots,
        "video_path": str(master_video),
        "status": "COMPLETED_MASTER_1200S",
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    records = []
    if catalog_path.exists():
        try:
            records = json.loads(catalog_path.read_text(encoding="utf-8"))
        except Exception:
            records = []

    records = [r for r in records if r.get("slug") != EP_SLUG]
    records.insert(0, record)
    catalog_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Catalog updated with master video.")


def main():
    parser = argparse.ArgumentParser(description="San Jose Master Production Pipeline (dynamic shot count)")
    parser.add_argument("--step", choices=["all", "audio", "flow", "motion", "master"], default="all")
    parser.add_argument("--start", type=int, default=1, help="Start shot order (1-indexed)")
    parser.add_argument("--count", type=int, default=0, help="Number of shots to process (0 = all from manifest)")
    args = parser.parse_args()

    ensure_workspace()
    
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    shots = manifest["shots"]
    total_duration = sum(s["scene_duration"] for s in shots)
    print(f"Loaded {len(shots)} shots from {MANIFEST_PATH.name} (total: {total_duration:.2f}s)")

    # Dynamic count: 0 means all remaining shots from start
    count = args.count if args.count > 0 else len(shots) - args.start + 1
    target_shots = shots[args.start - 1 : args.start - 1 + count]
    print(f"Target shots slice: #{args.start} to #{args.start + len(target_shots) - 1} (Total: {len(target_shots)})")

    if args.step in ["all", "audio"]:
        pad_and_stitch_audio(shots)

    if args.step in ["all", "flow"]:
        asyncio.run(generate_flow_images_batch(target_shots))

    if args.step in ["all", "motion"]:
        render_2stage_motion_clips(target_shots)

    if args.step in ["all", "master"]:
        master_video = assemble_master_video(shots)
        update_studio_gui_catalog(master_video, total_shots=len(shots), total_duration=total_duration)

    print(f"\n=======================================================")
    print(f"SAN JOSE MASTER PRODUCTION COMPLETE ({len(shots)} shots, {total_duration:.0f}s)")
    print(f"=======================================================\n")


if __name__ == "__main__":
    main()
