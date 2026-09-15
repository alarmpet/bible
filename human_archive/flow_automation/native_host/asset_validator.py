from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from PIL import Image, ImageOps, UnidentifiedImageError

from flow_automation.native_host.job_store import atomic_write_json

TARGET_SIZE = (1920, 1080)
PARTIAL_SUFFIXES = {".crdownload", ".partial"}
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}

@dataclass(frozen=True)
class AssetValidationResult:
    status: str
    code: str
    sha256: str | None
    width: int | None
    height: int | None
    mime_type: str | None
    approved_path: str | None
    rejected_path: str | None
    source_sha256: str | None = None

def validate_asset(job: Mapping[str, Any], shot_id: str, chrome_path: str | Path, downloads_root: str | Path, prior_assets: list[Any], *, binding: Mapping[str, Any]) -> AssetValidationResult:
    """Validate one completed download using binding={expected: {...}, observed: {...}}. Both subobjects require job_id, shot_id, prompt_sha256, attempt, card_id, media_identity, download_id, and original_filename. Expected values must match the active job/shot; expected and observed must be identical, and observed.original_filename must equal the source basename."""
    root = Path(downloads_root).resolve()
    source = Path(chrome_path).resolve()
    shot = _find_shot(job, shot_id)
    if shot is None: return _result("REJECTED", "UNKNOWN_SHOT_ID")
    if not source.is_relative_to(root): return _result("REJECTED", "DOWNLOAD_PATH_OUTSIDE_ROOT")
    binding_code = _validate_binding(job, shot, shot_id, source, binding)
    if binding_code: return _reject(job, shot, source, root, binding_code)
    if source.suffix.lower() in PARTIAL_SUFFIXES: return _reject(job, shot, source, root, "PARTIAL_DOWNLOAD")
    if not source.exists() or not source.is_file(): return _result("REJECTED", "SOURCE_NOT_REGULAR_FILE")
    if source.stat().st_size <= 0: return _reject(job, shot, source, root, "EMPTY_FILE")
    try:
        with Image.open(source) as image: image.verify()
        with Image.open(source) as image:
            width, height = image.size
            fmt = str(image.format or "").upper()
            mime = Image.MIME.get(fmt) or mimetypes.guess_type(source.name)[0]
    except (UnidentifiedImageError, OSError):
        return _reject(job, shot, source, root, "IMAGE_DECODE_FAILED")
    if mime not in ALLOWED_MIME_TYPES: return _reject(job, shot, source, root, "UNSUPPORTED_MEDIA_TYPE", width=width, height=height, mime_type=mime)
    if width * 9 != height * 16 and abs(width / height - 16 / 9) > 0.05: return _reject(job, shot, source, root, "INVALID_ASPECT_RATIO", width=width, height=height, mime_type=mime)
    original_name = source.name
    source_digest = _sha256_file(source)
    approved = root / "approved" / str(shot["expected_filename"])
    approved.parent.mkdir(parents=True, exist_ok=True)
    _normalize_to_png(source, approved)
    digest = _sha256_file(approved)
    if digest in _accepted_hashes(prior_assets):
        approved.unlink()
        return _reject(job, shot, source, root, "DUPLICATE_ASSET_HASH", sha256=digest, width=width, height=height, mime_type=mime)
    source.unlink()
    result = AssetValidationResult("ACCEPTED", "OK", digest, 1920, 1080, "image/png", str(approved), None, source_digest)
    payload = _approved_payload(job, shot, original_name, approved, result, binding)
    atomic_write_json(approved.with_suffix(".json"), payload)
    _append_manifest(job, root, payload)
    return result

def _find_shot(job: Mapping[str, Any], shot_id: str) -> Mapping[str, Any] | None:
    shots = job.get("shots", [])
    if not isinstance(shots, list): return None
    for order, shot in enumerate(shots, 1):
        if isinstance(shot, Mapping) and str(shot.get("shot_id")) == shot_id: return {**shot, "_order": order}
    return None

def _validate_binding(job: Mapping[str, Any], shot: Mapping[str, Any], shot_id: str, source: Path, binding: Mapping[str, Any]) -> str | None:
    fields = ("job_id", "shot_id", "prompt_sha256", "attempt", "card_id", "media_identity", "download_id", "original_filename")
    if not isinstance(binding, Mapping): return "MISSING_ASSET_BINDING"
    expected, observed = binding.get("expected"), binding.get("observed")
    if not isinstance(expected, Mapping) or not isinstance(observed, Mapping): return "MISSING_ASSET_BINDING"
    if any(not str(values.get(field, "")).strip() for values in (expected, observed) for field in fields): return "MISSING_ASSET_BINDING"
    if any(str(expected[field]) != str(observed[field]) for field in fields): return "ASSET_BINDING_MISMATCH"
    active = {"job_id": job.get("job_id", ""), "shot_id": shot_id, "prompt_sha256": shot.get("prompt_sha256", ""), "attempt": shot.get("attempt", 1), "card_id": shot.get("card_id", "")}
    for field, value in active.items():
        if str(expected[field]) != str(value): return "ASSET_BINDING_MISMATCH"
    if str(observed["original_filename"]) != source.name: return "ORIGINAL_FILENAME_MISMATCH"
    return None
