# -*- coding: utf-8 -*-
"""Bind generated or pre-existing images to canonical image requests."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from PIL import Image


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def bind_existing_assets(requests: list[dict[str, Any]], images_dir: Path) -> dict[str, Any]:
    assets = []
    images_dir = Path(images_dir)
    for request in requests:
        scene_id = request["scene_id"]
        path = images_dir / f"{scene_id}.jpg"
        item = {"request_id": request["request_id"], "scene_id": scene_id, "request_sha256": request["request_sha256"], "file_path": path.name}
        if not path.exists():
            item.update({"status": "MISSING", "sha256": "", "width": 0, "height": 0})
        else:
            with Image.open(path) as image:
                item.update({"status": "COMPLETED", "sha256": _sha(path), "width": image.width, "height": image.height})
        assets.append(item)
    return {"schema_version": 1, "assets": assets}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.requests.read_text(encoding="utf-8"))
    result = bind_existing_assets(manifest.get("requests", []), args.images)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
