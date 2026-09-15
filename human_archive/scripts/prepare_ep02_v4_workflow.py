# -*- coding: utf-8 -*-
"""Build role-aware doodle visual contracts and provider requests from a script."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from lib.doodle_scene_planner import plan_scenes
from lib.doodle_visual_roles import validate_role_mix
from lib.prompt_compiler import compile_scene_request


def _canonical_sha(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def prepare_visual_workflow(
    script: dict[str, Any],
    output_root: Path,
    *,
    claims: dict[str, Any] | None = None,
    target_chars: int = 55,
) -> dict[str, Any]:
    output_root = Path(output_root)
    source_dir = output_root.parent / "source"
    scenes = plan_scenes(script["sentences"], claims or {}, target_chars=target_chars)
    validate_role_mix(scenes)

    contract = {
        "schema_version": 2,
        "episode_id": script.get("episode_id", "HA002"),
        "title": script.get("title", "EP02"),
        "script_sha256": _canonical_sha(script),
        "channel_profile_id": "doodle_seonbi_v1",
        "scenes": scenes,
    }
    image_requests = [compile_scene_request(scene) for scene in scenes]
    image_request_manifest = {
        "schema_version": 2,
        "episode_id": contract["episode_id"],
        "contract_sha256": _canonical_sha(contract),
        "requests": image_requests,
    }
    overlay_events = [
        {
            "scene_id": scene["scene_id"],
            "sentence_ids": scene["sentence_ids"],
            "items": scene["overlay_text"],
            "render_layer": "deterministic_overlay",
        }
        for scene in scenes
        if scene["overlay_text"]
    ]
    overlay_manifest = {
        "schema_version": 1,
        "episode_id": contract["episode_id"],
        "events": overlay_events,
    }

    compatibility_shots = []
    compatibility_prompts = []
    request_by_id = {request["scene_id"]: request for request in image_requests}
    for scene in scenes:
        scene_id = scene["scene_id"]
        request = request_by_id[scene_id]
        shot = {
            "shot_id": scene_id,
            "order": scene["order"],
            "chapter": scene["chapter"],
            "sentence_ids": scene["sentence_ids"],
            "tts_text": scene["narration_text"],
            "display_text": scene["narration_text"],
            "duration_target_sec": [4.0, 12.0],
            "visual_role": scene["visual_role"],
            "host_mode": scene["host_mode"],
            "visual": {
                "subject": scene["historical_subjects"],
                "place": scene["place"],
                "era": scene["era_context"],
                "art_style": "doodle_seonbi_v1",
                "lighting": scene["lighting"],
                "action": scene["action"],
                "disclosure": "AI historical reconstruction",
            },
        }
        compatibility_shots.append(shot)
        compatibility_prompts.append({
            "shot_id": scene_id,
            "order": scene["order"],
            "filename": f"{scene_id}.jpg",
            "prompt": request["positive_prompt"],
            "negative": request["negative"],
            "request_sha256": request["request_sha256"],
            "source_sentence_ids": scene["sentence_ids"],
            "visual_role": scene["visual_role"],
            "host_mode": scene["host_mode"],
        })

    shot_contract = {
        "schema_version": 2,
        "episode_id": contract["episode_id"],
        "title": contract["title"],
        "script_sha256": contract["script_sha256"],
        "shots": compatibility_shots,
    }
    _write_json(output_root / "episode_visual_contract_v2.json", contract)
    _write_json(output_root / "image_request_manifest.json", image_request_manifest)
    _write_json(output_root / "overlay_event_manifest.json", overlay_manifest)
    _write_json(output_root / "flow_image_prompts.json", compatibility_prompts)
    _write_json(source_dir / "shot_contract_v4.json", shot_contract)
    return {
        "contract": contract,
        "image_requests": image_requests,
        "overlay_manifest": overlay_manifest,
        "shot_contract": shot_contract,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--claims", type=Path)
    parser.add_argument("--target-chars", type=int, default=55)
    args = parser.parse_args()
    script = json.loads(args.script.read_text(encoding="utf-8"))
    claims = json.loads(args.claims.read_text(encoding="utf-8")) if args.claims else {}
    result = prepare_visual_workflow(script, args.output_root, claims=claims, target_chars=args.target_chars)
    print(f"Prepared {len(result['contract']['scenes'])} role-aware scenes from {len(script['sentences'])} sentences")
    print(f"Visual contract: {args.output_root / 'episode_visual_contract_v2.json'}")
    print(f"Image requests: {args.output_root / 'image_request_manifest.json'}")


if __name__ == "__main__":
    main()
