# -*- coding: utf-8 -*-
"""Integration tests for Human Library exact clone pipeline runner."""
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
