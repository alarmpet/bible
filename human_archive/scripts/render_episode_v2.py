# -*- coding: utf-8 -*-
"""Render documentary video build atomically using immutable hash chains into candidate/."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.provenance import compute_file_sha256
from lib.build_manifest import verify_upstream_hash_freshness


def build_mux_command(
    visual_file: Path,
    master_audio_file: Path,
    subtitles_file: Path,
    candidate_part: Path,
    *,
    bgm_file: Path | None = None,
) -> list[str]:
    """Build the final mux command, optionally adding -18dB sidechain BGM."""
    esc_ass = str(subtitles_file).replace("\\", "/").replace(":", "\\:")
    vf_sub = f"subtitles='{esc_ass}'"
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(visual_file),
        "-i", str(master_audio_file),
    ]
    if bgm_file is not None:
        cmd.extend(["-stream_loop", "-1", "-i", str(bgm_file)])
        filter_complex = (
            f"[0:v]{vf_sub}[vout];"
            "[1:a]aformat=sample_rates=48000:channel_layouts=stereo[voice];"
            "[2:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=-18dB[bed];"
            "[bed][voice]sidechaincompress=threshold=0.05:ratio=6:attack=20:release=300[ducked];"
            "[voice][ducked]amix=inputs=2:weights=1 0.25:duration=first:dropout_transition=0[aout]"
        )
        cmd.extend(["-filter_complex", filter_complex, "-map", "[vout]", "-map", "[aout]"])
    else:
        cmd.extend(["-vf", vf_sub, "-map", "0:v:0", "-map", "1:a:0"])
    cmd.extend([
        "-c:v", "libx264",
        "-profile:v", "high",
        "-level", "4.1",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-color_range", "tv",
        "-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ac", "2",
        "-ar", "48000",
        "-shortest",
        "-movflags", "+faststart",
        "-f", "mp4",
        str(candidate_part),
    ])
    return cmd

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def render_build(build_dir: Path, output_file: Path | None = None) -> Path:
    build_dir = Path(build_dir).resolve()
    ok, errors = verify_upstream_hash_freshness(build_dir)
    if not ok:
        raise SystemExit(f"Build freshness check failed: {errors}")

    contract_file = build_dir / "image_request_manifest.json"
    if not contract_file.exists():
        contract_file = build_dir.parent / "source" / "shot_contract_v4.json"
    if not contract_file.exists():
        contract_file = build_dir.parent / "source" / "shot_contract.json"
    asset_manifest_file = build_dir / "asset_manifest.json"
    # nollam_file_v1 builds write sentence_audio_manifest.json (real
    # per-sentence TTS timing); older ep01/ep02 doodle_seonbi_v1 builds write
    # scene_audio_manifest.json (per-shot). 2026-09-16 finding: this
    # unconditionally pointed at the legacy filename, so hashing it for
    # build_manifest.json's provenance record crashed with FileNotFoundError
    # on an otherwise fully-rendered nollam_file_v1 build.
    audio_manifest_file = build_dir / "sentence_audio_manifest.json"
    if not audio_manifest_file.exists():
        audio_manifest_file = build_dir / "scene_audio_manifest.json"
    subtitles_file = build_dir / "subtitles.ass"
    master_audio_file = build_dir / "master_audio_48k.wav"
    bgm_file = build_dir / "bgm.wav"
    if not bgm_file.is_file():
        bgm_file = None
    motion_dir = build_dir / "motion_clips"

    work_dir = build_dir / "work"
    candidate_dir = build_dir / "candidate"
    work_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir.mkdir(parents=True, exist_ok=True)

    # scene_audio_manifest.json (legacy, per-shot) has a "shots" key directly
    # usable here; sentence_audio_manifest.json (nollam_file_v1, per-sentence)
    # does not -- shot_id/motion-clip lookup below needs shot-level rows, so
    # a sentence-shaped audio manifest falls through to asset_manifest.json
    # (which always has shot-level rows) instead of yielding an empty list.
    audio_data = json.loads(audio_manifest_file.read_text(encoding="utf-8")) if audio_manifest_file.exists() else {}
    shots = audio_data.get("shots", [])
    if not shots and asset_manifest_file.exists():
        am_data = json.loads(asset_manifest_file.read_text(encoding="utf-8"))
        shots = am_data.get("assets", [])
    if not shots:
        contract_data = json.loads(contract_file.read_text(encoding="utf-8"))
        shots = contract_data.get("shots", [])

    if "ep02" in build_dir.parent.name or "ep02" in build_dir.name:
        ep_id = "HA002"
    elif "ep03" in build_dir.parent.name:
        ep_id = "HA003"
    else:
        ep_id = "HA001"

    # 1. Assemble motion clips. Prefer the v3 lossless (.mkv/FFV1) clips
    # (scripts/lib/motion_engine_v3.py) over legacy (.mp4/H.264) ones -- concatenating
    # with `-c:v copy` only re-encodes zero times if the segments are already lossless.
    # A build mixing the two formats is refused rather than silently concatenated,
    # since stream-copy concat across different codecs produces a broken or
    # unpredictable result.
    concat_list_file = work_dir / "motion_concat.txt"
    motion_files = []
    for s in shots:
        sid = s["shot_id"]
        mkv_path = motion_dir / f"{sid}_motion.mkv"
        mp4_path = motion_dir / f"{sid}_motion.mp4"
        if mkv_path.exists():
            motion_files.append(mkv_path)
        elif mp4_path.exists():
            motion_files.append(mp4_path)
        else:
            raise SystemExit(f"Missing motion clip: {mkv_path} (or legacy {mp4_path})")

    formats = {p.suffix for p in motion_files}
    if len(formats) > 1:
        raise SystemExit(
            f"Mixed motion clip formats in {motion_dir}: {sorted(formats)}. Stream-copy "
            "concat cannot mix FFV1 (.mkv, motion_engine_v3) and H.264 (.mp4, legacy) "
            "segments -- re-render the whole episode's motion clips with one engine."
        )
    lossless = ".mkv" in formats

    concat_list_file.write_text("\n".join(f"file '{p.as_posix()}'" for p in motion_files), encoding="utf-8")

    visual_assembled = work_dir / ("visual_assembled.mkv" if lossless else "visual_assembled.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_list_file),
        "-c:v", "copy",
        str(visual_assembled)
    ], check=True)

    # 2. Burn in subtitles and mux master audio into candidate .part with universal player compatibility
    if not output_file:
        output_file = candidate_dir / f"{ep_id}-{build_dir.name}.mp4"

    candidate_part = work_dir / f"{output_file.name}.part"

    cmd = build_mux_command(
        visual_assembled,
        master_audio_file,
        subtitles_file,
        candidate_part,
        bgm_file=bgm_file,
    )
    subprocess.run(cmd, check=True)

    # Atomic rename from .part to candidate
    if output_file.exists():
        output_file.unlink()
    os.replace(candidate_part, output_file)

    file_sha = compute_file_sha256(output_file)

    build_manifest = {
        "schema_version": 1,
        "build_id": build_dir.name,
        "rendered_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_file": output_file.name,
        "candidate_sha256": file_sha,
        "candidate_video_sha256": file_sha,
        "upstream_artifacts": {
            "shot_contract_sha256": compute_file_sha256(contract_file),
            "asset_manifest_sha256": compute_file_sha256(asset_manifest_file),
            "audio_manifest_sha256": compute_file_sha256(audio_manifest_file),
            "subtitles_sha256": compute_file_sha256(subtitles_file),
            "master_audio_sha256": compute_file_sha256(master_audio_file),
        },
    }

    manifest_output = build_dir / "build_manifest.json"
    manifest_output.write_text(json.dumps(build_manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"✅ CANDIDATE RENDER COMPLETE: {output_file}")
    print(f"   Candidate SHA-256: {file_sha}")
    print(f"   Build Manifest: {manifest_output}")
    print("=" * 60 + "\n")

    return output_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    render_build(args.build, output_file=args.output)


if __name__ == "__main__":
    main()
