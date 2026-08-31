"""Deterministic v4 artifact hashing, parent contracts, and sidecar helpers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def canonical_payload_sha256(payload: Any) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest().upper()


def envelope_core_sha256(envelope: dict[str, Any]) -> str:
    core = {k: v for k, v in envelope.items() if k not in {"created_at", "envelope_core_sha256"}}
    return canonical_payload_sha256(core)


def validate_parent_matrix(artifact_type: str, parents: list[dict[str, str]], scope: dict[str, str]) -> list[str]:
    errors: list[str] = []
    if not scope.get("scope_kind") or not scope.get("scope_id"):
        errors.append("scope_kind and scope_id are required")
    for index, parent in enumerate(parents):
        if not parent.get("artifact_id"):
            errors.append(f"parent[{index}].artifact_id is required")
        if not parent.get("payload_sha256") or not parent.get("envelope_core_sha256"):
            errors.append(f"parent[{index}] requires payload_sha256 and envelope_core_sha256")
    if artifact_type == "verified_script_v3" and not parents:
        errors.append("verified_script_v3 requires at least one parent")
    if any(not p.get("payload_sha256") or not p.get("envelope_core_sha256") for p in parents):
        raise ValueError("parent payload and envelope-core digests are required")
    return errors


def build_envelope(*, artifact_id: str, artifact_type: str, schema_version: str, scope_kind: str, scope_id: str, run_id: str, payload_sha256: str, parents: list[dict[str, str]], generator: dict[str, str], policy_sha256: str, created_at: str) -> dict[str, Any]:
    envelope = {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "schema_version": schema_version,
        "scope_kind": scope_kind,
        "scope_id": scope_id,
        "run_id": run_id,
        "payload_sha256": payload_sha256,
        "parents": parents,
        "generator": generator,
        "policy_sha256": policy_sha256,
        "created_at": created_at,
    }
    envelope["envelope_core_sha256"] = envelope_core_sha256(envelope)
    return envelope


def write_sidecar(target_path: Path, envelope: dict[str, Any]) -> Path:
    sidecar = target_path.with_name(target_path.name + ".lineage.json")
    sidecar.write_text(json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return sidecar
