from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_image_request_manifest_v5 import build_image_request_manifest
from lib.aligned_prompt_compiler import compile_aligned_prompt
from lib.provenance import compute_file_sha256
from lib.visual_brief_provider import build_fallback_brief


GENERIC_MARKERS = (
    "period-dressed palace figures perform the single concrete action described by the narration",
    "specific Joseon palace location implied by the narration",
)
HOST_INDICES = {0, 10, 20, 30, 40, 50, 60, 70, 80, 100}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def is_generic_brief(brief: dict[str, Any]) -> bool:
    anchors = " ".join(str(value) for value in brief.get("semantic_anchors", []))
    rendered = " ".join(str(brief.get(key, "")) for key in ("focal_subject", "action", "place"))
    return bool(re.search(r"[가-힣]", anchors)) or any(marker in rendered for marker in GENERIC_MARKERS)


def _archive_file(source: Path, archive_dir: Path, *, stem: str) -> dict[str, Any]:
    archive_dir.mkdir(parents=True, exist_ok=True)
    source_sha = compute_file_sha256(source)
    existing = sorted(archive_dir.glob(f"{stem}-*{source.suffix.lower()}"))
    for candidate in existing:
        if compute_file_sha256(candidate) == source_sha:
            return {"file_path": candidate.as_posix(), "sha256": source_sha, "reused": True}
    destination = archive_dir / f"{stem}-{len(existing) + 1:03d}{source.suffix.lower()}"
    shutil.copy2(source, destination)
    return {"file_path": destination.as_posix(), "sha256": source_sha, "reused": False}


