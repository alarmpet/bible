# -*- coding: utf-8 -*-
"""Unified Gate 0~5 physical verification test suite for Human Library 1:1 exact replication."""
import json
import sys
from pathlib import Path
import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.canonical_timeline_adapter import build_canonical_timeline
from lib.semantic_subtitle_engine import SemanticSubtitleEngine
from lib.subcut_montage_engine import plan_subcuts
from lib.audio_multitrack_mixer import build_3track_audio_command
from lib.branding_hud_overlay import build_branding_overlay_filtergraph
from postflight_release import ProductionProfile


def test_gate_0_duration_and_cfr_invariants():
    prof = ProductionProfile.from_fps(30)
    assert prof.fps == 30
    assert prof.samples_per_frame == 1600
    assert prof.window_size == 30
    assert prof.parity_tolerance_sec <= 0.034

    target_dur = 973.167
    total_frames = round(target_dur * prof.fps)
    assert total_frames == 29195

    # Parity Delta with 48kHz audio
    total_samples = total_frames * prof.samples_per_frame
    audio_dur = total_samples / 48000.0
    parity_delta = abs(target_dur - audio_dur)
    assert parity_delta <= 0.005, f"Gate 0 Parity Delta {parity_delta}s > 0.005s"


def test_gate_1_subtitles_ssot_and_no_zero_stacking():
    ass_path = Path(r"D:\module\bible\human_archive\runs\human_library_replica\rank1_race_adaptation\subtitles\rank1_exact_master_subtitles.ass")
    if not ass_path.exists():
        pytest.skip("Exact master subtitles ASS not yet compiled")

    res = SemanticSubtitleEngine.audit_ass_file(ass_path, max_line_chars=36)
    assert res["status"] == "PASS"
    assert res["violations_count"] == 0
    assert res["dialogue_events"] >= 346

    # Verify 0.0s stacking count is 0
    lines = [l for l in ass_path.read_text(encoding="utf-8").splitlines() if l.startswith("Dialogue:")]
    zero_starts = [l for l in lines if "0:00:00.00" in l]
    assert len(zero_starts) == 0, f"Detected {len(zero_starts)} dialogues starting at 0:00:00.00"

    # Verify yellow keyword highlighting tag presence
    yellow_lines = [l for l in lines if r"\c&H003BEBFF&" in l]
    assert len(yellow_lines) >= 50, f"Expected >= 50 yellow highlighted lines, got {len(yellow_lines)}"


def test_gate_2_2d_webtoon_prompt_aesthetic_hygiene():
    plan_path = Path(r"D:\module\bible\human_archive\runs\human_library_replica\rank1_race_adaptation\metadata\master_plates_composition_plan.json")
    if not plan_path.exists():
        pytest.skip("Master plates composition plan not found")

    with open(plan_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    plates = data.get("plates", [])
    assert len(plates) == 80, f"Expected 80 master plates, got {len(plates)}"

    banned_keywords = ["35mm film still", "Cooke anamorphic", "film grain", "Kodak 5219", "photorealistic", "35mm photograph"]
    for p in plates:
        prompt = p.get("flow_prompt_en", "").lower()
        assert "2d graphic novel illustration" in prompt, f"Plate {p['plate_id']} missing 2D graphic novel tag"
        assert "ligne claire" in prompt, f"Plate {p['plate_id']} missing ligne claire tag"
        for banned in banned_keywords:
            assert banned.lower() not in prompt, f"Plate {p['plate_id']} contains banned keyword: {banned}"


def test_gate_3_pacing_and_subcut_count():
    plan_path = Path(r"D:\module\bible\human_archive\runs\human_library_replica\rank1_race_adaptation\metadata\subcut_montage_plan.json")
    if not plan_path.exists():
        pytest.skip("Subcut montage plan not found")

    with open(plan_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cuts = data.get("cuts", [])
    assert 550 <= len(cuts) <= 600, f"Expected 550~600 cuts, got {len(cuts)}"
    assert sum(c["frame_count"] for c in cuts) == 29195

    # First 300s >= 180 cuts
    first_300s = [c for c in cuts if c["start_sec"] < 300.0]
    assert len(first_300s) >= 180


def test_gate_4_audio_multitrack_sidechain():
    cmd = build_3track_audio_command(
        voice_path=Path("voice.wav"),
        bgm_path=Path("bgm.wav"),
        output_path=Path("out.wav"),
        target_duration_sec=973.167,
    )
    cmd_str = " ".join(cmd)
    assert "sidechaincompress" in cmd_str
    assert "firequalizer" in cmd_str
    assert "loudnorm=I=-14" in cmd_str
    assert "apad=whole_dur=973.167" in cmd_str
    assert "-t 973.167" in cmd_str


def test_gate_5_branding_and_hud_assets():
    """Gate 5 originally verified that the *original YouTube channel's* watermark,
    emblem, and HUD-card PNGs were staged in the release-reachable
    assets/branding/ directory, per the 2026-09-11 "human-library-1to1-exact-
    replication" master plan's branding/HUD restoration item.

    That plan was withdrawn by docs/superpowers/plans/2026-09-15-human-archive-
    nollam-script-visual-motion-multi-llm-overhaul-plan.md section 6 point 2:
    cloning another channel's specific watermark/emblem/HUD design is exactly
    the kind of verbatim-replica artifact that must never reach a release
    path, so it orders the branding assets removed from assets/branding/
    immediately. Commit 88e4242 (Task 9) carried this out -- it relocated the
    four reference PNGs out of assets/branding/ into the gitignored,
    production-path-guarded
    research/human_library_benchmark_internal_only/
    reference_assets_do_not_use_in_production/ directory (see
    lib/production_path_guard.py) and left assets/branding/ empty.

    Gate 5's real invariant is therefore the inverse of what it originally
    checked: these four original-channel asset filenames must never reappear
    in the release-reachable assets/branding/ directory. This is a regression
    guard against someone re-adding the original channel's branding to a
    path the render/publish pipeline can actually pick up.
    """
    branding_dir = Path(r"D:\module\bible\human_archive\assets\branding")
    for name in ["golden_emblem_watermark.png", "laurel_wreath_opening.png", "ancient_spear_obsidian_hud.png", "epas1_dna_hud.png"]:
        p = branding_dir / name
        assert not p.exists(), (
            f"{p} must not exist: the original channel's branding asset was "
            "withdrawn from the release-reachable assets/branding/ directory "
            "by commit 88e4242 (see docs/superpowers/plans/2026-09-15-human-"
            "archive-nollam-script-visual-motion-multi-llm-overhaul-plan.md "
            "section 6 point 2). Its reference copy belongs only under "
            "research/human_library_benchmark_internal_only/"
            "reference_assets_do_not_use_in_production/."
        )
