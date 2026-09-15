from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from lib.visual_planning import build_visual_contract
from validate_visual_contract import validate_visual_contract


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--scene-plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    script = json.loads(args.script.read_text(encoding="utf-8"))
    scene_plan = json.loads(args.scene_plan.read_text(encoding="utf-8"))
    contract = build_visual_contract(script, scene_plan["scenes"])
    errors = validate_visual_contract(contract, {s["sentence_id"]: s.get("display_text") or s.get("tts_text", "") for s in script.get("sentences", [])})
    if errors:
        for error in errors:
            print(f"- {error}")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
