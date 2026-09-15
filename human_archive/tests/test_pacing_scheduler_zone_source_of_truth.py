# -*- coding: utf-8 -*-
"""Regression test for the pacing_scheduler.py / visual_pacing_profiles.yaml
zone-boundary drift flagged by the 2026-09-15 overhaul plan's Task 7 "참고
(설계 결정)" note
(docs/superpowers/plans/2026-09-15-human-archive-nollam-script-visual-motion-multi-llm-overhaul-plan.md).

lib/pacing_scheduler.py's `_zones()` independently reimplements the same
nollam_decay_20m 7-stage decay curve declared as data in
config/visual_pacing_profiles.yaml (also resolved at the real production
shot-timing entry point by lib/shot_timing.py's
`_resolve_nollam_decay_zones()`/`_zone_bounds_at()`), but the two disagree on
HOW zone boundaries are computed:

- pacing_scheduler._zones() expresses every boundary as a ratio of
  target_duration_sec, because build_pacing_schedule() is called from a
  nominal *target* duration during shot/cut budget planning, before the real
  TTS audio -- and therefore the actual episode length -- is known, and must
  produce a sensible 7-zone budget for any target across the documented
  14-26 minute tolerance band (840-1560s).
- shot_timing._resolve_nollam_decay_zones() resolves the YAML's zones
  against the real *measured* duration: the first five zones (cold_open
  through body) are FIXED absolute seconds (0/15/60/120/300/600) and only
  late_body/outro scale, via `end_offset_from_end_sec`, off the actual end.

Both were tuned so their numbers agree exactly at target=1200s (the shared
nollam_decay_20m nominal target both were calibrated against). This test
pins that agreement so a future edit to either implementation's boundary
math is caught immediately, and it documents/asserts the *expected* shape of
the divergence at other durations so nobody has to reverse-engineer whether
it is a bug (see pacing_scheduler.py's `_zones()` docstring for the full
rationale).
"""
from __future__ import annotations

from pathlib import Path

import yaml

from lib.pacing_scheduler import _zones as ratio_zones
from lib.shot_timing import _resolve_nollam_decay_zones

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "visual_pacing_profiles.yaml"

_ZONE_ORDER = (
    "cold_open", "hook", "roadmap", "early_body", "body", "late_body", "outro",
)


def _load_yaml_zones_cfg() -> list[dict]:
    document = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8"))
    return document["nollam_decay_20m"]["zones"]


def test_both_implementations_agree_at_the_1200s_nominal_calibration_target() -> None:
    """1200s is the nollam_decay_20m nominal target (config/visual_pacing_profiles.yaml's
    `target_duration_sec: 1200`) both implementations were calibrated against.
    At this one duration the two independently-computed boundary sets must be
    identical for every zone the two implementations both fully resolve
    (cold_open..late_body's start/end, and outro's start -- see the note on
    outro's end below)."""
    yaml_zones = {
        zone["zone_id"]: zone
        for zone in _resolve_nollam_decay_zones(_load_yaml_zones_cfg(), total_duration_sec=1200.0)
    }
    ratio = {zone["zone_id"]: zone for zone in ratio_zones(1200.0)}

    assert set(yaml_zones) == set(ratio) == set(_ZONE_ORDER)

    # cold_open..late_body: both start_sec and end_sec must match exactly.
    for zone_id in ("cold_open", "hook", "roadmap", "early_body", "body", "late_body"):
        assert ratio[zone_id]["start_sec"] == yaml_zones[zone_id]["start_sec"], zone_id
        assert ratio[zone_id]["end_sec"] == yaml_zones[zone_id]["end_sec"], zone_id

    # outro: only start_sec is compared. shot_timing._resolve_nollam_decay_zones()
    # reuses outro's end_offset_from_end_sec for BOTH the start-sentinel
    # resolution (start_sec: -1) and the end computation, so its resolved
    # outro end_sec comes out equal to late_body's end (1200 - 90 = 1110)
    # rather than the true episode end (1200) -- a pre-existing quirk in
    # shot_timing.py, out of scope for this fix. It is harmless in practice
    # because _zone_bounds_at() falls back to the last zone in the list (the
    # same outro zone) whenever no zone's [start, end) contains the queried
    # time, which is exactly what happens for any t >= 1110. This test only
    # asserts what both implementations agree on: where outro *starts*.
    assert ratio["outro"]["start_sec"] == yaml_zones["outro"]["start_sec"] == 1110.0
    assert ratio["outro"]["end_sec"] == 1200.0
    assert yaml_zones["outro"]["end_sec"] == 1110.0


