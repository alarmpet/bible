# -*- coding: utf-8 -*-
"""Regression tests for the Rank 2 visual-remediation contract."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from lib.rank2_visual_contract import (
    annotate_cut_contract,
    audit_plate_directory,
    blend_transition_frame,
    build_rank2_lineage,
    choose_motion_profile,
    detect_baked_in_plate_artifacts,
    prepare_clean_plate_set,
    transition_for_boundary,
)
from lib.exact_release_verifier import audit_subcut_montage_plan
from lib.subcut_montage_engine import SubcutPlan
from build_rank2_clean_subtitles import build_rank2_clean_ass


def test_rank2_lineage_binds_shot_to_sentence_cue_and_claim():
    bundle = {"shots": [{"shot_id": "SHOT_001", "sentence_spans": ["SENT_001"]}]}
    script = {"sentences": [{"sentence_id": "SENT_001", "claim_ids": ["CLAIM_007"]}]}
    canonical = {
        "sentence_mappings": {"SENT_001": ["CUE_001"]},
        "cues": [{"cue_id": "CUE_001", "parent_sentence_id": "SENT_001"}],
    }

    lineage = build_rank2_lineage(bundle, script, canonical)

    assert lineage["SHOT_001"] == {
        "sentence_ids": ["SENT_001"],
        "cue_ids": ["CUE_001"],
        "claim_ids": ["CLAIM_007"],
    }


def test_rank2_lineage_fails_closed_when_sentence_is_missing():
    with pytest.raises(ValueError, match="SENT_MISSING"):
        build_rank2_lineage(
            {"shots": [{"shot_id": "SHOT_001", "sentence_spans": ["SENT_MISSING"]}]},
            {"sentences": []},
            {"sentence_mappings": {}, "cues": []},
        )


def test_motion_profile_is_shot_local_and_has_real_trajectory():
    first = choose_motion_profile(shot_index=0, cut_index=0, cut_count=4)
    second_shot = choose_motion_profile(shot_index=1, cut_index=0, cut_count=4)

    assert first["motion_family"] != second_shot["motion_family"]
    assert first["start_zoom"] != first["end_zoom"] or first["start_cx"] != first["end_cx"]
    assert first["easing"] == "cosine_s"


def test_transition_policy_inserts_blend_only_at_meaningful_boundaries():
    assert transition_for_boundary(
        previous_shot="SHOT_001", next_shot="SHOT_002", previous_index=0
    )["type"] in {"hard_cut", "dissolve", "match_cut", "whip_pan"}
    assert transition_for_boundary(
        previous_shot="SHOT_001", next_shot="SHOT_001", previous_index=1
    )["type"] == "hard_cut"


def test_cut_contract_carries_lineage_and_transition_metadata():
    cut = {"cut_id": "CUT_001", "parent_shot_id": "SHOT_001", "plate_id": "SHOT_001_A"}
    result = annotate_cut_contract(
        cut,
        {"sentence_ids": ["SENT_001"], "cue_ids": ["CUE_001"], "claim_ids": ["CLAIM_007"]},
        visual_beat="context",
        motion_profile={"motion_family": "push"},
        transition_in={"type": "dissolve", "frames": 8},
    )
    assert result["sentence_ids"] == ["SENT_001"]
    assert result["cue_ids"] == ["CUE_001"]
    assert result["claim_ids"] == ["CLAIM_007"]
    assert result["transition_in"] == {"type": "dissolve", "frames": 8}


def test_transition_blend_is_a_real_pixel_interpolation():
    previous = np.zeros((2, 2, 3), dtype=np.uint8)
    current = np.full((2, 2, 3), 200, dtype=np.uint8)

    middle = blend_transition_frame(previous, current, 0.5)

    assert middle.dtype == np.uint8
    assert np.all(middle == 100)


def test_visual_cadence_contract_accepts_550_to_600_cuts():
    cuts = [
        {
            "frame_count": 72,
            "parent_shot_id": f"SHOT_{i // 2 + 1:03d}",
            "plate_id": f"SHOT_{i // 2 + 1:03d}_{'A' if i % 2 == 0 else 'B'}",
            "role": "context_wide" if i % 2 == 0 else "detail_evidence",
        }
        for i in range(600)
    ]
    cuts[-1]["frame_count"] += 43200 - sum(c["frame_count"] for c in cuts)

    result = audit_subcut_montage_plan(cuts, expected_min_cuts=550, expected_max_cuts=600)

    assert result["status"] == "PASS", result["errors"]


def test_subcut_plan_accepts_edit_graph_metadata():
    plan = SubcutPlan(
        cut_index=1,
        cut_id="CUT_001",
        start_sec=0.0,
        end_sec=1.0,
        duration_sec=1.0,
        frame_count=30,
        parent_shot_id="SHOT_001",
        plate_id="SHOT_001_A",
        transformation="push_in",
        sentence_ids=["SENT_001"],
        cue_ids=["CUE_001"],
        claim_ids=["CLAIM_007"],
        visual_beat="context",
        motion_profile={"motion_family": "push"},
        transition_in={"type": "hard_cut", "frames": 0},
    )

    assert plan.claim_ids == ["CLAIM_007"]
    assert plan.transition_in["type"] == "hard_cut"


def test_rank2_subtitle_style_is_large_boxed_and_safe_area_bound(tmp_path: Path):
    ass_path = build_rank2_clean_ass(output_ass=tmp_path / "rank2_candidate.ass")
    style = next(
        line for line in ass_path.read_text(encoding="utf-8").splitlines()
        if line.startswith("Style: DocuNarrator_Exact,")
    )
    fields = style.split(",")

    assert int(fields[2]) >= 70
    assert fields[15] == "3"
    assert int(fields[21]) >= 72


def test_plate_artifact_detector_rejects_provider_mark_and_bottom_band(tmp_path: Path):
    image = np.full((180, 320, 3), 220, dtype=np.uint8)
    image[150:, :] = 20
    image[138:165, 275:315] = 30
    path = tmp_path / "plate.jpg"
    Image.fromarray(image).save(path, quality=95)

    result = detect_baked_in_plate_artifacts(path)

    assert result["status"] == "FAIL"
    assert result["bottom_band_detected"] is True
    assert result["provider_mark_detected"] is True


def test_plate_directory_audit_reports_every_dirty_plate(tmp_path: Path):
    for name in ("SHOT_001_A.jpg", "SHOT_001_B.jpg"):
        image = np.full((180, 320, 3), 220, dtype=np.uint8)
        image[150:, :] = 20
        image[138:165, 275:315] = 30
        Image.fromarray(image).save(tmp_path / name, quality=95)

    result = audit_plate_directory(tmp_path, expected_count=2)

    assert result["status"] == "FAIL"
    assert result["dirty_count"] == 2


def test_clean_plate_set_uses_a_16_by_9_source_crop_without_touching_source(tmp_path: Path):
    source = tmp_path / "source"
    target = tmp_path / "clean"
    source.mkdir()
    image = Image.new("RGB", (2304, 1296), (220, 180, 120))
    image.save(source / "SHOT_001_A.jpg", quality=95)

    result = prepare_clean_plate_set(source, target)

    assert result["status"] == "PASS"
    assert Image.open(source / "SHOT_001_A.jpg").size == (2304, 1296)
    assert Image.open(target / "SHOT_001_A.jpg").size == (2304, 1296)
    assert result["method"] == "top_safe_crop_16x9"
