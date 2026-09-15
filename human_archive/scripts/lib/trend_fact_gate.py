from __future__ import annotations

from typing import Any


def validate_claim(claim: dict[str, Any]) -> dict[str, Any]:
    if claim.get("status") == "UNVERIFIED" and claim.get("criticality") == "core":
        raise ValueError("UNVERIFIED_CORE: core claims require verified evidence")
    if claim.get("criticality") == "core" and claim.get("claim_type") in {"sports_score", "official_filing", "court_order"} and claim.get("direct_record"):
        return {"ok": True, "mode": "direct_record"}
    if claim.get("criticality") == "core" and len(set(claim.get("sources", []))) < 2:
        return {"ok": False, "reason": "INDEPENDENT_CORROBORATION_REQUIRED"}
    return {"ok": True, "mode": "standard"}
