from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

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
