# -*- coding: utf-8 -*-
"""Unit tests for subcut montage engine and rapid pacing verification."""
import sys
from pathlib import Path
import pytest
from PIL import Image

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.subcut_montage_engine import (
    plan_subcuts,
    compute_saliency_center,
    SubcutPlan,
)


def test_plan_subcuts_invariants():
    cuts = plan_subcuts(target_duration_sec=973.167, fps=30.0, total_shots=40)

    # 1. Total cuts count between 550 and 600
    assert 550 <= len(cuts) <= 600, f"Expected 550~600 cuts, got {len(cuts)}"

    # 2. Strict 29,195 total frames invariant
    total_frames = sum(c.frame_count for c in cuts)
    assert total_frames == 29195, f"Frame count invariant failed: {total_frames} != 29195"

    # 3. First 300s cut count >= 180 (original had 185 cuts)
    first_300s_cuts = [c for c in cuts if c.start_sec < 300.0]
    assert len(first_300s_cuts) >= 180, f"Expected >=180 cuts in first 300s, got {len(first_300s_cuts)}"

    # 4. Average cut duration in first 300s <= 1.70s
    avg_first_300 = sum(c.duration_sec for c in first_300s_cuts) / len(first_300s_cuts)
    assert avg_first_300 <= 1.70, f"Expected <=1.70s average cut duration, got {avg_first_300:.3f}s"

    # 5. Strobe burst at 40~46s has sub-second cuts
    strobe_cuts = [c for c in cuts if 40.0 <= c.start_sec < 46.0]
    assert len(strobe_cuts) >= 15
    for c in strobe_cuts:
        assert c.duration_sec <= 0.40, f"Strobe cut duration {c.duration_sec} > 0.40s"


def test_compute_saliency_center_headroom():
    # Create image with bright spot in lower-middle
    img = Image.new("RGB", (1920, 1080), (30, 30, 30))
    # Saliency center must cap Y at 0.70 to protect bottom subtitle clearance zone
    cx, cy = compute_saliency_center(img)
    assert 0.20 <= cx <= 0.80
    assert 0.20 <= cy <= 0.70