def test_first_five_zones_diverge_at_other_durations_because_the_yaml_boundaries_are_fixed() -> None:
    """Away from the 1200s calibration point, pacing_scheduler's ratio zones
    and the YAML's fixed-second zones are EXPECTED to disagree for
    cold_open..body -- this is the documented, intentional divergence, not
    drift to be "fixed" by matching them. Demonstrated at 900s (a runtime
    within the 14-26 minute tolerance band): the YAML's fixed body zone
    (300-600s) would claim 33%-67% of a 900s episode, which is why
    pacing_scheduler cannot simply delegate to the YAML/shot_timing
    resolution for its target-duration budget planning."""
    yaml_zones_cfg = _load_yaml_zones_cfg()
    yaml_zones = {
        zone["zone_id"]: zone
        for zone in _resolve_nollam_decay_zones(yaml_zones_cfg, total_duration_sec=900.0)
    }
    ratio = {zone["zone_id"]: zone for zone in ratio_zones(900.0)}

    # cold_open's start is always 0.0 in both implementations (nothing to
    # diverge on there), so the divergence is checked via each zone's
    # end_sec, which is non-zero and fixed in the YAML for all five zones.
    for zone_id, fixed_end in (
        ("cold_open", 15.0), ("hook", 60.0), ("roadmap", 120.0),
        ("early_body", 300.0), ("body", 600.0),
    ):
        # The YAML's fixed absolute seconds do not move...
        assert yaml_zones[zone_id]["end_sec"] == fixed_end, zone_id
        # ...while pacing_scheduler's ratio zones scale down with the shorter
        # target, so the two disagree.
        assert ratio[zone_id]["end_sec"] != yaml_zones[zone_id]["end_sec"], (
            f"{zone_id} was expected to diverge at 900s but matched the fixed YAML value"
        )

    # late_body/outro both scale off the true end in both implementations,
    # but by different amounts (fixed 90s offset vs. a 7.5%-of-target ratio
    # offset that only equals 90s exactly at target=1200), so they diverge
    # here too.
    assert ratio["late_body"]["end_sec"] == 832.5
    assert yaml_zones["late_body"]["end_sec"] == 810.0
    assert ratio["late_body"]["end_sec"] != yaml_zones["late_body"]["end_sec"]


def test_ratio_zones_still_reproduce_the_seven_yaml_zone_ids_and_shot_length_policy() -> None:
    """Regardless of the boundary-computation divergence, both sources must
    keep describing the *same* nollam_decay_20m curve -- same seven zone ids
    in the same order, same per-zone target/min/hard_max shot seconds. If a
    future edit to the YAML's shot-length numbers is not mirrored into
    pacing_scheduler's hardcoded `policy` table (or vice versa), this test
    catches that drift even though it cannot catch boundary drift (which is
    the whole point of the two other tests above)."""
    yaml_zones_cfg = {zone["zone_id"]: zone for zone in _load_yaml_zones_cfg()}
    ratio = {zone["zone_id"]: zone for zone in ratio_zones(1200.0)}

    assert [z["zone_id"] for z in ratio_zones(1200.0)] == list(_ZONE_ORDER)
    for zone_id in _ZONE_ORDER:
        assert ratio[zone_id]["target_shot_sec"] == yaml_zones_cfg[zone_id]["target_shot_sec"], zone_id
        assert ratio[zone_id]["min_shot_sec"] == yaml_zones_cfg[zone_id]["min_shot_sec"], zone_id
        assert ratio[zone_id]["hard_max_shot_sec"] == yaml_zones_cfg[zone_id]["hard_max_shot_sec"], zone_id
