from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from flow_automation.native_host.job_store import (
    atomic_write_json,
    compile_job,
    validate_job,
)


@pytest.fixture
def valid_job(himalaya_manifest: Path, episode_dir: Path) -> dict[str, object]:
    return compile_job(
        himalaya_manifest,
        episode_dir,
        "https://labs.google/fx/ko/tools/flow/project/p1",
        "HIMALAYA-v1",
    )


def test_compile_job_hashes_exact_submission_prompt(
    himalaya_manifest: Path, episode_dir: Path
) -> None:
    job = compile_job(
        himalaya_manifest,
        episode_dir,
        "https://labs.google/fx/ko/tools/flow/project/p1",
        "HIMALAYA-v1",
    )
    first = job["shots"][0]
    assert first["shot_id"] == "SHOT_001"
    assert first["prompt_sha256"] == hashlib.sha256(
        first["prompt"].encode("utf-8")
    ).hexdigest()
    assert first["expected_filename"].startswith("SHOT_001__")


def test_validate_job_rejects_duplicate_shot_id(
    valid_job: dict[str, object], episode_dir: Path
) -> None:
    valid_job["shots"].append(dict(valid_job["shots"][0]))  # type: ignore[index]
    with pytest.raises(ValueError, match="duplicate shot_id"):
        validate_job(valid_job, episode_dir)


def test_validate_job_rejects_duplicate_prompt_sha256(
    valid_job: dict[str, object], episode_dir: Path
) -> None:
    second = dict(valid_job["shots"][1])  # type: ignore[index]
    second["prompt"] = valid_job["shots"][0]["prompt"]  # type: ignore[index]
    second["prompt_sha256"] = valid_job["shots"][0]["prompt_sha256"]  # type: ignore[index]
    second["expected_filename"] = "SHOT_002__" + str(second["prompt_sha256"])[:8] + ".png"
    valid_job["shots"][1] = second  # type: ignore[index]
    with pytest.raises(ValueError, match="duplicate prompt_sha256"):
        validate_job(valid_job, episode_dir)


def test_validate_job_rejects_duplicate_expected_filename(
    valid_job: dict[str, object], episode_dir: Path
) -> None:
    second = dict(valid_job["shots"][1])  # type: ignore[index]
    second["expected_filename"] = valid_job["shots"][0]["expected_filename"]  # type: ignore[index]
    valid_job["shots"][1] = second  # type: ignore[index]
    with pytest.raises(ValueError, match="duplicate expected_filename"):
        validate_job(valid_job, episode_dir)


def test_validate_job_rejects_hash_mismatched_expected_filename(
    valid_job: dict[str, object], episode_dir: Path
) -> None:
    valid_job["shots"][0]["expected_filename"] = "SHOT_001__deadbeef.png"  # type: ignore[index]
    with pytest.raises(ValueError, match="expected_filename must equal"):
        validate_job(valid_job, episode_dir)


def test_validate_job_rejects_filename_traversal(
    valid_job: dict[str, object], episode_dir: Path
) -> None:
    valid_job["shots"][0]["expected_filename"] = "SHOT_001__..\\..\\outside.png"  # type: ignore[index]
    with pytest.raises(ValueError, match="expected_filename must equal"):
        validate_job(valid_job, episode_dir)


def test_validate_job_rejects_nonpositive_duration(
    valid_job: dict[str, object], episode_dir: Path
) -> None:
    valid_job["shots"][0]["duration_sec"] = 0  # type: ignore[index]
    with pytest.raises(ValueError, match="Schema validation failed"):
        validate_job(valid_job, episode_dir)


def test_approved_asset_manifest_schema_rejects_invalid_sha256() -> None:
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "schemas"
        / "approved_asset_manifest.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    manifest = {
        "schema_version": 1,
        "job_id": "HIMALAYA-v1",
        "project": {
            "expected_url": "https://labs.google/fx/ko/tools/flow/project/p1",
            "project_id": "p1",
        },
        "output_dir": "D:/module/bible/human_archive/runs/example/generation/downloads",
        "approved_by": "codex",
        "approved_at_utc": "2026-09-03T00:00:00Z",
        "assets": [
            {
                "shot_id": "SHOT_001",
                "order": 1,
                "card_id": "FLOW-SHOT_001-DEADBEEF",
                "prompt_sha256": "a" * 64,
                "file_path": "SHOT_001__aaaaaaaa.png",
                "sha256": "not-a-sha256",
                "bytes": 123,
                "width": 1920,
                "height": 1080,
                "status": "COMPLETED",
            }
        ],
    }
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(manifest)


def test_validate_job_rejects_output_escape(
    valid_job: dict[str, object], episode_dir: Path
) -> None:
    valid_job["output_dir"] = "D:/outside"
    with pytest.raises(ValueError, match="generation directory"):
        validate_job(valid_job, episode_dir)


def test_atomic_write_json_round_trips_payload(tmp_path: Path) -> None:
    payload = {"schema_version": 1, "job_id": "HIMALAYA-v1"}
    output = tmp_path / "job.json"
    atomic_write_json(output, payload)
    assert json.loads(output.read_text(encoding="utf-8")) == payload

