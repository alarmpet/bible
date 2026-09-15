import importlib.util
from pathlib import Path

import pytest


GUARD = Path(r"D:\module\bible\human_archive\scripts\pilot_render_guard.py")


def load_guard():
    spec = importlib.util.spec_from_file_location("pilot_render_guard", GUARD)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_guard_rejects_missing_images():
    guard = load_guard()
    scenes = [{"shot_id": f"SHOT_{i:03d}"} for i in range(1, 21)]
    images = [Path(f"SHOT_{i:03d}.jpg") for i in range(1, 13)]
    with pytest.raises(ValueError, match="missing 8 images"):
        guard.validate_pilot_inputs(scenes, images)


def test_guard_rejects_duplicate_scene_ids():
    guard = load_guard()
    scenes = [{"shot_id": "SHOT_001"}, {"shot_id": "SHOT_001"}]
    images = [Path("SHOT_001.jpg"), Path("SHOT_002.jpg")]
    with pytest.raises(ValueError, match="duplicate"):
        guard.validate_pilot_inputs(scenes, images)
