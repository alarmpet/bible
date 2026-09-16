# -*- coding: utf-8 -*-
"""classify_motion_intent must never fall back to a round-robin rotation -- the legacy
defect (SHOT_MOTION_MAP id mismatch -> 100% of shots hit `idx % 4`) is fixed by having
no index-based fallback at all: an unmatched shot gets `static`, always the same,
correct-by-definition choice."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from build_motion_clips_v3 import _load_shot_durations, classify_motion_intent  # noqa: E402


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


def test_general_history_keyword_buckets_added_for_non_disaster_topics(tmp_path=None):
    """2026-09-16 finding: the original 4 buckets were tuned for disaster/
    archaeology scripts and left a real general-history episode
    (samurai/bushido) at 19/24 shots static -- not because static was the
    right call, but because none of its narration matched any bucket."""
    assert classify_motion_intent({"display_text": "치열한 전투 끝에 성이 함락되었다."}) == "push_in"
    assert classify_motion_intent({"display_text": "숨겨졌던 진실이 마침내 밝혀졌다."}) == "push_in"
    assert classify_motion_intent({"display_text": "진홍색 예복과 갑옷이 전시돼 있다."}) == "detail_crop"
    assert classify_motion_intent({"display_text": "메이지 유신 이후 새로운 시대가 열렸다."}) == "pan_left"


def test_narration_and_tts_text_are_also_checked():
    assert classify_motion_intent({"tts_text": "오래된 건물이 완전히 매몰되었다."}) == "pull_out"


def test_shot_durations_prefer_shot_timing_manifest_over_legacy_scene_audio(tmp_path):
    """2026-09-16 finding from a real nollam_file_v1 build: this used to look
    ONLY for scene_audio_manifest.json (an older ep01/ep02 doodle_seonbi_v1
    shape). A real nollam_file_v1 build writes shot_timing_manifest.json
    instead -- duration lookup silently stayed empty and every shot fell back
    to a hardcoded 6.0s default (verified live: 24 shots with real durations
    from 4.2s to 11.1s all rendered as exactly 6.00s)."""
    (tmp_path / "shot_timing_manifest.json").write_text(
        json.dumps({"shots": [
            {"shot_id": "S1", "duration_sec": 4.249},
            {"shot_id": "S2", "duration_sec": 11.147},
        ]}),
        encoding="utf-8",
    )
    durations = _load_shot_durations(tmp_path)
    assert durations == {"S1": 4.249, "S2": 11.147}


def test_shot_durations_fall_back_to_legacy_scene_audio_manifest(tmp_path):
    """Older ep01/ep02 doodle_seonbi_v1 builds only ever had
    scene_audio_manifest.json -- that path must keep working exactly as
    before when shot_timing_manifest.json doesn't exist."""
    (tmp_path / "scene_audio_manifest.json").write_text(
        json.dumps({
            "total_duration_sec": 15.0,
            "shots": [
                {"shot_id": "S1", "startSeconds": 0.0},
                {"shot_id": "S2", "startSeconds": 5.0},
                {"shot_id": "S3", "startSeconds": 9.0},
            ],
        }),
        encoding="utf-8",
    )
    durations = _load_shot_durations(tmp_path)
    assert durations == {"S1": 5.0, "S2": 4.0, "S3": 6.0}


def test_shot_durations_empty_when_neither_file_exists(tmp_path):
    assert _load_shot_durations(tmp_path) == {}


# --- 2026-09-16: camera text as primary motion source, Hard Gate 5 ramp, focal anchor ---

from build_motion_clips_v3 import (  # noqa: E402
    classify_camera_axis, derive_focal_anchor, resolve_shot_motion,
)
from lib.motion_engine_v3 import ramp_frac_for_duration  # noqa: E402

import pytest  # noqa: E402


@pytest.mark.parametrize("camera,scale,expected", [
    # verbatim camera strings from the samurai-bushido-myth-v1 briefs
    ("slow forward dolly from a distant profile", "wide full-body", "push_in"),
    ("slow upward tilt from the timber roofs to the defender", "wide full-body", "tilt_up"),
    ("slow retreat through the gallery", "wide closing view", "pull_out"),
    ("slow push toward the blank closed cover", "close artifact view", "detail_crop"),
    ("slow controlled push across the textile", "close artifact view", "detail_crop"),
    ("quiet character follow from behind and side", "medium full-body", "push_in"),
    ("slow reveal from the sword toward the mounted archer", "medium wide", "pull_out"),
    ("slow pan left across the wall", "medium wide", "pan_left"),
    ("slow lateral track to the right", "wide", "pan_right"),
])
def test_camera_text_maps_to_axis(camera, scale, expected):
    assert classify_camera_axis(camera, scale, shot_order=1) == expected


def test_directionless_lateral_moves_alternate_by_shot_order():
    assert classify_camera_axis("slow lateral orbit", "", shot_order=2) == "pan_left"
    assert classify_camera_axis("slow lateral orbit", "", shot_order=3) == "pan_right"


def test_arc_matches_as_word_not_substring():
    assert classify_camera_axis("slow search of the archive", "", 1) is None


def test_camera_text_outranks_narration_keywords():
    """Shot 1 regression: narration keywords used to leave the opening hook static even
    though its brief said 'slow forward dolly'."""
    item = {"display_text": "평범한 서술 문장입니다."}
    brief = {"camera": "slow forward dolly from a distant profile", "shot_scale": "wide full-body",
             "motion_profile": "reenactment_push"}
    assert resolve_shot_motion(item, brief, 1) == ("push_in", "camera")


def test_motion_profile_is_only_a_fallback_when_camera_is_unparseable():
    brief = {"camera": "locked-off frame", "motion_profile": "artifact_close_push"}
    assert resolve_shot_motion({}, brief, 1) == ("detail_crop", "motion_profile")


def test_explicit_intent_still_wins_over_brief():
    brief = {"camera": "slow forward dolly"}
    assert resolve_shot_motion({"motion_intent": "static"}, brief, 1) == ("static", "explicit")


def test_no_brief_falls_back_to_keyword_then_static():
    assert resolve_shot_motion({"display_text": "평범한 문장."}, None, 1) == ("static", "default_static")


@pytest.mark.parametrize("duration", [2.5, 6.69, 12.4])
def test_ramp_is_fixed_seconds_within_hard_gate_5(duration):
    ramp_sec = ramp_frac_for_duration(duration) * duration
    assert 0.2 <= ramp_sec <= 0.4


def test_ramp_frac_clamped_for_very_short_shots():
    assert ramp_frac_for_duration(0.4) == 0.49
    assert ramp_frac_for_duration(0.0) == 0.0


def test_focal_anchor_biases_up_for_full_body_and_centers_otherwise():
    assert derive_focal_anchor("wide full-body ensemble") == (0.5, 0.42)
    assert derive_focal_anchor("close artifact view") is None
    assert derive_focal_anchor("") is None
