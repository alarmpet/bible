"""Deterministic NOLLAM pacing schedule shared by planning and QA.

The scheduler distinguishes a *master shot* (one source image or video
asset) from a *perceptual cut* (a timed reframe/variant within that asset).
That distinction keeps the early montage fast without forcing the back half
of a documentary to generate one new image every few seconds.
"""

from __future__ import annotations

from typing import Any, Mapping

try:
    from .cinematic_editing_director import calculate_variable_shot_budget
except ImportError:  # Direct script imports keep legacy PYTHONPATH execution working.
    from cinematic_editing_director import calculate_variable_shot_budget


def _zones(target_duration_sec: float) -> list[dict[str, Any]]:
    """Resolve the seven policy zones, including the end-relative outro."""
    target = float(target_duration_sec)
    # The 20-minute profile's 15/60/120/300/600/1110 boundaries are
    # normalized to ratios so a measured 14–26 minute runtime keeps the same
    # editorial shape instead of inheriting stale absolute timestamps.
    boundaries = [
        ("cold_open", 0.0, target * 0.0125),
        ("hook", target * 0.0125, target * 0.05),
        ("roadmap", target * 0.05, target * 0.10),
        ("early_body", target * 0.10, target * 0.25),
        ("body", target * 0.25, target * 0.50),
        ("late_body", target * 0.50, target * 0.925),
        ("outro", target * 0.925, target),
    ]
    policy = {
        "cold_open": (4.0, 3.0, 5.0),
        "hook": (4.5, 3.5, 6.0),
        "roadmap": (6.5, 5.0, 9.0),
        "early_body": (8.5, 6.0, 12.0),
        "body": (10.0, 7.0, 14.0),
        "late_body": (11.5, 8.0, 15.0),
        "outro": (12.5, 9.0, 18.0),
    }
    return [
        {
            "zone_id": zone_id,
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "target_shot_sec": policy[zone_id][0],
            "min_shot_sec": policy[zone_id][1],
            "hard_max_shot_sec": policy[zone_id][2],
        }
        for zone_id, start, end in boundaries
    ]


def _zone_for_time(zones: list[dict[str, Any]], time_sec: float) -> str:
    for zone in zones:
        if zone["start_sec"] <= time_sec < zone["end_sec"]:
            return str(zone["zone_id"])
    return str(zones[-1]["zone_id"])


def _equal_intervals(start: float, end: float, count: int) -> list[tuple[float, float]]:
    if count <= 0 or end <= start:
        return []
    step = (end - start) / count
    intervals = []
    for index in range(count):
        left = start + step * index
        right = end if index == count - 1 else start + step * (index + 1)
        intervals.append((round(left, 3), round(right, 3)))
    return intervals


def _tier_intervals(start: float, end: float, count: int, *, hook: bool = False) -> list[tuple[float, float]]:
    if hook:
        if count < 1 or end - start < 11.0:
            raise ValueError("NOLLAM hook requires at least 11 seconds and one master shot")
        first_end = round(start + 11.0, 3)
        return [(round(start, 3), first_end), *_equal_intervals(first_end, end, count - 1)]
    return _equal_intervals(start, end, count)


def build_pacing_schedule(
    target_duration_sec: float,
    profile: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a reproducible 3-tier/7-zone pacing schedule.

    ``profile`` is accepted for future profile-resolver integration. The
    constitutional master-shot budget remains sourced from the canonical
    ``calculate_variable_shot_budget`` implementation until the resolver is
    wired into every production entry point.
    """
    del profile
    target = float(target_duration_sec)
    if target < 120.0:
        raise ValueError("NOLLAM pacing requires a target duration of at least 120 seconds")

    budget = calculate_variable_shot_budget(target)
    tier_specs = (
        ("tier_1_hook", 0.0, target * 0.10, budget["tier_1_hook"]["recommended_shots"], True),
        ("tier_2_context", target * 0.10, target * 0.30, budget["tier_2_context"]["recommended_shots"], False),
        ("tier_3_deep", target * 0.30, target, budget["tier_3_deep"]["recommended_shots"], False),
    )
    zones = _zones(target)
    master_shots: list[dict[str, Any]] = []
    order = 1
    for tier, start, end, count, is_hook in tier_specs:
        for left, right in _tier_intervals(start, end, count, hook=is_hook):
            master_shots.append({
                "shot_id": f"SHOT_{order:03d}",
                "order": order,
                "tier": tier,
                "zone_id": _zone_for_time(zones, (left + right) / 2.0),
                "start_sec": left,
                "end_sec": right,
                "duration_sec": round(right - left, 3),
                "motion_profile": "biphasic_ken_burns" if tier == "tier_3_deep" else "rapid_reframe",
            })
            order += 1

    perceptual_cuts: list[dict[str, Any]] = []
    for shot in master_shots:
        left, right = float(shot["start_sec"]), float(shot["end_sec"])
        if shot["order"] == 1:
            d1, d2, d3 = 3.0, 3.5, 4.5
            total = d1 + d2 + d3
            dur = right - left
            scale = dur / total
            c1_end = round(left + d1 * scale, 3)
            c2_end = round(c1_end + d2 * scale, 3)
            cut_intervals = ((left, c1_end), (c1_end, c2_end), (c2_end, right))
            opening_roles = ("context_wide", "subject_action", "evidence_detail")
            for cut_index, (cut_left, cut_right) in enumerate(cut_intervals, 1):
                v_role = opening_roles[cut_index - 1]
                perceptual_cuts.append({
                    "cut_id": f"CUT_{len(perceptual_cuts) + 1:03d}",
                    "master_shot_id": shot["shot_id"],
                    "cut_index": cut_index,
                    "cut_type": "opening_trilogy_cut",
                    "visual_role": v_role,
                    "asset_binding": "FLOW_IMAGE",
                    "zone_id": _zone_for_time(zones, (cut_left + cut_right) / 2.0),
                    "start_sec": round(cut_left, 3),
                    "end_sec": round(cut_right, 3),
                    "duration_sec": round(cut_right - cut_left, 3),
                })
            continue

        midpoint = left + (right - left) / 2.0
        cut_intervals = ((left, midpoint), (midpoint, right))
        for cut_index, (cut_left, cut_right) in enumerate(cut_intervals, 1):
            is_derived = cut_index == 2
            perceptual_cuts.append({
                "cut_id": f"CUT_{len(perceptual_cuts) + 1:03d}",
                "master_shot_id": shot["shot_id"],
                "cut_index": cut_index,
                "cut_type": "derived_variant" if is_derived else "primary_reframe",
                "asset_binding": "MASTER_IMAGE",
                "zone_id": _zone_for_time(zones, (cut_left + cut_right) / 2.0),
                "start_sec": round(cut_left, 3),
                "end_sec": round(cut_right, 3),
                "duration_sec": round(cut_right - cut_left, 3),
            })

    return {
        "schema_version": 1,
        "target_duration_sec": target,
        "budget": budget,
        "zones": zones,
        "master_shots": master_shots,
        "perceptual_cuts": perceptual_cuts,
        "master_shot_count": len(master_shots),
        "perceptual_cut_count": len(perceptual_cuts),
        "unique_image_count": len(master_shots),
        "derived_variant_count": sum(cut["cut_type"] == "derived_variant" for cut in perceptual_cuts),
    }
