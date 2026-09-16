from __future__ import annotations

import json
from pathlib import Path

from build_image_request_manifest_v5 import build_image_request_manifest
from lib.provenance import compute_file_sha256


def test_v5_request_manifest_binds_exact_flow_prompt_contract(tmp_path: Path):
    flow_prompts = {
        "episode_id": "HA002",
        "requests": [{
            "shot_id": "S1",
            "visual_mode": "historical_reconstruction",
            "semantic_anchors": ["palace gate"],
            "submission_prompt": "one palace gate",
            "positive_prompt": "one palace gate",
            "negative": {"mode": "prompt_exclusion", "items": []},
            "request_sha256": "REQUEST-HASH",
        }],
    }
    timing = {
        "shots": [{"shot_id": "S1", "order": 1, "start_sec": 0.0, "end_sec": 5.0, "duration_sec": 5.0}],
    }
    flow_path = tmp_path / "flow_image_prompts.json"
    flow_path.write_text(json.dumps(flow_prompts), encoding="utf-8")
    (tmp_path / "shot_timing_manifest.json").write_text(json.dumps(timing), encoding="utf-8")

    output = build_image_request_manifest(tmp_path)
    data = json.loads(output.read_text(encoding="utf-8"))

    assert data["contract_sha256"] == compute_file_sha256(flow_path)
    assert data["requests"][0]["request_sha256"] == "REQUEST-HASH"


def test_v5_falls_back_to_visual_brief_semantic_anchors_for_nollam_requests(
    tmp_path: Path,
):
    """2026-09-16 finding: compile_nollam_prompt()'s requests (unlike
    compile_aligned_prompt()'s) don't carry semantic_anchors at all, so a real
    nollam_file_v1 build hit a bare KeyError here. The anchors still exist one
    step upstream on the visual brief itself and must be threaded through."""
    flow_prompts = {
        "episode_id": "NOLLAM-TEST",
        "requests": [{
            "shot_id": "S1",
            "visual_mode": "historical_reconstruction",
            "submission_prompt": "a samurai courtyard",
            "positive_prompt": "a samurai courtyard",
            "negative": {"mode": "prompt_exclusion", "items": []},
            "request_sha256": "REQUEST-HASH",
        }],
    }
    timing = {
        "shots": [{"shot_id": "S1", "order": 1, "start_sec": 0.0, "end_sec": 5.0, "duration_sec": 5.0}],
    }
    brief_manifest = {
        "briefs": [
            {"shot_id": "S1", "semantic_anchors": ["lone samurai", "courtyard"]},
        ],
    }
    (tmp_path / "flow_image_prompts.json").write_text(json.dumps(flow_prompts), encoding="utf-8")
    (tmp_path / "shot_timing_manifest.json").write_text(json.dumps(timing), encoding="utf-8")
    (tmp_path / "visual_brief_manifest.json").write_text(json.dumps(brief_manifest), encoding="utf-8")

    output = build_image_request_manifest(tmp_path)
    data = json.loads(output.read_text(encoding="utf-8"))

    assert data["requests"][0]["semantic_anchors"] == ["lone samurai", "courtyard"]
