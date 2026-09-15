# -*- coding: utf-8 -*-
"""Artifact approval validation and exact SHA-256 freshness checking."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
import sys
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.provenance import compute_file_sha256

SHA256_RE = re.compile(r"^[A-F0-9]{64}$")


def validate_approval_freshness(approval: dict[str, Any], artifacts: dict[str, Path]) -> list[str]:
    errors: list[str] = []
    if approval.get("decision") != "approved":
        errors.append(f"Approval decision is '{approval.get('decision')}', not 'approved'")

    if approval.get("unresolved_issues", 0) > 0:
        errors.append(f"Approval has {approval.get('unresolved_issues')} unresolved issues")

    appr_arts = approval.get("artifacts", {})
    for art_key, disk_path in artifacts.items():
        if art_key not in appr_arts:
            errors.append(f"Missing artifact key '{art_key}' in approval")
            continue

        rec_hash = appr_arts[art_key]
        if not SHA256_RE.match(rec_hash):
            errors.append(f"invalid sha256 format for '{art_key}': '{rec_hash}'")
            continue

        if disk_path.exists():
            disk_hash = compute_file_sha256(disk_path)
            if disk_hash != rec_hash:
                errors.append(f"Hash mismatch for '{art_key}': recorded={rec_hash[:8]}, disk={disk_hash[:8]}")

    return errors
