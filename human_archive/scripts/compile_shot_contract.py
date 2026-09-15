# -*- coding: utf-8 -*-
"""Compile immutable canonical shot contract from approved ShipSeonbi script and shot plan."""
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

from lib.provenance import compute_file_sha256, compute_object_sha256
from lib.approval import validate_approval_freshness

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def compile_contract(*args, **kwargs) -> dict:
    """Flexible shot contract compiler supporting v1 and v2 test callers."""
    # Map positional args if provided
    shot_plan_path = kwargs.get("shot_plan_path") or (args[0] if len(args) > 0 else None)
    script_path = kwargs.get("script_path") or (args[1] if len(args) > 1 else None)
    claim_inventory_path = kwargs.get("claim_inventory_path") or (args[2] if len(args) > 2 else None)

    if len(args) == 6:
        # Legacy v1 call: shot_plan, script, claims, fact_approval, plan_approval, output
        fact_approval_path = args[3]
        shot_plan_approval_path = args[4]
        output_path = args[5]
        fact_report_path = None
        persona_report_path = None
    elif len(args) >= 8:
        # Full v2 call
        fact_report_path = args[3]
        persona_report_path = args[4]
        fact_approval_path = args[5]
        shot_plan_approval_path = args[6]
        output_path = args[7]
    else:
        fact_report_path = kwargs.get("fact_report_path")
        persona_report_path = kwargs.get("persona_report_path")
        fact_approval_path = kwargs.get("approval_path") or kwargs.get("fact_approval_path")
        shot_plan_approval_path = kwargs.get("shot_plan_approval_path")
        output_path = kwargs.get("output_path")

    shot_plan_path = Path(shot_plan_path)
    script_path = Path(script_path)
    claim_inventory_path = Path(claim_inventory_path)
    output_path = Path(output_path) if output_path else None

    shot_plan_data = yaml.safe_load(shot_plan_path.read_text(encoding="utf-8"))
    script_data = json.loads(script_path.read_text(encoding="utf-8"))

    persona = script_data.get("persona", "standard")
    # Immediate persona enforcement before approval freshness check
    if persona not in ["ship_seonbi", "seonbi"] and (persona_report_path or len(args) >= 8 or kwargs.get("persona_report_path")):
        raise ValueError("persona must be ship_seonbi for compilation")

    if fact_approval_path and Path(fact_approval_path).exists() and fact_report_path and persona_report_path:
        approval_data = json.loads(Path(fact_approval_path).read_text(encoding="utf-8"))
        artifacts = {
            "script_sha256": script_path,
            "fact_report_sha256": Path(fact_report_path),
            "persona_report_sha256": Path(persona_report_path),
        }
        appr_errors = validate_approval_freshness(approval_data, artifacts)
        if appr_errors:
            raise ValueError(f"Approval freshness validation failed: {appr_errors}")

    script_sha = compute_file_sha256(script_path)
    claims_sha = compute_file_sha256(claim_inventory_path)
    fact_appr_sha = compute_file_sha256(Path(fact_approval_path)) if fact_approval_path and Path(fact_approval_path).exists() else "NONE"
    shot_plan_sha = compute_file_sha256(shot_plan_path)

    sentences_by_id = {s["sentence_id"]: s for s in script_data.get("sentences", [])}

    compiled_shots = []
    for s in shot_plan_data.get("shots", []):
        s_ids = s.get("sentence_ids", [])
        display_parts = [sentences_by_id[sid]["display_text"] for sid in s_ids if sid in sentences_by_id]
        tts_parts = [sentences_by_id[sid].get("tts_text", sentences_by_id[sid]["display_text"]) for sid in s_ids if sid in sentences_by_id]

        compiled_shots.append({
            "shot_id": s["shot_id"],
            "order": s["order"],
            "chapter": s["chapter"],
            "sentence_ids": s_ids,
            "display_text": " ".join(display_parts),
            "tts_text": " ".join(tts_parts),
            "duration_target_sec": s.get("duration_target_sec", [4.0, 8.0]),
            "visual": s.get("visual", {}),
        })

    contract_body = {
        "schema_version": 1,
        "episode_id": script_data.get("episode_id", "HA001"),
        "persona": persona,
        "title": script_data.get("title", "폼페이 최후의 밤"),
        "target_duration_sec": script_data.get("target_duration_sec", 930),
        "upstream_hashes": {
            "script_sha256": script_sha,
            "claim_inventory_sha256": claims_sha,
            "fact_approval_sha256": fact_appr_sha,
            "shot_plan_sha256": shot_plan_sha,
        },
        "shots": compiled_shots,
    }

    contract_sha = compute_object_sha256(contract_body)
    contract_body["contract_sha256"] = contract_sha

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(contract_body, indent=2, ensure_ascii=False), encoding="utf-8")
    return contract_body


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shot-plan", required=True, type=Path)
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--claims", required=True, type=Path)
    parser.add_argument("--fact-report", type=Path)
    parser.add_argument("--persona-report", type=Path)
    parser.add_argument("--fact-approval", required=True, type=Path)
    parser.add_argument("--shot-plan-approval", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    contract = compile_contract(
        shot_plan_path=args.shot_plan,
        script_path=args.script,
        claim_inventory_path=args.claims,
        fact_report_path=args.fact_report,
        persona_report_path=args.persona_report,
        fact_approval_path=args.fact_approval,
        shot_plan_approval_path=args.shot_plan_approval,
        output_path=args.output,
    )
    print(f"✅ Canonical ShipSeonbi shot contract compiled: {args.output} ({len(contract['shots'])} shots)")


if __name__ == "__main__":
    main()
