from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PLACEHOLDER_MARKERS = (
    "narration-specific subject",
    "depict the narrated action directly",
    "historical people and setting",
    "period-dressed palace figures perform the single concrete action described by the narration",
    "specific joseon palace location implied by the narration",
)


def validate(build: Path) -> list[str]:
    data = json.loads((build / "flow_image_prompts.json").read_text(encoding="utf-8"))
    requests = data.get("requests", [])
    errors: list[str] = []
    if not requests:
        errors.append("no requests")
        return errors
    if not 95 <= len(requests) <= 120:
        errors.append(f"shot count {len(requests)} outside 95-120")
    for index, request in enumerate(requests):
        if not request.get("semantic_anchors"):
            errors.append(f"{index}: missing semantic anchors")
        elif any(re.search(r"[가-힣]", str(anchor)) for anchor in request.get("semantic_anchors", [])):
            errors.append(f"{index}: hangul semantic anchor may induce generated text")
        prompt = str(request.get("submission_prompt", ""))
        lowered = prompt.lower()
        if any(marker in lowered for marker in PLACEHOLDER_MARKERS):
            errors.append(f"{index}: production placeholder prompt")
        if "1701" in prompt:
            errors.append(f"{index}: forbidden 1701")
        if index and request.get("visual_mode") == "host_chapter_hinge" and requests[index - 1].get("visual_mode") == "host_chapter_hinge":
            errors.append(f"{index}: consecutive hosts")
    hosts = sum(request.get("visual_mode") == "host_chapter_hinge" for request in requests)
    if not 0.08 <= hosts / len(requests) <= 0.12:
        errors.append(f"host ratio {hosts / len(requests):.3f}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    args = parser.parse_args()
    errors = validate(args.build)
    if errors:
        print("\n".join(errors))
        raise SystemExit(1)
    count = len(json.loads((args.build / "flow_image_prompts.json").read_text(encoding="utf-8"))["requests"])
    print(f"PASS: {count} requests")


if __name__ == "__main__":
    main()
