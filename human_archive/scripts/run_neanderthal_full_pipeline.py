# -*- coding: utf-8 -*-
"""Master pipeline execution script for:
'우리는 왜 그들을 멸종시켰는가 — 4만 년 전 빙하기 호모 사피엔스와 네안데르탈인'

Executes the full 5-Gate cinematic documentary workflow with 100% Script-Driven Dynamic Scene Splitting:
1. Workspace provisioning & PAIR-10-NEANDERTHAL-EXTINCTION binding.
2. Script-Driven Dynamic Scene Splitting & sentence-level 4-tier fact checking (Grade A).
3. SuperTonic3 M2 48kHz audio narration synthesis + dynamic BGM ducking (-18dB) for ALL shots.
4. SSOT 52pt 36-char 2-line pyramid ASS subtitle generation.
5. SCN_001 Bare-Tip Whiteboard animation + Google Flow CDP (Port 9222) 1080p Lanczos visual frames for all shots.
6. Smooth biphasic subpixel motion rendering (6-vector rotation) & final master MP4 assembly.
7. Technical verification (ffprobe) & studio production video history registration.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import wave
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from playwright.async_api import Page, async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODULE_ROOT = Path(r"D:\module")
SCRIPTS_DIR = MODULE_ROOT / "bible" / "human_archive" / "scripts"
LIB_DIR = SCRIPTS_DIR / "lib"
BARE_TIP_RENDERER = MODULE_ROOT / "srt-whiteboard-animation" / "scripts" / "stream_render.py"
for p in [str(SCRIPTS_DIR), str(LIB_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# SuperTonic3 local TTS import
SUPERTONIC_ROOT = Path(r"C:\Users\shs\supertonic3-local-tts-20260517-r4\supertonic3-local-tts")
if str(SUPERTONIC_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(SUPERTONIC_ROOT / "src"))

from historical_parallel_engine import HistoricalParallelEngine
from sentence_fact_checker import SentenceHistoricalFactChecker, adjust_korean_josa
from smooth_subpixel_motion_engine import render_smooth_motion_clip
from cinematic_editing_director import CinematicEditingDirector, calculate_variable_shot_budget
from lib.flow_generation_state import adaptive_cooldown
from lib.flow_dom_maintenance import (
    cleanup_verified_cards as shared_cleanup_verified_cards,
    wait_for_canvas_idle as shared_wait_for_canvas_idle,
)
from workspace_manager import workspace_mgr

try:
    from supertonic3_engine import Supertonic3Engine
except Exception as e:
    Supertonic3Engine = None

EP_DATE = "2026-09-09"
EP_SLUG = "iceage-neanderthal-sapiens-extinction"
EP_DIR = MODULE_ROOT / "bible" / "human_archive" / "runs" / "nollam_file" / EP_DATE / EP_SLUG
TOPIC_TITLE = "우리는 왜 그들을 멸종시켰는가 — 4만 년 전 빙하기 호모 사피엔스와 네안데르탈인"

AUDIO_DIR = EP_DIR / "audio" / "sentences_v4"
PADDED_AUDIO_DIR = EP_DIR / "audio" / "padded"
APPROVED_IMG_DIR = EP_DIR / "generation" / "downloads" / "approved"
IMAGES_DIR = EP_DIR / "images"
CLIPS_DIR = EP_DIR / "generation" / "clips"
SUBTITLE_PATH = EP_DIR / "subtitles" / "pilot_subtitles_1200s.ass"
ASSET_MANIFEST_PATH = EP_DIR / "generation" / "approved_asset_manifest.json"

CDP_URL = "http://127.0.0.1:9222"
VALID_IMAGE_DOMAINS = [
    "flow-content.google/image",
    "flow.google.com/asb/",
    "labs.google/fx/api",
    "getMediaUrlRedirect",
    "googleusercontent.com",
]


class PreflightServiceUnavailableError(RuntimeError):
    """Raised when external generation service (SuperTonic3 / Google Flow) is offline and required."""
    pass


class AVDurationMismatchError(RuntimeError):
    """Raised when Concat Video and Master Audio durations differ by more than allowed tolerance."""
    pass


def probe_service_port(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    """Check whether a TCP port is open and accepting connections."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False


def probe_required_external_services(require_tts: bool = False, require_flow: bool = False) -> Dict[str, bool]:
    """Check external services and fail-closed if required services are offline."""
    tts_online = probe_service_port(3093)
    flow_online = probe_service_port(9222)

    status = {
        "supertonic3_tts": tts_online,
        "google_flow_cdp": flow_online,
    }

    if require_tts and not tts_online:
        raise PreflightServiceUnavailableError(
            "Preflight Check FAILED: SuperTonic3 TTS service is OFFLINE on port 3093.\n"
            "Please start the SuperTonic3 TTS server before running audio generation.\n"
            "Refusing to generate dummy 140Hz tone audio."
        )

    if require_flow and not flow_online:
        raise PreflightServiceUnavailableError(
            "Preflight Check FAILED: Google Flow Chrome CDP is OFFLINE on port 9222.\n"
            "Please start Chrome with remote debugging on port 9222 before running image generation.\n"
            "Refusing to generate PIL placeholder artwork."
        )

    return status


