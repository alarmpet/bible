# -*- coding: utf-8 -*-
"""SQLite-backed topics repository enforcing strict zero-reusage governance."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path("human_archive/db/topics_inventory.sqlite3")


def get_db_connection(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    p = Path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    return conn


def init_topics_db(db_path: Path | str = DEFAULT_DB_PATH) -> None:
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                topic_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                theme TEXT NOT NULL,
                historical_period TEXT,
                core_hook TEXT NOT NULL,
                primary_sources TEXT NOT NULL,
                modern_analogy TEXT,
                humanistic_insight TEXT,
                target_duration_sec INTEGER DEFAULT 1200,
                status TEXT NOT NULL CHECK(status IN ('AVAILABLE', 'RESERVED', 'USED', 'ARCHIVED')),
                used_in_episode_id TEXT,
                used_at_utc TEXT,
                created_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topic_usage_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id TEXT NOT NULL,
                episode_id TEXT,
                action TEXT NOT NULL,
                timestamp_utc TEXT NOT NULL,
                notes TEXT
            )
        """)
        conn.commit()


def import_topics_from_catalog(catalog_path: Path, db_path: Path | str = DEFAULT_DB_PATH) -> int:
    init_topics_db(db_path)
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    topics = data.get("topics", [])
    now_utc = datetime.now(timezone.utc).isoformat()

    inserted_count = 0
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        for t in topics:
            cursor.execute("""
                INSERT INTO topics (
                    topic_id, title, theme, historical_period, core_hook,
                    primary_sources, modern_analogy, humanistic_insight,
                    target_duration_sec, status, used_in_episode_id,
                    used_at_utc, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(topic_id) DO UPDATE SET
                    title=excluded.title,
                    theme=excluded.theme,
                    historical_period=excluded.historical_period,
                    core_hook=excluded.core_hook,
                    primary_sources=excluded.primary_sources,
                    modern_analogy=excluded.modern_analogy,
                    humanistic_insight=excluded.humanistic_insight,
                    target_duration_sec=excluded.target_duration_sec,
                    updated_at_utc=excluded.updated_at_utc
                WHERE topics.status = 'AVAILABLE'
            """, (
                t["topic_id"],
                t["title"],
                t["theme"],
                t.get("historical_period", ""),
                t["core_hook"],
                json.dumps(t.get("primary_sources", []), ensure_ascii=False),
                t.get("modern_analogy", ""),
                t.get("humanistic_insight", ""),
                t.get("target_duration_sec", 1200),
                t.get("status", "AVAILABLE"),
                t.get("used_in_episode_id"),
                t.get("used_at_utc"),
                now_utc,
                now_utc,
            ))
            inserted_count += 1
        conn.commit()
    return inserted_count


def get_available_topics(db_path: Path | str = DEFAULT_DB_PATH, theme: str | None = None) -> list[dict[str, Any]]:
    init_topics_db(db_path)
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        if theme:
            cursor.execute("SELECT * FROM topics WHERE status = 'AVAILABLE' AND theme = ? ORDER BY topic_id", (theme,))
        else:
            cursor.execute("SELECT * FROM topics WHERE status = 'AVAILABLE' ORDER BY topic_id")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_topic_detail(db_path: Path | str = DEFAULT_DB_PATH, topic_id: str = "") -> dict[str, Any] | None:
    init_topics_db(db_path)
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM topics WHERE topic_id = ?", (topic_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def reserve_topic(db_path: Path | str = DEFAULT_DB_PATH, topic_id: str = "", episode_id: str = "") -> None:
    init_topics_db(db_path)
    now_utc = datetime.now(timezone.utc).isoformat()
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, used_in_episode_id FROM topics WHERE topic_id = ?", (topic_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Topic '{topic_id}' does not exist in database")

        st = row["status"]
        used_ep = row["used_in_episode_id"]

        if st == "USED":
            raise ValueError(f"Topic '{topic_id}' has already been used in episode '{used_ep}' and cannot be reused")
        if st == "RESERVED" and used_ep != episode_id:
            raise ValueError(f"Topic '{topic_id}' is already in progress by episode '{used_ep}'")

        cursor.execute("""
            UPDATE topics
            SET status = 'RESERVED', used_in_episode_id = ?, updated_at_utc = ?
            WHERE topic_id = ?
        """, (episode_id, now_utc, topic_id))

        cursor.execute("""
            INSERT INTO topic_usage_log (topic_id, episode_id, action, timestamp_utc)
            VALUES (?, ?, 'RESERVED', ?)
        """, (topic_id, episode_id, now_utc))
        conn.commit()


def commit_topic_as_used(db_path: Path | str = DEFAULT_DB_PATH, topic_id: str = "", episode_id: str = "") -> None:
    init_topics_db(db_path)
    now_utc = datetime.now(timezone.utc).isoformat()
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, used_in_episode_id FROM topics WHERE topic_id = ?", (topic_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Topic '{topic_id}' does not exist in database")

        st = row["status"]
        used_ep = row["used_in_episode_id"]

        if st == "USED" and used_ep != episode_id:
            raise ValueError(f"Topic '{topic_id}' has already been used in episode '{used_ep}'")

        cursor.execute("""
            UPDATE topics
            SET status = 'USED', used_in_episode_id = ?, used_at_utc = ?, updated_at_utc = ?
            WHERE topic_id = ?
        """, (episode_id, now_utc, now_utc, topic_id))

        cursor.execute("""
            INSERT INTO topic_usage_log (topic_id, episode_id, action, timestamp_utc)
            VALUES (?, ?, 'COMMITTED_USED', ?)
        """, (topic_id, episode_id, now_utc))
        conn.commit()


def release_topic_reservation(db_path: Path | str = DEFAULT_DB_PATH, topic_id: str = "") -> None:
    init_topics_db(db_path)
    now_utc = datetime.now(timezone.utc).isoformat()
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM topics WHERE topic_id = ?", (topic_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Topic '{topic_id}' does not exist in database")

        if row["status"] == "USED":
            raise ValueError(f"Cannot release completed USED topic '{topic_id}'")

        cursor.execute("""
            UPDATE topics
            SET status = 'AVAILABLE', used_in_episode_id = NULL, updated_at_utc = ?
            WHERE topic_id = ?
        """, (now_utc, topic_id))

        cursor.execute("""
            INSERT INTO topic_usage_log (topic_id, episode_id, action, timestamp_utc)
            VALUES (?, NULL, 'RELEASED_TO_AVAILABLE', ?)
        """, (topic_id, now_utc))
        conn.commit()
