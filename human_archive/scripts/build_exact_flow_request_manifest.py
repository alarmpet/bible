"""Build the exact-release 80-request Google Flow image manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


STYLE_PREFIX = (
    "2D graphic novel illustration, bold clean black ink contour outlines, clean ligne claire, "
    "flat cel-shaded coloring, Korean webtoon documentary aesthetic"
)
STYLE_SUFFIX = (
    "keep the bottom 18% visually clear for subtitles, no photorealism, no 3D render, "
    "no live-action photograph, no text, no watermark, no logo"
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def build_manifest(plan_path: Path, output_path: Path, *, expected_count: int = 80) -> Path:
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    plates = list(plan.get("plates", []))
    if len(plates) != expected_count:
        raise ValueError(
            f"Exact Flow manifest requires {expected_count} A/B plates, found {len(plates)}"
        )

    requests: list[dict[str, Any]] = []
    for order, plate in enumerate(plates, start=1):
        plate_id = str(plate["plate_id"])
        prompt = f"{STYLE_PREFIX}, {plate['flow_prompt_en']}, {STYLE_SUFFIX}."
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
