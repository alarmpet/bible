from __future__ import annotations

import pytest

from lib.doodle_visual_roles import classify_visual_role, validate_role_mix


def test_fact_body_maps_to_reconstruction_without_host():
    result = classify_visual_role({"beat": "body", "claim_ids": ["CLM-JH-002"]})
    assert result.role == "historical_reconstruction"
    assert result.host_mode == "absent"


def test_evidence_commentary_maps_to_evidence_object():
    result = classify_visual_role({"beat": "source_commentary", "claim_ids": ["CLM-JH-003"]})
    assert result.role == "evidence_object"
    assert result.host_mode == "absent"


def test_host_quota_rejects_omnipresent_presenter():
    scenes = [{"visual_role": "host_explainer", "host_mode": "full"}] * 20
    with pytest.raises(ValueError, match="host presence"):
        validate_role_mix(scenes)


def test_host_quota_rejects_episode_without_presenter_beats():
    scenes = [{"visual_role": "historical_reconstruction", "host_mode": "absent"}] * 20
    with pytest.raises(ValueError, match="host presence"):
        validate_role_mix(scenes)


def test_host_quota_rejects_three_consecutive_host_scenes():
    scenes = (
        [{"visual_role": "historical_reconstruction", "host_mode": "absent"}] * 8
        + [{"visual_role": "host_explainer", "host_mode": "full"}] * 3
        + [{"visual_role": "historical_reconstruction", "host_mode": "absent"}] * 7
        + [{"visual_role": "host_explainer", "host_mode": "full"}] * 2
    )
    with pytest.raises(ValueError, match="consecutive"):
        validate_role_mix(scenes)


def test_non_host_role_rejects_visible_host_mode():
    scenes = (
        [{"visual_role": "historical_reconstruction", "host_mode": "absent"}] * 15
        + [{"visual_role": "host_explainer", "host_mode": "full"}] * 4
        + [{"visual_role": "evidence_object", "host_mode": "full"}]
    )
    with pytest.raises(ValueError, match="host_mode"):
        validate_role_mix(scenes)
