# -*- coding: utf-8 -*-
"""Chrome native messaging protocol helpers for Flow automation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, BinaryIO, Mapping

import jsonschema


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "native_message.schema.json"
MESSAGE_TYPES_PATH = Path(__file__).resolve().parents[1] / "extension" / "shared" / "message_types.json"
MAX_MESSAGE_BYTES = 1_048_576
MESSAGE_TYPES = frozenset(json.loads(MESSAGE_TYPES_PATH.read_text(encoding="utf-8")))
_ALLOWED_KEYS = frozenset(
    {"protocol_version", "message_id", "type", "job_id", "payload"}
)


class ProtocolError(ValueError):
    """Raised when a native message envelope is malformed."""


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


_VALIDATOR = jsonschema.Draft202012Validator(_load_schema())


def validate_envelope(
    message: Mapping[str, Any], expected_job_id: str | None = None
) -> dict[str, Any]:
    if not isinstance(message, Mapping):
        raise ProtocolError("message must be an object")

    unknown_keys = sorted(set(message) - _ALLOWED_KEYS)
    if unknown_keys:
        raise ProtocolError(
            f"Unknown envelope field(s): {', '.join(unknown_keys)}"
        )

    errors = sorted(
        _VALIDATOR.iter_errors(dict(message)),
        key=lambda error: [str(part) for part in error.path],
    )
    if errors:
        first = errors[0]
        path = "/".join(str(part) for part in first.path) or "message"
        raise ProtocolError(f"Invalid {path}: {first.message}")

    if message["type"] not in MESSAGE_TYPES:
        raise ProtocolError("type must be an allowlisted message type")

    job_id = str(message["job_id"]).strip()
    if not job_id:
        raise ProtocolError("job_id must be non-empty")
    if expected_job_id is not None and job_id != str(expected_job_id).strip():
        raise ProtocolError("job_id does not match expected_job_id")

    payload = message["payload"]
    if not isinstance(payload, Mapping):
        raise ProtocolError("payload must be an object")

    return {
        "protocol_version": 1,
        "message_id": str(message["message_id"]),
        "type": str(message["type"]),
        "job_id": job_id,
        "payload": dict(payload),
    }


def read_message(stream: BinaryIO) -> dict[str, Any]:
    header = stream.read(4)
    if not header:
        raise EOFError
    if len(header) != 4:
        raise ProtocolError("truncated native message header")

    size = int.from_bytes(header, "little")
    if size <= 0 or size > MAX_MESSAGE_BYTES:
        raise ProtocolError("invalid native message length")

    body = stream.read(size)
    if len(body) != size:
        raise ProtocolError("truncated native message")

    try:
        message = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("invalid native message JSON") from exc

    return validate_envelope(message)


def write_message(stream: BinaryIO, message: Mapping[str, Any]) -> None:
    normalized = validate_envelope(message)
    body = json.dumps(normalized, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    if len(body) > MAX_MESSAGE_BYTES:
        raise ProtocolError("invalid native message length")

    stream.write(len(body).to_bytes(4, "little"))
    stream.write(body)
