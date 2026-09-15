# -*- coding: utf-8 -*-
"""Fail-closed validation for the caption-to-scene visual contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

GENERIC_ACTIONS = {"Scene depicting historical context...", "historical context"}


def validate_visual_contract(contract: dict[str, Any], script_sentences: dict[str, str] | None = None) -> list[str]:
    errors: list[str] = []
    script_sentences = script_sentences or {}
    scenes = {s.get("scene_id"): s for s in contract.get("scenes", [])}
    caption_ids: set[str] = set()
    for caption in contract.get("captions", []):
        cid = caption.get("caption_id", "")
        if cid in caption_ids:
            errors.append(f"Duplicate caption_id '{cid}'")
        caption_ids.add(cid)
        sid = caption.get("sentence_id", "")
        if script_sentences and sid not in script_sentences:
            errors.append(f"Sentence ID '{sid}' not in approved script")
        if sid in script_sentences and caption.get("text_span", "") not in script_sentences[sid]:
            errors.append(f"Caption '{cid}' text_span is not contained in sentence '{sid}'")
        if caption.get("scene_id") not in scenes:
            errors.append(f"Caption '{cid}' references missing scene '{caption.get('scene_id')}'")
    referenced = {c.get("scene_id") for c in contract.get("captions", [])}
    for scene in contract.get("scenes", []):
        sid = scene.get("scene_id", "")
        if sid not in referenced:
            errors.append(f"Orphan scene '{sid}'")
        for key in ("visual_beat", "place", "era", "action", "depiction_mode"):
            if not scene.get(key):
                errors.append(f"Scene '{sid}' missing required field '{key}'")
        actions = scene.get("action", [])
        if any(str(action).strip() in GENERIC_ACTIONS for action in actions):
            errors.append(f"Generic action in scene '{sid}'")
    if script_sentences:
        covered = {c.get("sentence_id") for c in contract.get("captions", [])}
        for sid in script_sentences:
            if sid not in covered:
                errors.append(f"Approved sentence '{sid}' has no caption")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", type=Path)
    parser.add_argument("--script", type=Path)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    script = {}
    if args.script:
        data = json.loads(args.script.read_text(encoding="utf-8"))
        script = {s["sentence_id"]: s.get("display_text") or s.get("tts_text", "") for s in data.get("sentences", [])}
    errors = validate_visual_contract(contract, script)
    if errors:
        for error in errors:
            print(f"- {error}")
        return 1
    print("Visual contract validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
