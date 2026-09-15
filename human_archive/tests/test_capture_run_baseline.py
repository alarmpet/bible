# -*- coding: utf-8 -*-
"""Test baseline capture and verification for Pompeii episode 1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import pytest

# Add human_archive/scripts to sys.path
_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from capture_run_baseline import capture_baseline, verify_baseline, compute_file_sha256


def test_rejects_output_inside_run_root(tmp_path: Path):
    run_root = tmp_path / "run_root"
    run_root.mkdir()
    inside_output = run_root / "baseline.json"

    with pytest.raises(ValueError, match="Output path cannot be inside the run root"):
        capture_baseline(
            run_root=run_root,
            code_roots=[],
            output_path=inside_output,
        )


def test_captures_inventory_recursively(tmp_path: Path):
    run_root = tmp_path / "run_root"
    run_root.mkdir()
    sub_dir = run_root / "images"
    sub_dir.mkdir()
    (sub_dir / "shot_01.jpg").write_bytes(b"fake_image_bytes")
    (run_root / "script.json").write_text('{"title": "test"}', encoding="utf-8")

    out_file = tmp_path / "baseline.json"
    result = capture_baseline(
        run_root=run_root,
        code_roots=[],
        output_path=out_file,
    )

    assert out_file.exists()
    assert result["run_root_summary"]["total_files"] == 2
    items = {item["relative_path"]: item for item in result["run_inventory"]}
    assert "images/shot_01.jpg" in items
    assert items["images/shot_01.jpg"]["bytes"] == len(b"fake_image_bytes")
    assert items["images/shot_01.jpg"]["sha256"] == compute_file_sha256(sub_dir / "shot_01.jpg")


def test_verify_baseline_detects_mutation(tmp_path: Path):
    run_root = tmp_path / "run_root"
    run_root.mkdir()
    target_file = run_root / "data.txt"
    target_file.write_text("initial content", encoding="utf-8")

    out_file = tmp_path / "baseline.json"
    capture_baseline(
        run_root=run_root,
        code_roots=[],
        output_path=out_file,
    )

    # Verify pass when unchanged
    assert verify_baseline(run_root=run_root, code_roots=[], baseline_file=out_file) is True

    # Mutate file and verify failure
    target_file.write_text("mutated content", encoding="utf-8")
    assert verify_baseline(run_root=run_root, code_roots=[], baseline_file=out_file) is False


def test_actual_pompeii_baseline_exists_and_matches():
    run_root = _PROJECT_ROOT / "human_archive" / "runs" / "ep01_pompeii_18hours"
    baseline_path = _PROJECT_ROOT / "human_archive" / "audits" / "ep01_pompeii_18hours_2026-08-21" / "baseline.json"
    
    if not baseline_path.exists():
        pytest.skip("baseline.json not yet generated for actual run")

    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    final_info = data.get("final_media_info", {})
    expected_sha = "DA91A7F62549B24434D9EDE94E55EEEE9E3287D871815E3618A7DDD649455BC9"
    assert final_info.get("sha256", "").upper() == expected_sha
