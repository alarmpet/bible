from __future__ import annotations

from typing import Any


def validate_render_contract(render: dict[str, Any]) -> dict[str, Any]:
    required = {"width": 1920, "height": 1080, "fps": 25, "format_id": "nollam_file_long", "voice_lock_id": "M2_WARM"}
    failures = [f"{key}={render.get(key)!r}, expected {value!r}" for key, value in required.items() if render.get(key) != value]
    return {"ok": not failures, "failures": failures}


def validate_duration(
    duration_sec: float,
    *,
    min_sec: float = 840.0,
    max_sec: float = 1560.0,
    target_sec: float = 1200.0,
) -> dict[str, Any]:
    """Validate that rendered duration falls within the delivery profile's
    bounds. Defaults to trend_explainer_20m's bounds (840-1560s, target
    1200s) for backward compatibility. Pass min_sec/max_sec/target_sec
    explicitly for any other delivery profile -- e.g. quick_3m's
    170/190/180 (config/delivery_profiles.yaml). 2026-09-16 finding: this was
    hardcoded to trend_explainer_20m only, so it rejected a real, correctly
    rendered quick_3m episode's ~190s duration outright."""
    failures = []
    if duration_sec < min_sec:
        failures.append(f"duration={duration_sec:.1f}s is below minimum {min_sec:.0f}s")
    if duration_sec > max_sec:
        failures.append(f"duration={duration_sec:.1f}s exceeds maximum {max_sec:.0f}s")
    return {
        "ok": not failures,
        "duration_sec": duration_sec,
        "target_sec": target_sec,
        "deviation_pct": round(abs(duration_sec - target_sec) / target_sec * 100, 1) if target_sec else 0.0,
        "failures": failures,
    }


def validate_full_postflight(
    render: dict[str, Any],
    duration_sec: float,
    *,
    min_sec: float = 840.0,
    max_sec: float = 1560.0,
    target_sec: float = 1200.0,
) -> dict[str, Any]:
    """Run all postflight validations for a Nollam episode. Duration bounds
    default to trend_explainer_20m; pass min_sec/max_sec/target_sec for any
    other delivery profile (see validate_duration)."""
    contract_result = validate_render_contract(render)
    duration_result = validate_duration(
        duration_sec, min_sec=min_sec, max_sec=max_sec, target_sec=target_sec
    )
    all_failures = contract_result["failures"] + duration_result["failures"]
    return {
        "ok": not all_failures,
        "contract": contract_result,
        "duration": duration_result,
        "failures": all_failures,
    }


if __name__ == "__main__":
    raise SystemExit("Use validate_render_contract / validate_duration / validate_full_postflight from the Nollam orchestration runner.")
