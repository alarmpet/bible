from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from smooth_subpixel_motion_engine import compute_biphasic_trajectory
from smooth_subpixel_motion_engine import compute_tri_phasic_trajectory
from smooth_subpixel_motion_engine import compute_trajectory


def trajectory(frame: int, total_frames: int, motion: str = "push_in") -> tuple[float, float, float]:
    """Compatibility adapter backed by the canonical smooth motion engine."""
    if motion == "diagonal_drift":
        motion = "push_in"
    if motion in {"tri_phasic", "tri_phasic_ken_burns", "long_take_tri_phasic"}:
        return compute_tri_phasic_trajectory(frame, total_frames)
    if motion in {"biphasic_ken_burns", "biphasic_push_in"}:
        return compute_biphasic_trajectory(frame, total_frames, "push_in")
    if motion == "zoom_out":
        motion = "pull_out"
    return compute_trajectory(frame, total_frames, motion)

