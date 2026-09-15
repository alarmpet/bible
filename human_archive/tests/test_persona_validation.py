# -*- coding: utf-8 -*-
"""Test ShipSeonbi persona and 5-stage story beat validation."""
from __future__ import annotations

import copy
import sys
from pathlib import Path
import pytest
import yaml

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.persona_validation import validate_persona


@pytest.fixture
def policy():
    p_path = _PROJECT_ROOT / "human_archive" / "config" / "seonbi_narration_policy.yaml"
    return yaml.safe_load(p_path.read_text(encoding="utf-8"))


@pytest.fixture
def valid_script():
    return {
        "schema_version": 2,
        "episode_id": "HA001",
        "persona": "ship_seonbi",
        "title": "폼페이 최후의 밤",
        "target_duration_sec": 930,
        "sentences": [
            {
                "sentence_id": "s-01",
                "beat": "hook",
                "display_text": "다들 폼페이 사람이 다 죽은 줄 아시지요? 허허, 천만의 말씀!",
                "segments": [{"kind": "fact", "text": "..."}],
            },
            {
                "sentence_id": "s-02",
                "beat": "roadmap",
                "display_text": "오늘 선비와 함께 3가지 진실을 파헤쳐 보시지요!",
                "segments": [{"kind": "transition", "text": "..."}],
            },
            {
                "sentence_id": "s-03",
                "beat": "body",
                "display_text": "초기에 수많은 시민들은 대피에 성공했답니다.",
                "segments": [{"kind": "fact", "text": "..."}],
            },
            {
                "sentence_id": "s-04",
                "beat": "analogy",
                "display_text": "쉽게 말해 지붕 위에 덤프트럭이 올라앉은 꼴이지요.",
                "segments": [{"kind": "analogy", "text": "..."}],
            },
            {
                "sentence_id": "s-05",
                "beat": "source_commentary",
                "display_text": "사료를 보면 소 플리니우스가 붓을 쥐고 기록했답니다.",
                "segments": [{"kind": "direct_quote", "text": "..."}],
            },
            {
                "sentence_id": "s-06",
                "beat": "insight",
                "display_text": "재난 앞 인간의 선택은 오늘날 우리에게 묵직한 질문을 던집니다.",
                "segments": [{"kind": "insight", "text": "..."}],
            },
            {
                "sentence_id": "s-07",
                "beat": "outro",
                "display_text": "다음에도 귀에 쏙 박히는 역사로 찾아오지요!",
                "segments": [{"kind": "transition", "text": "..."}],
            },
        ],
    }


def test_rejects_signature_without_five_stage_structure(valid_script, policy):
    bad_script = copy.deepcopy(valid_script)
    bad_script["sentences"] = [bad_script["sentences"][0]]
    report = validate_persona(bad_script, policy)
    assert report["overall_status"] == "FAIL"
    assert any("missing beat: roadmap" in err for err in report["errors"])


def test_timing_requires_audio_measurement(valid_script, policy):
    report = validate_persona(valid_script, policy, audio_manifest=None)
    assert report["timing_status"] == "REVIEW_REQUIRED"


def test_current_sentence_audio_rows_measure_both_boundaries(valid_script, policy):
    test_policy = copy.deepcopy(policy)
    test_policy["story"]["hook_end_sec_max"] = 10.0
    test_policy["story"]["roadmap_end_sec_max"] = 20.0
    audio_manifest = {
        "sentences": [
            {"sentence_id": "s-01", "start_sec": 0.0, "end_sec": 9.5, "beat": "hook"},
            {"sentence_id": "s-02", "start_sec": 9.5, "end_sec": 19.5, "beat": "roadmap"},
            {"sentence_id": "s-03", "start_sec": 19.5, "end_sec": 29.5, "beat": "body"},
            {"sentence_id": "s-04", "start_sec": 29.5, "end_sec": 39.5, "beat": "analogy"},
            {"sentence_id": "s-05", "start_sec": 39.5, "end_sec": 49.5, "beat": "source_commentary"},
            {"sentence_id": "s-06", "start_sec": 49.5, "end_sec": 59.5, "beat": "insight"},
            {"sentence_id": "s-07", "start_sec": 59.5, "end_sec": 69.5, "beat": "outro"},
        ]
    }

    report = validate_persona(valid_script, test_policy, audio_manifest)

    assert report["overall_status"] == "PASS"
    assert report["timing_status"] == "PASS"
    assert report["timing_checks"] == {
        "hook_end_sec": 9.5,
        "hook_end_sec_max": 10.0,
        "roadmap_end_sec": 19.5,
        "roadmap_end_sec_max": 20.0,
    }


