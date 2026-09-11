# -*- coding: utf-8 -*-
"""Integration tests for Human Library exact clone pipeline runner."""
import json
import sys
from pathlib import Path
import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from run_human_library_exact_clone_pipeline import (
    EP_DIR,
    METADATA_DIR,
    SUBTITLES_DIR,
    BRANDING_DIR,
    CANONICAL_MANIFEST_PATH,
    SUBCUT_PLAN_PATH,
    PLATES_PLAN_PATH,
    ASS_PATH,
    build_cinema_filtergraph,
    build_master_audio_command,
    get_ffprobe_info,
    resolve_plate_image,
    validate_master_plate_plan,
    step_4_verify_postflight,
)


def test_pipeline_essential_contracts_exist():
    assert CANONICAL_MANIFEST_PATH.exists(), "Canonical timeline manifest missing"
    assert SUBCUT_PLAN_PATH.exists(), "Subcut montage plan missing"
    assert PLATES_PLAN_PATH.exists(), "Master plates plan missing"
    assert ASS_PATH.exists(), "Exact subtitles ASS missing"

    # Branding assets
    for name in ["golden_emblem_watermark.png", "laurel_wreath_opening.png", "ancient_spear_obsidian_hud.png", "epas1_dna_hud.png"]:
        p = BRANDING_DIR / name
        assert p.exists(), f"Branding asset {name} missing"


def test_subcut_plan_contract_frame_count():
    import json
    with open(SUBCUT_PLAN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    cuts = data.get("cuts", [])
    assert 550 <= len(cuts) <= 600
    assert sum(c["frame_count"] for c in cuts) == 29195


def test_missing_ab_plate_fails_closed_instead_of_parent_fallback(tmp_path):
    with pytest.raises(FileNotFoundError, match="SHOT_001_A"):
        resolve_plate_image(
            plate_id="SHOT_001_A",
            parent_shot_id="SHOT_001",
            plates_dir=tmp_path,
            fallback_images_dir=tmp_path,
        )


def test_clean_profile_does_not_add_branding_inputs():
    extra_inputs, filtergraph = build_cinema_filtergraph(
        ass_subtitles=Path("subtitles.ass"),
        include_branding=False,
    )
    assert extra_inputs == []
    assert "golden_emblem" not in filtergraph
    assert "overlay" not in filtergraph
    assert "ass=" in filtergraph


def test_audio_command_binds_exact_sample_boundary():
    command = build_master_audio_command(
        original_mp4=Path("original.mp4"),
        output_path=Path("audio.wav"),
        sample_count=46_711_584,
    )
    command_text = " ".join(command)
    assert "-frames:a 46711584" in command_text
    assert "-t 973.167" not in command_text


def test_ffprobe_collection_includes_average_frame_rate():
    probe = get_ffprobe_info(
        Path(
            r"D:\module\bible\human_archive\runs\human_library_replica\rank1_race_adaptation\rank1_exact_master_documentary.mp4"
        )
    )
    video = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    assert video["avg_frame_rate"] == "30/1"


def test_master_plate_plan_validation_is_fail_closed(tmp_path):
    plan = tmp_path / "plates.json"
    plan.write_text(json.dumps({"plates": [{"plate_id": "SHOT_001_A"}]}), encoding="utf-8")

    result = validate_master_plate_plan(plan, expected_count=1)

    assert result["status"] == "FAIL"
    assert any("path" in error for error in result["errors"])
