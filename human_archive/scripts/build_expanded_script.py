from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.script_expansion import (
    apply_script_metadata_patches,
    compile_script_expansion,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--expansion", type=Path, required=True)
    parser.add_argument("--metadata-patches", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    base = json.loads(args.base.read_text(encoding="utf-8"))
    claims = json.loads(args.claims.read_text(encoding="utf-8"))
    expansion = json.loads(args.expansion.read_text(encoding="utf-8"))
    result = compile_script_expansion(base, claims, expansion)
    if args.metadata_patches:
        patch_manifest = json.loads(args.metadata_patches.read_text(encoding="utf-8"))
        result = apply_script_metadata_patches(result, claims, patch_manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".part")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(args.output)
    patch_count = 0
    if args.metadata_patches:
        patch_count = len(patch_manifest.get("patches", []))
    print(
        f"Expanded script: {len(base['sentences'])} -> "
        f"{len(result['sentences'])} sentences; metadata patches: {patch_count}"
    )


if __name__ == "__main__":
    main()
