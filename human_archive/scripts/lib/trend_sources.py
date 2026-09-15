from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

REQUIRED_PROVIDERS = {"offline_fixture", "google_trends_official", "google_news_human_verified"}
OPTIONAL_PROVIDERS = {"x", "threads", "reddit", "youtube"}

@dataclass(frozen=True)
class CapabilityResult:
    provider_id: str
    available: bool
    reason: str = ""

def validate_capability(provider_config: dict[str, Any]) -> CapabilityResult:
    provider_id = str(provider_config.get("provider_id") or provider_config.get("id") or provider_config.get("name") or "unknown")
    required = bool(provider_config.get("required", False))
    available = bool(provider_config.get("endpoint") or provider_id == "offline_fixture" or provider_config.get("collection"))
    return CapabilityResult(provider_id, available, "configured" if available else ("required" if required else "optional"))

def collect_signals(input_dir: str | Path, providers: Sequence[str]) -> dict[str, Any]:
    root = Path(input_dir)
    signal_file = root / "signals.json"
    required = set(providers) & REQUIRED_PROVIDERS
    if required and not signal_file.exists():
        raise ValueError(f"SOURCE_UNAVAILABLE: {','.join(sorted(required))}")
    signals = json.loads(signal_file.read_text(encoding="utf-8")) if signal_file.exists() else []
    return {"schema_version": 1, "signals": signals, "provider_ids": list(providers), "optional_unavailable": sorted(set(providers) & OPTIONAL_PROVIDERS), "scraper_fallback": False}
