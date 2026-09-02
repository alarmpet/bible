from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from flow_automation.native_host.job_store import (
    JobSnapshot,
    ShotState,
    append_event,
    atomic_write_json,
    compile_job,
    next_runnable_shot,
    replay_job,
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


def make_event(
    event_id: str,
    event_type: str,
    shot_id: str = "SHOT_001",
    *,
    attempt: int = 1,
    job_id: str = "HIMALAYA-v1",
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "event_id": event_id,
        "timestamp": "2026-09-03T00:00:00Z",
        "job_id": job_id,
        "shot_id": shot_id,
        "attempt": attempt,
        "type": event_type,
        "payload": payload or {},
    }


def accepted_event(
    event_id: str,
    shot_id: str,
    *,
    attempt: int = 1,
    job_id: str = "HIMALAYA-v1",
) -> dict[str, object]:
    return make_event(
        event_id,
        "SHOT_ACCEPTED",
        shot_id,
        attempt=attempt,
        job_id=job_id,
        payload={
            "approved_path": f"D:/module/bible/human_archive/runs/example/{shot_id}.png"
        },
    )


def valid_event_line() -> str:
    return json.dumps(accepted_event("e1", "SHOT_001"), ensure_ascii=False)


def write_jsonl(path: Path, events: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(
            json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
            for event in events
        ),
        encoding="utf-8",
    )


@pytest.fixture
def snapshot_with_first_accepted(valid_job: dict[str, object]) -> JobSnapshot:
    shot_ids = [shot["shot_id"] for shot in valid_job["shots"]]  # type: ignore[index]
    shots = {
        shot_id: ShotState(
            shot_id=shot_id,
            status="ACCEPTED" if shot_id == "SHOT_001" else "PENDING",
            attempt=1 if shot_id == "SHOT_001" else 0,
            approved_path=(
                "D:/module/bible/human_archive/runs/example/SHOT_001.png"
                if shot_id == "SHOT_001"
                else None
            ),
        )
        for shot_id in shot_ids
    }
    return JobSnapshot(
        job_id=str(valid_job["job_id"]),
        shots=shots,
        retry_limit=int(valid_job["retry_limit"]),
        applied_event_ids={"e1"},
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


def test_append_event_appends_json_line(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    append_event(path, accepted_event("e1", "SHOT_001"))
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows == [accepted_event("e1", "SHOT_001")]


def test_replay_ignores_duplicate_event_id(
    valid_job: dict[str, object], tmp_path: Path
) -> None:
    event = accepted_event("e1", "SHOT_001", attempt=1)
    write_jsonl(tmp_path / "events.jsonl", [event, event])
    snapshot = replay_job(valid_job, tmp_path / "events.jsonl")
    assert snapshot.shots["SHOT_001"].status == "ACCEPTED"
    assert snapshot.applied_event_ids == {"e1"}


def test_generate_missing_never_returns_accepted_shot(
    snapshot_with_first_accepted: JobSnapshot,
) -> None:
    assert next_runnable_shot(snapshot_with_first_accepted, "missing").shot_id == "SHOT_002"


def test_replay_truncated_last_line_preserves_prior_events(
    valid_job: dict[str, object], tmp_path: Path
) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(valid_event_line() + "\n{", encoding="utf-8")
    assert replay_job(valid_job, path).shots["SHOT_001"].status == "ACCEPTED"


def test_replay_waiting_for_result_blocks_next_runnable(
    valid_job: dict[str, object], tmp_path: Path
) -> None:
    write_jsonl(
        tmp_path / "events.jsonl",
        [make_event("e1", "SHOT_STARTED", "SHOT_001", attempt=1)],
    )
    snapshot = replay_job(valid_job, tmp_path / "events.jsonl")
    assert snapshot.shots["SHOT_001"].status == "WAITING_FOR_RESULT"
    assert next_runnable_shot(snapshot, "missing") is None


def test_replay_pause_blocks_runnable_shot(
    valid_job: dict[str, object], tmp_path: Path
) -> None:
    write_jsonl(
        tmp_path / "events.jsonl",
        [make_event("e1", "JOB_PAUSED", "", attempt=0)],
    )
    assert next_runnable_shot(replay_job(valid_job, tmp_path / "events.jsonl"), "missing") is None


def test_replay_stop_blocks_runnable_shot(
    valid_job: dict[str, object], tmp_path: Path
) -> None:
    write_jsonl(
        tmp_path / "events.jsonl",
        [make_event("e1", "JOB_STOPPED", "", attempt=0)],
    )
    assert next_runnable_shot(replay_job(valid_job, tmp_path / "events.jsonl"), "missing") is None


def test_replay_failed_shot_exhaustion_skips_to_next_shot(
    valid_job: dict[str, object], tmp_path: Path
) -> None:
    write_jsonl(
        tmp_path / "events.jsonl",
        [make_event("e1", "SHOT_FAILED", "SHOT_001", attempt=2, payload={"error": "boom"})],
    )
    snapshot = replay_job(valid_job, tmp_path / "events.jsonl")
    assert snapshot.shots["SHOT_001"].status == "EXHAUSTED"
    assert next_runnable_shot(snapshot, "missing").shot_id == "SHOT_002"


def test_generate_all_requires_new_job_id_after_progress(
    snapshot_with_first_accepted: JobSnapshot,
) -> None:
    with pytest.raises(ValueError, match="new job ID"):
        next_runnable_shot(snapshot_with_first_accepted, "all")


def test_replay_rejects_mismatched_job_id(
    valid_job: dict[str, object], tmp_path: Path
) -> None:
    write_jsonl(tmp_path / "events.jsonl", [accepted_event("e1", "SHOT_001", job_id="OTHER")])
    with pytest.raises(ValueError, match="job_id"):
        replay_job(valid_job, tmp_path / "events.jsonl")


def test_replay_rejects_malformed_complete_line(
    valid_job: dict[str, object], tmp_path: Path
) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(valid_event_line() + "\n{bad}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed event"):
        replay_job(valid_job, path)

def test_replay_rejects_malformed_eof_without_newline(
    valid_job: dict[str, object], tmp_path: Path
) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(valid_event_line() + "\nnot-json", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed event"):
        replay_job(valid_job, path)


def test_replay_rejects_mismatched_job_id_even_for_duplicate_event_id(
    valid_job: dict[str, object], tmp_path: Path
) -> None:
    write_jsonl(
        tmp_path / "events.jsonl",
        [
            accepted_event("e1", "SHOT_001"),
            accepted_event("e1", "SHOT_001", job_id="OTHER"),
        ],
    )
    with pytest.raises(ValueError, match="job_id"):
        replay_job(valid_job, tmp_path / "events.jsonl")