def test_later_hook_sentence_controls_hook_boundary(valid_script, policy):
    test_policy = copy.deepcopy(policy)
    test_policy["story"]["hook_end_sec_max"] = 10.0
    test_policy["story"]["roadmap_end_sec_max"] = 20.0
    later_hook = {
        "sentence_id": "s-08",
        "beat": "hook",
        "display_text": "뒤늦은 훅입니다.",
        "segments": [{"kind": "fact", "text": "..."}],
    }
    script = copy.deepcopy(valid_script)
    script["sentences"].append(later_hook)
    audio_manifest = {
        "sentences": [
            {"sentence_id": "s-01", "start_sec": 0.0, "end_sec": 9.0, "beat": "hook"},
            {"sentence_id": "s-08", "start_sec": 9.0, "end_sec": 10.5, "beat": "hook"},
            {"sentence_id": "s-02", "start_sec": 10.5, "end_sec": 19.0, "beat": "roadmap"},
        ]
    }

    report = validate_persona(script, test_policy, audio_manifest)

    assert report["overall_status"] == "FAIL"
    assert report["timing_status"] == "FAIL"
    assert any("Hook exceeded max time (10.5s > 10.0s)" in err for err in report["errors"])


def test_roadmap_boundary_exceeding_maximum_fails(valid_script, policy):
    test_policy = copy.deepcopy(policy)
    test_policy["story"]["hook_end_sec_max"] = 10.0
    test_policy["story"]["roadmap_end_sec_max"] = 20.0
    audio_manifest = {
        "sentences": [
            {"sentence_id": "s-01", "start_sec": 0.0, "end_sec": 9.0, "beat": "hook"},
            {"sentence_id": "s-02", "start_sec": 9.0, "end_sec": 20.5, "beat": "roadmap"},
        ]
    }

    report = validate_persona(valid_script, test_policy, audio_manifest)

    assert report["overall_status"] == "FAIL"
    assert report["timing_status"] == "FAIL"
    assert any("Roadmap exceeded max time (20.5s > 20.0s)" in err for err in report["errors"])


@pytest.mark.parametrize("audio_manifest", [{}, {"shots": []}, {"unrecognized": []}])
def test_unusable_non_null_manifest_requires_review(valid_script, policy, audio_manifest):
    report = validate_persona(valid_script, policy, audio_manifest)

    assert report["timing_status"] == "REVIEW_REQUIRED"
    assert report["overall_status"] == "REVIEW_REQUIRED"


@pytest.mark.parametrize("audio_manifest", [[], "invalid", 123])
def test_non_dict_manifest_requires_review(valid_script, policy, audio_manifest):
    report = validate_persona(valid_script, policy, audio_manifest)

    assert report["timing_status"] == "REVIEW_REQUIRED"
    assert report["overall_status"] == "REVIEW_REQUIRED"


@pytest.mark.parametrize("container_name", ["sentences", "shots"])
def test_null_timing_container_requires_review(valid_script, policy, container_name):
    report = validate_persona(valid_script, policy, {container_name: None})

    assert report["timing_status"] == "REVIEW_REQUIRED"
    assert report["overall_status"] == "REVIEW_REQUIRED"


