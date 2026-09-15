from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from generate_visual_briefs import select_host_shot_ids
from lib.semantic_image_reuse import plan_semantic_image_reuse


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-build", type=Path, required=True)
    parser.add_argument("--target-build", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--host-ratio", type=float, default=0.10)
    parser.add_argument("--host-min-non-host-gap", type=int, default=7)
    args = parser.parse_args()

    source_build = args.source_build.resolve()
    target_build = args.target_build.resolve()
    source_assets = copy.deepcopy(_read(source_build / "asset_manifest.json"))
    for asset in source_assets.get("assets", []):
        file_path = str(asset.get("file_path", ""))
        if file_path and not (source_build / "images" / file_path).exists():
            asset["status"] = "MISSING"

    source_script = _read(source_build / "source" / "script_candidate.json")
    target_timing = _read(target_build / "shot_timing_manifest.json")
    target_host_shot_ids = select_host_shot_ids(
        target_timing["shots"],
        ratio=args.host_ratio,
        min_non_host_gap=args.host_min_non_host_gap,
    )
    result = plan_semantic_image_reuse(
        _read(source_build / "shot_timing_manifest.json"),
        target_timing,
        _read(source_build / "visual_brief_manifest.json"),
        source_assets,
        base_sentence_ids={
            str(sentence["sentence_id"])
            for sentence in source_script.get("sentences", [])
        },
        target_host_shot_ids=target_host_shot_ids,
        source_request_manifest=_read(source_build / "image_request_manifest.json"),
        target_request_manifest=_read(target_build / "image_request_manifest.json"),
    )
    result["source_build"] = str(source_build)
    result["target_build"] = str(target_build)
    output = args.output or target_build / "image_reuse_plan.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    temporary.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(output)
    print(json.dumps(result["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
