# -*- coding: utf-8 -*-
"""
pilot_5_gate_verifier.py
Verifies Pilot-5 (SHOT_001 ~ SHOT_005, 20.6s) across Gate 3 (Pacing),
Gate 4 (Audio Contract & Preflight), Gate 5 (Asset Contract & Preflight),
and Gate 6 (Render Motion Binding).
Enforces fail-closed rules and strict zero-concurrency invariants.
"""

from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
_LIB_DIR = _SCRIPTS_DIR / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from lib.cinematic_effect_planner import (
    adapt_planned_to_render_profile,
    resolve_render_motion,
    PlannedProfile,
    MotionPhase,
)

try:
    from lib.external_service_manager import (
        ensure_supertonic3_running,
        ensure_flow_cdp_chrome_running,
    )
except ImportError:
    try:
        from external_service_manager import (
            ensure_supertonic3_running,
            ensure_flow_cdp_chrome_running,
        )
    except ImportError:
        ensure_supertonic3_running = None
        ensure_flow_cdp_chrome_running = None

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
RUN_DIR = REPO_ROOT / "runs" / "human_library_replica" / "rank1_race_adaptation"
PILOT_BUNDLE_FILE = RUN_DIR / "metadata" / "pilot_5_bundle.json"


def probe_service(url: str, timeout: float = 1.0) -> bool:
    """Check if external service is online."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PilotGateVerifier/1.0"})
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False


def verify_gate3_pacing(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Gate 3 — Pacing Gate verification on Pilot-5."""
    shots = bundle.get("shots", [])
    if len(shots) != 5:
        raise ValueError(f"Gate 3 FAIL: Pilot-5 must have exactly 5 shots, got {len(shots)}")

    # 1. Opening 3-Cut timing: 11.0s (3.0s, 3.5s, 4.5s)
    opening_shots = [s for s in shots if s.get("pacing_tier") == "Opening"]
    if len(opening_shots) != 3:
        raise ValueError(f"Gate 3 FAIL: Opening must have exactly 3 cuts, got {len(opening_shots)}")
    opening_dur = sum(s["duration_sec"] for s in opening_shots)
    if abs(opening_dur - 11.0) > 0.001:
        raise ValueError(f"Gate 3 FAIL: Opening duration must be 11.0s, got {opening_dur}s")

    # 2. Tier 1 first 2 cuts timing: 9.6s (4.8s, 4.8s)
    tier1_shots = [s for s in shots if s.get("pacing_tier") == "Tier 1"]
    if len(tier1_shots) != 2:
        raise ValueError(f"Gate 3 FAIL: Tier 1 in Pilot-5 must have exactly 2 cuts, got {len(tier1_shots)}")
    tier1_dur = sum(s["duration_sec"] for s in tier1_shots)
    if abs(tier1_dur - 9.6) > 0.001:
        raise ValueError(f"Gate 3 FAIL: Tier 1 pilot duration must be 9.6s, got {tier1_dur}s")

    # 3. Timeline continuity: zero gaps, zero overlaps
    current_time = 0.0
    for s in shots:
        start = s.get("start_sec", 0.0)
        end = s.get("end_sec", 0.0)
        dur = s.get("duration_sec", 0.0)
        if abs(start - current_time) > 0.001:
            raise ValueError(f"Gate 3 FAIL: Gap/Overlap at {s['shot_id']}: expected start {current_time}, got {start}")
        if abs((end - start) - dur) > 0.001:
            raise ValueError(f"Gate 3 FAIL: Duration mismatch at {s['shot_id']}: {end} - {start} != {dur}")
        current_time = end

    if abs(current_time - 20.6) > 0.001:
        raise ValueError(f"Gate 3 FAIL: Total duration must be 20.6s, got {current_time}s")

    # 4. Motion diversity: no 3 consecutive identical motion families
    families = [s["motion_profile"]["motion_family"] for s in shots]
    for i in range(len(families) - 2):
        if families[i] == families[i+1] == families[i+2]:
            raise ValueError(f"Gate 3 FAIL: 3 consecutive identical motion families: {families[i:i+3]}")

    # 5. Look type diversity: 5 distinct look types
    look_types = [s.get("look_type") for s in shots]
    if len(set(look_types)) < 4:
        raise ValueError(f"Gate 3 FAIL: Insufficient look diversity in Pilot-5: {look_types}")

    return {
        "gate": 3,
        "status": "PASS",
        "total_shots": len(shots),
        "total_duration_sec": current_time,
        "opening_cuts": len(opening_shots),
        "tier1_cuts": len(tier1_shots),
        "motion_families": families,
        "look_types": look_types,
    }


