import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from build_full_job import scene_from_segment  # noqa: E402


def test_full_job_scene_preserves_hook_phase():
    scene = scene_from_segment(
        {"seg_id": "open_01", "unit": "opening", "speaker": "narrator", "text": "훅", "hook_phase": "hook"},
        1,
    )
    assert scene["meta"]["hook_phase"] == "hook"
