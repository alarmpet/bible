from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_image_request_manifest_v5 import build_image_request_manifest
from lib.provenance import compute_file_sha256


OCR_POSITIVE_CONSTRAINT = (
    "OCR-safe retry composition: use only broad clean shapes and smooth blank surfaces; "
    "remove every paper, book, scroll, sign, plaque, banner, seal, label, patterned border, "
    "decorative glyph, tally, and repeated small mark that could resemble text"
)
OCR_NEGATIVE_CONSTRAINT = (
    "text-like strokes, pseudo-writing, glyph-like decoration, repeated short lines, "
    "alphabet-like shapes, numeral-like shapes, character-like marks"
)
OCR_ULTRA_POSITIVE_CONSTRAINT = (
    "Ultra-minimal OCR-safe retry: show one large focal subject in an uncluttered scene with "
    "broad flat unpatterned walls, garments, and objects; use very low detail and generous empty space"
)
OCR_ULTRA_NEGATIVE_CONSTRAINT = (
    "grids and lattice, repeated vertical or horizontal strokes, repeated circles, patterned fabric, "
    "roof-end ornament, shelf rows, grouped containers, tiny props, dense architectural detail"
)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_atomic(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _request_sha(request: dict[str, Any]) -> str:
    payload = dict(request)
    payload.pop("request_sha256", None)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest().upper()


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


def backfill_ocr_asset_history(build_dir: Path) -> int:
    build_dir = Path(build_dir)
    asset_path = build_dir / "asset_manifest.json"
    audit_path = build_dir / "ocr_retry_manifest.json"
    if not asset_path.exists() or not audit_path.exists():
        return 0
    manifest = _read(asset_path)
    audit = _read(audit_path)
    history = list(manifest.get("asset_history", []))
    keys = {
        (str(row.get("shot_id", "")), str(row.get("prompt_sha256", "")), str(row.get("sha256", "")))
        for row in history
    }
    added = 0
    for retry in audit.get("retries", []):
        archived = retry.get("archived_asset") or {}
        relative = str(archived.get("file_path", ""))
        if not relative:
            continue
        archived_path = build_dir / relative
        if not archived_path.exists():
            continue
        row = {
            "shot_id": str(retry.get("scene_id", "")),
            "prompt_sha256": str(retry.get("old_request_sha256", "")),
            "sha256": str(archived.get("sha256", "")),
            "file_path": relative,
            "archived_file_path": relative,
            "bytes": archived_path.stat().st_size,
            "width": 1920,
            "height": 1080,
            "status": "COMPLETED",
            "archive_reason": "embedded_text_detected",
            "replaced_by_prompt_sha256": str(retry.get("new_request_sha256", "")),
            "archived_at_utc": str(retry.get("rewritten_at_utc", "")),
        }
        key = (row["shot_id"], row["prompt_sha256"], row["sha256"])
        if key in keys:
            continue
        history.append(row)
        keys.add(key)
        added += 1
    if added:
        manifest["asset_history"] = history
        _write_atomic(asset_path, manifest)
    return added


def rewrite_ocr_failed(build_dir: Path, scene_ids: list[str]) -> dict[str, Any]:
    build_dir = Path(build_dir)
    flow_path = build_dir / "flow_image_prompts.json"
    asset_path = build_dir / "asset_manifest.json"
    audit_path = build_dir / "ocr_retry_manifest.json"
    flow = _read(flow_path)
    requests = {str(row["shot_id"]): row for row in flow.get("requests", [])}
    unknown = sorted(set(scene_ids) - set(requests))
    if unknown:
        raise ValueError(f"unknown scene IDs: {unknown}")
    if len(scene_ids) != len(set(scene_ids)):
        raise ValueError("duplicate scene IDs are not allowed")

    asset_manifest = _read(asset_path) if asset_path.exists() else {"assets": []}
    assets = {str(row.get("shot_id", "")): row for row in asset_manifest.get("assets", [])}
    archive_root = build_dir / "rejected_visual_variants" / "ocr-detected-001"
    audit = _read(audit_path) if audit_path.exists() else {"schema_version": 1, "retries": []}
    retry_rows = list(audit.get("retries", []))
    changed_ids: list[str] = []
    archived_assets: list[dict[str, Any]] = []
    history = list(asset_manifest.get("asset_history", []))
    history_keys = {
        (str(row.get("shot_id", "")), str(row.get("prompt_sha256", "")), str(row.get("sha256", "")))
        for row in history
    }

    for scene_id in scene_ids:
        request = requests[scene_id]
        old_sha = str(request.get("request_sha256", ""))
        attempt = int(request.get("ocr_retry_attempt", 0)) + 1
        if OCR_POSITIVE_CONSTRAINT not in str(request.get("positive_prompt", "")):
            request["positive_prompt"] = f"{request.get('positive_prompt', '')}; {OCR_POSITIVE_CONSTRAINT}"
        negative = request.setdefault("negative", {"mode": "prompt_exclusion", "items": []})
        items = list(negative.get("items", []))
        if OCR_NEGATIVE_CONSTRAINT not in items:
            items.append(OCR_NEGATIVE_CONSTRAINT)
        if attempt >= 2:
            if OCR_ULTRA_POSITIVE_CONSTRAINT not in str(request.get("positive_prompt", "")):
                request["positive_prompt"] = (
                    f"{request.get('positive_prompt', '')}; {OCR_ULTRA_POSITIVE_CONSTRAINT}"
                )
            if OCR_ULTRA_NEGATIVE_CONSTRAINT not in items:
                items.append(OCR_ULTRA_NEGATIVE_CONSTRAINT)
        negative["items"] = items
        request["submission_prompt"] = (
            str(request["positive_prompt"]) + ". Strict exclusions: " + "; ".join(items) + "."
        )
        request["ocr_retry_attempt"] = attempt
        request["retry_reason"] = "embedded_text_detected"
        request["request_sha256"] = _request_sha(request)
        changed_ids.append(scene_id)

        asset = assets.get(scene_id)
        archived: dict[str, Any] | None = None
        if asset and asset.get("file_path"):
            source = build_dir / "images" / str(asset["file_path"])
            if source.is_file():
                archived = _archive_file(source, archive_root / scene_id, stem="variant")
                archived["file_path"] = Path(archived["file_path"]).relative_to(build_dir).as_posix()
                archived_assets.append({"scene_id": scene_id, **archived})
                snapshot = dict(asset)
                snapshot["archive_reason"] = "embedded_text_detected"
                snapshot["archived_file_path"] = archived["file_path"]
                snapshot["replaced_by_prompt_sha256"] = request["request_sha256"]
                snapshot["archived_at_utc"] = datetime.now(timezone.utc).isoformat()
                history_key = (
                    str(snapshot.get("shot_id", "")),
                    str(snapshot.get("prompt_sha256", "")),
                    str(snapshot.get("sha256", "")),
                )
                if history_key not in history_keys:
                    history.append(snapshot)
                    history_keys.add(history_key)
            raw_relative = str((asset.get("postprocess") or {}).get("raw_file", ""))
            raw_source = build_dir / "images" / raw_relative if raw_relative else None
            if raw_source and raw_source.is_file():
                raw_archive = _archive_file(raw_source, archive_root / scene_id, stem="raw")
                raw_archive["file_path"] = Path(raw_archive["file_path"]).relative_to(build_dir).as_posix()
                archived_assets.append({"scene_id": scene_id, **raw_archive})

        retry_rows.append({
            "scene_id": scene_id,
            "reason": "embedded_text_detected",
            "attempt": attempt,
            "old_request_sha256": old_sha,
            "new_request_sha256": request["request_sha256"],
            "archived_asset": archived,
            "rewritten_at_utc": datetime.now(timezone.utc).isoformat(),
        })

    flow["requests"] = [requests[str(row["shot_id"])] for row in flow.get("requests", [])]
    if asset_path.exists():
        asset_manifest["asset_history"] = history
        _write_atomic(asset_path, asset_manifest)
    _write_atomic(flow_path, flow)
    image_request_path = build_image_request_manifest(build_dir)
    audit["retries"] = retry_rows
    audit["latest_changed_ids"] = changed_ids
    audit["latest_contract_sha256"] = _read(image_request_path).get("contract_sha256", "")
    _write_atomic(audit_path, audit)
    return {
        "changed_ids": changed_ids,
        "archived_assets": archived_assets,
        "image_request_manifest": image_request_path.as_posix(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--scene-id", required=True, nargs="+")
    args = parser.parse_args()
    result = rewrite_ocr_failed(args.build, args.scene_id)
    print(f"OCR retry prompts updated: {len(result['changed_ids'])}")
    for scene_id in result["changed_ids"]:
        print(scene_id)


if __name__ == "__main__":
    main()
