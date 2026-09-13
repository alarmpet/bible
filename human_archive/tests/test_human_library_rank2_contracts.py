# -*- coding: utf-8 -*-
"""
test_human_library_rank2_contracts.py
Validates Human Library Rank 2 ('잊혀진 문명, 세계 최강이 사라진 이유') contracts:
1. Gate 0: source_evidence_manifest.json (evidence files, hashes, provenance metrics)
2. Gate 1: master_script_clean.json, normalized_script.json, scientific_fact_inventory.json
3. Gate 2: scenes_manifest.json, shot_composition_plan.json, normalized_replica_bundle.json
"""

import json
from pathlib import Path
import pytest

RUN_DIR = Path(r"D:\module\bible\human_archive\runs\human_library_replica\rank2_forgotten_civilization")
META_DIR = RUN_DIR / "metadata"
SCRIPT_DIR = RUN_DIR / "script"

def test_rank2_source_evidence_manifest():
    p = META_DIR / "source_evidence_manifest.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["gate"] == "Gate 0 - Evidence & Originality Gate"
    assert data["status"] == "PASSED"
    assert data["target_episode"]["source_video_id"] == "o-x6sIGANPY"
    assert data["provenance_metrics"]["raw_cue_count"] == 507
    assert data["provenance_metrics"]["logical_sentence_count"] == 274
    assert data["provenance_metrics"]["clean_char_count_no_space"] == 7202
    assert data["provenance_metrics"]["planned_runtime_sec"] == 1440.0
    assert 4.9 <= data["provenance_metrics"]["true_cps"] <= 5.1

    inventory = data["evidence_file_inventory"]
    assert len(inventory) >= 6
    for k, v in inventory.items():
        assert v["exists"] is True, f"Evidence file {k} missing!"
        assert len(v["sha256"]) == 64, f"Invalid SHA-256 for {k}"
        assert v["size_bytes"] > 0

def test_rank2_master_script_clean():
    p = SCRIPT_DIR / "master_script_clean.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["video_id"] == "o-x6sIGANPY"
    assert data["total_duration_sec"] == 1440.0
    assert data["total_chars_no_space"] == 7202
    assert 4.9 <= data["true_cps"] <= 5.1
    assert len(data["sentences"]) == 274

    for s in data["sentences"]:
        assert s["duration"] > 0.0, f"Zero duration sentence: {s}"
        assert len(s["text"].strip()) > 0

def test_rank2_scientific_fact_inventory():
    p = META_DIR / "scientific_fact_inventory.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["episode_id"] == "human_library_rank2_forgotten_civilization"
    claims = data["claims"]
    assert len(claims) == 7

    claim_ids = [c["claim_id"] for c in claims]
    assert claim_ids == [f"CLAIM_{i:03d}" for i in range(1, 8)]

    assert any("나일강" in c["topic"] and "시리우스" in c["topic"] for c in claims)
    assert any("나르메르" in c["topic"] and "전기메기" in c["topic"] for c in claims)
    assert any("임호텝" in c["topic"] and "스네프루" in c["topic"] for c in claims)
    assert any("쿠푸" in c["topic"] and "노예설 반박" in c["topic"] for c in claims)
    assert any("4.2k" in c["topic"] and "가뭄" in c["topic"] for c in claims)
    assert any("바다민족" in c["topic"] and "파업" in c["topic"] for c in claims)
    assert any("상형문자" in c["topic"] and "샹폴리옹" in c["topic"] for c in claims)

    for c in claims:
        assert c["grade"] == "Grade A"
        assert len(c["citations"]) >= 1

def test_rank2_scenes_manifest_contracts():
    p = META_DIR / "scenes_manifest.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["video_id"] == "o-x6sIGANPY"
    assert data["total_shots"] == 64
    assert data["total_duration_sec"] == 1440.0

    scenes = data["scenes"]
    assert len(scenes) == 64

    opening = [s for s in scenes if s["tier"] == "Opening"]
    assert len(opening) == 3
    assert abs(sum(s["dur"] for s in opening) - 12.0) < 0.01

    assert scenes[0]["start"] == 0.0
    for i in range(len(scenes) - 1):
        assert abs(scenes[i]["end"] - scenes[i+1]["start"]) < 0.001
    assert abs(scenes[-1]["end"] - 1440.0) < 0.01

def test_rank2_shot_composition_plan():
    p = META_DIR / "shot_composition_plan.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_shots"] == 64
    assert data["total_plates"] == 128
    assert data["target_resolution"] == "2304x1296"

    shots = data["shots"]
    assert len(shots) == 64
    for s in shots:
        assert "plate_a" in s and "plate_b" in s
        assert s["plate_a"]["char_count"] <= 441
        assert s["plate_b"]["char_count"] <= 441
        assert "2D Ligne Claire" in s["plate_a"]["prompt"] or "2D graphic novel" in s["plate_a"]["prompt"]

def test_rank2_normalized_bundle_timeline_and_coverage():
    p = META_DIR / "normalized_replica_bundle.json"
    assert p.exists(), f"Missing {p}"
    with open(p, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    assert bundle["episode_id"] == "human_library_rank2_forgotten_civilization"
    assert bundle["target_duration_sec"] == 1440.0
    shots = bundle["shots"]
    assert len(shots) == 64

    with open(SCRIPT_DIR / "normalized_script.json", "r", encoding="utf-8") as f:
        script = json.load(f)
    all_sentence_ids = [s["sentence_id"] for s in script["sentences"]]
    assert len(all_sentence_ids) == 274

    assigned_sentence_ids = []
    for shot in shots:
        spans = shot["sentence_spans"]
        assert len(spans) >= 1, f"Shot {shot['shot_id']} has empty spans!"
        assigned_sentence_ids.extend(spans)

    assert len(assigned_sentence_ids) == 274
    assert len(set(assigned_sentence_ids)) == 274, "Duplicate sentence spans detected!"
    assert assigned_sentence_ids == all_sentence_ids, "Sentence ordering mismatch!"

    assert shots[0]["start_sec"] == 0.0
    for i in range(len(shots) - 1):
        assert abs(shots[i]["end_sec"] - shots[i+1]["start_sec"]) < 0.001
    assert abs(shots[-1]["end_sec"] - 1440.0) < 0.01
