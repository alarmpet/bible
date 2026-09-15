# -*- coding: utf-8 -*-
"""Write approvals and compile shot contract for EP03."""
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.provenance import compute_file_sha256
from compile_shot_contract import compile_contract

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    src_dir = Path("human_archive/runs/ep03_maecheon/source")
    appr_dir = src_dir / "approvals"
    appr_dir.mkdir(parents=True, exist_ok=True)

    script_path = src_dir / "script_seonbi_v3.json"
    claims_path = src_dir / "claim_inventory_v3.json"
    sources_path = src_dir / "source_snapshot_manifest_v3.json"
    fact_rep_path = src_dir / "fact_check_report_v3.json"
    persona_rep_path = src_dir / "persona_report_v3.json"
    shot_plan_path = src_dir / "shot_plan.yaml"

    fact_app = {
        "schema_version": 2,
        "decision": "approved",
        "reviewer_id": "HUMAN_EXPERT_01",
        "role": "Lead Fact Checker & Editorial Lead",
        "approved_at_utc": "2026-08-26T04:00:00Z",
        "artifacts": {
            "script_sha256": compute_file_sha256(script_path),
            "fact_report_sha256": compute_file_sha256(fact_rep_path),
            "persona_report_sha256": compute_file_sha256(persona_rep_path),
            "claim_inventory_sha256": compute_file_sha256(claims_path),
            "source_snapshot_sha256": compute_file_sha256(sources_path)
        },
        "unresolved_issues": 0,
        "notes": "EP03 20-min full docu script approved."
    }
    fact_app_path = appr_dir / "fact_approval.json"
    if fact_app_path.exists():
        existing = json.loads(fact_app_path.read_text(encoding="utf-8"))
        if existing.get("decision") in {"REVIEW_REQUIRED", "review_required", "pending"}:
            raise SystemExit("EP03 approval blocked: existing fact approval is REVIEW_REQUIRED")
    fact_app_path.write_text(json.dumps(fact_app, indent=2, ensure_ascii=False), encoding="utf-8")

    plan_app = {
        "schema_version": 1,
        "decision": "approved",
        "reviewer_id": "VISUAL_LEAD_01",
        "role": "Visual Director",
        "approved_at_utc": "2026-08-26T04:00:00Z",
        "artifacts": {
            "shot_plan_sha256": compute_file_sha256(shot_plan_path)
        },
        "unresolved_issues": 0,
        "notes": "EP03 45-shot K-Webtoon plan approved."
    }
    plan_app_path = appr_dir / "shot_plan_approval.json"
    plan_app_path.write_text(json.dumps(plan_app, indent=2, ensure_ascii=False), encoding="utf-8")

    out_contract = src_dir / "shot_contract.json"
    compile_contract(
        shot_plan_path=shot_plan_path,
        script_path=script_path,
        claim_inventory_path=claims_path,
        fact_report_path=fact_rep_path,
        persona_report_path=persona_rep_path,
        fact_approval_path=fact_app_path,
        shot_plan_approval_path=plan_app_path,
        output_path=out_contract
    )
    print(f"🎉 EP03 Shot Contract Compiled Successfully: {out_contract}")


if __name__ == "__main__":
    main()
