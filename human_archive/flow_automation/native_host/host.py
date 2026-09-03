"""Native messaging dispatcher for the NOLLAM Flow extension."""
from __future__ import annotations
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from .job_store import append_event, replay_job
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
        return [_envelope("RUN_SHOT", job_id, {"shot_id": shot_id, "attempt": attempt})]
    if kind in {"JOB_PAUSED", "SHOT_ACCEPTED", "SHOT_RETRY"}:
        _event(context, normalized, kind, str(payload.get("shot_id", "")), int(payload.get("attempt", 0)), payload)
        return [_envelope("JOB_STATE", job_id, {"control_state": "PAUSED" if kind == "JOB_PAUSED" else "RUNNING"})]
    return [_envelope("JOB_PAUSED", job_id, {"code": "UNSUPPORTED_COMMAND"})]

def main() -> None:
    while True:
        try:
            message = read_message(sys.stdin.buffer)
        except EOFError:
            return
        except ProtocolError as exc:
            write_message(sys.stdout.buffer, _envelope("JOB_PAUSED", "protocol-error", {"code": "PROTOCOL_ERROR", "message": str(exc)})); return
        for response in dispatch(message, _default_context(message)):
            write_message(sys.stdout.buffer, response)
            sys.stdout.buffer.flush()

def _default_context(message: Mapping[str, Any]) -> HostContext:
    raise RuntimeError("host.py main requires an installed job context")

if __name__ == "__main__":
    main()
