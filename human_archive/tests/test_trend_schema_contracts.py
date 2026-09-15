from pathlib import Path
import json
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def test_trend_schema_set_exists_and_validates_minimum_contracts():
    names = {
        "trend_job_contract_v1": {"schema_version": 1, "job_id": "j1", "profile_id": "nollam_file_v1", "profile_bundle_sha256": "a" * 64, "format_id": "nollam_file_long", "freshness_class": "DAILY", "run_root": "runs/x", "source_provider_ids": ["offline_fixture"]},
        "trend_signal_manifest_v1": {"signal_id": "s1", "platform": "fixture", "canonical_url_or_provider_id": "fixture:s1", "observed_at_utc": "2026-09-01T00:00:00Z", "region": "KR", "window": "24h", "event_fingerprint": "e1", "source_state": "active", "discovery_role": "DISCOVERY_ONLY", "retention_class": "ephemeral"},
        "trend_topic_candidate_v1": {"candidate_id": "c1", "event_fingerprint": "e1", "discovery_score": 50, "evidence_readiness_score": 20, "final_score": 70, "status": "DISCOVERED", "center_question": "왜 지금인가?", "freshness_class": "DAILY"},
        "trend_research_packet_v1": {"packet_id": "p1", "candidate_id": "c1", "claims": [], "source_snapshots": [], "claim_ledger": [], "risk_gate": {}, "freshness_deadline_utc": "2026-09-02T00:00:00Z", "profile_bundle_sha256": "a" * 64},
        "trend_verified_script_v1": {"script_id": "s1", "job_id": "j1", "format_id": "nollam_file_long", "sentences": [], "claim_ids": [], "persona_id": "nollam_curious_explainer_v1", "voice_lock_id": "M2_WARM", "script_hash": "b" * 64},
        "resolved_profile_bundle_v1": {"profile_id": "nollam_file_v1", "binding_scope": "trend_envelope_only", "profile_bundle_sha256": "a" * 64, "policies": {}},
        "overlay_event_manifest_v1": {"manifest_id": "o1", "events": [], "base_image_text_policy": "no_glyph"},
        "correction_action_manifest_v1": {"action_id": "a1", "severity": "MATERIAL", "surfaces": ["subtitles"], "status": "PROPOSED"},
        "studio_disclosure_manifest_v1": {"manifest_id": "d1", "ai_media_types": ["synthetic_voice"], "operator_approved": False},
    }
    for name, instance in names.items():
        path = ROOT / "schemas" / f"{name}.schema.json"
        assert path.exists(), name
        Draft202012Validator(json.loads(path.read_text(encoding="utf-8"))).validate(instance)

