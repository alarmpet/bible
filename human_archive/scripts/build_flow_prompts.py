# -*- coding: utf-8 -*-
"""Build English Flow prompts from shot_contract.json visual metadata.

Reads shot_contract.json, extracts the `visual` field for each shot,
and produces a structured prompt suitable for Google Flow image generation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_NEGATIVE_SUFFIX = (
    "No text, no watermark, no labels, no modern elements, no UI overlays, "
    "no English signs, no modern clothing, no glasses, no photography equipment. "
    "Photorealistic cinematic historical reconstruction, 8K, dramatic lighting."
)

_ERA_STYLE_MAP = {
    "AD 79": "Ancient Roman era, 1st century AD, classical architecture, toga and tunic clothing",
    "1748": "18th century European Bourbon-era, tricorn hats, period excavation tools",
    "modern_science": "Modern laboratory, clean scientific equipment, subtle lighting",
    "archaeological": "Archaeological excavation site, careful brushwork, layered earth",
}


def build_prompt_from_visual(visual: dict, narration_context: str = "") -> str:
    """Build a detailed English prompt from shot visual metadata."""
    parts = []

    # Main subject
    subject = visual.get("subject", "")
    if subject:
        parts.append(subject)

    # Place and era
    place = visual.get("place", "")
    era = visual.get("era", "AD 79")
    era_style = _ERA_STYLE_MAP.get(era, f"Historical era: {era}")

    if place:
        parts.append(f"Location: {place}")
    parts.append(era_style)

    # Action and mood
    action = visual.get("action", "")
    if action:
        parts.append(f"Action: {action}")

    tone = visual.get("tone", "cinematic, dramatic")
    parts.append(f"Mood: {tone}")

    # Camera angle
    camera = visual.get("camera", "")
    if camera:
        parts.append(f"Camera: {camera}")

    # Compose final prompt
    prompt = ". ".join(parts) + ". " + _NEGATIVE_SUFFIX
    return prompt


def build_prompts_for_contract(contract_path: Path) -> list[dict]:
    """Build prompts for all shots in a contract file."""
    data = json.loads(contract_path.read_text(encoding="utf-8"))
    shots = data.get("shots", [])
    results = []

    for shot in shots:
        shot_id = shot["shot_id"]
        visual = shot.get("visual", {})
        narration = shot.get("tts_text", "")

        if not visual:
            # Fallback: construct minimal visual from narration context
            visual = {
                "subject": f"Historical scene related to: {narration[:80]}",
                "era": "AD 79",
                "tone": "cinematic, dramatic lighting",
            }

        prompt = build_prompt_from_visual(visual, narration)
        results.append({
            "shot_id": shot_id,
            "order": shot.get("order", 0),
            "prompt": prompt,
            "visual_meta": visual,
        })

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    prompts = build_prompts_for_contract(args.contract)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps({"prompts": prompts}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"✅ Built {len(prompts)} Flow prompts → {args.output}")
    else:
        for p in prompts:
            print(f"[{p['shot_id']}] {p['prompt'][:120]}...")


if __name__ == "__main__":
    main()
