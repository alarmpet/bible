from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from generate_flow_batch import merge_asset_rows, summarize_batch


def rebuild_manifest(build: Path) -> dict:
    requests_data = json.loads((build / "image_request_manifest.json").read_text(encoding="utf-8"))
    requests = requests_data.get("requests", [])
    existing_path = build / "asset_manifest.json"
    existing = json.loads(existing_path.read_text(encoding="utf-8")) if existing_path.exists() else {}
    updates = []
    for order, request in enumerate(requests, 1):
        shot_id = request["scene_id"]
        image_path = build / "images" / f"{shot_id}.jpg"
        if not image_path.exists():
            continue
        digest = hashlib.sha256(image_path.read_bytes()).hexdigest().upper()
        with Image.open(image_path) as image:
            width, height = image.size
        updates.append({
            "shot_id": shot_id,
            "order": int(request.get("order", order)),
            "card_id": f"FLOW-{shot_id}-{digest[:8]}",
            "prompt_sha256": request["request_sha256"],
            "file_path": image_path.name,
            "sha256": digest,
            "bytes": image_path.stat().st_size,
            "width": width,
            "height": height,
            "status": "COMPLETED",
        })
    manifest = merge_asset_rows(existing, updates)
    manifest.update({
        "schema_version": 2,
        "build_id": build.name,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "google_flow_cdp",
    })
    existing_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    expected = [request["scene_id"] for request in requests]
    report = summarize_batch(expected, [row["shot_id"] for row in manifest["assets"] if row.get("status") == "COMPLETED"])
    print(f"rebuilt asset manifest: {report['downloaded_count']}/{report['expected_count']} ({report['status']})")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=Path)
    args = parser.parse_args()
    rebuild_manifest(args.build)


if __name__ == "__main__":
    main()
