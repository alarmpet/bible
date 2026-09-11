# -*- coding: utf-8 -*-
"""Unit tests for branding and HUD overlay module."""
import sys
from pathlib import Path
import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.branding_hud_overlay import build_branding_overlay_filtergraph


def test_branding_assets_exist():
    branding_dir = Path(r"D:\module\bible\human_archive\assets\branding")
    assert branding_dir.exists()

    emblem_p = branding_dir / "golden_emblem_watermark.png"
    wreath_p = branding_dir / "laurel_wreath_opening.png"
    hud1_p = branding_dir / "ancient_spear_obsidian_hud.png"
    hud2_p = branding_dir / "epas1_dna_hud.png"

    for p in [emblem_p, wreath_p, hud1_p, hud2_p]:
        assert p.exists(), f"Missing asset: {p}"
        assert p.stat().st_size > 500, f"Asset size too small: {p.stat().st_size} bytes"


def test_build_branding_overlay_filtergraph():
    branding_dir = Path(r"D:\module\bible\human_archive\assets\branding")
    emblem_p = branding_dir / "golden_emblem_watermark.png"
    wreath_p = branding_dir / "laurel_wreath_opening.png"
    hud1_p = branding_dir / "ancient_spear_obsidian_hud.png"
    hud2_p = branding_dir / "epas1_dna_hud.png"

    inputs, fg = build_branding_overlay_filtergraph(
        emblem_path=emblem_p,
        wreath_path=wreath_p,
        hud1_path=hud1_p,
        hud2_path=hud2_p,
        base_video_label="[v_in]",
        out_label="[v_out]",
    )

    assert len(inputs) == 8  # 4 x ("-i", path)
    assert "overlay=W-w-30:30" in fg
    assert "between(t,0,3.0)" in fg
    assert "between(t,6.5,15.0)" in fg
    assert "between(t,40.0,55.0)" in fg
    assert "[v_out]" in fg
