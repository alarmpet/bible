from __future__ import annotations

from datetime import datetime, timezone


def create_correction_action(asset_id: str, severity: str, surfaces: list[str]) -> dict[str, object]:
    if severity not in {"CRITICAL", "MATERIAL", "MINOR"}:
        raise ValueError(f"Unknown severity: {severity}")
    if not surfaces:
        raise ValueError("At least one correction surface is required")
    return {"schema_version": 1, "action_id": f"correction-{asset_id}", "asset_id": asset_id, "severity": severity, "surfaces": surfaces, "status": "PROPOSED", "auto_post": False, "created_at_utc": datetime.now(timezone.utc).isoformat()}
