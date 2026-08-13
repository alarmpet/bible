import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from build_episode import opening_segment  # noqa: E402
from pack_to_hermes import scene_meta_from_segment  # noqa: E402


def test_opening_phase_survives_episode_build_and_hermes_pack():
    segment = opening_segment(
        {"speaker": "narrator", "text": "공감 문장", "hook_phase": "mirror"},
        2,
    )

    assert segment["seg_id"] == "open_02"
    assert segment["hook_phase"] == "mirror"
    assert scene_meta_from_segment(segment)["hook_phase"] == "mirror"