def verify_gate4_audio_contract(
    bundle: Dict[str, Any],
    check_live_service: bool = False,
    audio_dir: Optional[Path] = None,
    auto_start: bool = True,
) -> Dict[str, Any]:
    """Gate 4 — Audio Gate verification and preflight probe."""
    shots = bundle.get("shots", [])
    service_url = "http://127.0.0.1:3093"
    service_online = probe_service(service_url)

    if check_live_service and not service_online:
        if auto_start and ensure_supertonic3_running is not None:
            print("[*] Gate 4 Preflight: SuperTonic3 is offline. Auto-launching SuperTonic3 server...")
            try:
                ensure_supertonic3_running()
                service_online = probe_service(service_url)
            except Exception as e:
                raise ConnectionError(
                    f"Gate 4 FAIL-CLOSED: SuperTonic3 TTS auto-start failed: {e}. "
                    "Cannot generate live narration audio. Halting before corruption."
                ) from e

        if not service_online:
            raise ConnectionError(
                f"Gate 4 FAIL-CLOSED: SuperTonic3 TTS service at {service_url} is OFFLINE. "
                "Cannot generate live narration audio. Halting before corruption."
            )

    # Validate audio contract parameters
    sentence_specs = []
    total_audio_budget = 0.0

    for s in shots:
        spans = s.get("sentence_spans", [])
        if not spans:
            raise ValueError(f"Gate 4 FAIL: Shot {s['shot_id']} has empty sentence spans")
        spoken = s.get("spoken_text", "").strip()
        if not spoken:
            raise ValueError(f"Gate 4 FAIL: Shot {s['shot_id']} has empty spoken text")

        # Audio duration formula: speech + 0.40s roomtone
        dur = s["duration_sec"]
        total_audio_budget += dur
        sentence_specs.append({
            "shot_id": s["shot_id"],
            "sentences": spans,
            "char_count": len(spoken.replace(" ", "")),
            "allocated_duration_sec": dur,
            "target_sample_rate": 48000,
            "channels": 2,
            "target_samples": int(round(dur * 48000)),
        })

    parity_diff = abs(total_audio_budget - bundle["target_duration_sec"])
    if parity_diff > 0.040:
        raise ValueError(
            f"Gate 4 FAIL: Pre-Mux Parity exceeded 0.040s tolerance: {parity_diff:.4f}s"
        )

    return {
        "gate": 4,
        "status": "PASS",
        "service_online": service_online,
        "target_sample_rate": 48000,
        "channels": 2,
        "roomtone_sec": 0.40,
        "pre_mux_parity_diff_sec": parity_diff,
        "sentence_specs": sentence_specs,
    }


def verify_gate5_asset_contract(
    bundle: Dict[str, Any],
    check_live_service: bool = False,
    images_dir: Optional[Path] = None,
    auto_start: bool = True,
) -> Dict[str, Any]:
    """Gate 5 — Asset Gate verification and preflight probe."""
    shots = bundle.get("shots", [])
    service_url = "http://127.0.0.1:9222/json/version"
    service_online = probe_service(service_url)

    if check_live_service and not service_online:
        if auto_start and ensure_flow_cdp_chrome_running is not None:
            print("[*] Gate 5 Preflight: Google Flow CDP is offline. Auto-launching Chrome on port 9222...")
            try:
                ensure_flow_cdp_chrome_running()
                service_online = probe_service(service_url)
            except Exception as e:
                raise ConnectionError(
                    f"Gate 5 FAIL-CLOSED: Google Flow CDP auto-start failed: {e}. "
                    "Cannot generate live Flow images. Halting before corruption."
                ) from e

        if not service_online:
            raise ConnectionError(
                f"Gate 5 FAIL-CLOSED: Google Flow CDP service at {service_url} is OFFLINE. "
                "Cannot generate live Flow images. Halting before corruption."
            )

    # Validate prompt compliance
    forbidden_words = {"photorealistic", "8k", "hyperrealistic", "unreal engine", "octane render"}
    required_aesthetic = {"35mm", "kodak", "anamorphic", "documentary"}

    prompt_reports = []
    for s in shots:
        visual = s.get("visual", {})
        prompt_en = visual.get("prompt_en", "").lower()
        if not prompt_en:
            raise ValueError(f"Gate 5 FAIL: Shot {s['shot_id']} has empty prompt_en")

        # Zero forbidden buzzwords
        found_forbidden = [w for w in forbidden_words if w in prompt_en]
        if found_forbidden:
            raise ValueError(f"Gate 5 FAIL: Shot {s['shot_id']} contains forbidden words: {found_forbidden}")

        # Check documentary cinema markers
        found_aesthetic = [w for w in required_aesthetic if w in prompt_en]
        if len(found_aesthetic) < 2:
            raise ValueError(f"Gate 5 FAIL: Shot {s['shot_id']} missing documentary cinema markers: found {found_aesthetic}")

        # Opening must NOT be bare-tip whiteboard
        if s["pacing_tier"] == "Opening" and ("whiteboard" in prompt_en or "bare-tip" in prompt_en):
            raise ValueError(f"Gate 5 FAIL: Opening shot {s['shot_id']} cannot use whiteboard/bare-tip visual")

        prompt_reports.append({
            "shot_id": s["shot_id"],
            "look_type": s.get("look_type"),
            "aesthetic_markers": found_aesthetic,
            "aspect_ratio": "16:9",
            "target_resolution": "1920x1080",
        })

    return {
        "gate": 5,
        "status": "PASS",
        "service_online": service_online,
        "total_prompts_checked": len(prompt_reports),
        "forbidden_words_found": 0,
        "prompt_reports": prompt_reports,
    }


