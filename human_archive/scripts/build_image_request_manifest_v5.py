from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from lib.provenance import compute_file_sha256


VISUAL_ROLE_BY_MODE = {
    "host_chapter_hinge": "host_explainer",
    "historical_reconstruction": "historical_reconstruction",
    "evidence_artifact": "evidence_object",
    "place_establishing": "atmosphere",
    "analogy_explainer": "diagram_metaphor",
}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_image_request_manifest(build_dir: Path) -> Path:
    build_dir = Path(build_dir)
    prompt_path = build_dir / "flow_image_prompts.json"
    timing_path = build_dir / "shot_timing_manifest.json"
    prompt_data = _read(prompt_path)
    timing_data = _read(timing_path)
    timing_by_id = {str(shot["shot_id"]): shot for shot in timing_data["shots"]}

    rows: list[dict[str, Any]] = []
    for request in prompt_data["requests"]:
        shot_id = str(request["shot_id"])
        timing = timing_by_id[shot_id]
        row = {
            "scene_id": shot_id,
            "shot_id": shot_id,
            "order": timing["order"],
            "start_sec": timing["start_sec"],
            "end_sec": timing["end_sec"],
            "duration_sec": timing["duration_sec"],
            "visual_mode": request["visual_mode"],
            "visual_role": VISUAL_ROLE_BY_MODE.get(request["visual_mode"], "atmosphere"),
            "semantic_anchors": request["semantic_anchors"],
            "submission_prompt": request["submission_prompt"],
            "positive_prompt": request["positive_prompt"],
            "negative": request["negative"],
            "request_sha256": request["request_sha256"],
        }
        if request.get("host_overlay"):
            row["host_overlay"] = request["host_overlay"]
        for optional_key in ("ocr_retry_attempt", "retry_reason"):
            if optional_key in request:
                row[optional_key] = request[optional_key]
        rows.append(row)

    output_data = {
        "schema_version": 2,
        "episode_id": prompt_data["episode_id"],
        "contract_sha256": compute_file_sha256(prompt_path),
        "requests": rows,
    }
    output = build_dir / "image_request_manifest.json"
    output.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    args = parser.parse_args()
    print(build_image_request_manifest(args.build))


if __name__ == "__main__":
    main()
