# -*- coding: utf-8 -*-
"""run_human_library_rank2_exact_clone_pipeline.py

Master Pipeline Runner for Human Library Rank 2 1:1 Exact Replication:
- Title: "잊혀진 문명, 세계 최강이 사라진 이유" (YouTube o-x6sIGANPY, 1,440.0초 / 24.00분)
- Video: 837 Saliency Subcuts (2D Webtoon Graphic Novel, ~1.72s/cut, 1920x1080 30.00fps CFR, 43,200 frames, 1,440.000s)
- Audio: Exact-boundary 48kHz Stereo Master (voice-only for current scope, exactly 69,120,000 sample frames)
- Visual Overlays: optional profile; disabled by default for this release scope
- Subtitles: DocuNarrator_Exact 1-Line Semi-Transparent Box ASS with Bright Yellow Keyword Highlighting
- Gate 0~5 Physical Postflight Verification & Release Manifest
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = Path(__file__).resolve().parent
LIB_DIR = SCRIPTS_DIR / "lib"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from lib.canonical_timeline_adapter import build_canonical_timeline
from lib.subcut_montage_engine import plan_subcuts, render_subcut_montage_stream, SubcutPlan
from lib.audio_multitrack_mixer import build_3track_audio_command, mix_multitrack_audio
from lib.branding_hud_overlay import build_branding_overlay_filtergraph
from lib.exact_release_verifier import (
    audit_ass_strict,
    audit_subcut_montage_plan,
    compute_sha256_chain,
    count_wav_sample_frames,
    validate_audio_probe,
    validate_plate_manifest,
    validate_video_probe,
)

# Canonical Paths
REPO_ROOT = SCRIPTS_DIR.parents[2]
EP_DIR = SCRIPTS_DIR.parent / "runs" / "human_library_replica" / "rank2_forgotten_civilization"
METADATA_DIR = EP_DIR / "metadata"
SUBTITLES_DIR = EP_DIR / "subtitles"
AUDIO_DIR = EP_DIR / "audio"
IMAGES_DIR = EP_DIR / "images_2d_master"
VIDEO_DIR = EP_DIR / "video"
BRANDING_DIR = SCRIPTS_DIR.parent / "assets" / "branding"
TOP3_DIR = REPO_ROOT / "scratch" / "human_library_top3"

ORIGINAL_MP4 = TOP3_DIR / "original_rank2.mp4"
CUES_PATH = TOP3_DIR / "rank2_o-x6sIGANPY_cues.json"
TRANSCRIPT_PATH = TOP3_DIR / "rank2_o-x6sIGANPY_full_transcript.txt"
SCRIPT_PATH = EP_DIR / "script" / "master_script_clean.json"

CANONICAL_MANIFEST_PATH = METADATA_DIR / "canonical_timeline_manifest.json"
SUBCUT_PLAN_PATH = METADATA_DIR / "subcut_montage_plan.json"
PLATES_PLAN_PATH = METADATA_DIR / "master_plates_composition_plan.json"
ASS_PATH = SUBTITLES_DIR / "rank2_exact_master_subtitles.ass"

RAW_AUDIO_PATH = AUDIO_DIR / "rank2_exact_master_audio_48k.wav"
RAW_MONTAGE_VIDEO = VIDEO_DIR / "rank2_exact_montage_raw.mp4"
FINAL_MASTER_VIDEO = EP_DIR / "rank2_exact_master_documentary.mp4"
RELEASE_MANIFEST_PATH = METADATA_DIR / "rank2_exact_release_manifest.json"

TARGET_DURATION_SEC = 1440.000
TARGET_FRAMES = 43200
TARGET_FPS = "30/1"
MASTER_AUDIO_SAMPLE_RATE = 48_000
MASTER_AUDIO_SAMPLES = 69_120_000
EXPECTED_PLATES_COUNT = 128
EXPECTED_SUBCUTS_COUNT = 837


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def get_ffprobe_info(media_path: Path) -> Dict[str, Any]:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=codec_type,codec_name,profile,width,height,r_frame_rate,avg_frame_rate,duration,sample_rate,channels,nb_frames,bit_rate",
        "-show_entries", "format=duration,size",
        "-of", "json",
        str(media_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def build_master_audio_command(
    original_mp4: Path,
    output_path: Path,
    *,
    sample_count: int = MASTER_AUDIO_SAMPLES,
) -> list[str]:
    """Build the master audio command with an exact PCM sample boundary."""
    if sample_count <= 0:
        raise ValueError("sample_count must be positive")
    return [
        "ffmpeg", "-y",
        "-i", str(original_mp4),
        "-vn",
        "-af", (
            "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
            "firequalizer=gain_entry='entry(20,5);entry(50,6);entry(80,4);entry(120,0)',"
            "loudnorm=I=-14:LRA=11:TP=-1.5"
        ),
        "-frames:a", str(sample_count),
        "-c:a", "pcm_s16le",
        "-ar", str(MASTER_AUDIO_SAMPLE_RATE),
        "-ac", "2",
        str(output_path),
    ]


def step_1_prepare_audio(target_duration_sec: float = TARGET_DURATION_SEC) -> Path:
    print("\n=======================================================")
    print("🎵 [STEP 1] Preparing exact-boundary 48kHz Stereo Master Audio (Rank 2)")
    print("=======================================================")
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    if RAW_AUDIO_PATH.exists() and RAW_AUDIO_PATH.stat().st_size > 100000000:
        existing_samples = count_wav_sample_frames(RAW_AUDIO_PATH)
        if existing_samples != MASTER_AUDIO_SAMPLES:
            raise RuntimeError(
                f"Existing master audio has stale sample boundary: "
                f"{existing_samples} != {MASTER_AUDIO_SAMPLES}"
            )
        print(f"Master audio already exists: {RAW_AUDIO_PATH} ({RAW_AUDIO_PATH.stat().st_size:,} bytes)")
        return RAW_AUDIO_PATH

    print(f"Extracting and mastering 48kHz stereo audio from {ORIGINAL_MP4}...")
    cmd = build_master_audio_command(ORIGINAL_MP4, RAW_AUDIO_PATH)
    subprocess.run(cmd, check=True)
    actual_samples = count_wav_sample_frames(RAW_AUDIO_PATH)
    if actual_samples > MASTER_AUDIO_SAMPLES:
        import wave
        tmp_wav = RAW_AUDIO_PATH.with_suffix(".clamped.wav")
        with wave.open(str(RAW_AUDIO_PATH), "rb") as r:
            params = r.getparams()
            frames = r.readframes(MASTER_AUDIO_SAMPLES)
        with wave.open(str(tmp_wav), "wb") as w:
            w.setparams(params)
            w.setnframes(MASTER_AUDIO_SAMPLES)
            w.writeframes(frames)
        tmp_wav.replace(RAW_AUDIO_PATH)
        actual_samples = count_wav_sample_frames(RAW_AUDIO_PATH)

    if actual_samples != MASTER_AUDIO_SAMPLES:
        raise RuntimeError(
            f"Exact WAV boundary failed: {actual_samples} != {MASTER_AUDIO_SAMPLES} sample frames"
        )
    print(f"✅ Master audio created: {RAW_AUDIO_PATH} ({RAW_AUDIO_PATH.stat().st_size:,} bytes)")
    return RAW_AUDIO_PATH


def resolve_plate_image(
    plate_id: str,
    parent_shot_id: str,
    plates_dir: Path,
    fallback_images_dir: Path,
    *,
    allow_parent_fallback: bool = False,
) -> Path:
    """Resolve a physical A/B plate; missing assets fail closed by default."""
    plates_dir = Path(plates_dir)
    fallback_images_dir = Path(fallback_images_dir)
    for ext in (".jpg", ".png", ".jpeg"):
        candidate = plates_dir / f"{plate_id}{ext}"
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    if allow_parent_fallback:
        for ext in (".jpg", ".png", ".jpeg"):
            candidate = fallback_images_dir / f"{parent_shot_id}{ext}"
            if candidate.is_file() and candidate.stat().st_size > 0:
                return candidate
    raise FileNotFoundError(
        f"Missing required plate {plate_id}; parent fallback is disabled"
    )


def validate_master_plate_plan(
    plan_path: Path = PLATES_PLAN_PATH,
    *,
    expected_count: int = EXPECTED_PLATES_COUNT,
) -> dict[str, Any]:
    """Validate the physical plate registry before any cached montage reuse."""
    data = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    return validate_plate_manifest(data.get("plates", []), expected_count=expected_count)


def step_2_render_montage(cuts: List[SubcutPlan]) -> Path:
    print("\n=======================================================")
    print(f"🎬 [STEP 2] Rendering {len(cuts)} Saliency Subcuts Montage Video Stream (Rank 2)")
    print("=======================================================")
    plate_check = validate_master_plate_plan()
    if plate_check["status"] != "PASS":
        raise RuntimeError(
            "Master plate validation failed before montage reuse: "
            + "; ".join(plate_check["errors"][:12])
        )
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    if RAW_MONTAGE_VIDEO.exists() and RAW_MONTAGE_VIDEO.stat().st_size > 50000000:
        print(f"Raw montage video already exists: {RAW_MONTAGE_VIDEO} ({RAW_MONTAGE_VIDEO.stat().st_size:,} bytes)")
        return RAW_MONTAGE_VIDEO

    t0 = time.time()
    out = render_subcut_montage_stream(
        cuts=cuts,
        plates_dir=IMAGES_DIR,
        fallback_images_dir=IMAGES_DIR,
        out_video_path=RAW_MONTAGE_VIDEO,
        fps=30,
    )
    t1 = time.time()
    print(f"✅ Raw montage video rendered in {t1-t0:.1f}s: {out} ({out.stat().st_size:,} bytes)")
    return out


def build_cinema_filtergraph(
    ass_subtitles: Path,
    *,
    include_branding: bool = False,
) -> tuple[list[str], str]:
    """Build the subtitle filter with optional, explicitly scoped overlays."""
    ass_escaped = Path(ass_subtitles).as_posix().replace(":", r"\:")
    if not include_branding:
        return [], f"[0:v]ass='{ass_escaped}',fps=30,format=yuv420p[v_final]"

    extra_inputs, branding_filter = build_branding_overlay_filtergraph(
        emblem_path=BRANDING_DIR / "golden_emblem_watermark.png",
        wreath_path=BRANDING_DIR / "laurel_wreath_opening.png",
        hud1_path=BRANDING_DIR / "ancient_spear_obsidian_hud.png",
        hud2_path=BRANDING_DIR / "epas1_dna_hud.png",
        base_video_label="[0:v]",
        out_label="[v_branded]",
    )
    return extra_inputs, f"{branding_filter};[v_branded]ass='{ass_escaped}',fps=30,format=yuv420p[v_final]"


def step_3_cinema_assembly(
    montage_video: Path,
    master_audio: Path,
    ass_subtitles: Path,
    output_mp4: Path,
    target_duration_sec: float = TARGET_DURATION_SEC,
    target_frames: int = TARGET_FRAMES,
    include_branding: bool = False,
) -> Path:
    print("\n=======================================================")
    profile_name = "branding-enabled" if include_branding else "clean-scope"
    print(f"🏛️ [STEP 3] Cinema Assembly ({profile_name} + Subtitle Burn-In + Mux)")
    print("=======================================================")

    extra_inputs, combined_vfilter = build_cinema_filtergraph(
        ass_subtitles=ass_subtitles,
        include_branding=include_branding,
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(montage_video),
        *extra_inputs,
        "-i", str(master_audio),
        "-filter_complex", combined_vfilter,
        "-map", "[v_final]",
        "-map", f"{1 + len(extra_inputs)//2}:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-color_range", "tv",
        "-r", "30",
        "-vsync", "cfr",
        "-video_track_timescale", "30000",
        "-c:a", "aac",
        "-b:a", "320k",
        "-ar", "48000",
        "-frames:v", str(target_frames),
        "-f", "mp4",
        str(output_mp4.with_name(f"{output_mp4.stem}.part.mp4")),
    ]

    print("Executing final multiplex command...")
    t0 = time.time()
    temporary_output = output_mp4.with_name(f"{output_mp4.stem}.part.mp4")
    res = subprocess.run(cmd, capture_output=True, text=True)
    t1 = time.time()
    if res.returncode != 0:
        temporary_output.unlink(missing_ok=True)
        raise RuntimeError(f"FFmpeg assembly failed (code {res.returncode}):\n{res.stderr[-800:]}")

    os.replace(temporary_output, output_mp4)

    print(f"✅ Final Master Documentary rendered in {t1-t0:.1f}s: {output_mp4} ({output_mp4.stat().st_size:,} bytes)")
    return output_mp4


def step_4_verify_postflight(master_mp4: Path) -> Dict[str, Any]:
    print("\n=======================================================")
    print("🔍 [STEP 4] Gate 0~5 Postflight Physical Verification (Rank 2)")
    print("=======================================================")
    info = get_ffprobe_info(master_mp4)

    v_stream = next(s for s in info["streams"] if s["codec_type"] == "video")
    a_stream = next(s for s in info["streams"] if s["codec_type"] == "audio")

    v_dur = float(v_stream.get("duration", info["format"]["duration"]))
    a_dur = float(a_stream.get("duration", info["format"]["duration"]))
    v_frames = int(v_stream.get("nb_frames", 0))
    v_fps = v_stream.get("r_frame_rate", "")
    a_sr = int(a_stream.get("sample_rate", 0))

    delta = abs(v_dur - a_dur)
    print(f"Video Duration: {v_dur:.4f}s ({v_frames} frames @ {v_fps} fps)")
    print(f"Audio Duration: {a_dur:.4f}s ({a_sr} Hz stereo)")
    print(f"AV Parity Delta: {delta:.4f}s (Threshold <= 0.033s)")

    video_check = validate_video_probe(
        v_stream,
        target_frames=TARGET_FRAMES,
        target_fps=TARGET_FPS,
        target_duration_sec=TARGET_DURATION_SEC,
        duration_tolerance_sec=0.033333,
    )
    assert video_check["status"] == "PASS", "; ".join(video_check["errors"])
    assert delta <= 0.033, f"AV Parity Delta {delta}s > 0.033s"
    audio_check = validate_audio_probe(a_stream)
    assert audio_check["status"] == "PASS", "; ".join(audio_check["errors"])

    decode_errors = []
    for selector in ("0:v:0", "0:a:0"):
        result = subprocess.run(
            ["ffmpeg", "-v", "error", "-err_detect", "explode", "-i", str(master_mp4),
             "-map", selector, "-f", "null", "NUL"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            decode_errors.append(f"{selector}: {result.stderr[-500:]}")
    assert not decode_errors, "Decoded stream failure: " + " | ".join(decode_errors)

    ass_check = audit_ass_strict(ASS_PATH, target_duration_sec=v_dur)
    assert ass_check["status"] == "PASS", "; ".join(ass_check["errors"])

    plate_check = validate_master_plate_plan()
    assert plate_check["status"] == "PASS", "; ".join(plate_check["errors"])

    subcut_data = json.loads(SUBCUT_PLAN_PATH.read_text(encoding="utf-8"))
    subcut_check = audit_subcut_montage_plan(subcut_data.get("cuts", []))
    assert subcut_check["status"] == "PASS", "; ".join(subcut_check["errors"])
    assert subcut_check["aba_repeats"] == 0, f"Detected {subcut_check['aba_repeats']} ABA toggle loops"
    assert subcut_check["role_reversals"] == 0, f"Detected {subcut_check['role_reversals']} role reversals"

    wav_sample_frames = count_wav_sample_frames(RAW_AUDIO_PATH)
    assert wav_sample_frames == MASTER_AUDIO_SAMPLES, (
        f"WAV sample boundary {wav_sample_frames} != {MASTER_AUDIO_SAMPLES}"
    )

    print("✅ Gate 0~5 Physical Postflight Verification PASSED!")
    return {
        "status": "PASS",
        "video_duration_sec": v_dur,
        "audio_duration_sec": a_dur,
        "parity_delta_sec": delta,
        "total_frames": v_frames,
        "frame_rate": v_fps,
        "audio_sample_rate": a_sr,
        "audio_codec": a_stream.get("codec_name"),
        "audio_bitrate": a_stream.get("bit_rate"),
        "video_codec": v_stream.get("codec_name"),
        "video_profile": v_stream.get("profile"),
        "wav_sample_frames": wav_sample_frames,
        "decoded_streams": ["video", "audio"],
        "subtitle_metrics": ass_check,
        "plate_metrics": plate_check,
        "subcut_montage_metrics": subcut_check,
    }


def step_5_generate_release_manifest(
    master_mp4: Path,
    postflight_metrics: Dict[str, Any],
) -> Path:
    print("\n=======================================================")
    print("📜 [STEP 5] Generating Atomic Release Manifest (SHA-256 Chain)")
    print("=======================================================")

    artifact_specs = [
        ("source_original_mp4", ORIGINAL_MP4, "source"),
        ("source_cues_json", CUES_PATH, "source"),
        ("canonical_timeline_manifest", CANONICAL_MANIFEST_PATH, "intermediate"),
        ("master_plates_plan", PLATES_PLAN_PATH, "intermediate"),
        ("subcut_montage_plan", SUBCUT_PLAN_PATH, "intermediate"),
        ("master_subtitles_ass", ASS_PATH, "intermediate"),
        ("master_audio_wav", RAW_AUDIO_PATH, "intermediate"),
        ("raw_montage_video", RAW_MONTAGE_VIDEO, "intermediate"),
        ("master_documentary_mp4", master_mp4, "release"),
    ]
    artifacts: dict[str, dict[str, Any]] = {}
    chain_entries: list[dict[str, str]] = []
    for artifact_id, path, kind in artifact_specs:
        path = Path(path)
        if not path.is_file() or path.stat().st_size <= 0:
            raise FileNotFoundError(f"Cannot freeze release; missing artifact: {path}")
        digest = sha256_file(path)
        artifacts[artifact_id] = {
            "kind": kind,
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": digest,
        }
        chain_entries.append({"artifact_id": artifact_id, "sha256": digest})

    manifest = {
        "release_id": "HL-RANK2-EXACT-CLONE-V1",
        "video_id": "o-x6sIGANPY",
        "title": "잊혀진 문명, 세계 최강이 사라진 이유",
        "schema_version": "human_library_exact_release_v2",
        "status": "PROMOTED_MASTER",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_duration_sec": TARGET_DURATION_SEC,
        "target_fps": 30.0,
        "target_audio_sample_rate": MASTER_AUDIO_SAMPLE_RATE,
        "target_audio_sample_frames": MASTER_AUDIO_SAMPLES,
        "total_frames": postflight_metrics["total_frames"],
        "parity_delta_sec": postflight_metrics["parity_delta_sec"],
        "postflight_metrics": postflight_metrics,
        "artifacts": artifacts,
        "sha256_chain": chain_entries,
        "sha256_chain_root": compute_sha256_chain(chain_entries),
        "gate_results": {
            "gate_0_duration": "PASS",
            "gate_1_subtitles": postflight_metrics["subtitle_metrics"]["status"],
            "gate_2_art_style_and_plates": postflight_metrics["plate_metrics"]["status"],
            "gate_3_pacing": postflight_metrics["subcut_montage_metrics"]["status"],
            "gate_4_audio_boundary": "PASS",
            "gate_5_integrity_decode": "PASS",
        },
    }

    temp_path = RELEASE_MANIFEST_PATH.with_suffix(RELEASE_MANIFEST_PATH.suffix + ".part")
    with open(temp_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, RELEASE_MANIFEST_PATH)

    print(f"✅ Release manifest frozen: {RELEASE_MANIFEST_PATH}")
    return RELEASE_MANIFEST_PATH


def run_pipeline(*, include_branding: bool = False) -> Path:
    print("================================================================================")
    print("🚀 HUMAN LIBRARY RANK 2 EXACT CLONE PRODUCTION PIPELINE (1,440.00s / 24.00m)")
    print("================================================================================")

    # 1. Audio
    master_audio = step_1_prepare_audio(TARGET_DURATION_SEC)

    # 2. Subcut Montage Plan
    with open(SUBCUT_PLAN_PATH, "r", encoding="utf-8") as f:
        subcut_data = json.load(f)
    cuts = [SubcutPlan(**c) for c in subcut_data["cuts"]]
    print(f"Loaded {len(cuts)} cuts from {SUBCUT_PLAN_PATH} ({sum(c.frame_count for c in cuts)} frames)")

    # 3. Video Montage Stream
    montage_video = step_2_render_montage(cuts)

    # 4. Cinema Assembly
    master_mp4 = step_3_cinema_assembly(
        montage_video=montage_video,
        master_audio=master_audio,
        ass_subtitles=ASS_PATH,
        output_mp4=FINAL_MASTER_VIDEO,
        target_duration_sec=TARGET_DURATION_SEC,
        target_frames=TARGET_FRAMES,
        include_branding=include_branding,
    )

    # 5. Postflight Verification
    metrics = step_4_verify_postflight(master_mp4)

    # 6. Release Manifest
    step_5_generate_release_manifest(master_mp4, metrics)

    print("\n🎉 Rank 2 Exact Clone Pipeline Complete & Release Manifest Frozen!")
    return master_mp4


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Human Library Rank 2 Exact Clone Pipeline Runner")
    parser.add_argument("--with-branding", action="store_true", help="Enable optional channel branding overlays")
    args = parser.parse_args()

    run_pipeline(include_branding=args.with_branding)


if __name__ == "__main__":
    main()