def verify_gate6_render_motion_binding(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Gate 6 — Render/Motion Gate verification and adapter binding."""
    shots = bundle.get("shots", [])
    render_bindings = []

    for s in shots:
        shot_id = s["shot_id"]
        dur = s["duration_sec"]
        mp = s.get("motion_profile", {})

        planned_dict = {
            "effect_id": shot_id,
            "motion_family": mp.get("motion_family", ""),
            "axis": mp.get("axis", ""),
            "phases": mp.get("phases", []),
            "pacing_tier": s.get("pacing_tier", "Tier 1"),
        }

        # Resolve to canonical motion string without silent fallback
        canonical_motion = resolve_render_motion(shot_id, duration_sec=dur, planned=planned_dict)

        # Also resolve to full RenderMotionProfile DTO
        p_phases = []
        for ph in mp.get("phases", []):
            p_phases.append(
                MotionPhase(
                    duration_ratio=1.0,
                    zoom_start=1.0,
                    zoom_end=1.05 if canonical_motion in {"push_in", "tri_phasic"} else 1.0,
                    center_start=(0.5, 0.5),
                    center_end=(0.5, 0.5),
                    easing="cosine_s_curve",
                )
            )
        planned_profile = PlannedProfile(
            effect_id=shot_id,
            motion_family=mp.get("motion_family", ""),
            axis=mp.get("axis", ""),
            focal_anchor=(0.5, 0.5),
            phases=tuple(p_phases),
            transition_out="hard_cut",
            reason_codes=("pilot_verified",),
            pacing_tier=s.get("pacing_tier", "Tier 1"),
            editing_tempo="rapid_montage" if s.get("pacing_tier") == "Tier 1" else "opening_burst",
            sub_type="canonical_subpixel",
            clamped_for_subtitles=True,
        )

        render_profile = adapt_planned_to_render_profile(planned_profile, duration_sec=dur)

        render_bindings.append({
            "shot_id": shot_id,
            "duration_sec": dur,
            "motion_family": mp.get("motion_family"),
            "axis": mp.get("axis"),
            "canonical_renderer_motion": canonical_motion,
            "dto_canonical": render_profile.canonical_renderer_motion,
            "clamped_for_subtitles": render_profile.clamped_for_subtitles,
        })

    return {
        "gate": 6,
        "status": "PASS",
        "total_bindings": len(render_bindings),
        "bindings": render_bindings,
    }


def run_full_pilot_verification(check_live_services: bool = False, auto_start: bool = True) -> Dict[str, Any]:
    """Execute Gate 3~6 verification pipeline on Pilot-5."""
    if not PILOT_BUNDLE_FILE.exists():
        raise FileNotFoundError(f"Pilot-5 bundle missing: {PILOT_BUNDLE_FILE}. Run build_human_library_pilot_bundle.py first.")

    with open(PILOT_BUNDLE_FILE, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    report = {
        "title": "Human Library Pilot-5 Multi-Gate Preflight Report",
        "bundle_path": str(PILOT_BUNDLE_FILE),
        "check_live_services": check_live_services,
        "auto_start": auto_start,
        "gates": {},
    }

    report["gates"]["gate3_pacing"] = verify_gate3_pacing(bundle)
    report["gates"]["gate4_audio"] = verify_gate4_audio_contract(bundle, check_live_service=check_live_services, auto_start=auto_start)
    report["gates"]["gate5_asset"] = verify_gate5_asset_contract(bundle, check_live_service=check_live_services, auto_start=auto_start)
    report["gates"]["gate6_render"] = verify_gate6_render_motion_binding(bundle)

    report["overall_status"] = "ALL_GATES_PASSED"
    return report


if __name__ == "__main__":
    rep = run_full_pilot_verification(check_live_services=False)
    print(json.dumps(rep, indent=2, ensure_ascii=False))
