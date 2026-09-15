from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lib.context_sample import load_context_sample_manifest, validate_context_sample_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--source-build", type=Path)
    parser.add_argument("--context-manifest", type=Path)
    parser.add_argument("--delivery-profile")
    parser.add_argument("--phase", choices=["source", "full"], default="full")
    args = parser.parse_args()
    manifest_path = args.context_manifest or (args.build / "source" / "context_sample_manifest.json")
    manifest = load_context_sample_manifest(manifest_path)
    if args.delivery_profile and manifest.get("delivery_profile") != args.delivery_profile:
        print("delivery profile does not match manifest", file=sys.stderr)
        return 1
    source_build = args.source_build or Path(manifest["source_artifacts"]["source_build_path"])
    errors = validate_context_sample_manifest(manifest, source_build)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, "build": str(args.build), "phase": args.phase}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
