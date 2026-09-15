# -*- coding: utf-8 -*-
"""Record an explicit human approval for fact-review-only findings."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.fact_review_approval import record_fact_review_approval


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--fact-report", required=True, type=Path)
    parser.add_argument("--persona-report", required=True, type=Path)
    parser.add_argument("--claims", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--reviewer-id", required=True)
    parser.add_argument("--approval-source", required=True)
    parser.add_argument("--approved-at-utc")
    args = parser.parse_args()

    approved_at_utc = args.approved_at_utc or datetime.now(timezone.utc).isoformat()
    approval = record_fact_review_approval(
        script_path=args.script,
        fact_report_path=args.fact_report,
        persona_report_path=args.persona_report,
        claim_inventory_path=args.claims,
        source_snapshot_path=args.sources,
        output_path=args.output,
        reviewer_id=args.reviewer_id,
        approval_source=args.approval_source,
        approved_at_utc=approved_at_utc,
    )
    print(
        f"Recorded {approval['review_scope']['review_required_count']} fact review items: "
        f"{args.output}"
    )


if __name__ == "__main__":
    main()
