# -*- coding: utf-8 -*-
"""Test script approval binding and rejection of non-seonbi scripts."""
from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from compile_shot_contract import compile_contract
from helpers_v2 import ApprovedBundlePaths
from lib.approval import validate_approval_freshness
from lib.provenance import compute_file_sha256


@pytest.fixture
def valid_paths(tmp_path: Path) -> ApprovedBundlePaths:
    script_p = tmp_path / "script.json"
    claims_p = tmp_path / "claims.json"
    sources_p = tmp_path / "sources.json"
    fact_rep_p = tmp_path / "fact_report.json"
    pers_rep_p = tmp_path / "persona_report.json"
    appr_p = tmp_path / "approval.json"
    plan_p = tmp_path / "shot_plan.yaml"
    plan_appr_p = tmp_path / "plan_approval.json"
    out_p = tmp_path / "shot_contract.json"

    script_data = {
        "schema_version": 2,
        "episode_id": "EP01",
        "persona": "ship_seonbi",
        "title": "테스트",
        "target_duration_sec": 930,
        "sentences": [
            {
                "sentence_id": "s-01",
                "beat": "hook",
                "display_text": "테스트 문장입니다.",
                "tts_text": "테스트 문장입니다.",
                "segments": [{"kind": "fact", "text": "테스트 문장입니다."}],
            }
        ],
    }
    script_p.write_text(json.dumps(script_data, ensure_ascii=False), encoding="utf-8")
    claims_p.write_text(json.dumps({"claims": []}), encoding="utf-8")
    sources_p.write_text(json.dumps({"sources": []}), encoding="utf-8")
    fact_rep_p.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    pers_rep_p.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    plan_p.write_text("shots:\n  - shot_id: 'ch1_01'\n    order: 1\n    chapter: 1\n    sentence_ids: ['s-01']\n", encoding="utf-8")
    plan_appr_p.write_text(json.dumps({"decision": "approved"}), encoding="utf-8")

    appr_data = {
        "schema_version": 2,
        "decision": "approved",
        "reviewer_id": "REV-01",
        "approved_at_utc": "2026-08-21T00:00:00Z",
        "artifacts": {
            "script_sha256": compute_file_sha256(script_p),
            "fact_report_sha256": compute_file_sha256(fact_rep_p),
            "persona_report_sha256": compute_file_sha256(pers_rep_p),
        },
        "unresolved_issues": 0,
    }
    appr_p.write_text(json.dumps(appr_data), encoding="utf-8")

    return ApprovedBundlePaths(
        script=script_p,
        claim_inventory=claims_p,
        source_snapshots=sources_p,
        fact_report=fact_rep_p,
        persona_report=pers_rep_p,
        approval=appr_p,
        shot_plan=plan_p,
        shot_plan_approval=plan_appr_p,
        output=out_p,
    )


def test_compile_rejects_non_seonbi_script(valid_paths):
    script = json.loads(valid_paths.script.read_text(encoding="utf-8"))
    script["persona"] = "standard"
    valid_paths.script.write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="persona must be ship_seonbi"):
        compile_contract(**valid_paths.as_kwargs())


def test_approval_requires_exact_current_hashes(valid_paths):
    approval = json.loads(valid_paths.approval.read_text(encoding="utf-8"))
    approval["artifacts"]["script_sha256"] = "PENDING_COMPILATION"
    errors = validate_approval_freshness(approval, valid_paths.artifacts)
    assert any("invalid sha256" in err for err in errors)
