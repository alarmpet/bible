from __future__ import annotations

from typing import Any


def score_candidate(cluster: dict[str, Any]) -> dict[str, Any]:
    discovery = min(75, max(0, int(cluster.get("signal_count", cluster.get("independent_corroboration_groups", 0) * 2) * 20)))
    evidence = min(25, max(0, int(cluster.get("independent_corroboration_groups", 0) * 12.5)))
    if cluster.get("manipulation_risk"):
        discovery, evidence = 75, 25
        status = "QUARANTINED"
    else:
        status = "DISCOVERED"
    return {"discovery_score": discovery, "evidence_readiness_score": evidence, "final_score": discovery + evidence, "status": status}
