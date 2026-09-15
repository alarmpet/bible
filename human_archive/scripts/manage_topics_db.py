# -*- coding: utf-8 -*-
"""CLI utility to manage, inspect, and query historical topics inventory database."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.topics_inventory import (
    DEFAULT_DB_PATH,
    init_topics_db,
    import_topics_from_catalog,
    get_available_topics,
    get_topic_detail,
    reserve_topic,
    commit_topic_as_used,
    release_topic_reservation,
    get_db_connection,
)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser(description="ShipSeonbi Historical Topics Database Manager")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = subparsers.add_parser("init", help="Initialize database and seed topics")
    p_init.add_argument("--seed", type=Path, default=Path("human_archive/db/seeds/topics_seed.json"))

    # list
    p_list = subparsers.add_parser("list", help="List topics")
    p_list.add_argument("--status", choices=["AVAILABLE", "RESERVED", "USED", "ARCHIVED", "all"], default="AVAILABLE")
    p_list.add_argument("--theme", type=str)

    # inspect
    p_insp = subparsers.add_parser("inspect", help="Inspect a specific topic")
    p_insp.add_argument("--topic-id", required=True, type=str)

    # reserve
    p_res = subparsers.add_parser("reserve", help="Reserve topic for an episode")
    p_res.add_argument("--topic-id", required=True, type=str)
    p_res.add_argument("--episode-id", required=True, type=str)

    # release
    p_rel = subparsers.add_parser("release", help="Release reserved topic back to available")
    p_rel.add_argument("--topic-id", required=True, type=str)

    # stats
    subparsers.add_parser("stats", help="Show database statistics")

    args = parser.parse_args()

    if args.command == "init":
        init_topics_db(args.db)
        if args.seed and args.seed.exists():
            cnt = import_topics_from_catalog(args.seed, args.db)
            print(f"✅ Initialized database and imported {cnt} topics from {args.seed}")
        else:
            print(f"✅ Initialized empty database at {args.db}")

    elif args.command == "list":
        with get_db_connection(args.db) as conn:
            cursor = conn.cursor()
            if args.status == "all":
                cursor.execute("SELECT topic_id, title, theme, status, used_in_episode_id FROM topics ORDER BY topic_id")
            else:
                cursor.execute("SELECT topic_id, title, theme, status, used_in_episode_id FROM topics WHERE status = ? ORDER BY topic_id", (args.status,))
            rows = cursor.fetchall()

        print(f"\n=== Topics List ({len(rows)} items, Status: {args.status}) ===")
        for r in rows:
            used_str = f" (Episode: {r['used_in_episode_id']})" if r["used_in_episode_id"] else ""
            print(f"  [{r['status']}] {r['topic_id']}: {r['title']} [{r['theme']}]{used_str}")
        print()

    elif args.command == "inspect":
        detail = get_topic_detail(args.db, args.topic_id)
        if not detail:
            print(f"❌ Topic '{args.topic_id}' not found.")
            sys.exit(1)
        print(f"\n=== Topic Detail: {args.topic_id} ===")
        print(f"Title: {detail['title']}")
        print(f"Theme: {detail['theme']} | Period: {detail['historical_period']}")
        print(f"Status: {detail['status']} (Used in: {detail['used_in_episode_id'] or 'None'})")
        print(f"Hook: {detail['core_hook']}")
        print(f"Analogy: {detail['modern_analogy']}")
        print(f"Insight: {detail['humanistic_insight']}")
        print(f"Primary Sources: {detail['primary_sources']}")
        print()

    elif args.command == "reserve":
        reserve_topic(args.db, args.topic_id, args.episode_id)
        print(f"✅ Topic '{args.topic_id}' reserved for episode '{args.episode_id}'")

    elif args.command == "release":
        release_topic_reservation(args.db, args.topic_id)
        print(f"✅ Reservation for topic '{args.topic_id}' released back to AVAILABLE")

    elif args.command == "stats":
        with get_db_connection(args.db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) as cnt FROM topics GROUP BY status")
            stats = {r["status"]: r["cnt"] for r in cursor.fetchall()}
            cursor.execute("SELECT COUNT(*) as total FROM topics")
            total = cursor.fetchone()["total"]

        print("\n=== Topics Database Statistics ===")
        print(f"Total Topics: {total}")
        for st, cnt in stats.items():
            print(f"  - {st}: {cnt}")
        print()


if __name__ == "__main__":
    main()
