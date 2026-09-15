from pathlib import Path
import yaml
import pytest
from lib.schema_validation import load_schema, validate_json

ROOT = Path(__file__).resolve().parents[1]

def test_hybrid_profile_has_approved_exact_limits():
    data = yaml.safe_load((ROOT / "config" / "visual_pacing_profiles.yaml").read_text(encoding="utf-8"))
    profile = data["narration_aligned_hybrid_v1"]
    assert (profile["min_shot_sec"], profile["target_shot_sec"], profile["max_shot_sec"]) == (9.0, 10.5, 12.0)
    assert profile["hard_max_shot_sec"] == 15.0
    assert (profile["host_ratio_min"], profile["host_ratio_max"]) == (0.08, 0.12)
    assert profile["host_min_non_host_gap"] == 7

def test_sentence_audio_schema_rejects_missing_script_hash():
    schema = load_schema(ROOT / "schemas" / "sentence_audio_manifest.schema.json")
    with pytest.raises(ValueError, match="script_sha256"):
        validate_json({"schema_version": 1, "episode_id": "HA002", "sentences": []}, schema)
