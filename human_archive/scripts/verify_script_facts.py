# -*- coding: utf-8 -*-
"""Verify script statements against approved claim inventory and source snapshots."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.fact_verification import verify_script

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--claims", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    script_data = json.loads(args.script.read_text(encoding="utf-8"))
    claim_inventory = json.loads(args.claims.read_text(encoding="utf-8"))
    source_snapshots = json.loads(args.sources.read_text(encoding="utf-8"))

    report = verify_script(script_data, claim_inventory, source_snapshots)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if report["overall_status"] == "FAIL":
        print(f"❌ Script Fact Verification FAILED! (Failures: {report['fail_count']})")
        sys.exit(1)

    print(f"✅ Script Fact Verification Status: {report['overall_status']} (Total segments: {report['total_segments']})")
    sys.exit(0)


if __name__ == "__main__":
    main()