def migrate_semantic_briefs(
    build_dir: Path,
    *,
    script_path: Path,
    timing_path: Path,
    expected_count: int | None = None,
) -> dict[str, Any]:
    build_dir = Path(build_dir)
    script_path = Path(script_path)
    timing_path = Path(timing_path)
    brief_path = build_dir / "visual_brief_manifest.json"
    flow_path = build_dir / "flow_image_prompts.json"
    asset_path = build_dir / "asset_manifest.json"
    old_brief_manifest = _read(brief_path)
    old_flow = _read(flow_path)
    timing = _read(timing_path)
    script = _read(script_path)
    sentence_texts = {
        str(sentence["sentence_id"]): str(sentence.get("tts_text", ""))
        for sentence in script.get("sentences", [])
    }
    old_briefs = {str(row["shot_id"]): row for row in old_brief_manifest.get("briefs", [])}
    old_requests = {str(row["shot_id"]): row for row in old_flow.get("requests", [])}
    target_ids = [
        str(shot["shot_id"])
        for shot in timing.get("shots", [])
        if is_generic_brief(old_briefs[str(shot["shot_id"])])
    ]
    if expected_count is not None and len(target_ids) != expected_count:
        raise ValueError(f"expected {expected_count} generic briefs, found {len(target_ids)}")

    updated_briefs = dict(old_briefs)
    updated_requests = dict(old_requests)
    for index, shot in enumerate(timing.get("shots", [])):
        shot_id = str(shot["shot_id"])
        if shot_id not in target_ids:
            continue
        brief = build_fallback_brief(shot, sentence_texts)
        if index in HOST_INDICES:
            brief["visual_mode"] = "host_chapter_hinge"
            brief["motion_profile"] = "host_hinge"
        updated_briefs[shot_id] = brief
        updated_requests[shot_id] = compile_aligned_prompt(brief)

    archive_root = build_dir / "rejected_visual_variants" / "semantic-fallback-002"
    for source_name in (
        "visual_brief_manifest.json",
        "flow_image_prompts.json",
        "image_request_manifest.json",
        "asset_manifest.json",
        "contact_sheet.jpg",
        "visual_content_report.json",
    ):
        source = build_dir / source_name
        if source.is_file():
            _archive_file(source, archive_root / "metadata", stem=source.stem)

    asset_manifest = _read(asset_path) if asset_path.exists() else {"assets": []}
    history = list(asset_manifest.get("asset_history", []))
    history_keys = {
        (str(row.get("shot_id", "")), str(row.get("prompt_sha256", "")), str(row.get("sha256", "")))
        for row in history
    }
    assets_by_id = {str(row.get("shot_id", "")): row for row in asset_manifest.get("assets", [])}
    preserved_assets: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()
    for shot_id in target_ids:
        asset = assets_by_id.get(shot_id)
        if not asset or not asset.get("file_path"):
            continue
        image_path = build_dir / "images" / str(asset["file_path"])
        if not image_path.is_file():
            continue
        archived = _archive_file(image_path, archive_root / shot_id, stem="variant")
        archived_relative = Path(archived["file_path"]).relative_to(build_dir).as_posix()
        preserved_assets.append({"shot_id": shot_id, "file_path": archived_relative, "sha256": archived["sha256"]})
        snapshot = dict(asset)
        snapshot.update({
            "archive_reason": "generic_semantic_fallback",
            "archived_file_path": archived_relative,
            "replaced_by_prompt_sha256": updated_requests[shot_id]["request_sha256"],
            "archived_at_utc": now,
        })
        key = (str(snapshot.get("shot_id", "")), str(snapshot.get("prompt_sha256", "")), str(snapshot.get("sha256", "")))
        if key not in history_keys:
            history.append(snapshot)
            history_keys.add(key)
        raw_relative = str((asset.get("postprocess") or {}).get("raw_file", ""))
        raw_path = build_dir / "images" / raw_relative if raw_relative else None
        if raw_path and raw_path.is_file():
            raw_archived = _archive_file(raw_path, archive_root / shot_id, stem="raw")
            preserved_assets.append({
                "shot_id": shot_id,
                "file_path": Path(raw_archived["file_path"]).relative_to(build_dir).as_posix(),
                "sha256": raw_archived["sha256"],
            })
    if asset_path.exists():
        asset_manifest["asset_history"] = history
        _write_atomic(asset_path, asset_manifest)

    brief_rows = [updated_briefs[str(shot["shot_id"])] for shot in timing.get("shots", [])]
    request_rows = [updated_requests[str(shot["shot_id"])] for shot in timing.get("shots", [])]
    new_brief_manifest = dict(old_brief_manifest)
    new_brief_manifest.update({
        "script_sha256": timing.get("script_sha256", ""),
        "timing_sha256": timing.get("timing_sha256", ""),
        "provider": "curated",
        "model": "deterministic-semantic-v2",
        "briefs": brief_rows,
    })
    new_brief_manifest["brief_manifest_sha256"] = hashlib.sha256(
        json.dumps(brief_rows, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    new_flow = dict(old_flow)
    new_flow["requests"] = request_rows
    _write_atomic(brief_path, new_brief_manifest)
    _write_atomic(flow_path, new_flow)
    image_request_path = build_image_request_manifest(build_dir)

    audit = {
        "schema_version": 1,
        "migrated_at_utc": now,
        "changed_count": len(target_ids),
        "changed_ids": target_ids,
        "archive_root": archive_root.relative_to(build_dir).as_posix(),
        "preserved_assets": preserved_assets,
        "brief_manifest_sha256": new_brief_manifest["brief_manifest_sha256"],
        "contract_sha256": _read(image_request_path).get("contract_sha256", ""),
    }
    _write_atomic(build_dir / "semantic_brief_migration.json", audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--timing", type=Path, required=True)
    parser.add_argument("--expected-count", type=int)
    args = parser.parse_args()
    result = migrate_semantic_briefs(
        args.build,
        script_path=args.script,
        timing_path=args.timing,
        expected_count=args.expected_count,
    )
    print(f"Semantic briefs migrated: {result['changed_count']}")
    for shot_id in result["changed_ids"]:
        print(shot_id)


if __name__ == "__main__":
    main()
