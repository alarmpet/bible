from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from lib.motion_engine_v3 import trajectory


def test_push_in_trajectory_is_monotonic_and_has_meaningful_delta():
    values = [trajectory(i, 100, "push_in") for i in range(100)]
    zooms = [value[0] for value in values]
    assert zooms[0] == 1.0
    assert zooms[-1] > 1.08
    assert all(a <= b for a, b in zip(zooms, zooms[1:]))
    assert max(zooms) - min(zooms) > 0.08


def test_static_trajectory_does_not_move():
    assert len(set(trajectory(i, 100, "static") for i in range(100))) == 1
