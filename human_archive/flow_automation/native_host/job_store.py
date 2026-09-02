# -*- coding: utf-8 -*-
"""Deterministic job compilation and validation for Flow automation."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

import jsonschema


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
AUTOMATION_JOB_SCHEMA_PATH = SCHEMA_DIR / "automation_job.schema.json"
APPROVED_ASSET_MANIFEST_SCHEMA_PATH = (
    SCHEMA_DIR / "approved_asset_manifest.schema.json"
)


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