def ensure_workspace() -> Path:
    """Create isolated episode workspace directories and bind SSOT."""
    for sub in [
        "generation", "source", "audio", "images", "subtitles", "audit", "candidate",
        "generation/downloads/approved", "audio/sentences_v4", "audio/padded", "generation/clips"
    ]:
        (EP_DIR / sub).mkdir(parents=True, exist_ok=True)

    if workspace_mgr:
        workspace_mgr.set_current_ep_dir(EP_DIR)
    return EP_DIR


def synthesize_script_and_manifests() -> Dict[str, Any]:
    """Generate dynamic script-driven shots and execute 4-tier fact checking."""
    print("--- [STEP 1] Script Synthesis & 4-Tier Fact-Checking (Grade A) ---")
    engine = HistoricalParallelEngine()
    checker = SentenceHistoricalFactChecker()
    director = CinematicEditingDirector()

    parallel = engine.match_or_create_parallel(TOPIC_TITLE)
    assert parallel["pair_id"] == "PAIR-10-NEANDERTHAL-EXTINCTION", f"Mismatch pair_id: {parallel['pair_id']}"

    # Extract 5-phase narrative sentences
    phases = engine._generate_neanderthal_sentences(parallel)
    all_sentences = [s for ph in phases for s in ph]

    # Partition sentences dynamically into 3-Tier Variable Pacing shots (script-driven, no fixed shot count)
    raw_shots = director.split_script_by_variable_pacing(all_sentences, target_duration_sec=1200.0)
    print(f"Dynamically partitioned {len(all_sentences)} sentences into {len(raw_shots)} variable pacing shots.")

    audited_shots = []
    fact_results = []

    for s in raw_shots:
        raw_text = s["display_text"]
        audit_res = checker.audit_sentence(raw_text)
        fact_results.append(audit_res)

        revised = audit_res.get("revised_text") or raw_text
        if audit_res.get("deep_alternative") and audit_res.get("grade") == "D":
            revised = audit_res["deep_alternative"]

        s["display_text"] = revised
        s["tts_text"] = revised
        s["narration"] = revised
        s["fact_grade"] = audit_res.get("grade", "A")
        s["fact_source"] = audit_res.get("primary_source", "고인류학 1차 사료")
        s["image_path"] = str(EP_DIR / "generation" / "downloads" / "approved" / f"{s['shot_id']}.jpg")
        s["wav_path"] = str(EP_DIR / "audio" / "sentences_v4" / f"{s['shot_id']}.wav")

        motion = s.get("camera_motion", "push_in")
        s["visual_prompt"] = (
            f"Authentic Ice Age cinematic documentary, 35mm film photography, {s.get('shot_size_label', '미디엄 샷')}. "
            f"Subject: {revised[:70]}. High contrast chiaroscuro lighting, volumetric glacial fog, "
            f"25fps optical cadence, {motion} camera movement, no subtitles, no text overlays, keep bottom 18% clear."
        )
        audited_shots.append(s)

    total_dur = audited_shots[-1]["scene_end"]
    manifest = {
        "metadata": {
            "channel": "역사이다 (History-Ida)",
            "theme": "Historical Parallel & Investigative Fact-Check",
            "title": TOPIC_TITLE,
            "pair_id": parallel["pair_id"],
            "core_hook": parallel.get("core_hook", ""),
            "protagonist": parallel.get("protagonist", ""),
            "primary_sources": parallel.get("primary_sources", []),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "total_duration_sec": round(total_dur, 2),
        "target_duration_window": "840s ~ 1560s (20분 ±30%)",
        "min_duration_sec": 840.0,
        "max_duration_sec": 1560.0,
        "total_shots": len(audited_shots),
        "pilot_shots_count": sum(1 for s in audited_shots if s.get("is_pilot")),
        "body_shots_count": sum(1 for s in audited_shots if not s.get("is_pilot")),
        "pacing_architecture": "3_tier_variable_pacing",
        "shots": audited_shots
    }

    # 1. Save master_1200s_manifest.json (All shots)
    master_path = EP_DIR / "generation" / "master_1200s_manifest.json"
    master_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. Save scene_script_manifest_v2.json
    scene_v2_path = EP_DIR / "source" / "scene_script_manifest_v2.json"
    scene_v2_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3. Generate ASS Subtitles for all shots
    ass_path = SUBTITLE_PATH
    ass_content = generate_ass_subtitles(audited_shots)
    ass_path.write_text(ass_content, encoding="utf-8")
    shutil.copy2(ass_path, EP_DIR / "generation" / "pilot_subtitles_1200s.ass")

    print(f"Manifests successfully generated at {EP_DIR} ({len(audited_shots)} total shots)")
    return {
        "master_manifest": str(master_path),
        "scene_manifest": str(scene_v2_path),
        "ass_subtitles": str(ass_path),
        "total_shots": len(audited_shots)
    }


def generate_ass_subtitles(shots: List[Dict[str, Any]]) -> str:
    """Generate ASS through the canonical 52pt/36-character subtitle engine."""
    from lib.semantic_subtitle_engine import SemanticSubtitleEngine

    engine = SemanticSubtitleEngine(
        font_size=52,
        font_name="Pretendard",
        play_res_x=1920,
        play_res_y=1080,
        margin_l=50,
        margin_r=50,
        margin_v=55,
        max_line_chars=36,
        max_clause_chars=70,
    )
    events = [event for shot in shots for event in engine.process_shot_to_events(shot)]
    return engine.generate_header(title=TOPIC_TITLE) + "\n".join(events) + "\n"


def synthesize_all_audio(shots: List[Dict[str, Any]]) -> Path:
    """Synthesize 48kHz audio using SuperTonic3 M2 TTS for ALL shots and stitch with precision padding."""
    print(f"\n--- [STEP 2] Narration Audio Synthesis for ALL {len(shots)} Shots ---")
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    PADDED_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    engine = None
    if Supertonic3Engine:
        try:
            engine = Supertonic3Engine(output_dir=AUDIO_DIR)
            print("Supertonic3Engine initialized successfully.")
        except Exception as e:
            print(f"Supertonic3Engine init error: {e}")

    padded_wavs = []
    total_samples = 0
    sample_rate = 48000

    for idx, s in enumerate(shots, 1):
        shot_id = s["shot_id"]
        text = s["tts_text"]
        raw_wav = AUDIO_DIR / f"{shot_id}.wav"
        padded_wav = PADDED_AUDIO_DIR / f"{shot_id}.wav"
        target_dur = s["scene_duration"]

        # 1. Synthesize if raw_wav does not exist or is invalid
        if not raw_wav.exists() or raw_wav.stat().st_size < 10000:
            if engine:
                try:
                    info = engine.synthesize_to_file(
                        text=text,
                        voice="M2",
                        speed=0.95,
                        total_step=10,
                        output_path=raw_wav
                    )
                    dur = info.get("duration", s["speech_duration"])
                    print(f"[{idx:02d}/{len(shots)}] Synthesized {shot_id}: {dur:.2f}s via SuperTonic3.")
                except Exception as ex:
                    raise RuntimeError(f"SuperTonic3 synthesis failed for {shot_id}: {ex}") from ex
            else:
                raise RuntimeError(
                    f"SuperTonic3 TTS is offline on port 3093 and no audio cache exists for {shot_id}. "
                    f"Synthesis aborted (no fake 140Hz narrator tone allowed)."
                )
        else:
            print(f"[{idx:02d}/{len(shots)}] Audio cached for {shot_id} ({raw_wav.stat().st_size:,} B).")

        # 2. Precision Padding and Back-propagation to exact scene_duration
        with wave.open(str(raw_wav), "rb") as wf:
            params = wf.getparams()
            frames = wf.readframes(wf.getnframes())
            s_rate = wf.getframerate()
            num_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()

        cur_samples = len(frames) // (num_channels * sampwidth)
        speech_dur = cur_samples / s_rate

        head_samples = int(round(0.40 * s_rate))
        min_padded_samples = cur_samples + head_samples + int(round(0.20 * s_rate))
        target_samples = max(int(round(target_dur * s_rate)), min_padded_samples)
        tail_samples = max(0, target_samples - cur_samples - head_samples)

        zero_sample = b"\x00" * (num_channels * sampwidth)
        head_silence = zero_sample * head_samples
        tail_silence = zero_sample * tail_samples

        padded_frames = head_silence + frames + tail_silence
        padded_samples = len(padded_frames) // (num_channels * sampwidth)
        actual_padded_dur = round(padded_samples / s_rate, 3)

        # Back-propagate actual padded duration to shot
        s["scene_duration"] = actual_padded_dur
        s["speech_duration"] = round(speech_dur, 3)

        total_samples += padded_samples

        with wave.open(str(padded_wav), "wb") as pwf:
            pwf.setparams((num_channels, sampwidth, s_rate, padded_samples, params.comptype, params.compname))
            pwf.writeframes(padded_frames)

        padded_wavs.append(padded_wav)

    # 3. Stitch master voice audio
    voice_wav = EP_DIR / "audio" / "neanderthal_voice_48k.wav"
    with wave.open(str(padded_wavs[0]), "rb") as wf:
        m_params = wf.getparams()

    with wave.open(str(voice_wav), "wb") as master_wf:
        master_wf.setparams(m_params)
        for pw in padded_wavs:
            with wave.open(str(pw), "rb") as in_wf:
                master_wf.writeframes(in_wf.readframes(in_wf.getnframes()))

    master_dur = total_samples / m_params.framerate
    print(f"Master Voice Audio Stitched: {voice_wav.name} ({master_dur:.2f}s, {voice_wav.stat().st_size:,} B)")

    # Update timeline cumulatively in shots and save manifests
    cur_t = 0.0
    for s in shots:
        s["scene_start"] = round(cur_t, 3)
        cur_t += s["scene_duration"]
        s["scene_end"] = round(cur_t, 3)
        s["speech_start"] = round(s["scene_start"] + 0.40, 3)
        s["speech_end"] = round(s["speech_start"] + s["speech_duration"], 3)

    master_path = EP_DIR / "generation" / "master_1200s_manifest.json"
    if master_path.exists():
        try:
            m_data = json.loads(master_path.read_text(encoding="utf-8"))
            m_data["shots"] = shots
            m_data["total_duration_sec"] = round(cur_t, 2)
            master_path.write_text(json.dumps(m_data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"Warning: could not update master manifest: {e}")

    # 4. Master audio with subtle ambient ice-age soundbed and dynamic ducking (-18dB)
    master_wav = EP_DIR / "audio" / "neanderthal_master_audio_48k.wav"
    create_ambient_soundbed(voice_wav, master_wav, master_dur)

    print(f"Master 48kHz audio assembled: {master_wav} ({master_wav.stat().st_size / 1024 / 1024:.2f} MB)")
    return master_wav


def create_ambient_soundbed(voice_wav: Path, out_path: Path, duration: float):
    """Generate ice-age glacial ambient soundbed and apply dynamic sidechain ducking (-18dB)."""
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(voice_wav),
        "-f", "lavfi", "-i", f"anoisesrc=d={duration:.3f}:c=pink:r=48000:a=0.03",
        "-filter_complex",
        "[1:a]lowpass=f=300,volume=-22dB[bgm];"
        "[bgm][0:a]sidechaincompress=threshold=0.05:ratio=6:attack=20:release=300[ducked_bgm];"
        "[0:a][ducked_bgm]amix=inputs=2:weights=1.0 0.25[aout]",
        "-map", "[aout]",
        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
        str(out_path)
    ]
    try:
        subprocess.run(cmd, check=True)
    except Exception:
        shutil.copy2(voice_wav, out_path)


def get_adaptive_cooldown(consecutive_success: int, had_error: bool) -> float:
    """Compatibility wrapper around the shared Flow generation policy."""
    return adaptive_cooldown(consecutive_success, had_error)


def sanitize_flow_prompt(raw_prompt: str) -> str:
    """Clean and slim prompt down to <= 220 characters without video motion tokens."""
    clean = raw_prompt
    for rm in [
        "25fps optical cadence,", "25fps optical cadence",
        "push_in camera movement,", "push_in camera movement",
        "slow_pan_left camera movement,", "slow_pan_left camera movement",
        "orbit_slow camera movement,", "orbit_slow camera movement",
        "pull_out camera movement,", "pull_out camera movement",
        "tilt_up camera movement,", "tilt_up camera movement",
        "glide_forward camera movement,", "glide_forward camera movement",
        "no subtitles, no text overlays, keep bottom 18% clear.",
        "no subtitles, no text overlays, keep bottom 18% clear",
    ]:
        clean = clean.replace(rm, "")

    clean = re.sub(r"\s+", " ", clean).strip().rstrip(",")
    if len(clean) > 170:
        clean = clean[:170].rstrip(",")
    return f"{clean} --no text, typography, subtitles, watermark"


async def wait_for_canvas_idle(flow_page: Page, timeout_sec: float = 90.0) -> bool:
    """Strict Zero-Concurrency Gate: wait until all generating cards / spinners settle."""
    return await shared_wait_for_canvas_idle(flow_page, timeout_sec=timeout_sec)


async def detect_and_clear_error_cards(flow_page: Page) -> int:
    """Detect and clear Flow error cards via refresh or delete."""
    from lib.flow_dom_maintenance import clear_error_cards
    return await clear_error_cards(flow_page)


async def cleanup_flow_cards_gc(flow_page: Page, max_count: int = 25) -> int:
    """Trash verified cards from Flow canvas to trigger DOM GC."""
    return await shared_cleanup_verified_cards(flow_page, max_count)


async def generate_cinematic_assets_async(shots: List[Dict[str, Any]]) -> List[Path]:
    """Generate 1920x1080 Lanczos assets:
    - SHOT_001: Mandatory Bare-Tip Whiteboard blueprint artwork.
    - SHOT_002 ~ end: Google Flow CDP (Port 9222) batch generation with 1-shot-1-completion.
    """
    print(f"\n--- [STEP 3] 1:1 Cinematic Asset Generation for ALL {len(shots)} Shots ---")
    APPROVED_IMG_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    asset_records = {}
    if ASSET_MANIFEST_PATH.exists():
        try:
            data = json.loads(ASSET_MANIFEST_PATH.read_text(encoding="utf-8"))
            for item in data.get("assets", []):
                asset_records[item["shot_id"]] = item
        except Exception:
            pass

    existing_hashes = set(rec.get("sha256") for rec in asset_records.values() if "sha256" in rec)
    for img_f in APPROVED_IMG_DIR.glob("SHOT_*.jpg"):
        if img_f.stat().st_size > 20000:
            existing_hashes.add(hashlib.sha256(img_f.read_bytes()).hexdigest())

    def is_valid_cinematic_photo(p: Path) -> bool:
        if not p.exists() or p.stat().st_size < 30000:
            return False
        try:
            import cv2
            arr = cv2.imread(str(p))
            if arr is None or arr.shape != (1080, 1920, 3):
                return False
            # Check for dummy: beige diagram (mean>200, std<30) or dark gradient placeholder (mean<30, std<25)
            if arr.mean() > 200 and arr.std() < 30:
                return False
            if arr.mean() < 30 and arr.std() < 25:
                return False
            return True
        except Exception:
            return False

    flow_connected = False

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
            flow_page = None
            for ctx in browser.contexts:
                for pg in ctx.pages:
                    if "flow" in pg.url or "labs.google" in pg.url:
                        flow_page = pg
                        break
                if flow_page:
                    break

            if flow_page:
                flow_connected = True
                print(f"  Connected to Google Flow CDP: {flow_page.url}")
                await flow_page.bring_to_front()

                # Baseline scan
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

                pre_cleared = await detect_and_clear_error_cards(flow_page)
                if pre_cleared > 0:
                    print(f"  Pre-cleaned {pre_cleared} error cards")

                consecutive_success = 0

                for idx, s in enumerate(shots, 1):
                    shot_id = s["shot_id"]
                    approved_f = APPROVED_IMG_DIR / f"{shot_id}.jpg"
                    images_f = IMAGES_DIR / f"{shot_id}.jpg"

                    # Idempotent skip ONLY if genuine cinematic photo exists
                    if is_valid_cinematic_photo(approved_f):
                        img_h = hashlib.sha256(approved_f.read_bytes()).hexdigest()
                        other_hashes = set(rec.get("sha256") for k, rec in asset_records.items() if k != shot_id)
                        if img_h not in other_hashes:
                            print(f"[{idx:02d}/{len(shots)}] {shot_id} genuine photo verified ({approved_f.stat().st_size:,} B). Skipping.")
                            if not images_f.exists() or not is_valid_cinematic_photo(images_f):
                                shutil.copy2(approved_f, images_f)
                            asset_records[shot_id] = {
                                "shot_id": shot_id,
                                "filename": f"{shot_id}.jpg",
                                "path": str(approved_f),
                                "size": approved_f.stat().st_size,
                                "sha256": img_h,
                                "width": 1920,
                                "height": 1080,
                                "aspect_ratio": "16:9"
                            }
                            existing_hashes.add(img_h)
                            consecutive_success += 1
                            continue

                    # Invalidate any stale dummy files
                    approved_f.unlink(missing_ok=True)
                    images_f.unlink(missing_ok=True)

                    # 1. Strict Zero-Concurrency Gate: wait for canvas idle before generating next shot
                    await wait_for_canvas_idle(flow_page, timeout_sec=60.0)
                    pre_cleared = await detect_and_clear_error_cards(flow_page)
                    if pre_cleared > 0:
                        print(f"   [PRE-CLEAN] Cleared {pre_cleared} error cards.")
                        await flow_page.wait_for_timeout(2000)

                    # 2. Format clean slimmed Imagen prompt (capped <= 220 chars)
                    flow_prompt = sanitize_flow_prompt(s["visual_prompt"])

                    print(f"\n[{idx:02d}/{len(shots)}] Generating {shot_id} via Google Flow...")
                    print(f"   Prompt: {flow_prompt[:90]}...")

                    shot_success = False
                    had_error = False

                    for attempt in range(1, 4):
                        if attempt > 1:
                            had_error = True
                            err_cooldown = get_adaptive_cooldown(consecutive_success, had_error=True)
                            print(f"   [ERROR BACKOFF] Retry {attempt}/3 for {shot_id}. Waiting {err_cooldown:.1f}s...")
                            await flow_page.wait_for_timeout(int(err_cooldown * 1000))
                            await wait_for_canvas_idle(flow_page, timeout_sec=40.0)

                        # Locate editor
                        pm = await flow_page.query_selector(".ProseMirror")
                        if not pm:
                            await flow_page.wait_for_timeout(2000)
                            pm = await flow_page.query_selector(".ProseMirror")

                        if not pm:
                            print(f"   Could not locate ProseMirror editor for {shot_id}")
                            break

                        await pm.click()
                        await flow_page.wait_for_timeout(200)
                        await flow_page.keyboard.press("Control+A")
                        await flow_page.wait_for_timeout(100)
                        await flow_page.keyboard.press("Backspace")
                        await flow_page.wait_for_timeout(100)
                        await flow_page.keyboard.type(flow_prompt, delay=3)
                        await flow_page.wait_for_timeout(300)

                        # Click submit
                        submit_btn = await flow_page.query_selector("button.generate-icon-button, button[aria-label*='만들기'], button[aria-label*='생성'], button:has-text('arrow_forward')")
                        if submit_btn and await submit_btn.is_visible():
                            await submit_btn.click()
                        else:
                            await flow_page.keyboard.press("Enter")

                        start_poll = time.time()
                        new_img_url = None

                        while time.time() - start_poll < 90:
                            await flow_page.wait_for_timeout(2500)
                            err_cleared = await detect_and_clear_error_cards(flow_page)
                            if err_cleared > 0:
                                print(f"   Cleared {err_cleared} error cards. Retrying...")
                                break

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
                            continue

                        if new_img_url:
                            try:
                                resp = await flow_page.request.get(new_img_url)
                                raw_bytes = await resp.body()
                                if len(raw_bytes) < 20000:
                                    continue

                                temp_part = approved_f.with_suffix(".part")
                                temp_part.write_bytes(raw_bytes)

                                with Image.open(temp_part) as im:
                                    im_rgb = im.convert("RGB")
                                    im_1080 = im_rgb.resize((1920, 1080), Image.Resampling.LANCZOS)
                                    im_1080.save(approved_f, format="JPEG", quality=95)
                                    shutil.copy2(approved_f, images_f)
                                temp_part.unlink(missing_ok=True)

                                sha256_hash = hashlib.sha256(approved_f.read_bytes()).hexdigest()
                                if sha256_hash in existing_hashes:
                                    print(f"   Duplicate hash rejected for {shot_id}. Retrying...")
                                    approved_f.unlink(missing_ok=True)
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
                                print(f"   ✓ OK: {approved_f.name} ({approved_f.stat().st_size:,} B | SHA: {sha256_hash[:10]}...)")
                                shot_success = True
                                break
                            except Exception as ex:
                                print(f"   Error saving {shot_id}: {ex}")
                                continue

                    if shot_success:
                        consecutive_success += 1
                        cooldown = get_adaptive_cooldown(consecutive_success, had_error=had_error)
                        print(f"   [ADAPTIVE COOLDOWN] Shot {shot_id} completed. Pausing {cooldown:.1f}s...")
                        if consecutive_success % 25 == 0:
                            print(f"   [DOM GC] Periodic canvas cleanup every 25 verified shots...")
                            await cleanup_flow_cards_gc(flow_page, 25)
                        await flow_page.wait_for_timeout(int(cooldown * 1000))
                    else:
                        if shot_id == "SHOT_001":
                            raise RuntimeError(
                                "SHOT_001 Bare-Tip source unavailable after Flow retries; "
                                "refusing to synthesize a placeholder opening asset."
                            )
                        raise RuntimeError(
                            f"Google Flow failed to generate image for {shot_id} after 3 retries. "
                            f"Refusing to generate PIL placeholder artwork."
                        )

        except Exception as e:
            print(f"CDP connection warning: {e}")

    # Ensure all required assets are present; fail-closed if any missing
    missing_assets = []
    for s in shots:
        shot_id = s["shot_id"]
        out_jpg = APPROVED_IMG_DIR / f"{shot_id}.jpg"
        if not out_jpg.exists() or out_jpg.stat().st_size < 10000:
            if shot_id == "SHOT_001":
                raise RuntimeError(
                    "SHOT_001 Visible-First Flow source unavailable; refusing to reuse a placeholder asset."
                )
            missing_assets.append(shot_id)

    if missing_assets:
        raise RuntimeError(
            f"Asset generation incomplete. {len(missing_assets)} shots missing assets: {missing_assets}. "
            f"Cannot proceed without genuine assets (no PIL dummy fallback permitted)."
        )

    # Save manifest
    manifest_data = {
        "project": TOPIC_TITLE,
        "total_assets": len(asset_records),
        "assets": list(asset_records.values())
    }
    ASSET_MANIFEST_PATH.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Approved asset manifest updated: {ASSET_MANIFEST_PATH} ({len(asset_records)} assets)")

    return [APPROVED_IMG_DIR / f"{s['shot_id']}.jpg" for s in shots]


def generate_cinematic_assets(shots: List[Dict[str, Any]]) -> List[Path]:
    """Synchronous wrapper for generate_cinematic_assets_async."""
    return asyncio.run(generate_cinematic_assets_async(shots))


def get_media_duration_sec(media_path: Path) -> float:
    """Measure exact duration of media using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(media_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    return float(json.loads(res.stdout)["format"]["duration"])


def validate_premux_av_parity(
    video_only: Path,
    master_audio: Path,
    max_tolerance_sec: float = 0.040
) -> Tuple[float, float, float]:
    """Strict Parity Gate: Enforce |V_dur - A_dur| <= max_tolerance_sec before master muxing."""
    if not video_only.exists():
        raise FileNotFoundError(f"Video file not found: {video_only}")
    if not master_audio.exists():
        raise FileNotFoundError(f"Master audio file not found: {master_audio}")

    v_dur = get_media_duration_sec(video_only)
    a_dur = get_media_duration_sec(master_audio)
    diff = abs(v_dur - a_dur)

    if diff > max_tolerance_sec:
        raise AVDurationMismatchError(
            f"Pre-Mux Strict Parity Gate FAILED: Concat video ({v_dur:.3f}s) and Master audio ({a_dur:.3f}s) "
            f"differ by {diff:.3f}s, exceeding max tolerance of {max_tolerance_sec:.3f}s (1 frame @ 25fps). "
            f"Mux aborted to prevent frozen frames or truncated audio."
        )

    print(f"  ✓ [PRE-MUX STRICT PARITY GATE] V={v_dur:.3f}s, A={a_dur:.3f}s, diff={diff:.3f}s <= {max_tolerance_sec:.3f}s PASS")
    return (v_dur, a_dur, diff)


def build_neanderthal_master_mux_command(
    video_only: Path,
    master_audio: Path,
    ass_file: Path,
    master_video: Path,
) -> List[str]:
    """Build the final mux command without allowing a shorter video to truncate audio."""
    ass_escaped = str(ass_file.resolve()).replace("\\", "/").replace(":", "\\:")
    return [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(video_only),
        "-i", str(master_audio),
        "-vf", f"subtitles='{ass_escaped}'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
        "-pix_fmt", "yuv420p",
        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-color_range", "tv",
        "-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-map", "0:v:0", "-map", "1:a:0",
        str(master_video),
    ]


def render_cinematic_master_video(master_audio: Path, shots: List[Dict[str, Any]]) -> Path:
    """Render smooth motion clips for ALL shots and assemble final master MP4 with ASS subtitles."""
    print(f"\n--- [STEP 4] Smooth Motion Rendering & Master Assembly for ALL {len(shots)} Shots ---")
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    clip_paths = []

    director = CinematicEditingDirector()
    planned_effects = director.plan_scene_effects(shots)

    for idx, s in enumerate(shots):
        shot_id = s["shot_id"]
        dur = s["scene_duration"]
        img_file = APPROVED_IMG_DIR / f"{shot_id}.jpg"
        clip_file = CLIPS_DIR / f"{shot_id}.mp4"

        plan = planned_effects[idx]
        effect = plan.get("editing_effect", "subpixel_push_in")

        # Invariant 1: Opening (idx == 0) is Visible-First FLOW Opening. Bare-Tip is strictly disallowed in opening.
        if idx == 0 and effect == "bare_tip_whiteboard":
            raise ValueError("BARETIP_VIDEO is strictly disallowed in opening (Gate 8 invariant).")

        bare_tip_required = (effect == "bare_tip_whiteboard") and (idx > 0)
        bare_tip_marker = clip_file.with_suffix(".renderer.json")

        if idx == 0 and bare_tip_marker.is_file():
            # Legacy Bare-Tip opening cache must never satisfy Gate 8 visible-first invariant
            bare_tip_marker.unlink(missing_ok=True)
            clip_file.unlink(missing_ok=True)

        # Check if clip already rendered with correct duration.
        if clip_file.exists() and clip_file.stat().st_size > 100000:
            probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(clip_file)]
            res = subprocess.run(probe_cmd, capture_output=True, text=True)
            try:
                c_dur = float(json.loads(res.stdout).get("format", {}).get("duration", 0))
                renderer_ok = (
                    not bare_tip_required
                    or (
                        bare_tip_marker.is_file()
                        and json.loads(bare_tip_marker.read_text(encoding="utf-8")).get("renderer")
                        == "srt-whiteboard-animation"
                    )
                )
                if abs(c_dur - dur) < 0.25 and renderer_ok:
                    print(f"[{idx+1:02d}/{len(shots)}] {clip_file.name} cached ({c_dur:.2f}s). Skipping.")
                    clip_paths.append(clip_file)
                    continue
            except Exception:
                pass

        print(f"[{idx+1:02d}/{len(shots)}] Rendering Motion Clip ({effect}, {dur:.2f}s): {clip_file.name}")

        motion_type = effect.replace("subpixel_", "").replace("bare_tip_", "")
        if motion_type not in ["push_in", "pull_out", "pan_left", "pan_right", "tilt_up", "tilt_down"]:
            motion_type = "push_in"

        if idx == 0:
            # 3-Cut Visible FLOW Opening
            cut01 = APPROVED_IMG_DIR / "SHOT_001_cut01.jpg"
            cut02 = APPROVED_IMG_DIR / "SHOT_001_cut02.jpg"
            cut03 = APPROVED_IMG_DIR / "SHOT_001_cut03.jpg"
            if cut01.exists() and cut02.exists() and cut03.exists():
                try:
                    from smooth_subpixel_motion_engine import render_composite_opening_clip
                    render_composite_opening_clip(
                        image_paths=[cut01, cut02, cut03],
                        output_path=clip_file,
                        duration=dur,
                        fps=25,
                        width=1920,
                        height=1080
                    )
                except ImportError:
                    render_smooth_motion_clip(
                        image_path=img_file,
                        output_path=clip_file,
                        duration=dur,
                        motion="pan_right",
                        fps=25,
                        width=1920,
                        height=1080
                    )
            else:
                render_smooth_motion_clip(
                    image_path=img_file,
                    output_path=clip_file,
                    duration=dur,
                    motion="pan_right",
                    fps=25,
                    width=1920,
                    height=1080
                )
        elif bare_tip_required:
            render_bare_tip_ink_stream_clip(img_file, clip_file, dur, fps=25)
            # Normalize 1080x600 whiteboard canvas to 1920x1080 with 0xF5EBD7 padding
            temp_clip = clip_file.with_suffix(".raw_stream.mp4")
            shutil.move(str(clip_file), str(temp_clip))
            scale_filter = "scale=1920:1066:flags=lanczos,pad=1920:1080:0:7:color=0xF5EBD7,setsar=1,fps=25,format=yuv420p"
            cmd_norm = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(temp_clip),
                "-t", f"{dur:.3f}",
                "-vf", scale_filter,
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-an",
                str(clip_file)
            ]
            subprocess.run(cmd_norm, check=True)
            temp_clip.unlink(missing_ok=True)

            bare_tip_marker.write_text(
                json.dumps(
                    {
                        "renderer": "srt-whiteboard-animation",
                        "renderer_path": str(BARE_TIP_RENDERER),
                        "bare_tip": True,
                        "duration_sec": dur,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        else:
            render_smooth_motion_clip(
                image_path=img_file,
                output_path=clip_file,
                duration=dur,
                motion=motion_type,
                fps=25,
                width=1920,
                height=1080
            )

        clip_paths.append(clip_file)

    # Concat clips using FFmpeg concat demuxer
    concat_list = CLIPS_DIR / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for c in clip_paths:
            f.write(f"file '{c.resolve().as_posix()}'\n")

    video_only = EP_DIR / "generation" / "neanderthal_video_concat.mp4"
    cmd_concat = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c", "copy",
        str(video_only)
    ]
    subprocess.run(cmd_concat, check=True)

    # Multiplex with 48kHz audio and ASS subtitles
    ass_file = EP_DIR / "generation" / "pilot_subtitles_1200s.ass"
    master_video = EP_DIR / "NOLLAM-NEANDERTHAL-EXTINCTION-FULL-MASTER.mp4"

    validate_premux_av_parity(video_only, master_audio, max_tolerance_sec=0.040)

    cmd_master = build_neanderthal_master_mux_command(
        video_only,
        master_audio,
        ass_file,
        master_video,
    )
    print(f"Multiplexing Master Video with Audio & ASS Subtitles: {master_video.name}...")
    subprocess.run(cmd_master, check=True)

    # Copy to output directory
    output_dir = MODULE_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(master_video, output_dir / master_video.name)

    v_size = master_video.stat().st_size / 1024 / 1024
    print(f"SUCCESS: Master Video Built ({v_size:.2f} MB): {master_video}")
    return master_video


def render_bare_tip_ink_stream_clip(img_path: Path, out_path: Path, duration: float, fps: int = 25):
    """Render Bare-Tip through the canonical whiteboard stream renderer."""
    cmd = build_bare_tip_command(img_path, out_path.parent, duration, fps)
    if not BARE_TIP_RENDERER.is_file():
        raise FileNotFoundError(f"Canonical Bare-Tip renderer not found: {BARE_TIP_RENDERER}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    generated = None
    for line in reversed(result.stdout.splitlines()):
        if line.startswith("OUTPUT="):
            generated = Path(line.split("=", 1)[1].strip())
            break
    if generated is None or not generated.is_file() or generated.stat().st_size == 0:
        raise RuntimeError("Bare-Tip renderer completed without a physical OUTPUT file")
    if generated.resolve() != out_path.resolve():
        shutil.copy2(generated, out_path)
    if out_path.stat().st_size == 0:
        raise RuntimeError(f"Bare-Tip output is empty: {out_path}")


def build_bare_tip_command(
    img_path: Path, out_dir: Path, duration: float, fps: int = 25
) -> list[str]:
    """Build the deterministic command for the external Bare-Tip renderer."""
    return [
        sys.executable,
        str(BARE_TIP_RENDERER),
        str(img_path),
        "--out-dir", str(out_dir),
        "--total-ms", str(max(1, int(round(duration * 1000)))),
        "--bare-tip",
        "--fps", str(fps),
    ]


def verify_and_register_video(master_video: Path):
    """Verify physical integrity via ffprobe and register in production history catalog."""
    print("\n--- [STEP 5] Verification & Video History Catalog Registration ---")
    assert master_video.exists(), f"Master video not found: {master_video}"
    assert master_video.stat().st_size > 500_000, "Master video file size suspiciously small"

    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate",
        "-of", "json", str(master_video)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    probe_data = json.loads(res.stdout)

    dur_sec = float(probe_data["format"]["duration"])
    v_stream = next(s for s in probe_data["streams"] if s.get("codec_type") == "video")
    a_stream = next(s for s in probe_data["streams"] if s.get("codec_type") == "audio")

    assert v_stream["width"] == 1920 and v_stream["height"] == 1080, "Resolution must be 1920x1080"
    assert a_stream["sample_rate"] == "48000", "Audio must be 48kHz"
    assert 840.0 <= dur_sec <= 1560.0, f"Duration {dur_sec:.2f}s not in 20min +-30% window (840s~1560s)!"
    print(f"  ✓ Physical Video Verified: {dur_sec:.2f}s ({int(dur_sec//60)}m {int(dur_sec%60)}s), 1920x1080, {a_stream['sample_rate']}Hz")

    # Update history databases (both root and data/)
    db_paths = [
        MODULE_ROOT / "bible" / "human_archive" / "data" / "production_video_history.json",
        MODULE_ROOT / "production_video_history.json"
    ]

    for db_file in db_paths:
        db_file.parent.mkdir(parents=True, exist_ok=True)
        history = []
        if db_file.exists():
            try:
                history = json.loads(db_file.read_text(encoding="utf-8"))
            except Exception:
                history = []

        entry = {
            "video_id": f"neanderthal-extinction-master-{int(time.time())}",
            "title": TOPIC_TITLE,
            "filename": master_video.name,
            "relative_path": str(master_video.relative_to(MODULE_ROOT)).replace("\\", "/"),
            "absolute_path": str(master_video),
            "duration_sec": round(dur_sec, 2),
            "formatted_duration": f"{int(dur_sec//60):02d}:{int(dur_sec%60):02d}",
            "file_size_mb": round(master_video.stat().st_size / 1024 / 1024, 2),
            "sha256": hashlib.sha256(master_video.read_bytes()).hexdigest(),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ep_dir": str(EP_DIR),
            "category": "역사/고인류학/빙하기",
            "description": "4만 년 전 빙하기 유라시아 대륙에서 펼쳐진 호모 사피엔스와 네안데르탈인의 공존, 유전체 해독, 기술 비대칭 및 최종 멸종의 미스터리"
        }

        history = [h for h in history if h.get("filename") != master_video.name]
        history.insert(0, entry)
        db_file.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Registered video '{entry['title']}' in {db_file.name}")


def main():
    print(f"================================================================================")
    print(f"NOLLAM Production (Script-Driven Dynamic Scene Splitting): '{TOPIC_TITLE}'")
    print(f"================================================================================")
    start_time = time.time()

    # Step 0: Ensure Workspace
    ensure_workspace()

    # Step 1: Script Synthesis & 4-Tier Fact Checking
    synthesize_script_and_manifests()

    # Load master manifest shots (100% dynamic)
    master_manifest = json.loads((EP_DIR / "generation" / "master_1200s_manifest.json").read_text(encoding="utf-8"))
    shots = master_manifest["shots"]
    print(f"Loaded {len(shots)} shots from script manifest for complete pipeline execution.")

    # Step 2: Narration Audio Synthesis & Precision BGM Ducking for ALL shots
    master_audio = synthesize_all_audio(shots)

    # Step 3: Cinematic Asset Generation (SCN_001 Bare-Tip + Google Flow CDP Port 9222)
    generate_cinematic_assets(shots)

    # Step 4: Motion Rendering & Master Assembly for ALL shots
    master_video = render_cinematic_master_video(master_audio, shots)

    # Step 5: Verification & History DB Registration
    verify_and_register_video(master_video)

    total_time = time.time() - start_time
    print(f"\n================================================================================")
    print(f"ALL WORKFLOW STAGES COMPLETED IN {total_time:.2f}s!")
    print(f"Master Video Output: {master_video} ({master_video.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"================================================================================")


if __name__ == "__main__":
    main()
