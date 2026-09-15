# -*- coding: utf-8 -*-
"""Build immutable source snapshot manifest from approved source ledger v2."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def build_snapshots(ledger_path: Path, evidence_dir: Path | None, output_path: Path) -> dict:
    ledger_data = json.loads(ledger_path.read_text(encoding="utf-8"))
    sources = ledger_data.get("sources", [])

    snapshots = []
    for s in sources:
        spans = s.get("evidence_spans", [])
        snapshots.append({
            "source_id": s["source_id"],
            "title": s["title"],
            "author_or_agency": s["author_or_agency"],
            "year": s["year"],
            "source_type": s["source_type"],
            "peer_reviewed": s["peer_reviewed"],
            "url_or_doi": s.get("url_or_doi", ""),
            "evidence_spans": spans,
        })

    manifest = {
        "schema_version": 2,
        "episode_id": ledger_data.get("episode_id", "HA001"),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "ledger_sha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest().upper(),
        "sources": snapshots,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    manifest = build_snapshots(args.ledger, args.evidence_dir, args.output)
    print(f"✅ Source snapshots manifest v2 saved to {args.output} ({len(manifest['sources'])} sources)")


if __name__ == "__main__":
    main()
