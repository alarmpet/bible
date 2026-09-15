from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from lib.profile_resolver import resolve_pipeline_context


CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


def test_nollam_context_resolves_all_required_policies() -> None:
    context = resolve_pipeline_context(CONFIG_DIR)

    assert context.profile_id == "nollam_file_v1"
    assert context.delivery_profile_id == "trend_explainer_20m"
    assert context.pacing_profile_id == "nollam_decay_20m"
    assert context.channel_profile["voice_lock_id"] == "M2_WARM"
    assert context.script_policy["profile_id"] == context.profile_id
    assert context.audio_policy["voice"]["voice_lock_id"] == "M2_WARM"
    assert context.visual_policy["format_id"] == "nollam_file_long"


def test_pipeline_context_hash_is_stable_and_context_is_frozen() -> None:
    first = resolve_pipeline_context(CONFIG_DIR, "nollam_file_v1")
    second = resolve_pipeline_context(CONFIG_DIR, "nollam_file_v1")

    assert first.policy_sha256 == second.policy_sha256
    assert len(first.policy_sha256) == 64
    with pytest.raises(FrozenInstanceError):
        first.profile_id = "doodle_seonbi_v1"  # type: ignore[misc]


def test_unknown_profile_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unknown channel profile"):
        resolve_pipeline_context(CONFIG_DIR, "unknown_profile")
