# -*- coding: utf-8 -*-
"""Validate documentary contract, source ledger v2, and evidence snapshots against academic consensus."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
import yaml

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.schema_validation import load_schema, validate_json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def validate_evidence_package(ledger: dict[str, Any], snapshots: dict[str, Any]) -> list[str]:
    """Validate source ledger v2 and evidence snapshots for consistency and completeness."""
    errors: list[str] = []

    schema_dir = _SCRIPTS_DIR.parent / "schemas"
    ledger_schema = schema_dir / "source_ledger_v2.schema.json"
    if ledger_schema.exists():
        try:
            validate_json(ledger, load_schema(ledger_schema))
        except ValueError as ve:
            errors.append(f"Ledger Schema Error: {ve}")

    sources_by_id = {s["source_id"]: s for s in snapshots.get("sources", [])}
    all_spans_by_id = {}
    for s in snapshots.get("sources", []):
        for sp in s.get("evidence_spans", []):
            sp_id = sp.get("span_id", "")
            if sp.get("capture_method") == "ledger_notes_copy":
                errors.append(f"[{sp_id}] ledger notes are not evidence excerpt")
            all_spans_by_id[sp_id] = sp

    for claim in ledger.get("claims", []):
        cid = claim.get("claim_id", "")
        risk = claim.get("risk", "low")
        src_ids = claim.get("source_ids", [])
        ev_refs = claim.get("evidence_refs", [])

        for sid in src_ids:
            if sid not in sources_by_id:
                errors.append(f"Claim {cid} references unknown source_id '{sid}'")

        for ref in ev_refs:
            if ref not in all_spans_by_id:
                errors.append(f"Claim {cid} references unknown evidence span '{ref}'")

        if risk == "high" and len(src_ids) < 2:
            errors.append(f"Claim {cid}: high-risk claim requires two independent sources")

    return errors


def validate_contract_and_ledger(contract_path: Path, ledger_path: Path) -> list[str]:
    errors: list[str] = []
    contract_data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    ledger_data = json.loads(ledger_path.read_text(encoding="utf-8"))

    # Duration check (840s - 1560s for standard docu: 1200s +- 30%)
    target_dur = contract_data.get("target_duration_sec", 0)
    if not (840 <= target_dur <= 1560):
        errors.append(f"target_duration_sec must be between 840 and 1560 seconds (got {target_dur})")

    # Check unverified claims in core_paradox
    paradox = contract_data.get("core_paradox", "")
    forbid_paradox = ["18시간 내내", "탈출하지 못했다", "재산에 집착"]
    for fp in forbid_paradox:
        if fp in paradox:
            errors.append(f"core_paradox contains unverified claim or myth: '{fp}'")

    # Check forbidden myths in contract
    forbid = ["모든 시민이 사망", "재산 때문에 머무름", "500도 고열 몰살", "18시간 동안 무관심"]
    contract_str = yaml.dump(contract_data, allow_unicode=True)
    for f in forbid:
        if f in contract_str:
            errors.append(f"Contract contains forbidden unscientific myth: '{f}'")

    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--snapshots", type=Path)
    args = parser.parse_args()

    errors = validate_contract_and_ledger(args.contract, args.ledger)
    if args.snapshots and args.snapshots.exists():
        ledger_data = json.loads(args.ledger.read_text(encoding="utf-8"))
        snap_data = json.loads(args.snapshots.read_text(encoding="utf-8"))
        errors.extend(validate_evidence_package(ledger_data, snap_data))

    if errors:
        print("❌ Contract & Ledger Validation FAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("✅ Documentary Contract and Source Ledger PASSED!")
    sys.exit(0)


if __name__ == "__main__":
    main()
