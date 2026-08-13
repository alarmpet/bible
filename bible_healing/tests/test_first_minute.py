import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from first_minute import summarize_first_minute  # noqa: E402


def test_first_scripture_start_is_measured_from_locked_manifest():
    manifest = {
        "scenes": [
            {"order": 1, "startSeconds": 0.0, "endSeconds": 20.0},
            {"order": 2, "startSeconds": 20.0, "endSeconds": 48.0},
            {"order": 3, "startSeconds": 48.0, "endSeconds": 52.0},
            {"order": 4, "startSeconds": 52.0, "endSeconds": 80.0},
        ]
    }
    scenes = [
        {"order": 1, "meta": {"unit": "opening", "speaker": "narrator"}},
        {"order": 2, "meta": {"unit": "opening", "speaker": "narrator"}},
        {"order": 3, "meta": {"unit": "opening", "speaker": "narrator"}},
        {"order": 4, "meta": {"unit": "u01", "speaker": "scripture"}},
    ]

    result = summarize_first_minute(manifest, scenes)

    assert result["first_scripture_start_sec"] == 52.0
    assert result["first_scripture_in_target_window"] is True


def test_first_minute_reports_forbidden_copy_and_non_optional_breathing():
    manifest = {
        "scenes": [
            {"order": 1, "startSeconds": 0.0, "endSeconds": 5.0},
            {"order": 2, "startSeconds": 5.0, "endSeconds": 30.0},
            {"order": 3, "startSeconds": 30.0, "endSeconds": 48.0},
        ]
    }
    scenes = [
        {
            "order": 1,
            "narration": "반드시 잠들고 치유됩니다.",
            "meta": {"unit": "opening", "speaker": "narrator", "hook_phase": "hook"},
        },
        {
            "order": 2,
            "narration": "눈을 감고 깊게 숨 쉬세요. 다시 숨 쉬세요.",
            "meta": {"unit": "opening", "speaker": "narrator", "hook_phase": "mirror"},
        },
        {
            "order": 3,
            "narration": "이제 말씀을 읽겠습니다.",
            "meta": {"unit": "opening", "speaker": "narrator", "hook_phase": "permission_bridge"},
        },
    ]

    result = summarize_first_minute(manifest, scenes)

    assert "forbidden_claim_in_first_minute" in result["violations"]
    assert "breathing_instruction_not_optional" in result["violations"]


def test_first_minute_rejects_unknown_hook_phase():
    manifest = {"scenes": [{"order": 1, "startSeconds": 0.0, "endSeconds": 3.0}]}
    scenes = [
        {
            "order": 1,
            "meta": {"unit": "opening", "speaker": "narrator", "hook_phase": "teaser"},
        }
    ]

    with pytest.raises(ValueError, match="unknown hook_phase"):
        summarize_first_minute(manifest, scenes)
