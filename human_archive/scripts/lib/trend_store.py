from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class TrendStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                signal_id TEXT PRIMARY KEY,
                event_fingerprint TEXT NOT NULL,
                region TEXT NOT NULL,
                window TEXT NOT NULL,
                source_state TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.commit()

    def upsert_signal(self, signal: dict[str, Any]) -> None:
        required = ("signal_id", "event_fingerprint", "region", "window", "source_state")
        missing = [key for key in required if not signal.get(key)]
        if missing:
            raise ValueError(f"Missing signal fields: {', '.join(missing)}")
        self._conn.execute(
            """INSERT INTO signals(signal_id,event_fingerprint,region,window,source_state)
               VALUES (?,?,?,?,?)
               ON CONFLICT(signal_id) DO UPDATE SET
                 event_fingerprint=excluded.event_fingerprint,
                 region=excluded.region, window=excluded.window,
                 source_state=excluded.source_state""",
            tuple(signal[key] for key in required),
        )
        self._conn.commit()

    def count_signals_for_event(self, event_fingerprint: str) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM signals WHERE event_fingerprint=?", (event_fingerprint,)).fetchone()
        return int(row[0])

    def observations_for_event(self, event_fingerprint: str) -> list[tuple[str, str]]:
        rows = self._conn.execute(
            "SELECT region, window FROM signals WHERE event_fingerprint=? ORDER BY signal_id",
            (event_fingerprint,),
        ).fetchall()
        return [(str(region), str(window)) for region, window in rows]

    def get_source_state(self, signal_id: str) -> str | None:
        row = self._conn.execute("SELECT source_state FROM signals WHERE signal_id=?", (signal_id,)).fetchone()
        return None if row is None else str(row[0])

    def close(self) -> None:
        self._conn.close()
