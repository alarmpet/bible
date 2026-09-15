from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from .schema_validation import load_schema, validate_json


SHA256_RE = "^[A-F0-9]{64}$"
DELIVERY_CONFIG = Path(__file__).resolve().parents[2] / "config" / "delivery_profiles.yaml"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "context_sample_build_v1.schema.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_context_sample_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_json(manifest, load_schema(SCHEMA_PATH))
    return manifest


def resolve_delivery_profile(name: str, config_path: Path = DELIVERY_CONFIG) -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    profile = config.get("profiles", {}).get(name)
    if not isinstance(profile, dict):
        raise ValueError(f"Unknown delivery profile: {name}")
    return profile


def validate_segment_approval(segment: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if segment.get("edit_mode") == "rewrite" and not segment.get("editorial_approval_sha256"):
        errors.append(f"segment {segment.get('sample_sentence_id')}: rewrite requires editorial approval SHA")
    visual = segment.get("visual", {})
    origin = visual.get("asset_origin")
    if origin == "reuse":
        required = ("source_asset_path", "source_asset_sha256", "source_request_sha256", "approval_sha256")
    elif origin in {"generated", "imported"}:
        required = ("file_path", "file_sha256", "request_sha256", "approval_sha256")
    else:
        return [f"segment {segment.get('sample_sentence_id')}: unknown visual asset origin"]
    for key in required:
        if not visual.get(key):
            errors.append(f"segment {segment.get('sample_sentence_id')}: visual {key} is required")
    path_value = visual.get("source_asset_path") or visual.get("file_path")
    if path_value:
        asset_path = Path(path_value)
        if not asset_path.exists():
            errors.append(f"segment {segment.get('sample_sentence_id')}: source asset missing: {asset_path}")
        elif visual.get("source_asset_sha256") and _sha256_file(asset_path) != visual.get("source_asset_sha256"):
            errors.append(f"segment {segment.get('sample_sentence_id')}: source asset SHA does not match")
    if origin == "imported" and path_value and Path(path_value).is_absolute() and not visual.get("file_sha256"):
        errors.append(f"segment {segment.get('sample_sentence_id')}: external imported asset requires archived file SHA")
    return errors


def validate_source_bindings(manifest: dict[str, Any], source_build: Path) -> list[str]:
    errors: list[str] = []
    artifacts = manifest.get("source_artifacts", {})
    script_path = Path(artifacts.get("source_script_path", ""))
    if not script_path.exists():
        return [f"source script missing: {script_path}"]
    if _sha256_file(script_path) != artifacts.get("script_sha256"):
        errors.append("source script SHA does not match manifest")
    try:
        script = json.loads(script_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"source script unreadable: {exc}"]
    source_sentences = {str(row.get("sentence_id")): row for row in script.get("sentences", [])}
    for segment in manifest.get("segments", []):
        source_rows = [source_sentences.get(str(sid)) for sid in segment.get("source_sentence_ids", [])]
        if any(row is None for row in source_rows):
            errors.append(f"segment {segment.get('sample_sentence_id')}: source sentence missing")
            continue
        source_text = " ".join(str(row.get("tts_text", row.get("display_text", ""))) for row in source_rows)
        if segment.get("edit_mode") == "exact" and segment.get("display_text") != source_text:
            errors.append(f"segment {segment.get('sample_sentence_id')}: exact text does not match source")
    return errors


def validate_context_sample_manifest(manifest: dict[str, Any], source_build: Path) -> list[str]:
    errors: list[str] = []
    try:
        validate_json(manifest, load_schema(SCHEMA_PATH))
    except ValueError as exc:
        errors.append(str(exc))
        return errors
    try:
        resolve_delivery_profile(manifest["delivery_profile"])
    except (OSError, ValueError, yaml.YAMLError) as exc:
        errors.append(str(exc))
    ids = [row.get("sample_sentence_id") for row in manifest.get("segments", [])]
    if len(ids) != len(set(ids)):
        errors.append("duplicate sample sentence id")
    errors.extend(validate_source_bindings(manifest, source_build))
    for segment in manifest.get("segments", []):
        text = segment.get("display_text", "")
        expected_sha = hashlib.sha256(text.encode("utf-8")).hexdigest().upper()
        if segment.get("tts_text_sha256") != expected_sha:
            errors.append(f"segment {segment.get('sample_sentence_id')}: tts text SHA mismatch")
        errors.extend(validate_segment_approval(segment))
    return errors
