from __future__ import annotations

from typing import Any


def validate_render_contract(render: dict[str, Any]) -> dict[str, Any]:
    required = {"width": 1920, "height": 1080, "fps": 25, "format_id": "nollam_file_long", "voice_lock_id": "M2_WARM"}
    failures = [f"{key}={render.get(key)!r}, expected {value!r}" for key, value in required.items() if render.get(key) != value]
    return {"ok": not failures, "failures": failures}


def validate_duration(duration_sec: float) -> dict[str, Any]:
    """Validate that rendered duration falls within trend_explainer_20m bounds (840-1560s)."""
    min_sec = 840.0
    max_sec = 1560.0
    target_sec = 1200.0
    failures = []
    if duration_sec < min_sec:
        failures.append(f"duration={duration_sec:.1f}s is below minimum {min_sec:.0f}s (14 min)")
    if duration_sec > max_sec:
        failures.append(f"duration={duration_sec:.1f}s exceeds maximum {max_sec:.0f}s (26 min)")
    return {
        "ok": not failures,
        "duration_sec": duration_sec,
        "target_sec": target_sec,
        "deviation_pct": round(abs(duration_sec - target_sec) / target_sec * 100, 1),
        "failures": failures,
    }


def validate_full_postflight(render: dict[str, Any], duration_sec: float) -> dict[str, Any]:
    """Run all postflight validations for a Nollam 20-minute episode."""
    contract_result = validate_render_contract(render)
    duration_result = validate_duration(duration_sec)
    all_failures = contract_result["failures"] + duration_result["failures"]
    return {
        "ok": not all_failures,
        "contract": contract_result,
        "duration": duration_result,
        "failures": all_failures,
    }


if __name__ == "__main__":
    raise SystemExit("Use validate_render_contract / validate_duration / validate_full_postflight from the Nollam orchestration runner.")
