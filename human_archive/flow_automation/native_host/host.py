"""Native messaging dispatcher for the NOLLAM Flow extension."""
from __future__ import annotations
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from .job_store import append_event, replay_job, validate_job
from .protocol import validate_envelope, read_message, write_message, ProtocolError

ALLOWED_EXTENSION_IDS = frozenset()
ALLOWED_RETRY_LIMIT = 2
ALLOWED_MODES = frozenset({"missing", "all"})

@dataclass
class HostContext:
    job: Mapping[str, Any]
    events_path: Path
    extension_ids: frozenset[str] = field(default_factory=lambda: ALLOWED_EXTENSION_IDS)
    expected_extension_id: str | None = None
    snapshot: Any = None
    def __post_init__(self) -> None:
        self.events_path = Path(self.events_path)
        if self.snapshot is None:
            self.snapshot = replay_job(self.job, self.events_path)

def _envelope(message_type: str, job_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    import uuid
    return {"protocol_version": 1, "message_id": str(uuid.uuid4()), "type": message_type, "job_id": job_id, "payload": dict(payload)}

def _event(ctx: HostContext, message: Mapping[str, Any], event_type: str, shot_id: str = "", attempt: int = 0, payload: Mapping[str, Any] | None = None) -> None:
    append_event(ctx.events_path, {"event_id": str(message["message_id"]), "timestamp": datetime.now(timezone.utc).isoformat(), "job_id": str(message["job_id"]), "shot_id": shot_id, "attempt": attempt, "type": event_type, "payload": dict(payload or {})})

def dispatch(message: Mapping[str, Any], context: HostContext) -> list[dict[str, Any]]:
    normalized = validate_envelope(message, expected_job_id=context.job["job_id"])
    kind, payload, job_id = normalized["type"], normalized["payload"], normalized["job_id"]
    if kind == "HELLO":
        extension_id = str(payload.get("extension_id", ""))
        if context.extension_ids and extension_id not in context.extension_ids:
            return [_envelope("JOB_PAUSED", job_id, {"code": "EXTENSION_ID_NOT_ALLOWED"})]
        context.expected_extension_id = extension_id
        return [_envelope("JOB_STATE", job_id, {"control_state": context.snapshot.control_state, "shots": {key: vars(value) for key, value in context.snapshot.shots.items()}})]
    if kind == "LOAD_JOB":
        return [_envelope("JOB_STATE", job_id, {"control_state": context.snapshot.control_state, "shots": {key: vars(value) for key, value in context.snapshot.shots.items()}})]
    if kind == "JOB_STOPPED":
        _event(context, normalized, "JOB_STOPPED")
        return [_envelope("JOB_STATE", job_id, {"control_state": "STOPPED"})]
    if kind == "JOB_START_REQUESTED":
        mode = str(payload.get("mode", "missing")).lower()
        retry_limit = payload.get("retry_limit", context.job.get("retry_limit"))
        if mode not in ALLOWED_MODES or not isinstance(retry_limit, int) or retry_limit < 0 or retry_limit > ALLOWED_RETRY_LIMIT:
            _event(context, normalized, "JOB_PAUSED", payload={"code": "UNAPPROVED_LIMITS"})
            return [_envelope("JOB_PAUSED", job_id, {"code": "UNAPPROVED_LIMITS"})]
        return [_envelope("JOB_STATE", job_id, {"control_state": "RUNNING", "mode": mode})]
    if kind == "SHOT_SUBMITTED":
        shot_id = str(payload.get("shot_id", ""))
        attempt = int(payload.get("attempt", 0))
        _event(context, normalized, "SHOT_SUBMITTED", shot_id, attempt, payload)
        context.snapshot = replay_job(context.job, context.events_path)
        return [_envelope("RUN_SHOT", job_id, {"shot_id": shot_id, "attempt": attempt})]
    if kind == "DOWNLOAD_COMPLETED":
        shot_id = str(payload.get("shotId", payload.get("shot_id", "")))
        attempt = int(payload.get("attempt", 1))
        filename = str(payload.get("filename", ""))
        downloads_root = Path(str(context.job.get("output_dir", "")))
        source_path = Path(filename)
        expected_binding = {
            "job_id": job_id,
            "shot_id": shot_id,
            "prompt_sha256": str(payload.get("promptSha256", payload.get("prompt_sha256", ""))),
            "attempt": attempt,
            "card_id": str(payload.get("cardId", payload.get("card_id", f"card-{shot_id}"))),
            "media_identity": str(payload.get("mediaIdentity", payload.get("media_identity", f"media-{shot_id}"))),
            "download_id": str(payload.get("downloadId", payload.get("download_id", "0"))),
            "original_filename": source_path.name,
        }
        binding = payload.get("binding", {"expected": expected_binding, "observed": expected_binding})
        prior_assets: list[Any] = []
        approved_manifest_path = downloads_root / "approved_asset_manifest.json"
        if approved_manifest_path.exists():
            try:
                import json
                prior_assets = json.loads(approved_manifest_path.read_text(encoding="utf-8")).get("assets", [])
            except Exception:
                pass
        try:
            from .asset_validator import validate_asset
            res = validate_asset(context.job, shot_id, source_path, downloads_root, prior_assets, binding=binding)
            if res.status == "APPROVED":
                _event(context, normalized, "SHOT_ACCEPTED", shot_id, attempt, {"approved_path": res.approved_path, "sha256": res.sha256})
                context.snapshot = replay_job(context.job, context.events_path)
                return [
                    _envelope("SHOT_ACCEPTED", job_id, {"shot_id": shot_id, "approved_path": res.approved_path}),
                    _envelope("JOB_STATE", job_id, {"control_state": "RUNNING", "shots": {k: vars(v) for k, v in context.snapshot.shots.items()}})
                ]
            else:
                _event(context, normalized, "SHOT_RETRY", shot_id, attempt, {"error": res.code})
                context.snapshot = replay_job(context.job, context.events_path)
                return [
                    _envelope("SHOT_RETRY", job_id, {"shot_id": shot_id, "code": res.code}),
                    _envelope("JOB_STATE", job_id, {"control_state": "RUNNING", "shots": {k: vars(v) for k, v in context.snapshot.shots.items()}})
                ]
        except Exception as exc:
            _event(context, normalized, "JOB_PAUSED", shot_id, attempt, {"code": "VALIDATION_EXCEPTION", "message": str(exc)})
            context.snapshot = replay_job(context.job, context.events_path)
            return [_envelope("JOB_PAUSED", job_id, {"code": "VALIDATION_EXCEPTION", "message": str(exc)})]
    if kind in {"JOB_PAUSED", "SHOT_ACCEPTED", "SHOT_RETRY"}:
        _event(context, normalized, kind, str(payload.get("shot_id", "")), int(payload.get("attempt", 0)), payload)
        context.snapshot = replay_job(context.job, context.events_path)
        return [_envelope("JOB_STATE", job_id, {"control_state": "PAUSED" if kind == "JOB_PAUSED" else "RUNNING"})]
    return [_envelope("JOB_PAUSED", job_id, {"code": "UNSUPPORTED_COMMAND"})]

def main() -> None:
    context: HostContext | None = None
    while True:
        try:
            message = read_message(sys.stdin.buffer)
        except EOFError:
            return
        except ProtocolError as exc:
            write_message(sys.stdout.buffer, _envelope("JOB_PAUSED", "protocol-error", {"code": "PROTOCOL_ERROR", "message": str(exc)})); return
        if context is None:
            if message.get("type") != "LOAD_JOB":
                write_message(sys.stdout.buffer, _envelope("JOB_PAUSED", str(message.get("job_id", "protocol-error")), {"code": "JOB_NOT_LOADED"}))
                sys.stdout.buffer.flush()
                continue
            payload = message.get("payload", {})
            job = payload.get("job") if isinstance(payload, Mapping) else None
            if not isinstance(job, Mapping):
                write_message(sys.stdout.buffer, _envelope("JOB_PAUSED", str(message["job_id"]), {"code": "JOB_PAYLOAD_REQUIRED"}))
                sys.stdout.buffer.flush()
                continue
            try:
                episode_dir = Path(str(job["output_dir"])).resolve().parent.parent
                validate_job(job, episode_dir)
                events_path = Path(str(job["output_dir"])).resolve().parent / "automation_events.jsonl"
                context = HostContext(job, events_path)
            except (KeyError, TypeError, ValueError) as exc:
                write_message(sys.stdout.buffer, _envelope("JOB_PAUSED", str(message["job_id"]), {"code": "INVALID_JOB", "message": str(exc)}))
                sys.stdout.buffer.flush()
                continue
        for response in dispatch(message, context):
            write_message(sys.stdout.buffer, response)
            sys.stdout.buffer.flush()

if __name__ == "__main__":
    main()
