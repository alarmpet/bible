# -*- coding: utf-8 -*-
"""Unit tests for branding and HUD overlay module."""
import sys
from pathlib import Path
import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.branding_hud_overlay import build_branding_overlay_filtergraph


def test_original_channel_branding_assets_absent_from_production_dir():
    """This test originally asserted that the *original YouTube channel's*
    watermark/emblem/HUD PNGs existed in the release-reachable
    assets/branding/ directory, per the withdrawn 2026-09-11
    "human-library-1to1-exact-replication" master plan.

    docs/superpowers/plans/2026-09-15-human-archive-nollam-script-visual-
    motion-multi-llm-overhaul-plan.md section 6 point 2 withdrew that plan and
    ordered the branding assets removed from assets/branding/ immediately, on
    the grounds that reproducing another channel's specific watermark/emblem/
    HUD design must never reach a release path. Commit 88e4242 (Task 9)
    relocated the four reference PNGs into the gitignored,
    production-path-guarded
    research/human_library_benchmark_internal_only/
    reference_assets_do_not_use_in_production/ directory instead (see
    lib/production_path_guard.py) and left assets/branding/ empty.

    The directory itself is kept (e.g. for this channel's own future
    branding); only the four original-channel filenames must never reappear
    there. This is a regression guard against someone re-adding the original
    channel's branding to a path the render/publish pipeline can actually
    pick up.
    """
    branding_dir = Path(r"D:\module\bible\human_archive\assets\branding")
    assert branding_dir.exists()

    emblem_p = branding_dir / "golden_emblem_watermark.png"
    wreath_p = branding_dir / "laurel_wreath_opening.png"
    hud1_p = branding_dir / "ancient_spear_obsidian_hud.png"
    hud2_p = branding_dir / "epas1_dna_hud.png"

    for p in [emblem_p, wreath_p, hud1_p, hud2_p]:
        assert not p.exists(), (
            f"{p} must not exist: withdrawn by commit 88e4242 per "
            "docs/superpowers/plans/2026-09-15-human-archive-nollam-script-"
            "visual-motion-multi-llm-overhaul-plan.md section 6 point 2."
        )


def test_build_branding_overlay_filtergraph(tmp_path):
    # Exercise the filtergraph-building logic in isolation with synthetic
    # fixture files (not the withdrawn original-channel branding assets --
    # see test_original_channel_branding_assets_absent_from_production_dir
    # above) so this unit test does not depend on assets that must not exist
    # in the repository.
    emblem_p = tmp_path / "emblem.png"
    wreath_p = tmp_path / "wreath.png"
    hud1_p = tmp_path / "hud1.png"
    hud2_p = tmp_path / "hud2.png"
    for p in [emblem_p, wreath_p, hud1_p, hud2_p]:
        p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 512)

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
