"""Resolve NOLLAM production policies into one immutable context."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(document, dict):
        raise ValueError(f"Expected mapping in policy file: {path}")
    return document


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class PipelineContext:
    profile_id: str
    delivery_profile_id: str
    pacing_profile_id: str
    channel_profile: Mapping[str, Any]
    delivery_profile: Mapping[str, Any]
    pacing_profile: Mapping[str, Any]
    script_policy: Mapping[str, Any]
    audio_policy: Mapping[str, Any]
    visual_policy: Mapping[str, Any]
    policy_sha256: str


def resolve_pipeline_context(
    config_dir: str | Path,
    profile_id: str | None = None,
) -> PipelineContext:
    """Load the selected channel profile and every policy it binds."""
    config_path = Path(config_dir)
    channel_document = _load_yaml(config_path / "channel_profiles.yaml")
    profiles = channel_document.get("profiles") or {}
    selected_id = profile_id or channel_document.get("default_profile_id")
    if selected_id not in profiles:
        raise ValueError(f"Unknown channel profile: {selected_id}")

    channel_profile = dict(profiles[selected_id])
    delivery_profile_id = channel_profile.get("delivery_profile_id") or channel_profile.get("delivery_profile")
    if not isinstance(delivery_profile_id, str) or not delivery_profile_id:
        raise ValueError(f"Channel profile {selected_id} has no delivery profile")

    delivery_document = _load_yaml(config_path / "delivery_profiles.yaml")
    delivery_profiles = delivery_document.get("profiles") or {}
    if delivery_profile_id not in delivery_profiles:
        raise ValueError(f"Unknown delivery profile: {delivery_profile_id}")

    pacing_profile_id = "nollam_decay_20m" if selected_id == "nollam_file_v1" else "narration_aligned_hybrid_v1"
    pacing_document = _load_yaml(config_path / "visual_pacing_profiles.yaml")
    if pacing_profile_id not in pacing_document:
        raise ValueError(f"Unknown pacing profile: {pacing_profile_id}")

    script_policy = _load_yaml(config_path / "script_policy_v3.yaml")
    audio_policy = _load_yaml(config_path / "audio_mix_policy.yaml")
    visual_policy = _load_yaml(config_path / "nollam_file_visual_policy.yaml")
    for name, policy in (("script", script_policy), ("audio", audio_policy), ("visual", visual_policy)):
        bound_profile = policy.get("profile_id")
        if bound_profile and bound_profile != selected_id:
            raise ValueError(f"{name} policy is bound to {bound_profile}, not {selected_id}")

    resolved = {
        "profile_id": selected_id,
        "delivery_profile_id": delivery_profile_id,
        "pacing_profile_id": pacing_profile_id,
        "channel_profile": channel_profile,
        "delivery_profile": delivery_profiles[delivery_profile_id],
        "pacing_profile": pacing_document[pacing_profile_id],
        "script_policy": script_policy,
        "audio_policy": audio_policy,
        "visual_policy": visual_policy,
    }
    canonical = json.dumps(resolved, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    frozen = _freeze(resolved)
    return PipelineContext(
        profile_id=selected_id,
        delivery_profile_id=delivery_profile_id,
        pacing_profile_id=pacing_profile_id,
        channel_profile=frozen["channel_profile"],
        delivery_profile=frozen["delivery_profile"],
        pacing_profile=frozen["pacing_profile"],
        script_policy=frozen["script_policy"],
        audio_policy=frozen["audio_policy"],
        visual_policy=frozen["visual_policy"],
        policy_sha256=digest,
    )
