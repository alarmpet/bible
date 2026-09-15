# -*- coding: utf-8 -*-
"""Test TTS provenance and audio duration consistency."""
from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.tts_provider import validate_audio_provenance


def test_release_rejects_tone_fixture():
    audio_manifest = {
        "ok": True,
        "provenance": {"audio_kind": "tone_fixture"},
    }
    errors = validate_audio_provenance(audio_manifest, publishable=True)
    assert any("non-speech fixture" in err for err in errors)
