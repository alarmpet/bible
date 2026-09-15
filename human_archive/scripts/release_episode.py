# -*- coding: utf-8 -*-
"""Promote verified candidate video to final release atomically with exact hash approvals and topic DB commitment."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.provenance import compute_file_sha256
from lib.topics_inventory import DEFAULT_DB_PATH, commit_topic_as_used
from lib.production_path_guard import assert_not_isolated_research_path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SHA256_RE = re.compile(r"^[A-F0-9]{64}$")


def validate_release_approval(approval: dict[str, Any]) -> list[str]:
    errors = []
    if approval.get("decision") != "approved":
        errors.append(f"Release decision is '{approval.get('decision')}', not 'approved'")

    cand_hash = approval.get("artifacts", {}).get("candidate_video_sha256", "")
    if not SHA256_RE.match(cand_hash):
        errors.append(f"invalid sha256 format for candidate_video_sha256: '{cand_hash}'")

    return errors


def promote_release(
    candidate: Path,
    final_path: Path,
    release_report: Path,
    approval: Path,
    topic_id: str | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> Path:
    candidate = Path(candidate).resolve()
    final_path = Path(final_path).resolve()
    release_report = Path(release_report).resolve()
    approval = Path(approval).resolve()

    assert_not_isolated_research_path(candidate, final_path, release_report, approval)

    if not candidate.exists():
        raise SystemExit(f"Candidate file missing: {candidate}")

    rep_data = json.loads(release_report.read_text(encoding="utf-8"))
    if rep_data.get("overall_status") != "PASS":
        raise ValueError(f"release report is not PASS (status={rep_data.get('overall_status')})")

    appr_data = json.loads(approval.read_text(encoding="utf-8"))
    appr_errors = validate_release_approval(appr_data)
    if appr_errors:
        raise ValueError(f"Release approval validation failed: {appr_errors}")

    cand_sha = compute_file_sha256(candidate)
    rep_sha = rep_data.get("sha256", "")
    appr_sha = appr_data.get("artifacts", {}).get("candidate_video_sha256", "")

    if cand_sha != rep_sha or cand_sha != appr_sha:
        raise ValueError(f"SHA-256 mismatch: candidate={cand_sha[:8]}, report={rep_sha[:8]}, approval={appr_sha[:8]}")

    final_path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(candidate, final_path)

    # Commit topic as USED in local database
    if topic_id and db_path.exists():
        ep_id = final_path.name.split("-")[0]
        commit_topic_as_used(db_path, topic_id, ep_id)
        print(f"🔒 Topic '{topic_id}' permanently marked as USED in {db_path}")

    print(f"🎉 FINAL RELEASE PROMOTED: {final_path} (SHA-256: {cand_sha})")
    return final_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--approval", required=True, type=Path)
    parser.add_argument("--final", required=True, type=Path)
    parser.add_argument("--topic-id", type=str)
    parser.add_argument("--db", default=DEFAULT_DB_PATH, type=Path)
    args = parser.parse_args()

    promote_release(args.candidate, args.final, args.report, args.approval, topic_id=args.topic_id, db_path=args.db)


if __name__ == "__main__":
    main()
