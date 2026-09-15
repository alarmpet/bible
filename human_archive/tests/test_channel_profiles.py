from __future__ import annotations

import sys
from pathlib import Path

import pytest


_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.channel_profiles import load_channel_profile


PROFILES = _PROJECT_ROOT / "human_archive" / "config" / "channel_profiles.yaml"


def test_nollam_is_default_and_legacy_profiles_are_selectable() -> None:
    nollam = load_channel_profile(PROFILES, "nollam_file_v1")
    assert nollam["is_default"] is True
    assert nollam["delivery_profile_id"] == "trend_explainer_20m"
    doodle = load_channel_profile(PROFILES, "doodle_seonbi_v1")
    assert doodle["is_default"] is False
    assert load_channel_profile(PROFILES, "human_archive_cinematic_v1")["is_default"] is False


def test_unknown_profile_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unknown channel profile"):
        load_channel_profile(PROFILES, "missing")
