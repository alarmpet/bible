"""Build the exact-release 80-request Google Flow image manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any


STYLE_PREFIX = (
    "2D graphic novel illustration, bold black ink contour outlines, clean ligne claire, "
    "flat cel-shaded colors, Korean webtoon documentary aesthetic"
)
STYLE_SUFFIX = (
    "flat lower 18% subtitle-safe area, no photorealism, no 3D, no text, no watermark, no logos"
)
MAX_PROMPT_CHARS = 441
FLOW_PROJECT_URL = "https://flow.google.com/project/8550306b-a63c-450f-beda-5ed1d72a760e"
FLOW_PROJECT_ID = "8550306b-a63c-450f-beda-5ed1d72a760e"

_SENSITIVE_REPLACEMENTS = (
    (r"disintegrating[^,.;]*", "abstract molecular crystal diagram"),
    (r"(?:intense\s+)?uv\s+rays?", "warm light rays"),
    (r"healthy\s+cellular\s+membrane", "abstract educational cell diagram"),
    (r"folate(?:\s+vitamin)?\s+b9|vitamin\s+b9|folate", "amber molecular nutrient"),
    (r"sickle(?:[- ]cell|[- ]shaped)?|erythrocyte|hemoglobin|malaria", "abstract curved cell"),
    (r"medical", "educational"),
    (r"photorealistic", "illustrated"),
)

_REMOVE_CLAUSES = (
    "2d graphic novel illustration", "bold black ink contour outlines",
    "flat cel-shaded colors",
    "2d graphic novel illustration style", "bold clean black ink contour outlines",
    "clean ligne claire", "flat cel-shaded coloring", "korean webtoon documentary aesthetic",
    "no photorealism", "no photorealistic", "no 3d render", "no live-action photograph",
    "no camera lens flare", "zero watermark", "keep bottom 18% visually clear for subtitles",
    "keep the bottom 18% visually clear for subtitles", "no text", "no watermark", "no logo",
    "no logos", "cinematic photograph", "bbc documentary realism", "human emotional realism",
    "35mm", "f/1.8",
)


def sanitize_flow_prompt(prompt: str, *, max_chars: int = MAX_PROMPT_CHARS) -> str:
    """Normalize a plan prompt into one bounded, safe Flow still-image request."""
    text = re.sub(r"\s+", " ", str(prompt or "")).strip(" ,.")
    for pattern, replacement in _SENSITIVE_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    for clause in _REMOVE_CLAUSES:
        text = re.sub(re.escape(clause), "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*,\s*", ", ", text)
    clauses: list[str] = []
    seen: set[str] = set()
    for clause in (part.strip(" ,.") for part in text.split(",")):
        if not clause:
            continue
        key = clause.casefold()
        if key in seen:
            continue
        seen.add(key)
        clauses.append(clause)
    core = ", ".join(clauses) or "editorial documentary scene"
    fixed = f"{STYLE_PREFIX}, {core}, {STYLE_SUFFIX}."
    if len(fixed) > max_chars:
        budget = max_chars - len(STYLE_PREFIX) - len(STYLE_SUFFIX) - 4
        core = core[:max(1, budget)].rsplit(" ", 1)[0].rstrip(" ,.")
        fixed = f"{STYLE_PREFIX}, {core}, {STYLE_SUFFIX}."
    return fixed


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def build_manifest(
    plan_path: Path,
    output_path: Path,
    *,
    expected_count: int = 80,
    asset_manifest_path: Path | None = None,
) -> Path:
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    plates = list(plan.get("plates", []))
    if len(plates) != expected_count:
        raise ValueError(
            f"Exact Flow manifest requires {expected_count} A/B plates, found {len(plates)}"
        )

    requests: list[dict[str, Any]] = []
    for order, plate in enumerate(plates, start=1):
        plate_id = str(plate["plate_id"])
        prompt = sanitize_flow_prompt(plate["flow_prompt_en"])

        requests.append(
            {
                "scene_id": plate_id,
                "shot_id": str(plate.get("parent_shot_id", plate_id)),
                "plate_id": plate_id,
                "order": order,
                "visual_mode": "exact_2d_webtoon_plate",
                "visual_role": str(plate.get("plate_role", "documentary_plate")),
                "positive_prompt": prompt,
                "submission_prompt": prompt,
                "negative": "photorealism, live action, 3d render, text, watermark, logo",
                "request_sha256": _sha256_text(prompt),
            }
        )

    payload = {
        "schema_version": 2,
        "episode_id": "HL-RANK1-EXACT-CLONE-V1",
        "provider": "google_flow_cdp_playwright",
        "project_url": FLOW_PROJECT_URL,
        "project_id": FLOW_PROJECT_ID,
        "target_dimensions": {"width": 2304, "height": 1296},
        "contract_sha256": _sha256_text(Path(plan_path).read_text(encoding="utf-8")),
        "requests": requests,
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    with open(temporary, "r+b") as handle:
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, output_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(build_manifest(args.plan, args.output))


if __name__ == "__main__":
    main()