@pytest.mark.parametrize(
    "audio_manifest",
    [
        {"sentences": {}},
        {"sentences": "invalid"},
        {"sentences": 123},
        {"shots": {}},
        {"shots": "invalid"},
        {"shots": 123},
    ],
)
def test_non_list_timing_container_requires_review(valid_script, policy, audio_manifest):
    report = validate_persona(valid_script, policy, audio_manifest)

    assert report["timing_status"] == "REVIEW_REQUIRED"
    assert report["overall_status"] == "REVIEW_REQUIRED"


@pytest.mark.parametrize(
    "audio_manifest",
    [
        {
            "sentences": [
                {"sentence_id": "s-01", "end_sec": 9.0},
                {"sentence_id": "s-02", "end_sec": 19.0},
                None,
            ]
        },
        {
            "sentences": [
                {"sentence_id": "s-01", "end_sec": 9.0},
                {"sentence_id": "s-02", "end_sec": 19.0},
                {"sentence_id": "s-03", "end_sec": "29.0"},
            ]
        },
        {
            "shots": [
                {"shot_id": "s-01", "endSeconds": 9.0},
                {"shot_id": "s-02", "endSeconds": 19.0},
                [],
            ]
        },
        {
            "shots": [
                {"shot_id": "s-01", "endSeconds": 9.0},
                {"shot_id": "s-02", "endSeconds": 19.0},
                {"shot_id": "s-03", "endSeconds": True},
            ]
        },
    ],
)
def test_malformed_timing_rows_require_review(valid_script, policy, audio_manifest):
    test_policy = copy.deepcopy(policy)
    test_policy["story"]["hook_end_sec_max"] = 10.0
    test_policy["story"]["roadmap_end_sec_max"] = 20.0

    report = validate_persona(valid_script, test_policy, audio_manifest)

    assert report["timing_status"] == "REVIEW_REQUIRED"
    assert report["overall_status"] == "REVIEW_REQUIRED"


@pytest.mark.parametrize(
    "audio_manifest",
    [
        {
            "sentences": [
                {"sentence_id": "s-01", "end_sec": "9.0"},
                {"sentence_id": "s-02", "end_sec": 19.0},
            ]
        },
        {
            "shots": [
                {"shot_id": "s-01", "endSeconds": 9.0},
                {"shot_id": "s-02", "endSeconds": None},
            ]
        },
    ],
)
def test_nonnumeric_required_boundary_requires_review(valid_script, policy, audio_manifest):
    report = validate_persona(valid_script, policy, audio_manifest)

    assert report["timing_status"] == "REVIEW_REQUIRED"
    assert report["overall_status"] == "REVIEW_REQUIRED"


def test_empty_current_sentence_manifest_requires_review(valid_script, policy):
    report = validate_persona(valid_script, policy, {"sentences": []})

    assert report["timing_status"] == "REVIEW_REQUIRED"
    assert report["overall_status"] == "REVIEW_REQUIRED"


@pytest.mark.parametrize(
    ("row", "expected_checks"),
    [
        (
            {"sentence_id": "s-01", "end_sec": 9.0},
            {
                "hook_end_sec_max": 10.0,
                "roadmap_end_sec_max": 20.0,
                "hook_end_sec": 9.0,
            },
        ),
        (
            {"sentence_id": "s-02", "end_sec": 19.0},
            {
                "hook_end_sec_max": 10.0,
                "roadmap_end_sec_max": 20.0,
                "roadmap_end_sec": 19.0,
            },
        ),
    ],
)
def test_one_current_boundary_requires_review(
    valid_script,
    policy,
    row,
    expected_checks,
):
    test_policy = copy.deepcopy(policy)
    test_policy["story"]["hook_end_sec_max"] = 10.0
    test_policy["story"]["roadmap_end_sec_max"] = 20.0

    report = validate_persona(valid_script, test_policy, {"sentences": [row]})

    assert report["timing_status"] == "REVIEW_REQUIRED"
    assert report["overall_status"] == "REVIEW_REQUIRED"
    assert report["timing_checks"] == expected_checks


