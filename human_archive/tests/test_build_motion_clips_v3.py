# -*- coding: utf-8 -*-
"""classify_motion_intent must never fall back to a round-robin rotation -- the legacy
defect (SHOT_MOTION_MAP id mismatch -> 100% of shots hit `idx % 4`) is fixed by having
no index-based fallback at all: an unmatched shot gets `static`, always the same,
correct-by-definition choice."""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from build_motion_clips_v3 import classify_motion_intent  # noqa: E402


def test_explicit_motion_intent_is_used_as_is():
    assert classify_motion_intent({"motion_intent": "pan_left"}) == "pan_left"


def test_invalid_explicit_motion_intent_is_not_trusted_blindly():
    assert classify_motion_intent({"motion_intent": "not_a_real_intent",
                                    "display_text": "평범한 문장입니다."}) == "static"


def test_unmatched_text_falls_back_to_static_not_a_rotation():
    """The critical regression test: no matter the shot index, an unmatched sentence
    must always resolve to the same answer (static), never a cycling preset."""
    results = {classify_motion_intent({"display_text": "평범한 서술 문장입니다."})
               for _ in range(10)}
    assert results == {"static"}


def test_keyword_match_selects_a_specific_intent():
    assert classify_motion_intent({"display_text": "화산이 크게 분연을 뿜었다."}) == "tilt_up"
    assert classify_motion_intent({"narration": "거대한 도시 전경이 펼쳐진다."}) == "pan_right"


def test_narration_and_tts_text_are_also_checked():
    assert classify_motion_intent({"tts_text": "오래된 건물이 완전히 매몰되었다."}) == "pull_out"
