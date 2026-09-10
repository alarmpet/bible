from pathlib import Path

import json
import yaml
from jsonschema import Draft202012Validator

from human_archive.scripts.lib.channel_profiles import (
    load_channel_profile,
    resolve_nollam_profile,
)


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "config" / "channel_profiles.yaml"
SCHEMA_PATH = ROOT / "schemas" / "channel_profile.schema.json"


def test_nollam_profile_is_default_and_uses_20m_delivery():
    profile = load_channel_profile(PROFILE_PATH, "nollam_file_v1")
    assert profile["profile_id"] == "nollam_file_v1"
    assert profile["is_default"] is True
    assert profile["delivery_profile_id"] == "trend_explainer_20m"
    assert "delivery_profile" not in profile
    assert profile["voice_lock_id"] == "M2_WARM"


def test_v2_schema_strictly_validates_nollam_profile_document():
    document = yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(document)
    assert document["schema_version"] == 2


def test_resolved_nollam_bundle_has_stable_hash_and_primary_binding():
    bundle = resolve_nollam_profile(PROFILE_PATH)
    assert bundle["profile_id"] == "nollam_file_v1"
    assert bundle["delivery_profile_id"] == "trend_explainer_20m"
    assert len(bundle["profile_bundle_sha256"]) == 64
    assert bundle["binding_scope"] == "nollam_20m_primary"
