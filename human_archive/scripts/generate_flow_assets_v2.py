# -*- coding: utf-8 -*-
"""Generate visual assets with card ID lineage and fail-closed timeout."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.provider_flow import FlowProviderAdapter

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def generate_assets(
    contract_path: Path,
    build_id: str,
    output_root: Path,
    mode: str = "fixture",
    fixture_cards: dict | None = None,
    limit_shots: list[str] | None = None,
    until_sec: float | None = None,
) -> dict:
    contract_data = json.loads(contract_path.read_text(encoding="utf-8"))
    shots = contract_data.get("shots", [])

    build_dir = output_root / build_id
    images_dir = build_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    adapter = FlowProviderAdapter(mode=mode)
    assets = []

    elapsed_sec = 0.0

    for s in shots:
        sid = s["shot_id"]
        if limit_shots and sid not in limit_shots:
            continue

        if until_sec and elapsed_sec >= until_sec:
            break

        # Simulate or perform generation
        asset_info = adapter.generate_shot_asset(s, images_dir, fixture_cards=fixture_cards)
        assets.append(asset_info)

        dur_target = s.get("duration_target_sec", [4.0, 8.0])
        elapsed_sec += dur_target[0]

    manifest = {
        "schema_version": 1,
        "build_id": build_id,
        "contract_sha256": contract_data.get("contract_sha256", ""),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "assets": assets,
    }

    manifest_path = build_dir / "asset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    has_failures = any(a["status"] != "COMPLETED" for a in assets)
    if has_failures:
        print(f"⚠️ Generated asset manifest with failures: {manifest_path}")
    else:
        print(f"✅ Generated clean asset manifest: {manifest_path} ({len(assets)} assets)")

    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--build-id", required=True, type=str)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--mode", default="fixture", choices=["fixture", "cdp"])
    parser.add_argument("--shots", nargs="*")
    parser.add_argument("--until-sec", type=float)
    args = parser.parse_args()

    # Default valid fixture cards map for tests/smoke
    c_data = json.loads(args.contract.read_text(encoding="utf-8"))
    valid_cards = {s["shot_id"]: {"card_id": f"CARD-FX-{s['shot_id']}", "status": "COMPLETED"} for s in c_data.get("shots", [])}

    manifest = generate_assets(
        args.contract,
        args.build_id,
        args.output_root,
        mode=args.mode,
        fixture_cards=valid_cards,
        limit_shots=args.shots,
        until_sec=args.until_sec,
    )

    failed = any(a["status"] != "COMPLETED" for a in manifest["assets"])
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
