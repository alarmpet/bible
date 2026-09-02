# -*- coding: utf-8 -*-
"""Deterministic job compilation and validation for Flow automation."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

import jsonschema


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
AUTOMATION_JOB_SCHEMA_PATH = SCHEMA_DIR / "automation_job.schema.json"
APPROVED_ASSET_MANIFEST_SCHEMA_PATH = (
    SCHEMA_DIR / "approved_asset_manifest.schema.json"
)

_REQUIRED_EVENT_KEYS = (
    "event_id",
    "timestamp",
    "job_id",
    "shot_id",
    "attempt",
    "type",
    "payload",
)
_WAITING_EVENT_TYPES = {
    "SHOT_QUEUED",
    "SHOT_STARTED",
    "SHOT_SUBMITTED",
    "WAITING_FOR_RESULT",
}
_ACCEPTED_EVENT_TYPES = {"SHOT_ACCEPTED", "SHOT_COMPLETED"}
_FAILURE_EVENT_TYPES = {"SHOT_FAILED", "SHOT_ERROR", "SHOT_REJECTED"}
_RESET_EVENT_TYPES = {"SHOT_RESET", "SHOT_RETRY_REQUESTED", "SHOT_REQUEUED"}
_PAUSED_EVENT_TYPES = {"JOB_PAUSED", "PAUSED", "PAUSE_REQUESTED"}
_STOPPED_EVENT_TYPES = {"JOB_STOPPED", "STOPPED", "STOP_REQUESTED"}
_RESUMED_EVENT_TYPES = {"JOB_RESUMED", "RESUMED", "JOB_STARTED", "JOB_CONTINUED"}
_JOB_NOOP_EVENT_TYPES = {"JOB_CREATED"}


@dataclass(frozen=True)
class ShotState:
    shot_id: str
    status: str = "PENDING"
    attempt: int = 0
    error: str | None = None
    approved_path: str | None = None


@dataclass(frozen=True)
class JobSnapshot:
    job_id: str
    shots: dict[str, ShotState]
    retry_limit: int = 0
    control_state: str = "RUNNING"
    applied_event_ids: set[str] = field(default_factory=set)
    shot_order: tuple[str, ...] = ()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_schema(instance: Mapping[str, Any], schema_path: Path) -> None:
    validator = jsonschema.Draft202012Validator(_load_schema(schema_path))
    errors = sorted(validator.iter_errors(instance), key=lambda error: error.path)
    if errors:
        message = "; ".join(
            f"[{'/'.join(map(str, error.path))}] {error.message}" for error in errors
        )
        raise ValueError(f"Schema validation failed: {message}")


def atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    """Atomically write a JSON document with a trailing newline."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def append_event(events_path: Path, event: Mapping[str, Any]) -> None:
    """Append one durable event record before any external side effects."""
    normalized = _normalize_event(event)
    events_path = Path(events_path)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(normalized, ensure_ascii=False, separators=(",", ":")) + "\n"
    with events_path.open("a", encoding="utf-8", newline="") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def replay_job(job: Mapping[str, Any], events_path: Path) -> JobSnapshot:
    """Rebuild the durable job state by replaying its JSONL event log."""
    job_id = str(job.get("job_id", "")).strip()
    if not job_id:
        raise ValueError("job_id is required")

    shots_data = job.get("shots")
    if not isinstance(shots_data, list):
        raise ValueError("job shots must be a list")

    shot_order: list[str] = []
    shots: dict[str, ShotState] = {}
    for item in shots_data:
        if not isinstance(item, Mapping):
            raise ValueError("job shots must contain objects")
        shot_id = str(item.get("shot_id", "")).strip()
        if not shot_id:
            raise ValueError("shot_id is required")
        shot_order.append(shot_id)
        shots[shot_id] = ShotState(shot_id=shot_id)

    retry_limit = int(job.get("retry_limit", 0))
    control_state = "RUNNING"
    applied_event_ids: set[str] = set()
    events_path = Path(events_path)
    if not events_path.exists():
        return JobSnapshot(
            job_id=job_id,
            shots=shots,
            retry_limit=retry_limit,
            control_state=control_state,
            applied_event_ids=applied_event_ids,
            shot_order=tuple(shot_order),
        )

    lines = events_path.read_text(encoding="utf-8").splitlines(keepends=True)
    for index, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\r\n")
        if not line:
            continue
        try:
            event_obj = json.loads(line)
        except json.JSONDecodeError as exc:
            is_last_line = index == len(lines)
            if is_last_line and not raw_line.endswith(("\n", "\r")):
                break
            raise ValueError(f"Malformed event at line {index}") from exc

        normalized = _normalize_event(event_obj)
        event_id = str(normalized["event_id"])
        if event_id in applied_event_ids:
            continue
        if normalized["job_id"] != job_id:
            raise ValueError(
                f"event job_id does not match replay job_id at line {index}"
            )
        applied_event_ids.add(event_id)

        event_type = str(normalized["type"])
        if event_type in _JOB_NOOP_EVENT_TYPES:
            continue
        if event_type in _PAUSED_EVENT_TYPES:
            control_state = "PAUSED"
            continue
        if event_type in _STOPPED_EVENT_TYPES:
            control_state = "STOPPED"
            continue
        if event_type in _RESUMED_EVENT_TYPES:
            control_state = "RUNNING"
            continue

        shot_id = str(normalized["shot_id"])
        if shot_id not in shots:
            raise ValueError(f"unknown shot_id in event log: {shot_id}")
        prior = shots[shot_id]
        attempt = int(normalized["attempt"])
        payload = normalized["payload"]

        if event_type in _WAITING_EVENT_TYPES:
            shots[shot_id] = ShotState(
                shot_id=shot_id,
                status="WAITING_FOR_RESULT",
                attempt=max(prior.attempt, attempt),
                error=None,
                approved_path=prior.approved_path,
            )
            continue
        if event_type in _ACCEPTED_EVENT_TYPES:
            approved_path = payload.get("approved_path")
            shots[shot_id] = ShotState(
                shot_id=shot_id,
                status="ACCEPTED",
                attempt=max(prior.attempt, attempt),
                error=None,
                approved_path=(
                    str(approved_path) if approved_path is not None else prior.approved_path
                ),
            )
            continue
        if event_type in _FAILURE_EVENT_TYPES:
            error = payload.get("error")
            next_status = "EXHAUSTED" if attempt >= retry_limit else "FAILED"
            shots[shot_id] = ShotState(
                shot_id=shot_id,
                status=next_status,
                attempt=max(prior.attempt, attempt),
                error=str(error) if error is not None else None,
                approved_path=None,
            )
            continue
        if event_type in _RESET_EVENT_TYPES:
            shots[shot_id] = ShotState(shot_id=shot_id)
            continue

        raise ValueError(f"Unsupported event type: {event_type}")

    return JobSnapshot(
        job_id=job_id,
        shots=shots,
        retry_limit=retry_limit,
        control_state=control_state,
        applied_event_ids=applied_event_ids,
        shot_order=tuple(shot_order),
    )


