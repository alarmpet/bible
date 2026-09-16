# -*- coding: utf-8 -*-
"""Regression tests for voice resolution in build_sentence_audio_master.py.

2026-09-16 finding: running a real nollam_file_v1 episode through the exact
CLI command CLAUDE.md section 4 Step 2 documents synthesized every sentence
with voice M4, not the mandated M2 (voice_lock_id: M2_WARM in both
channel_profiles.yaml and the episode's own script_candidate.json) -- the
function's only caller hardcoded "M4" whenever no --voice was given, and the
CLI never exposed a --voice/--voice-lock-id flag at all. No test ever
exercised this path.
"""
from __future__ import annotations

import sys
from pathlib import Path

_TEST_DIR = Path(__file__).resolve().parent
_SCRIPTS_DIR = _TEST_DIR.parents[1] / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from build_sentence_audio_master import _resolve_voice


def test_defaults_to_m4_when_nothing_declares_a_voice():
    assert _resolve_voice(None, None, {}) == "M4"


def test_resolves_from_script_own_voice_lock_id_field():
    assert _resolve_voice(None, None, {"voice_lock_id": "M2_WARM"}) == "M2"


def test_explicit_voice_lock_id_param_overrides_script_field():
    assert _resolve_voice(None, "F5_LESS_THIN", {"voice_lock_id": "M2_WARM"}) == "F5"


def test_explicit_voice_param_wins_over_everything():
    assert _resolve_voice("M3", "M2_WARM", {"voice_lock_id": "M2_WARM"}) == "M3"