def _accepted_hashes(rows: list[Any]) -> set[str]:
    result = set()
    for row in rows:
        status = row.get("status") if isinstance(row, Mapping) else getattr(row, "status", None)
        digest = row.get("sha256") if isinstance(row, Mapping) else getattr(row, "sha256", None)
        if status == "ACCEPTED" and digest: result.add(str(digest))
    return result

def _normalize_to_png(source: Path, destination: Path) -> None:
    fd, name = tempfile.mkstemp(dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp")
    temp = Path(name)
    try:
        os.close(fd)
        with Image.open(source) as image:
            ImageOps.fit(image.convert("RGB"), TARGET_SIZE, method=Image.Resampling.LANCZOS).save(temp, format="PNG")
        with temp.open("r+b") as stream: stream.flush(); os.fsync(stream.fileno())
        os.replace(temp, destination)
    finally:
        if temp.exists(): temp.unlink()

def _reject(job: Mapping[str, Any], shot: Mapping[str, Any], source: Path, root: Path, code: str, *, sha256: str | None = None, width: int | None = None, height: int | None = None, mime_type: str | None = None) -> AssetValidationResult:
    if not source.exists(): return _result("REJECTED", code, sha256=sha256, width=width, height=height, mime_type=mime_type)
    rejected = root / "rejected" / source.name
    rejected.parent.mkdir(parents=True, exist_ok=True)
    os.replace(source, rejected)
    result = _result("REJECTED", code, sha256=sha256, width=width, height=height, mime_type=mime_type, rejected_path=str(rejected))
    atomic_write_json(rejected.with_suffix(".json"), {"status": result.status, "code": result.code, "job_id": str(job.get("job_id", "")), "shot_id": str(shot.get("shot_id", "")), "original_filename": source.name, "rejected_path": str(rejected), "sha256": result.sha256, "width": result.width, "height": result.height, "mime_type": result.mime_type, "validated_at_utc": _utc_now()})
    return result

def _approved_payload(job: Mapping[str, Any], shot: Mapping[str, Any], original_name: str, approved: Path, result: AssetValidationResult, binding: Mapping[str, Any]) -> dict[str, Any]:
    project = job.get("project", {})
    observed = binding["observed"]
    return {"shot_id": str(shot["shot_id"]), "order": int(shot.get("_order", 0)), "status": "COMPLETED", "card_id": str(observed["card_id"]), "prompt_sha256": str(observed["prompt_sha256"]), "file_path": str(approved), "approved_path": str(approved), "original_filename": original_name, "sha256": result.sha256, "source_sha256": result.source_sha256, "bytes": approved.stat().st_size, "width": result.width, "height": result.height, "mime_type": result.mime_type, "job_id": str(observed["job_id"]), "attempt": int(observed["attempt"]), "download_id": str(observed["download_id"]), "media_identity": str(observed["media_identity"]), "media_type": str(job.get("media_type", "image")), "project_id": str(project.get("project_id", "")) if isinstance(project, Mapping) else "", "validated_at_utc": _utc_now()}

def _append_manifest(job: Mapping[str, Any], root: Path, payload: Mapping[str, Any]) -> None:
    path = root / "approved_asset_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema_version": 1, "job_id": str(job.get("job_id", "")), "project": dict(job.get("project", {})), "output_dir": str(root), "approved_by": "asset_validator", "approved_at_utc": _utc_now(), "assets": []}
    manifest["assets"] = [row for row in manifest.get("assets", []) if row.get("shot_id") != payload["shot_id"]] + [dict(payload)]
    manifest["approved_at_utc"] = _utc_now()
    atomic_write_json(path, manifest)

def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()

def _utc_now() -> str: return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _result(status: str, code: str, *, sha256: str | None = None, width: int | None = None, height: int | None = None, mime_type: str | None = None, approved_path: str | None = None, rejected_path: str | None = None) -> AssetValidationResult:
    return AssetValidationResult(status, code, sha256, width, height, mime_type, approved_path, rejected_path)