def test_valid_legacy_shots_measure_both_boundaries(valid_script, policy):
    test_policy = copy.deepcopy(policy)
    test_policy["story"]["hook_end_sec_max"] = 10.0
    test_policy["story"]["roadmap_end_sec_max"] = 20.0
    audio_manifest = {
        "shots": [
            {"shot_id": "s-01", "endSeconds": 9.0},
            {"shot_id": "s-02", "endSeconds": 19.0},
        ]
    }

    report = validate_persona(valid_script, test_policy, audio_manifest)

    assert report["timing_status"] == "PASS"
    assert report["overall_status"] == "PASS"
    assert report["timing_checks"] == {
        "hook_end_sec_max": 10.0,
        "roadmap_end_sec_max": 20.0,
        "hook_end_sec": 9.0,
        "roadmap_end_sec": 19.0,
    }


def test_legacy_end_seconds_is_not_shadowed_by_conflicting_end_sec(valid_script, policy):
    test_policy = copy.deepcopy(policy)
    test_policy["story"]["hook_end_sec_max"] = 10.0
    test_policy["story"]["roadmap_end_sec_max"] = 20.0
    audio_manifest = {
        "shots": [
            {"shot_id": "s-01", "endSeconds": 9.0, "end_sec": None},
            {"shot_id": "s-02", "endSeconds": 19.0},
        ]
    }

    report = validate_persona(valid_script, test_policy, audio_manifest)

    assert report["timing_status"] == "PASS"
    assert report["overall_status"] == "PASS"
    assert report["timing_checks"] == {
        "hook_end_sec_max": 10.0,
        "roadmap_end_sec_max": 20.0,
        "hook_end_sec": 9.0,
        "roadmap_end_sec": 19.0,
    }


def test_later_roadmap_sentence_controls_roadmap_boundary(valid_script, policy):
    test_policy = copy.deepcopy(policy)
    test_policy["story"]["hook_end_sec_max"] = 10.0
    test_policy["story"]["roadmap_end_sec_max"] = 20.0
    script = copy.deepcopy(valid_script)
    script["sentences"].append(
        {
            "sentence_id": "s-08",
            "beat": "roadmap",
            "display_text": "마지막 길잡이입니다.",
            "segments": [{"kind": "transition", "text": "..."}],
        }
    )
    audio_manifest = {
        "sentences": [
            {"sentence_id": "s-01", "end_sec": 9.0},
            {"sentence_id": "s-02", "end_sec": 19.0},
            {"sentence_id": "s-08", "end_sec": 20.5},
        ]
    }

    report = validate_persona(script, test_policy, audio_manifest)

    assert report["timing_status"] == "FAIL"
    assert report["overall_status"] == "FAIL"
    assert any("Roadmap exceeded max time (20.5s > 20.0s)" in err for err in report["errors"])


@pytest.mark.parametrize(
    ("audio_manifest", "expected_error", "measured_key", "measured_end"),
    [
        (
            {"sentences": [{"sentence_id": "s-01", "end_sec": 10.5}]},
            "Hook exceeded max time (10.5s > 10.0s)",
            "hook_end_sec",
            10.5,
        ),
        (
            {"sentences": [{"sentence_id": "s-02", "end_sec": 20.5}]},
            "Roadmap exceeded max time (20.5s > 20.0s)",
            "roadmap_end_sec",
            20.5,
        ),
    ],
)
def test_measured_overflow_takes_precedence_over_missing_boundary(
    valid_script,
    policy,
    audio_manifest,
    expected_error,
    measured_key,
    measured_end,
):
    test_policy = copy.deepcopy(policy)
    test_policy["story"]["hook_end_sec_max"] = 10.0
    test_policy["story"]["roadmap_end_sec_max"] = 20.0

    report = validate_persona(valid_script, test_policy, audio_manifest)

    assert report["timing_status"] == "FAIL"
    assert report["overall_status"] == "FAIL"
    assert report["timing_checks"][measured_key] == measured_end
    assert any(expected_error in err for err in report["errors"])
