from __future__ import annotations

import json
from pathlib import Path

from lib.pacing_scheduler import build_pacing_schedule


def _assert_contiguous(intervals: list[dict], start: float, end: float) -> None:
    assert intervals
    assert intervals[0]["start_sec"] == start
    assert intervals[-1]["end_sec"] == end
    for previous, current in zip(intervals, intervals[1:]):
        assert previous["end_sec"] == current["start_sec"]


def test_synthetic_runtime_matrix_preserves_three_layer_timeline_contract(tmp_path: Path) -> None:
    output = tmp_path / "synthetic_e2e_matrix.json"
    matrix = []
    for runtime in (300.0, 960.0, 1200.0, 1560.0):
        schedule = build_pacing_schedule(runtime)
        _assert_contiguous(schedule["master_shots"], 0.0, runtime)
        _assert_contiguous(schedule["perceptual_cuts"], 0.0, runtime)

        first_shot = schedule["master_shots"][0]
        first_cuts = [
            cut for cut in schedule["perceptual_cuts"]
            if cut["master_shot_id"] == first_shot["shot_id"]
        ]
        assert first_shot["duration_sec"] == 11.0
        assert [cut["asset_binding"] for cut in first_cuts] == ["BARETIP_VIDEO", "FLOW_IMAGE"]

        tier_2 = [shot["duration_sec"] for shot in schedule["master_shots"] if shot["tier"] == "tier_2_context"]
        tier_3 = [shot["duration_sec"] for shot in schedule["master_shots"] if shot["tier"] == "tier_3_deep"]
        assert sum(tier_2) == runtime * 0.20
        assert sum(tier_3) == runtime * 0.70
        assert sum(tier_2) / len(tier_2) < sum(tier_3) / len(tier_3)

        matrix.append({
            "runtime_sec": runtime,
            "master_shots": schedule["master_shot_count"],
            "perceptual_cuts": schedule["perceptual_cut_count"],
            "derived_variants": schedule["derived_variant_count"],
        })

    output.write_text(json.dumps(matrix, indent=2), encoding="utf-8")
    assert output.stat().st_size > 0
    assert json.loads(output.read_text(encoding="utf-8")) == matrix