def next_runnable_shot(snapshot: JobSnapshot, mode: str) -> ShotState | None:
    """Return the next shot that may be started for the requested generation mode."""
    normalized_mode = str(mode).strip().lower()
    if normalized_mode not in {"all", "missing"}:
        raise ValueError("mode must be 'all' or 'missing'")
    if normalized_mode == "all" and snapshot.applied_event_ids:
        raise ValueError("Generate All requires a new job ID once progress exists")
    if snapshot.control_state in {"PAUSED", "STOPPED"}:
        return None
    if any(shot.status == "WAITING_FOR_RESULT" for shot in snapshot.shots.values()):
        return None

    shot_ids = snapshot.shot_order or tuple(snapshot.shots.keys())
    for shot_id in shot_ids:
        shot = snapshot.shots[shot_id]
        if shot.status == "ACCEPTED":
            continue
        if shot.status == "EXHAUSTED":
            continue
        if shot.status == "FAILED" and shot.attempt >= snapshot.retry_limit:
            continue
        return shot
    return None


def _normalize_event(event: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(event, Mapping):
        raise ValueError("event must be an object")
    missing = [key for key in _REQUIRED_EVENT_KEYS if key not in event]
    if missing:
        raise ValueError(f"event is missing required keys: {', '.join(missing)}")

    event_id = str(event.get("event_id", "")).strip()
    if not event_id:
        raise ValueError("event_id is required")

    timestamp = str(event.get("timestamp", "")).strip()
    if not timestamp:
        raise ValueError("timestamp is required")

    job_id = str(event.get("job_id", "")).strip()
    if not job_id:
        raise ValueError("job_id is required")

    shot_id = str(event.get("shot_id", "")).strip()

    try:
        attempt = int(event.get("attempt", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("attempt must be an integer") from exc
    if attempt < 0:
        raise ValueError("attempt must be non-negative")

    event_type = str(event.get("type", "")).strip().upper()
    if not event_type:
        raise ValueError("type is required")

    payload = event.get("payload")
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be an object")

    return {
        "event_id": event_id,
        "timestamp": timestamp,
        "job_id": job_id,
        "shot_id": shot_id,
        "attempt": attempt,
        "type": event_type,
        "payload": dict(payload),
    }


def _project_id_from_url(expected_url: str) -> str:
    parsed = urlsplit(expected_url)
    if parsed.scheme != "https":
        raise ValueError("project expected_url must use https")
    if parsed.netloc != "labs.google":
        raise ValueError("project expected_url must target labs.google")
    if "/tools/flow/project/" not in parsed.path:
        raise ValueError("project expected_url must be a Flow project URL")
    project_id = Path(parsed.path.rstrip("/")).name
    if not project_id:
        raise ValueError("project expected_url is missing a project_id")
    return project_id


def _scene_duration(scene: Mapping[str, Any], shot_id: str) -> float:
    duration = scene.get("duration_sec")
    if duration is None:
        if "start_sec" not in scene or "end_sec" not in scene:
            raise ValueError(f"shot {shot_id} is missing timing fields")
        duration = float(scene["end_sec"]) - float(scene["start_sec"])
    value = float(duration)
    if value <= 0:
        raise ValueError(f"shot {shot_id} has non-positive duration")
    return value


def _expected_filename(shot_id: str, prompt_sha256: str) -> str:
    return f"{shot_id}__{prompt_sha256[:8]}.png"


def compile_job(
    source_manifest: Path,
    episode_dir: Path,
    expected_url: str,
    job_id: str,
) -> dict[str, Any]:
    source = _read_json(Path(source_manifest))
    scenes = source.get("scenes")
    if not isinstance(scenes, list):
        raise ValueError("source manifest scenes array is required")

    output_dir = (Path(episode_dir) / "generation" / "downloads").resolve()
    project_id = _project_id_from_url(expected_url)

    shots: list[dict[str, Any]] = []
    for scene in scenes:
        if not isinstance(scene, Mapping):
            raise ValueError("source manifest scene entries must be objects")
        shot_id = str(scene.get("shot_id", "")).strip()
        if not shot_id:
            raise ValueError("source manifest shot_id is required")
        raw_prompt = str(scene.get("midjourney_prompt", "")).strip()
        if not raw_prompt:
            raise ValueError(f"source manifest midjourney_prompt is required for {shot_id}")
        prompt = raw_prompt.split("--ar", 1)[0].strip()
        prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        shots.append(
            {
                "shot_id": shot_id,
                "prompt": prompt,
                "prompt_sha256": prompt_sha256,
                "duration_sec": _scene_duration(scene, shot_id),
                "expected_filename": _expected_filename(shot_id, prompt_sha256),
            }
        )

    job: dict[str, Any] = {
        "schema_version": 1,
        "job_id": job_id,
        "project": {
            "expected_url": expected_url,
            "project_id": project_id,
        },
        "output_dir": str(output_dir),
        "media_type": "image",
        "aspect_ratio": "16:9",
        "retry_limit": 2,
        "random_delay_seconds": {"min": 5, "max": 15},
        "shots": shots,
    }
    validate_job(job, Path(episode_dir))
    return job


def validate_job(job: Mapping[str, Any], episode_dir: Path) -> None:
    _validate_schema(job, AUTOMATION_JOB_SCHEMA_PATH)

    project = job["project"]
    if not isinstance(project, Mapping):
        raise ValueError("job project must be an object")
    expected_url = str(project.get("expected_url", "")).strip()
    project_id = str(project.get("project_id", "")).strip()
    derived_project_id = _project_id_from_url(expected_url)
    if project_id != derived_project_id:
        raise ValueError("project_id does not match expected_url")

    output_path = Path(str(job["output_dir"])).resolve()
    generation_root = (Path(episode_dir).resolve() / "generation").resolve()
    if not output_path.is_relative_to(generation_root):
        raise ValueError("output_dir must stay within the generation directory")

    shots = job.get("shots", [])
    if not isinstance(shots, list):
        raise ValueError("job shots must be a list")

    seen_shot_ids: set[str] = set()
    seen_prompt_hashes: set[str] = set()
    seen_filenames: set[str] = set()

    for shot in shots:
        if not isinstance(shot, Mapping):
            raise ValueError("job shots must contain objects")
        shot_id = str(shot.get("shot_id", "")).strip()
        if not shot_id:
            raise ValueError("shot_id is required")
        if shot_id in seen_shot_ids:
            raise ValueError(f"duplicate shot_id: {shot_id}")
        seen_shot_ids.add(shot_id)

        prompt = str(shot.get("prompt", ""))
        prompt_sha256 = str(shot.get("prompt_sha256", ""))
        expected_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        if prompt_sha256 != expected_hash:
            raise ValueError(f"prompt_sha256 does not match prompt for {shot_id}")
        if prompt_sha256 in seen_prompt_hashes:
            raise ValueError(f"duplicate prompt_sha256: {prompt_sha256}")
        seen_prompt_hashes.add(prompt_sha256)

        expected_filename = str(shot.get("expected_filename", "")).strip()
        if expected_filename in seen_filenames:
            raise ValueError(f"duplicate expected_filename: {expected_filename}")
        canonical_filename = _expected_filename(shot_id, prompt_sha256)
        if expected_filename != canonical_filename:
            raise ValueError(
                f"expected_filename must equal the derived prompt hash filename: {shot_id}"
            )
        candidate_path = (output_path / expected_filename).resolve()
        if not candidate_path.is_relative_to(output_path):
            raise ValueError(
                f"expected_filename must stay within the generation directory: {shot_id}"
            )
        seen_filenames.add(expected_filename)

        duration_sec = float(shot.get("duration_sec", 0.0))
        if duration_sec <= 0:
            raise ValueError(f"shot {shot_id} must have a positive duration")
