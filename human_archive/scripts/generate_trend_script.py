from __future__ import annotations

import hashlib
import json
from typing import Any


def generate_trend_script(packet: dict[str, Any], profile_bundle: dict[str, Any]) -> dict[str, Any]:
    claims = packet.get("claims", [])
    claim_ids = [str(claim.get("claim_id")) for claim in claims if claim.get("claim_id")]
    sentences = [{"order": 1, "sentence_id": "s01", "tts_text": "지금 사람들이 놀란 사건부터 보겠습니다.", "claim_ids": claim_ids, "sentence_type": "hook"}]
    canonical = json.dumps(sentences, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return {"schema_version": 1, "script_id": f"trend-{packet.get('packet_id', 'packet')}", "job_id": packet.get("packet_id", ""), "format_id": "nollam_file_long", "sentences": sentences, "claim_ids": claim_ids, "persona_id": "nollam_curious_explainer_v1", "voice_lock_id": "M2_WARM", "script_hash": hashlib.sha256(canonical).hexdigest()}
