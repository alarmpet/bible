from human_archive.scripts.lib.trend_clustering import cluster_signals
from human_archive.scripts.lib.trend_selection import score_candidate


def test_event_fingerprint_deduplicates_crossposts_but_keeps_observations():
    signals = [
        {"signal_id": "x1", "event_fingerprint": "event-a", "origin_cluster_id": "origin-1", "corroboration_group_id": "g1"},
        {"signal_id": "x2", "event_fingerprint": "event-a", "origin_cluster_id": "origin-1", "corroboration_group_id": "g1"},
        {"signal_id": "n1", "event_fingerprint": "event-a", "origin_cluster_id": "origin-2", "corroboration_group_id": "g2"},
    ]
    clusters = cluster_signals(signals)
    assert len(clusters) == 1
    assert clusters[0]["signal_ids"] == ["x1", "x2", "n1"]
    assert clusters[0]["independent_corroboration_groups"] == 2


def test_manipulation_is_quarantined_not_score_deducted():
    result = score_candidate({"signal_count": 4, "independent_corroboration_groups": 2, "manipulation_risk": True})
    assert result["status"] == "QUARANTINED"
    assert result["discovery_score"] == 75
    assert result["evidence_readiness_score"] == 25

