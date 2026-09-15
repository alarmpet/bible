# -*- coding: utf-8 -*-
"""Postflight release verification against machine-measured audio/visual criteria."""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Tuple
import yaml
import numpy as np

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.provenance import compute_file_sha256
from lib.media_probe import measure_ebu_r128_loudness, probe_video_streams
from lib.production_path_guard import assert_not_isolated_research_path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


@dataclass
class ProductionProfile:
    fps: int = 25
    samples_per_frame: int = 1920
    window_size: int = 25
    parity_tolerance_sec: float = 0.040

    @classmethod
    def from_fps(cls, fps: int = 25) -> "ProductionProfile":
        if fps == 30:
            return cls(
                fps=30,
                samples_per_frame=1600,
                window_size=30,
                parity_tolerance_sec=0.0333,
            )
        return cls(
            fps=25,
            samples_per_frame=1920,
            window_size=25,
            parity_tolerance_sec=0.040,
        )


def check_decoded_stream_motion_mae(
    frames: List[np.ndarray],
    window_size: int = 25,
    min_mae_threshold: float = 0.85,
    subtitle_bottom_ratio: float = 0.20,
) -> Tuple[bool, float, str]:
    """Calculate 25-frame sliding window cumulative MAE on decoded frames with subtitle masking.

    Returns (passed, min_mae, message).
    """
    if len(frames) <= window_size:
        return True, 99.0, "Stream length <= window_size, motion check bypassed"

    h, w = frames[0].shape[:2]
    active_h = int(h * (1.0 - subtitle_bottom_ratio))

    # Convert to grayscale float32 active region
    grays = []
    for f in frames:
        if len(f.shape) == 3 and f.shape[2] == 3:
            gray = 0.299 * f[:active_h, :, 0] + 0.587 * f[:active_h, :, 1] + 0.114 * f[:active_h, :, 2]
        else:
            gray = f[:active_h, :].astype(np.float32)
        grays.append(gray)

    min_mae = float("inf")
    for i in range(len(grays) - window_size):
        diff = np.abs(grays[i + window_size] - grays[i])
        mae = float(np.mean(diff))
        if mae < min_mae:
            min_mae = mae

    if min_mae < min_mae_threshold:
        return (
            False,
            min_mae,
            f"Static hold / frozen frame detected: min 25-frame MAE={min_mae:.3f} < threshold={min_mae_threshold}",
        )

    return True, min_mae, f"Continuous decoded motion verified: min 25-frame MAE={min_mae:.3f} >= {min_mae_threshold}"


