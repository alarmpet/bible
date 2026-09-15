from pathlib import Path

from human_archive.scripts.lib.trend_store import TrendStore


def test_event_fingerprint_is_unique_and_observations_keep_region_window(tmp_path: Path):
    store = TrendStore(tmp_path / "trend.sqlite3")
    store.upsert_signal({"signal_id": "s1", "event_fingerprint": "e1", "region": "KR", "window": "24h", "source_state": "active"})
    store.upsert_signal({"signal_id": "s2", "event_fingerprint": "e1", "region": "US", "window": "7d", "source_state": "active"})
    assert store.count_signals_for_event("e1") == 2
    assert store.observations_for_event("e1") == [("KR", "24h"), ("US", "7d")]


def test_deleted_source_is_tombstoned_without_retracting_claim(tmp_path: Path):
    store = TrendStore(tmp_path / "trend.sqlite3")
    store.upsert_signal({"signal_id": "s1", "event_fingerprint": "e1", "region": "KR", "window": "24h", "source_state": "deleted"})
    assert store.get_source_state("s1") == "deleted"

