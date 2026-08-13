import shutil
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from build_episode import opening_rows  # noqa: E402


TEST_ROOT = Path(__file__).resolve().parent / "_opening_override_fixture"


def test_episode_opening_override_is_selected_when_present():
    TEST_ROOT.mkdir(exist_ok=True)
    override = TEST_ROOT / "ep01.yaml"
    try:
        override.write_text(
            "opening:\n  - speaker: narrator\n    hook_phase: hook\n    text: 새 훅\n",
            encoding="utf-8",
        )
        rows = opening_rows({"opening": [{"speaker": "narrator", "text": "기존"}]}, override)
        assert rows[0]["text"] == "새 훅"
        assert rows[0]["hook_phase"] == "hook"
    finally:
        shutil.rmtree(TEST_ROOT, ignore_errors=True)
