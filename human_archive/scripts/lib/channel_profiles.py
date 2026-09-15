from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib
import json
import yaml

def load_channel_profile(path: str | Path, profile_id: str | None = None) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    profiles = data.get("profiles", {})
    selected = profile_id or data.get("default_profile_id")
    if selected not in profiles:
        raise ValueError(f"Unknown channel profile: {selected}")
    result = dict(profiles[selected]); result["profile_id"] = selected
    return result

def resolve_delivery_profile(path: str | Path, profile_id: str) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if profile_id not in data.get("profiles", {}):
        raise ValueError(f"Unknown delivery profile: {profile_id}")
    result = dict(data["profiles"][profile_id]); result["profile_id"] = profile_id
    return result


def resolve_nollam_profile(path: str | Path) -> dict[str, Any]:
    """Resolve the Nollam profile (now the primary default production profile)."""
    profile = load_channel_profile(path, "nollam_file_v1")
    if "delivery_profile" in profile or profile.get("delivery_profile_id") != "trend_explainer_20m":
        raise ValueError("Nollam profile requires canonical trend_explainer_20m delivery_profile_id")
    if profile.get("voice_lock_id") != "M2_WARM":
        raise ValueError("Nollam profile requires M2_WARM voice lock")
    canonical = json.loads(json.dumps(profile, ensure_ascii=False, sort_keys=True))
    digest = hashlib.sha256(json.dumps(canonical, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()
    return {
        **canonical,
        "binding_scope": "nollam_20m_primary",
        "profile_bundle_sha256": digest,
    }
