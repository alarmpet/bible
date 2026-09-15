from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from lib.prompt_compiler import compile_scene_request


def compile_request_manifest(contract: dict, *, provider: str = "flow") -> dict:
    requests = []
    scenes = contract.get("scenes", [])
    if not scenes and contract.get("shots"):
        scenes = []
        for shot in contract["shots"]:
            visual = shot.get("visual", {})
            scenes.append({
                "scene_id": shot["shot_id"],
                "visual_beat": shot.get("display_text") or shot.get("tts_text") or shot["shot_id"],
                "subject_refs": visual.get("subject", []) if isinstance(visual.get("subject", []), list) else [visual.get("subject", "")],
                "action": visual.get("action", []) if isinstance(visual.get("action", []), list) else [visual.get("action", "")],
                "place": visual.get("place", ""), "era": visual.get("era", ""),
                "camera": visual.get("camera", ""), "composition": visual.get("composition", ""),
                "lighting": visual.get("lighting", ""), "style": visual.get("style", ""),
                "must_not": visual.get("must_not", []), "forbidden_implications": visual.get("forbidden_implications", []),
            })
    for scene in scenes:
        request = compile_scene_request(scene, provider=provider)
        request["request_id"] = f"req-{scene['scene_id']}"
        requests.append(request)
    return {"schema_version": 1, "episode_id": contract.get("episode_id", ""), "provider": provider, "requests": requests}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provider", default="flow")
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    manifest = compile_request_manifest(contract, provider=args.provider)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
