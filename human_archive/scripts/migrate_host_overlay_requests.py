# -*- coding: utf-8 -*-
"""Atomically migrate only host_explainer requests to the canonical overlay workflow."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.prompt_compiler import compile_scene_request


def _read_json(path: Path) -> dict[str, Any] | list[Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_atomic(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def migrate_host_requests(build_dir: Path) -> list[dict[str, Any]]:
    build_dir = Path(build_dir)
    contract = _read_json(build_dir / "episode_visual_contract_v2.json")
    request_path = build_dir / "image_request_manifest.json"
    request_manifest = _read_json(request_path)
    if not isinstance(contract, dict) or not isinstance(request_manifest, dict):
        raise ValueError("invalid contract or request manifest")
    scenes = {str(scene["scene_id"]): scene for scene in contract.get("scenes", [])}
    original_requests = list(request_manifest.get("requests", []))
    updated_requests = []
    audit_rows = []
    for request in original_requests:
        scene_id = str(request["scene_id"])
        scene = scenes[scene_id]
        if scene.get("visual_role") != "host_explainer":
            updated_requests.append(request)
            continue
        updated = compile_scene_request(scene, provider=str(request.get("provider", "flow")))
        updated_requests.append(updated)
        audit_rows.append({
            "scene_id": scene_id,
            "old_request_sha256": request.get("request_sha256"),
            "new_request_sha256": updated["request_sha256"],
            "host_overlay": updated["host_overlay"],
        })

    request_manifest["requests"] = updated_requests
    _write_json_atomic(request_path, request_manifest)
    compatibility_path = build_dir / "flow_image_prompts.json"
    if compatibility_path.exists():
        compatibility = _read_json(compatibility_path)
        if isinstance(compatibility, list):
            updates_by_id = {row["scene_id"]: row for row in updated_requests}
            for item in compatibility:
                request = updates_by_id.get(str(item.get("shot_id", "")))
                if request and request.get("visual_role") == "host_explainer":
                    item["prompt"] = request["positive_prompt"]
                    item["request_sha256"] = request["request_sha256"]
                    item["host_overlay"] = request["host_overlay"]
            _write_json_atomic(compatibility_path, compatibility)
    _write_json_atomic(build_dir / "host_overlay_migration.json", {
        "schema_version": 1,
        "migrated_at_utc": datetime.now(timezone.utc).isoformat(),
        "host_count": len(audit_rows),
        "requests": audit_rows,
    })
    return audit_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=Path)
    args = parser.parse_args()
    rows = migrate_host_requests(args.build)
    print(f"Migrated {len(rows)} host request(s) to canonical overlay mode")


if __name__ == "__main__":
    main()
