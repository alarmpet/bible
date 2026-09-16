# -*- coding: utf-8 -*-
"""Build manifest generator and verification of upstream hash chains."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
import sys
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.provenance import compute_file_sha256, compute_object_sha256


def _contract_sha256(contract_file: Path) -> str:
    """Return the compiler's semantic hash, excluding its self-referential field."""
    data = json.loads(contract_file.read_text(encoding="utf-8"))
    if isinstance(data, dict) and data.get("contract_sha256"):
        body = dict(data)
        body.pop("contract_sha256", None)
        return compute_object_sha256(body)
    return compute_file_sha256(contract_file)


def verify_upstream_hash_freshness(build_dir: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    build_dir = Path(build_dir).resolve()
    contract_file = build_dir / "image_request_manifest.json"
    if not contract_file.exists():
        contract_file = build_dir.parent / "source" / "shot_contract_v4.json"
    if not contract_file.exists():
        contract_file = build_dir.parent / "source" / "shot_contract.json"

    asset_manifest_file = build_dir / "asset_manifest.json"
    # nollam_file_v1 builds write sentence_audio_manifest.json (real per-sentence
    # TTS timing, from build_sentence_audio_master.py); older ep01/ep02
    # doodle_seonbi_v1 builds write scene_audio_manifest.json (per-shot). Either
    # one satisfies "the audio timing this build renders against actually
    # exists" -- 2026-09-16 finding: this unconditionally required
    # scene_audio_manifest.json, so a real, otherwise-complete nollam_file_v1
    # build failed this freshness check outright.
    audio_manifest_candidates = [
        build_dir / "sentence_audio_manifest.json",
        build_dir / "scene_audio_manifest.json",
    ]
    subtitles_file = build_dir / "subtitles.ass"
    approval_candidates = [
        build_dir / "approvals" / "visual_pilot_review.json",
        build_dir / "approvals" / "visual_approval.json",
    ]

    for p in [contract_file, asset_manifest_file, subtitles_file]:
        if not p.exists():
            errors.append(f"Required build upstream file missing: {p}")
    if not any(p.exists() for p in audio_manifest_candidates):
        errors.append(
            "Required build upstream file missing: "
            f"{audio_manifest_candidates[0]} or {audio_manifest_candidates[1]}"
        )

    approval_file = next((p for p in approval_candidates if p.exists()), None)
    if approval_file is None:
        errors.append(f"Required visual approval missing: {approval_candidates[0]} or {approval_candidates[1]}")

    if contract_file.exists() and asset_manifest_file.exists():
        manifest = json.loads(asset_manifest_file.read_text(encoding="utf-8"))
        recorded = str(manifest.get("contract_sha256", ""))
        if not recorded and contract_file.name == "image_request_manifest.json":
            req_data = json.loads(contract_file.read_text(encoding="utf-8"))
            recorded = str(req_data.get("contract_sha256", ""))
        actual = _contract_sha256(contract_file)
        if recorded and contract_file.name != "image_request_manifest.json" and recorded.upper() != actual.upper():
            errors.append(f"Contract hash mismatch: manifest={recorded[:12]}, actual={actual[:12]}")

    return len(errors) == 0, errors
