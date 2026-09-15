from __future__ import annotations

from collections import defaultdict
from typing import Any


def cluster_signals(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for signal in signals:
        grouped[str(signal["event_fingerprint"])].append(signal)
    result = []
    for fingerprint, items in grouped.items():
        result.append({
            "event_fingerprint": fingerprint,
            "signal_ids": [str(item["signal_id"]) for item in items],
            "independent_corroboration_groups": len({item.get("corroboration_group_id") for item in items if item.get("corroboration_group_id")}),
            "origin_clusters": sorted({item.get("origin_cluster_id") for item in items if item.get("origin_cluster_id")}),
        })
    return result
