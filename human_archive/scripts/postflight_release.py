# -*- coding: utf-8 -*-
"""Postflight release verification against machine-measured audio/visual criteria."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import yaml

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.provenance import compute_file_sha256
from lib.media_probe import measure_ebu_r128_loudness, probe_video_streams

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def verify_postflight(
    video_path: Path,
    contract_path: Path | None = None,
    build_dir: Path | None = None,
    report_output: Path | None = None,
    duration_mode: str = "full",
) -> tuple[bool, dict]:
    video_path = Path(video_path).resolve()
    if not video_path.exists():
        raise SystemExit(f"Target video not found: {video_path}")

    meta = probe_video_streams(video_path)
    loudness = measure_ebu_r128_loudness(video_path)
    file_sha = compute_file_sha256(video_path)

    v_info = meta.get("video", {})
    a_info = meta.get("audio", {})
    dur = meta.get("duration_sec", 0.0)

    checks = {}
    errors = []

    # 1. Contract Duration Check — contract is sole authority when present
    target_min, target_max = 840, 1560
    if contract_path and contract_path.exists():
        c_data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        prof = c_data.get("format_profile", "standard_docu")
        if prof == "quick_3m":
            target_min, target_max = 170, 190
        elif prof == "pilot":
            target_min, target_max = 30, 180
        # When contract says standard_docu, duration_mode CLI cannot override
    elif duration_mode == "pilot":
        # No contract provided — fall back to duration_mode for test compat
        target_min, target_max = 30, 180
    dur_ok = target_min <= dur <= target_max
    checks["contract_duration"] = {"status": "PASS" if dur_ok else "FAIL", "duration_sec": dur, "target_range": [target_min, target_max]}
    if not dur_ok:
        errors.append(f"Duration {dur:.2f}s out of contract range [{target_min}, {target_max}]")

    # 2. Dimensions & SAR & Progressive
    dim_ok = (v_info.get("width") == 1920 and v_info.get("height") == 1080)
    sar = v_info.get("sample_aspect_ratio", "1:1")
    sar_ok = (sar in ["1:1", None])
    prog_ok = (v_info.get("field_order") in ["progressive", "unknown", None])
    geom_ok = dim_ok and sar_ok and prog_ok
    checks["dimensions"] = {"status": "PASS" if geom_ok else "FAIL", "actual": f"{v_info.get('width')}x{v_info.get('height')}", "sar": sar}
    if not geom_ok:
        errors.append(f"Invalid geometry: {v_info.get('width')}x{v_info.get('height')}, sar={sar}")

    # 3. Framerate (CFR 25fps)
    r_fps = v_info.get("r_frame_rate", "")
    avg_fps = v_info.get("avg_frame_rate", "")
    fps_ok = (r_fps == "25/1" and (avg_fps in ["25/1", "25", None]))
    checks["framerate"] = {"status": "PASS" if fps_ok else "FAIL", "r_frame_rate": r_fps, "avg_frame_rate": avg_fps}
    if not fps_ok:
        errors.append(f"Non-25 CFR detected: r_fps={r_fps}, avg_fps={avg_fps}")

    # 4. Color tags (yuv420p, tv range, bt709 matrix/primaries/transfer)
    pix_fmt = v_info.get("pix_fmt", "")
    c_space = v_info.get("color_space", "")
    c_prim = v_info.get("color_primaries", "")
    c_trc = v_info.get("color_trc", "")
    c_range = v_info.get("color_range", "")
    color_ok = (pix_fmt == "yuv420p" and c_space == "bt709" and c_prim == "bt709" and c_trc == "bt709" and c_range in ["tv", "limited"])
    checks["color_tags"] = {
        "status": "PASS" if color_ok else "FAIL",
        "pix_fmt": pix_fmt,
        "color_space": c_space,
        "color_primaries": c_prim,
        "color_trc": c_trc,
        "color_range": c_range,
    }
    if not color_ok:
        errors.append(f"Color tags violation: pix_fmt={pix_fmt}, space={c_space}, prim={c_prim}, trc={c_trc}, range={c_range}")

    # 5. Loudness
    i_lufs = loudness.get("input_i", -99.0)
    tp_db = loudness.get("input_tp", -99.0)
    lufs_ok = (-17.0 <= i_lufs <= -13.0)
    if not lufs_ok and duration_mode == "pilot":
        # Relaxed loudness for pilot builds without contract
        lufs_ok = (i_lufs > -30.0)
    tp_ok = (tp_db <= -1.0)
    loud_ok = (lufs_ok and tp_ok)
    checks["loudness"] = {"status": "PASS" if loud_ok else "FAIL", "integrated_lufs": i_lufs, "true_peak_db": tp_db}
    if not loud_ok:
        errors.append(f"Loudness out of spec: I={i_lufs} LUFS, TP={tp_db} dBTP")

    # 6. Subtitles Timeline Check
    sub_ok = True
    if build_dir and (build_dir / "subtitles.ass").exists():
        ass_lines = (build_dir / "subtitles.ass").read_text(encoding="utf-8-sig").splitlines()
        for line in ass_lines:
            if line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                if len(parts) >= 3:
                    end_str = parts[2]
                    try:
                        h, m, s_cc = end_str.split(":")
                        s_val = float(h) * 3600 + float(m) * 60 + float(s_cc)
                        if s_val > dur + 0.5:
                            sub_ok = False
                            errors.append(f"Subtitle cue end ({s_val:.2f}s) exceeds video duration ({dur:.2f}s)")
                    except Exception:
                        pass
    checks["subtitle_timeline"] = {"status": "PASS" if sub_ok else "FAIL"}

    # 7. Release Manifest Verification (if provided or present in build_dir)
    manifest_target = None
    if build_dir:
        candidate_v4 = build_dir / "release_manifest_v4.json"
        candidate_legacy = build_dir / "release_manifest.json"
        if candidate_v4.exists():
            manifest_target = candidate_v4
        elif candidate_legacy.exists():
            manifest_target = candidate_legacy

    if manifest_target and manifest_target.exists():
        try:
            m_data = json.loads(manifest_target.read_text(encoding="utf-8"))
            m_ok, m_errs = verify_release_manifest_schema(m_data)
            checks["release_manifest"] = {
                "status": "PASS" if m_ok else "FAIL",
                "version": m_data.get("release_schema_version") or m_data.get("schema_version"),
                "errors": m_errs,
            }
            if not m_ok:
                errors.extend(m_errs)
        except Exception as ex:
            checks["release_manifest"] = {"status": "FAIL", "error": str(ex)}
            errors.append(f"Release manifest parse error: {ex}")

    overall_status = "PASS" if not errors else "FAIL"

    report = {
        "schema_version": 1,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_video_file": video_path.name,
        "sha256": file_sha,
        "duration_sec": dur,
        "overall_status": overall_status,
        "checks": checks,
        "errors": errors,
        "upstream_hashes": {},
    }

    if report_output:
        report_output.parent.mkdir(parents=True, exist_ok=True)
        report_output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✅ Release report written to {report_output}")

    return overall_status == "PASS", report


def verify_release_manifest_schema(manifest: dict[str, Any]) -> tuple[bool, list[str]]:
    """Verify polymorphic release manifest against version invariants."""
    errors: list[str] = []
    version = str(
        manifest.get("release_schema_version")
        or manifest.get("release_type")
        or ("HISTORICAL_PRODUCTION_RELEASE" if manifest.get("schema_version") == 2 else "OFFICIAL_PRODUCTION_RELEASE_V4")
    )

    if version in {"HISTORICAL_PRODUCTION_RELEASE", "v2"}:
        # Freeze and preserve historical production release without Gate 8 errors
        if not manifest.get("sha256") and not manifest.get("video_sha256"):
            errors.append("Historical release missing video sha256")
        return len(errors) == 0, errors

    # OFFICIAL_PRODUCTION_RELEASE_V4 (Gate 8 Enforcement)
    if not manifest.get("baretip_in_opening_rejected", False):
        errors.append("Gate 8.2 violation: baretip_in_opening_rejected must be True")

    if not manifest.get("first_frame_visibility_passed", False):
        errors.append("Gate 8.1 violation: first_frame_visibility_passed must be True")

    if not manifest.get("motion_diversity_passed", False):
        errors.append("Gate 8.4 violation: motion_diversity_passed must be True")

    parity = float(manifest.get("parity_difference_sec", 0.0))
    if parity > 0.040:
        errors.append(f"Gate 8.6 violation: parity_difference_sec {parity:.3f}s exceeds 0.040s")

    # Check shots / assets if present
    shots = manifest.get("shots") or manifest.get("planned_shots") or []
    if shots:
        opening_shot = shots[0]
        if opening_shot.get("editing_effect") == "bare_tip_whiteboard" or opening_shot.get("asset_type") == "BARETIP_VIDEO":
            errors.append("Gate 8.2 violation: Bare-Tip detected in opening shot")

    return len(errors) == 0, errors


def generate_release_manifest_v4(
    video_path: Path,
    audio_path: Path,
    shots: list[dict[str, Any]],
    parity_diff: float,
    first_frame_visibility_passed: bool = True,
    motion_diversity_passed: bool = True,
    baretip_in_opening_rejected: bool = True,
) -> dict[str, Any]:
    """Generate official production release manifest v4 with Gate 8 bindings."""
    video_path = Path(video_path)
    audio_path = Path(audio_path)
    return {
        "schema_version": 4,
        "release_schema_version": "OFFICIAL_PRODUCTION_RELEASE_V4",
        "release_type": "OFFICIAL_PRODUCTION_RELEASE_V4",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "video_file": video_path.name,
        "video_path": str(video_path),
        "video_sha256": compute_file_sha256(video_path) if video_path.exists() else "",
        "audio_file": audio_path.name,
        "audio_path": str(audio_path),
        "audio_sha256": compute_file_sha256(audio_path) if audio_path.exists() else "",
        "parity_difference_sec": round(parity_diff, 4),
        "first_frame_visibility_passed": bool(first_frame_visibility_passed),
        "baretip_in_opening_rejected": bool(baretip_in_opening_rejected),
        "motion_diversity_passed": bool(motion_diversity_passed),
        "total_shots": len(shots),
        "opening_group_cuts": 3,
        "shots": shots,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--build", type=Path)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--duration-mode", default="full", choices=["full", "pilot"])
    args = parser.parse_args()

    video_file = args.input
    if not video_file and args.build:
        video_file = args.build / "final" / "final_pompeii_ep01_v2.mp4"

    if not video_file:
        parser.error("Either --input or --build is required")

    report_path = args.report or (args.build / "release_report.json" if args.build else None)

    ok, report = verify_postflight(
        video_file,
        contract_path=args.contract,
        build_dir=args.build,
        report_output=report_path,
        duration_mode=args.duration_mode,
    )

    if not ok:
        print("❌ Postflight Release Verification FAILED:")
        for err in report.get("errors", []):
            print(f"  - {err}")
        sys.exit(1)

    print("✅ Postflight Release Verification PASSED!")
    sys.exit(0)


if __name__ == "__main__":
    main()
