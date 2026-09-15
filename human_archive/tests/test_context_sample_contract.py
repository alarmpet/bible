from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from lib.context_sample import validate_context_sample_manifest


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _source_build(tmp_path: Path) -> Path:
    source = tmp_path / "full-v6-001" / "source"
    source.mkdir(parents=True)
    script = {"sentences": [{"sentence_id": "HA002-S001", "tts_text": "첫 번째 승인 문장"}]}
    (source / "script_candidate.json").write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")
    images = source.parent / "images"
    images.mkdir()
    (images / "shot.jpg").write_bytes(b"fixture-image")
    return source.parent


def _manifest(source_build: Path) -> dict:
    text = "첫 번째 승인 문장"
    script_path = source_build / "source" / "script_candidate.json"
    return {
        "schema_version": 1,
        "episode_id": "HA002",
        "build_id": "sample-3m-v2-001",
        "delivery_profile": "quick_3m",
        "source_build_id": "full-v6-001",
        "source_artifacts": {
            "source_build_path": str(source_build),
            "source_script_path": str(script_path),
            "script_sha256": hashlib.sha256(script_path.read_bytes()).hexdigest().upper(),
            "claims_sha256": "A" * 64,
            "fact_report_sha256": "B" * 64,
            "fact_approval_sha256": "C" * 64,
            "persona_report_sha256": "D" * 64,
        },
        "segments": [
            {
                "sample_sentence_id": "HA002-Q3-001",
                "source_sentence_ids": ["HA002-S001"],
                "edit_mode": "exact",
                "display_text": text,
                "tts_text_sha256": _sha(text),
                "claim_ids": [],
                "evidence_span_ids": [],
                "visual": {
                    "asset_origin": "reuse",
                    "source_asset_path": str(source_build / "images" / "shot.jpg"),
                    "source_asset_sha256": hashlib.sha256(b"fixture-image").hexdigest().upper(),
                    "source_request_sha256": "F" * 64,
                    "approval_sha256": "1" * 64,
                },
            }
        ],
    }


def test_valid_manifest_binds_exact_source_text_and_profile(tmp_path: Path) -> None:
    source_build = _source_build(tmp_path)
    manifest = _manifest(source_build)
    script_path = Path(manifest["source_artifacts"]["source_script_path"])
    manifest["source_artifacts"]["script_sha256"] = hashlib.sha256(script_path.read_bytes()).hexdigest().upper()
    errors = validate_context_sample_manifest(manifest, source_build)
    assert errors == []


def test_rewrite_without_editorial_approval_fails(tmp_path: Path) -> None:
    source_build = _source_build(tmp_path)
    manifest = _manifest(source_build)
    segment = manifest["segments"][0]
    segment["edit_mode"] = "rewrite"
    segment["display_text"] = "승인되지 않은 변경 문장"
    segment["tts_text_sha256"] = _sha(segment["display_text"])
    errors = validate_context_sample_manifest(manifest, source_build)
    assert any("editorial_approval" in error.lower() or "editorial approval" in error.lower() for error in errors)


def test_missing_source_asset_fails_closed(tmp_path: Path) -> None:
    source_build = _source_build(tmp_path)
    manifest = _manifest(source_build)
    (source_build / "images" / "shot.jpg").unlink()
    errors = validate_context_sample_manifest(manifest, source_build)
    assert any("source asset" in error.lower() for error in errors)


def test_external_absolute_path_only_fails(tmp_path: Path) -> None:
    source_build = _source_build(tmp_path)
    manifest = _manifest(source_build)
    visual = manifest["segments"][0]["visual"]
    visual["asset_origin"] = "external"
    visual["source_asset_path"] = r"C:\Users\shs\.gemini\external.jpg"
    visual.pop("source_asset_sha256")
    errors = validate_context_sample_manifest(manifest, source_build)
    assert any("external" in error.lower() for error in errors)


def test_duplicate_sample_sentence_id_fails(tmp_path: Path) -> None:
    source_build = _source_build(tmp_path)
    manifest = _manifest(source_build)
    manifest["segments"].append(dict(manifest["segments"][0]))
    errors = validate_context_sample_manifest(manifest, source_build)
    assert any("duplicate" in error.lower() for error in errors)
