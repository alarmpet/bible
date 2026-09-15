import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(r"D:\module\bible\human_archive\scripts\render_himalaya_pilot_120s.py")


def load_renderer():
    spec = importlib.util.spec_from_file_location("himalaya_pilot_renderer", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_rejects_missing_images_instead_of_recycling_them():
    renderer = load_renderer()
    scenes = [{"shot_id": f"SHOT_{i:03d}", "duration_sec": 6.0} for i in range(1, 21)]
    images = [Path(f"SHOT_{i:03d}.jpg") for i in range(1, 13)]

    with pytest.raises(ValueError, match="missing.*8|requires.*20"):
        renderer.validate_pilot_inputs(scenes, images)


def test_rejects_duplicate_shot_ids_in_render_inputs():
    renderer = load_renderer()
    scenes = [
        {"shot_id": "SHOT_001", "duration_sec": 60.0},
        {"shot_id": "SHOT_001", "duration_sec": 60.0},
    ]
    images = [Path("SHOT_001.jpg"), Path("SHOT_002.jpg")]

    with pytest.raises(ValueError, match="duplicate"):
        renderer.validate_pilot_inputs(scenes, images)
