# -*- coding: utf-8 -*-
"""Extract approved claims inventory and validate evidence references."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def build_inventory(ledger_path: Path, sources_path: Path, output_path: Path) -> dict:
    ledger_data = json.loads(ledger_path.read_text(encoding="utf-8"))
    sources_data = json.loads(sources_path.read_text(encoding="utf-8"))

    all_spans = set()
    for s in sources_data.get("sources", []):
        for sp in s.get("evidence_spans", []):
            all_spans.add(sp.get("span_id"))

    claims = []
    for c in ledger_data.get("claims", []):
        for ref in c.get("evidence_refs", []):
            if ref not in all_spans:
                raise ValueError(f"Claim {c['claim_id']} references missing span '{ref}'")

        claims.append({
            "claim_id": c["claim_id"],
            "statement": c["statement"],
            "type": c["type"],
            "risk": c.get("risk", "low"),
            "source_ids": c["source_ids"],
            "evidence_refs": c["evidence_refs"],
            "approved_paraphrases": c.get("approved_paraphrases", []),
            "allowed_wording": c.get("allowed_wording", []),
            "forbidden_wording": c.get("forbidden_wording", []),
        })

    inventory = {
        "schema_version": 2,
        "episode_id": ledger_data.get("episode_id", "HA001"),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "ledger_sha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest().upper(),
        "sources_sha256": hashlib.sha256(sources_path.read_bytes()).hexdigest().upper(),
        "claims": claims,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
    return inventory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    inventory = build_inventory(args.ledger, args.sources, args.output)
    print(f"✅ Claim inventory v2 saved to {args.output} ({len(inventory['claims'])} claims)")


if __name__ == "__main__":
    main()
