# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path
import pytest

from lib.cinematic_effect_planner import resolve_render_motion

def test_canonical_renderer_binding_39_shots_diversity():
    manifest_path = Path(__file__).resolve().parents[1] / "runs" / "nollam_file" / "2026-09-09" / "iceage-neanderthal-sapiens-extinction" / "release_manifest_v4.json"
    assert manifest_path.exists(), f"Missing manifest: {manifest_path}"
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    shots = data.get("shots", [])
    assert len(shots) == 39
    
    resolved_motions = []
    for s in shots:
        eff = s.get("editing_effect", "")
        dur = float(s.get("scene_duration", 10.0))
        mot = resolve_render_motion(eff, dur, planned=s)
        resolved_motions.append(mot)
        
    # Crucial assertion: 39 shots must NOT all be push_in!
    unique_motions = set(resolved_motions)
    assert len(unique_motions) >= 4, f"Insufficient motion diversity: {unique_motions}"
    assert "push_in" in unique_motions
    assert "pan_right" in unique_motions or "pan_left" in unique_motions
    assert "tri_phasic" in unique_motions
    
    # Check that push_in count is less than 50% of total
    push_in_count = resolved_motions.count("push_in")
    assert push_in_count < 20, f"Too many push_in fallbacks: {push_in_count}/39"
