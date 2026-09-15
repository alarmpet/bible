# -*- coding: utf-8 -*-
"""Migrate host/evidence prompts to coherent-scene rules while preserving rejected assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.prompt_compiler import compile_scene_request


TARGET_ROLES = {"host_explainer", "evidence_object"}
ARCHIVE_NAME = "pre-coherent-scene-001"


def _read_json(path: Path) -> dict[str, Any] | list[Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _preserve_file(source: Path, destination: Path, build_dir: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_sha = _sha256(source)
    reused = destination.exists()
    if reused:
        if _sha256(destination) != source_sha:
            raise ValueError(f"archive collision with different content: {destination}")
    else:
        shutil.copy2(source, destination)
    return {
        "source": source.relative_to(build_dir).as_posix(),
        "archive": destination.relative_to(build_dir).as_posix(),
        "sha256": source_sha,
        "bytes": source.stat().st_size,
        "reused": reused,
    }


def migrate_requests(build_dir: Path) -> dict[str, Any]:
    build_dir = Path(build_dir)
    contract = _read_json(build_dir / "episode_visual_contract_v2.json")
    request_path = build_dir / "image_request_manifest.json"
    request_manifest = _read_json(request_path)
    asset_path = build_dir / "asset_manifest.json"
    asset_manifest = _read_json(asset_path) if asset_path.exists() else {"assets": []}
    if not isinstance(contract, dict) or not isinstance(request_manifest, dict) or not isinstance(asset_manifest, dict):
        raise ValueError("invalid contract, request manifest, or asset manifest")

    scenes = {str(scene["scene_id"]): scene for scene in contract.get("scenes", [])}
    assets = {str(asset.get("shot_id", "")): asset for asset in asset_manifest.get("assets", [])}
    changed_ids: list[str] = []
    skipped_policy_safe_ids: list[str] = []
    request_audit: list[dict[str, Any]] = []
    preserved_assets: list[dict[str, Any]] = []
    updated_requests: list[dict[str, Any]] = []
    changed_by_id: dict[str, dict[str, Any]] = {}
    archive_root = build_dir / "rejected_visual_variants" / ARCHIVE_NAME
    compatibility_path = build_dir / "flow_image_prompts.json"

    for request in request_manifest.get("requests", []):
        scene_id = str(request["scene_id"])
        scene = scenes[scene_id]
        if scene.get("visual_role") not in TARGET_ROLES:
            updated_requests.append(request)
            continue
        if request.get("policy_safe_retry") is True:
            skipped_policy_safe_ids.append(scene_id)
            updated_requests.append(request)
            continue

        updated = compile_scene_request(scene, provider=str(request.get("provider", "flow")))
        if updated["request_sha256"] == request.get("request_sha256"):
            updated_requests.append(request)
            continue

        asset = assets.get(scene_id)
        if (
            asset
            and asset.get("status") == "COMPLETED"
            and str(asset.get("prompt_sha256", "")) == str(request.get("request_sha256", ""))
        ):
            image_source = build_dir / "images" / str(asset.get("file_path", ""))
            if image_source.is_file():
                preserved_assets.append(
                    _preserve_file(image_source, archive_root / "images" / image_source.name, build_dir)
                )
            if scene.get("visual_role") == "host_explainer":
                raw_relative = str(asset.get("postprocess", {}).get("raw_file", f"raw/{scene_id}.jpg"))
                raw_source = build_dir / "images" / raw_relative
                if raw_source.is_file():
                    preserved_assets.append(
                        _preserve_file(raw_source, archive_root / "raw" / raw_source.name, build_dir)
                    )

        updated_requests.append(updated)
        changed_by_id[scene_id] = updated
        changed_ids.append(scene_id)
        request_audit.append({
            "scene_id": scene_id,
            "visual_role": scene.get("visual_role"),
            "old_request_sha256": request.get("request_sha256"),
            "new_request_sha256": updated["request_sha256"],
        })

    preserved_metadata: list[dict[str, Any]] = []
    if changed_ids:
        metadata_sources = [
            (request_path, "image_request_manifest_before.json"),
            (asset_path, "asset_manifest_before.json"),
            (compatibility_path, "flow_image_prompts_before.json"),
        ]
        for source, archive_name in metadata_sources:
            if source.is_file():
                preserved_metadata.append(
                    _preserve_file(source, archive_root / "metadata" / archive_name, build_dir)
                )

    request_manifest["requests"] = updated_requests
    _write_json_atomic(request_path, request_manifest)

    if compatibility_path.exists():
        compatibility = _read_json(compatibility_path)
        if isinstance(compatibility, list):
            for item in compatibility:
                updated = changed_by_id.get(str(item.get("shot_id", "")))
                if updated is None:
                    continue
                item["prompt"] = updated["positive_prompt"]
                item["request_sha256"] = updated["request_sha256"]
                item["negative"] = updated["negative"]
                if "host_overlay" in updated:
                    item["host_overlay"] = updated["host_overlay"]
                else:
                    item.pop("host_overlay", None)
            _write_json_atomic(compatibility_path, compatibility)

    audit = {
        "schema_version": 1,
        "migrated_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive_root": archive_root.relative_to(build_dir).as_posix(),
        "changed_count": len(changed_ids),
        "changed_ids": changed_ids,
        "skipped_policy_safe_ids": skipped_policy_safe_ids,
        "requests": request_audit,
        "preserved_assets": preserved_assets,
        "preserved_metadata": preserved_metadata,
    }
    _write_json_atomic(build_dir / "coherent_scene_migration.json", audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=Path)
    args = parser.parse_args()
    audit = migrate_requests(args.build)
    print(
        f"Migrated {audit['changed_count']} host/evidence request(s); "
        f"preserved {len(audit['preserved_assets'])} current asset file(s)"
    )


if __name__ == "__main__":
    main()
