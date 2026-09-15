# -*- coding: utf-8 -*-
"""Validate intro video clips (SHOT_001 to SHOT_008) against broadcast quality gates:
1080p, 25fps, 1:1 SAR, exact frame budget, zero audio tracks, zero decode errors."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
MOTION_CLIPS_DIR = EP_DIR / "candidate" / "motion_clips"
REPORT_OUTPUT = EP_DIR / "candidate" / "intro_video_qa_report.json"

EXPECTED_INTRO_SPECS: Dict[str, Dict[str, Any]] = {
    "SHOT_001": {"frames": 86, "duration_sec": 3.440},
    "SHOT_002": {"frames": 113, "duration_sec": 4.520},
    "SHOT_003": {"frames": 94, "duration_sec": 3.760},
    "SHOT_004": {"frames": 130, "duration_sec": 5.200},
    "SHOT_005": {"frames": 139, "duration_sec": 5.560},
    "SHOT_006": {"frames": 135, "duration_sec": 5.400},
    "SHOT_007": {"frames": 135, "duration_sec": 5.400},
    "SHOT_008": {"frames": 132, "duration_sec": 5.280},
}


def probe_clip(clip_path: Path) -> Dict[str, Any]:
    """Inspect clip streams and formats via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size,format_name",
        "-show_entries", "stream=index,codec_type,codec_name,width,height,r_frame_rate,nb_frames,sample_aspect_ratio,display_aspect_ratio,pix_fmt",
        "-of", "json",
        str(clip_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def test_decode_integrity(clip_path: Path) -> Tuple[bool, str]:
    """Test full decode pass to verify zero corruption or packet errors."""
    cmd = [
        "ffmpeg", "-v", "error",
        "-i", str(clip_path),
        "-f", "null", "-",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and not res.stderr.strip():
        return True, "Clean decode (0 errors)"
    return False, res.stderr.strip() or f"Decode exited with code {res.returncode}"


def validate_all_intro_clips(clips_dir: Path = MOTION_CLIPS_DIR) -> Dict[str, Any]:
    """Run full technical QA gate across all 8 intro clips."""
    print("=" * 70)
    print("🔍 Intro Video Technical QA Gate (SHOT_001 ~ SHOT_008)")
    print(f"Inspecting directory: {clips_dir}")
    print("=" * 70)

    report: Dict[str, Any] = {
        "status": "PASS",
        "total_intro_frames": 0,
        "total_intro_duration_sec": 0.0,
        "expected_total_frames": sum(s["frames"] for s in EXPECTED_INTRO_SPECS.values()),
        "expected_total_duration_sec": sum(s["duration_sec"] for s in EXPECTED_INTRO_SPECS.values()),
        "shots": {},
        "violations": [],
    }

    for shot_id, spec in EXPECTED_INTRO_SPECS.items():
        clip_path = clips_dir / f"{shot_id}_motion.mp4"
        shot_res: Dict[str, Any] = {
            "shot_id": shot_id,
            "path": str(clip_path),
            "exists": clip_path.exists(),
            "valid": True,
            "errors": [],
        }

        if not clip_path.exists():
            shot_res["valid"] = False
            shot_res["errors"].append("File not found on disk")
            report["violations"].append(f"[{shot_id}] Missing clip file: {clip_path.name}")
            report["shots"][shot_id] = shot_res
            continue

        # ffprobe inspection
        try:
            probe_data = probe_clip(clip_path)
            fmt = probe_data.get("format", {})
            streams = probe_data.get("streams", [])

            video_streams = [s for s in streams if s.get("codec_type") == "video"]
            audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

            if not video_streams:
                shot_res["valid"] = False
                shot_res["errors"].append("No video stream found")
            else:
                v = video_streams[0]
                w = v.get("width")
                h = v.get("height")
                fps = v.get("r_frame_rate")
                sar = v.get("sample_aspect_ratio", "1:1")
                nb_frames = int(v.get("nb_frames") or 0)
                dur = float(fmt.get("duration", 0.0))
                pix_fmt = v.get("pix_fmt")

                shot_res["width"] = w
                shot_res["height"] = h
                shot_res["fps"] = fps
                shot_res["sar"] = sar
                shot_res["nb_frames"] = nb_frames
                shot_res["duration"] = dur
                shot_res["pix_fmt"] = pix_fmt

                report["total_intro_frames"] += nb_frames
                report["total_intro_duration_sec"] += dur

                # Assertions
                if (w, h) != (1920, 1080):
                    shot_res["valid"] = False
                    shot_res["errors"].append(f"Resolution mismatch: got {w}x{h}, expected 1920x1080")

                if fps != "25/1":
                    shot_res["valid"] = False
                    shot_res["errors"].append(f"FPS mismatch: got {fps}, expected 25/1")

                if sar not in ("1:1", "0:1", None):
                    shot_res["valid"] = False
                    shot_res["errors"].append(f"SAR mismatch: got {sar}, expected 1:1")

                if nb_frames != spec["frames"]:
                    shot_res["valid"] = False
                    shot_res["errors"].append(f"Frame count mismatch: got {nb_frames}, expected {spec['frames']}")

                if abs(dur - spec["duration_sec"]) > 0.05:
                    shot_res["valid"] = False
                    shot_res["errors"].append(f"Duration mismatch: got {dur:.3f}s, expected {spec['duration_sec']:.3f}s")

            # Check audio stripping
            if audio_streams:
                shot_res["valid"] = False
                shot_res["errors"].append(f"Forbidden audio stream detected: {len(audio_streams)} audio streams present")

            # Check decode integrity
            clean_decode, decode_msg = test_decode_integrity(clip_path)
            shot_res["decode_clean"] = clean_decode
            if not clean_decode:
                shot_res["valid"] = False
                shot_res["errors"].append(f"Corrupt stream / decode error: {decode_msg}")

        except Exception as e:
            shot_res["valid"] = False
            shot_res["errors"].append(f"Probe exception: {str(e)}")

        if not shot_res["valid"]:
            report["status"] = "FAIL"
            for err in shot_res["errors"]:
                report["violations"].append(f"[{shot_id}] {err}")
            print(f"❌ [{shot_id}] FAILED: {', '.join(shot_res['errors'])}")
        else:
            print(f"✅ [{shot_id}] PASS: 1920x1080 @ 25fps, {shot_res['nb_frames']} frames ({shot_res['duration']:.3f}s), clean decode")

        report["shots"][shot_id] = shot_res

    # Check cumulative frame totals
    if report["total_intro_frames"] != report["expected_total_frames"]:
        report["status"] = "FAIL"
        report["violations"].append(
            f"Total intro frame mismatch: got {report['total_intro_frames']}, expected {report['expected_total_frames']}"
        )

    print("\n" + "=" * 70)
    print(f"Total Intro Frames:   {report['total_intro_frames']} / {report['expected_total_frames']}")
    print(f"Total Intro Duration: {report['total_intro_duration_sec']:.3f}s / {report['expected_total_duration_sec']:.3f}s")
    print(f"Overall QA Status:    {report['status']}")
    print("=" * 70)

    REPORT_OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Detailed QA report written to: {REPORT_OUTPUT}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate intro video clips technical quality gates")
    parser.add_argument("--clips-dir", type=Path, default=MOTION_CLIPS_DIR, help="Path to motion clips directory")
    args = parser.parse_args()

    qa_report = validate_all_intro_clips(args.clips_dir)
    if qa_report["status"] != "PASS":
        sys.exit(1)
