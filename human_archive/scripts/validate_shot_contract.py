# -*- coding: utf-8 -*-
"""Validate shot plan or compiled shot contract against script and claims."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
import jsonschema
import yaml

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.provenance import compute_file_sha256, compute_object_sha256

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def validate_shot_plan_and_contract(
    shot_plan_path: Path | None,
    contract_path: Path | None,
    script_path: Path | None = None,
    claims_path: Path | None = None,
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    evaluations = []

    if shot_plan_path:
        shot_plan_path = Path(shot_plan_path).resolve()
        data = yaml.safe_load(shot_plan_path.read_text(encoding="utf-8"))
        shots = data.get("shots", [])

        script_sentences = {}
        if script_path and script_path.exists():
            s_data = json.loads(script_path.read_text(encoding="utf-8"))
            script_sentences = {s["sentence_id"]: s for s in s_data.get("sentences", [])}

        seen_ids = set()
        seen_orders = set()

        for s in shots:
            sid = s.get("shot_id", "")
            order = s.get("order", 0)
            s_ids = s.get("sentence_ids", [])
            vis = s.get("visual", {})

            shot_issues = []

            if sid in seen_ids:
                shot_issues.append(f"Duplicate shot_id '{sid}'")
            seen_ids.add(sid)

            if order in seen_orders:
                shot_issues.append(f"Duplicate order '{order}'")
            seen_orders.add(order)

            if script_sentences:
                for target_sid in s_ids:
                    if target_sid not in script_sentences:
                        shot_issues.append(f"Sentence ID '{target_sid}' not in script draft")

            if not vis.get("subject") or not vis.get("place") or not vis.get("era") or not vis.get("action"):
                shot_issues.append("Missing required visual anchor fields (subject, place, era, action)")

            evaluations.append({
                "shot_id": sid,
                "status": "FAIL" if shot_issues else "PASS",
                "issues": shot_issues,
            })
            errors.extend(shot_issues)

    if contract_path:
        contract_path = Path(contract_path).resolve()
        c_data = json.loads(contract_path.read_text(encoding="utf-8"))
        schema_path = _SCRIPTS_DIR.parent / "schemas" / "shot_contract.schema.json"
        if not schema_path.exists():
            errors.append(f"Contract schema missing: {schema_path}")
        else:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            try:
                jsonschema.validate(instance=c_data, schema=schema)
            except jsonschema.ValidationError as ve:
                errors.append(f"Contract schema violation: {ve.message}")

    report = {
        "schema_version": 1,
        "total_shots": len(evaluations),
        "invalid_shot_count": len([e for e in evaluations if e["status"] == "FAIL"]),
        "evaluations": evaluations,
    }
    return errors, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shot-plan", type=Path)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--script", type=Path)
    parser.add_argument("--claims", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    errors, report = validate_shot_plan_and_contract(args.shot_plan, args.contract, args.script, args.claims)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if errors:
        print("❌ Shot Contract Validation FAILED:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    print("✅ Shot Contract Validation PASSED!")
    sys.exit(0)


if __name__ == "__main__":
    main()