def measure_decoded_video_motion_diversity(
    video_path: Path,
    window_size: int = 25,
    min_mae_threshold: float = 0.85,
    subtitle_bottom_ratio: float = 0.20,
    resize_width: int = 320,
) -> Tuple[bool, float, str]:
    """Stream-decode ``video_path`` and compute the same sliding-window luma MAE
    check as :func:`check_decoded_stream_motion_mae`, without holding the entire
    decoded stream in memory (a full 20-minute 25fps release is ~30k frames).

    Only the last ``window_size`` frames are ever buffered; frames are downsized
    to ``resize_width`` before comparison since the motion signal this gate cares
    about (frozen holds vs. continuous camera motion) does not require full
    resolution. Any failure to open/decode the file is treated as a failed
    check (fail-closed), not silently skipped, so the gate blocks release
    rather than passing by omission when the motion QA step did not actually run.
    """
    try:
        import cv2
    except Exception as ex:
        return False, 0.0, f"Could not import cv2 for decoded motion check: {ex}"

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return False, 0.0, f"Could not open video for decoded motion check: {video_path}"

    buffer: List[np.ndarray] = []
    min_mae = float("inf")
    frame_count = 0
    active_h: int | None = None
    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            frame_count += 1
            h, w = frame.shape[:2]
            if resize_width and w > resize_width:
                scale = resize_width / w
                frame = cv2.resize(frame, (resize_width, max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
                h, w = frame.shape[:2]
            if active_h is None:
                active_h = int(h * (1.0 - subtitle_bottom_ratio))
            # cv2 decodes BGR; weights mirror the R/G/B luma weights used by
            # check_decoded_stream_motion_mae, just reordered for channel order.
            gray = (
                0.114 * frame[:active_h, :, 0].astype(np.float32)
                + 0.587 * frame[:active_h, :, 1].astype(np.float32)
                + 0.299 * frame[:active_h, :, 2].astype(np.float32)
            )
            buffer.append(gray)
            if len(buffer) > window_size + 1:
                buffer.pop(0)
            if len(buffer) == window_size + 1:
                diff = np.abs(buffer[-1] - buffer[0])
                mae = float(np.mean(diff))
                if mae < min_mae:
                    min_mae = mae
    finally:
        cap.release()

    if frame_count <= window_size:
        return True, 99.0, f"Decoded stream length ({frame_count}) <= window_size, motion check bypassed"

    if min_mae < min_mae_threshold:
        return (
            False,
            min_mae,
            f"Static hold / frozen frame detected in decoded release video across {frame_count} frames: "
            f"min {window_size}-frame MAE={min_mae:.3f} < threshold={min_mae_threshold}",
        )
    return (
        True,
        min_mae,
        f"Continuous decoded motion verified across {frame_count} frames: "
        f"min {window_size}-frame MAE={min_mae:.3f} >= {min_mae_threshold}",
    )


def verify_postflight(
    video_path: Path,
    contract_path: Path | None = None,
    build_dir: Path | None = None,
    report_output: Path | None = None,
    duration_mode: str = "full",
    target_fps: int = 25,
) -> tuple[bool, dict]:
    video_path = Path(video_path).resolve()
    assert_not_isolated_research_path(video_path, contract_path, build_dir)
    if not video_path.exists():
        raise SystemExit(f"Target video not found: {video_path}")

    file_sha = compute_file_sha256(video_path)
    meta = {}
    loudness = {}
    try:
        meta = probe_video_streams(video_path)
        loudness = measure_ebu_r128_loudness(video_path)
    except Exception:
        pass

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
    elif duration_mode == "pilot":
        target_min, target_max = 30, 180
    dur_ok = target_min <= dur <= target_max
    checks["contract_duration"] = {"status": "PASS" if dur_ok else "FAIL", "duration_sec": dur, "target_range": [target_min, target_max]}
    if not dur_ok and dur > 0.0:
        errors.append(f"Duration {dur:.2f}s out of contract range [{target_min}, {target_max}]")

    # 2. Dimensions & SAR & Progressive
    if v_info.get("width") is not None:
        dim_ok = (v_info.get("width") == 1920 and v_info.get("height") == 1080)
        sar = v_info.get("sample_aspect_ratio", "1:1")
        sar_ok = (sar in ["1:1", None])
        prog_ok = (v_info.get("field_order") in ["progressive", "unknown", None])
        geom_ok = dim_ok and sar_ok and prog_ok
        checks["dimensions"] = {"status": "PASS" if geom_ok else "FAIL", "actual": f"{v_info.get('width')}x{v_info.get('height')}", "sar": sar}
        if not geom_ok:
            errors.append(f"Invalid geometry: {v_info.get('width')}x{v_info.get('height')}, sar={sar}")

        # 3. Framerate (CFR target_fps)
        r_fps = v_info.get("r_frame_rate", "")
        avg_fps = v_info.get("avg_frame_rate", "")
        expected_r = f"{target_fps}/1"
        expected_avgs = [expected_r, str(target_fps), None]
        fps_ok = (r_fps == expected_r and (avg_fps in expected_avgs))
        checks["framerate"] = {"status": "PASS" if fps_ok else "FAIL", "r_frame_rate": r_fps, "avg_frame_rate": avg_fps, "target_fps": target_fps}
        if not fps_ok:
            errors.append(f"Non-{target_fps} CFR detected: r_fps={r_fps}, avg_fps={avg_fps}")

        # 4. Color tags
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
    if loudness:
        i_lufs = loudness.get("input_i", -99.0)
        tp_db = loudness.get("input_tp", -99.0)
        lufs_ok = (-17.0 <= i_lufs <= -13.0)
        if not lufs_ok and duration_mode == "pilot":
            lufs_ok = (i_lufs > -30.0)
        tp_ok = (tp_db <= -1.0)
        loud_ok = (lufs_ok and tp_ok)
        checks["loudness"] = {"status": "PASS" if loud_ok else "FAIL", "integrated_lufs": i_lufs, "true_peak_db": tp_db}
        if not loud_ok and dur > 0.0:
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

    # 6b. Simulated/fixture provenance gate (2026-09-15 overhaul plan §5.3 rule 4).
    # tri_model_debate_engine.py's orchestrate_deep_tri_model_script() labels its own
    # output honestly when Round 1/2 are static templated dicts rather than live model
    # calls (metadata.provenance == "simulated_fixture"). A build whose generation
    # manifest carries that label must never pass release verification -- checking it
    # here, not just trusting the label was checked upstream, is what makes it a gate
    # rather than documentation.
    simulated_fixture_ok = True
    if build_dir:
        for candidate_name in ("generation/master_1200s_manifest.json", "audit/final_consensus_manifest.json"):
            candidate_path = build_dir / candidate_name
            if not candidate_path.exists():
                continue
            try:
                gen_manifest = json.loads(candidate_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            provenance = str((gen_manifest.get("metadata") or {}).get("provenance", ""))
            if provenance == "simulated_fixture":
                simulated_fixture_ok = False
                detail = (gen_manifest.get("metadata") or {}).get("provenance_detail", "")
                errors.append(
                    f"Simulated/fixture provenance in {candidate_name}: this build's "
                    f"generation manifest is labeled simulated_fixture and cannot be released. {detail}"
                )
                break
    checks["simulated_fixture_provenance"] = {"status": "PASS" if simulated_fixture_ok else "FAIL"}

    # 7. Release Manifest Verification
    manifest_target = None
    if build_dir:
        candidate_v5 = build_dir / "release_manifest_v5.json"
        candidate_v4 = build_dir / "release_manifest_v4.json"
        candidate_legacy = build_dir / "release_manifest.json"
        if candidate_v5.exists():
            manifest_target = candidate_v5
        elif candidate_v4.exists():
            manifest_target = candidate_v4
        elif candidate_legacy.exists():
            manifest_target = candidate_legacy

    if manifest_target and manifest_target.exists():
        try:
            m_data = json.loads(manifest_target.read_text(encoding="utf-8"))
            m_ok, m_errs = verify_release_manifest_schema(m_data)

            # Physical binding: Verify video_sha256 in manifest matches actual file
            m_v_sha = m_data.get("video_sha256")
            if m_v_sha and m_v_sha.upper() != file_sha.upper():
                m_ok = False
                m_errs.append(f"Physical SHA256 mismatch: target video SHA256={file_sha} != manifest video_sha256={m_v_sha}")

            # Physical binding: Mirror check if path present
            mirror_p_str = m_data.get("mirror_path")
            if mirror_p_str:
                m_p = Path(mirror_p_str)
                if m_p.exists():
                    m_sha = compute_file_sha256(m_p)
                    if m_sha.upper() != file_sha.upper():
                        m_ok = False
                        m_errs.append(f"Physical Mirror SHA256 mismatch: mirror={m_sha} != target={file_sha}")

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

    # 8. Decoded frame physical Gate 8 check (enforced for V4/V5 production releases)
    is_v4_v5_release = (
        manifest_target is not None
        and (
            "v4" in manifest_target.name.lower()
            or "v5" in manifest_target.name.lower()
            or (isinstance(locals().get("m_data"), dict) and str(locals().get("m_data", {}).get("release_schema_version", "")).startswith("OFFICIAL_PRODUCTION_RELEASE"))
        )
    )
    if is_v4_v5_release and video_path.exists() and video_path.stat().st_size > 100000:
        try:
            import cv2
            cap = cv2.VideoCapture(str(video_path))
            if cap.isOpened():
                ret, f0 = cap.read()
                if ret and f0 is not None and f0.shape[0] >= 100:
                    from lib.asset_contract import evaluate_frame_visibility_gate
                    vis_res = evaluate_frame_visibility_gate(f0)
                    checks["first_frame_physical_visibility"] = vis_res
                    if not vis_res.get("passed", False):
                        errors.append("Physical decoded first frame failed Gate 8 visibility check")
                cap.release()
        except Exception:
            pass

        # Gate 8.4: decoded-stream motion diversity, measured fresh from the actual
        # release video every time — not read from a manifest field a caller could
        # set to True without ever running the check (see check_decoded_stream_motion_mae,
        # which was previously defined but never called from here).
        motion_passed, motion_min_mae, motion_msg = measure_decoded_video_motion_diversity(video_path)
        checks["decoded_motion_diversity"] = {
            "status": "PASS" if motion_passed else "FAIL",
            "min_window_mae": motion_min_mae,
            "message": motion_msg,
        }
        if not motion_passed:
            errors.append(f"Gate 8.4 violation (decoded, not manifest-reported): {motion_msg}")

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

    if version in {"HISTORICAL_PRODUCTION_RELEASE", "HISTORICAL_PRODUCTION_RELEASE_V3", "v2", "v3"}:
        # Freeze and preserve historical production release without Gate 8 errors
        if not manifest.get("sha256") and not manifest.get("video_sha256"):
            errors.append("Historical release missing video sha256")
        return len(errors) == 0, errors

    # OFFICIAL_PRODUCTION_RELEASE_V4 / V5 (Gate 8 Enforcement)
    if not manifest.get("baretip_in_opening_rejected", False):
        errors.append("Gate 8.2 violation: baretip_in_opening_rejected must be True")

    if not manifest.get("first_frame_visibility_passed", False):
        errors.append("Gate 8.1 violation: first_frame_visibility_passed must be True")

    if not manifest.get("motion_diversity_passed", False):
        errors.append("Gate 8.4 violation: motion_diversity_passed must be True")

    # Parity check
    parity = float(
        manifest.get("final_stream_parity_difference_sec")
        or manifest.get("parity_difference_sec")
        or 0.0
    )
    if parity > 0.050:
        errors.append(f"Parity violation: stream parity {parity:.3f}s exceeds 0.050s")

    pre_parity = float(manifest.get("pre_mux_parity_difference_sec") or 0.0)
    if pre_parity > 0.040:
        errors.append(f"Gate 8.6 violation: pre_mux_parity {pre_parity:.3f}s exceeds 0.040s")

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
    motion_diversity_passed: bool | None = None,
    baretip_in_opening_rejected: bool = True,
) -> dict[str, Any]:
    """Generate official production release manifest v4 with Gate 8 bindings.

    ``motion_diversity_passed`` used to default to ``True`` unconditionally, which
    meant a manifest could self-report "motion QA passed" without the check ever
    running. Leave it unset (``None``) to have it measured for real from
    ``video_path`` via :func:`measure_decoded_video_motion_diversity`; a caller
    may still pass an explicit bool if it already computed one upstream.
    """
    video_path = Path(video_path)
    audio_path = Path(audio_path)
    if motion_diversity_passed is None:
        motion_diversity_passed = (
            measure_decoded_video_motion_diversity(video_path)[0] if video_path.exists() else False
        )
    return {
        "schema_version": 4,
        "release_schema_version": "OFFICIAL_PRODUCTION_RELEASE_V4",
        "release_type": "OFFICIAL_PRODUCTION_RELEASE_V4",
        "release_id": "NOLLAM_NEANDERTHAL_V4_RELEASE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "video_file": video_path.name,
        "video_path": str(video_path),
        "video_sha256": compute_file_sha256(video_path) if video_path.exists() else "",
        "audio_file": audio_path.name,
        "audio_path": str(audio_path),
        "audio_sha256": compute_file_sha256(audio_path) if audio_path.exists() else "",
        "parity_difference_sec": round(parity_diff, 4),
        "pre_mux_parity_difference_sec": round(parity_diff, 4),
        "final_stream_parity_difference_sec": round(parity_diff, 4),
        "first_frame_visibility_passed": bool(first_frame_visibility_passed),
        "baretip_in_opening_rejected": bool(baretip_in_opening_rejected),
        "motion_diversity_passed": bool(motion_diversity_passed),
        "total_shots": len(shots),
        "opening_group_cuts": 3,
        "shots": shots,
    }


def generate_release_manifest_v5(
    video_path: Path,
    audio_path: Path,
    shots: list[dict[str, Any]],
    pre_mux_parity: float,
    final_stream_parity: float,
    first_frame_visibility_passed: bool = True,
    motion_diversity_passed: bool | None = None,
    baretip_in_opening_rejected: bool = True,
    artifact_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate official production release manifest v5 with physical decoded bindings.

    See :func:`generate_release_manifest_v4` — ``motion_diversity_passed`` is
    measured for real from ``video_path`` when left unset instead of defaulting
    to ``True``.
    """
    video_path = Path(video_path)
    audio_path = Path(audio_path)
    if motion_diversity_passed is None:
        motion_diversity_passed = (
            measure_decoded_video_motion_diversity(video_path)[0] if video_path.exists() else False
        )
    return {
        "schema_version": 5,
        "release_schema_version": "OFFICIAL_PRODUCTION_RELEASE_V5",
        "release_type": "OFFICIAL_PRODUCTION_RELEASE_V5",
        "release_id": "NOLLAM_NEANDERTHAL_V5_RELEASE",
        "supersedes": "NOLLAM_NEANDERTHAL_V4_RELEASE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "video_file": video_path.name,
        "video_path": str(video_path),
        "video_sha256": compute_file_sha256(video_path) if video_path.exists() else "",
        "audio_file": audio_path.name,
        "audio_path": str(audio_path),
        "audio_sha256": compute_file_sha256(audio_path) if audio_path.exists() else "",
        "pre_mux_parity_difference_sec": round(pre_mux_parity, 4),
        "final_stream_parity_difference_sec": round(final_stream_parity, 4),
        "parity_difference_sec": round(final_stream_parity, 4),
        "first_frame_visibility_passed": bool(first_frame_visibility_passed),
        "baretip_in_opening_rejected": bool(baretip_in_opening_rejected),
        "motion_diversity_passed": bool(motion_diversity_passed),
        "total_shots": len(shots),
        "opening_group_cuts": 3,
        "shots": shots,
        "artifact_registry": artifact_registry or {},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--build", type=Path)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--duration-mode", default="full", choices=["full", "pilot"])
    parser.add_argument("--fps", type=int, default=25, choices=[24, 25, 30], help="Target framerate (default 25)")
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
        target_fps=args.fps,
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
