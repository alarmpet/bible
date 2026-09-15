# -*- coding: utf-8 -*-
"""Plan a role-safe doodle visual contract for any episode script."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from prepare_ep02_v4_workflow import prepare_visual_workflow


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--claims", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target-chars", type=int, default=55)
    args = parser.parse_args()
    script = json.loads(args.script.read_text(encoding="utf-8"))
    claims = json.loads(args.claims.read_text(encoding="utf-8")) if args.claims else {}
    result = prepare_visual_workflow(script, args.output.parent, claims=claims, target_chars=args.target_chars)
    generated = args.output.parent / "episode_visual_contract_v2.json"
    if args.output.resolve() != generated.resolve():
        args.output.write_text(generated.read_text(encoding="utf-8"), encoding="utf-8")
    scenes = result["contract"]["scenes"]
    host_count = sum(scene["visual_role"] == "host_explainer" for scene in scenes)
    print(f"Planned {len(scenes)} scenes; host ratio={host_count / len(scenes):.1%}")
    print(f"Contract: {args.output}")


if __name__ == "__main__":
    main()
