import pytest

from human_archive.scripts.lib.trend_fact_gate import validate_claim
from human_archive.scripts.generate_trend_script import generate_trend_script


def test_unverified_core_claim_is_rejected_but_direct_record_is_allowed():
    with pytest.raises(ValueError, match="UNVERIFIED_CORE"):
        validate_claim({"status": "UNVERIFIED", "criticality": "core", "sources": []})
    assert validate_claim({"status": "CONFIRMED", "criticality": "core", "claim_type": "sports_score", "direct_record": True, "sources": ["league"]})["ok"]


def test_script_generation_keeps_claim_mapping_and_nollam_format():
    result = generate_trend_script({"packet_id": "p1", "claims": [{"claim_id": "c1"}]}, {"profile_id": "nollam_file_v1"})
    assert result["format_id"] == "nollam_file_long"
    assert result["voice_lock_id"] == "M2_WARM"
    assert result["sentences"][0]["claim_ids"] == ["c1"]

