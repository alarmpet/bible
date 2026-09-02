from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from flow_automation.native_host.protocol import (
    ProtocolError,
    read_message,
    validate_envelope,
    write_message,
)


def valid_message() -> dict[str, object]:
    return {
        "protocol_version": 1,
        "message_id": "123e4567-e89b-42d3-a456-426614174000",
        "type": "SHOT_SUBMITTED",
        "job_id": "HIMALAYA-v1",
        "payload": {"shot_id": "SHOT_001"},
    }


def test_native_frame_is_little_endian_json() -> None:
    stream = io.BytesIO()
    write_message(stream, valid_message())
    raw = stream.getvalue()
    assert int.from_bytes(raw[:4], "little") == len(raw[4:])
    assert json.loads(raw[4:]) == valid_message()


def test_validate_envelope_rejects_mismatched_job_id() -> None:
    with pytest.raises(ProtocolError, match="job_id"):
        validate_envelope(valid_message(), expected_job_id="other-job")


def test_validate_envelope_rejects_unknown_type() -> None:
    message = valid_message() | {"type": "EXECUTE_SCRIPT"}
    with pytest.raises(ProtocolError, match="type"):
        validate_envelope(message)


def test_validate_envelope_rejects_unknown_envelope_field() -> None:
    message = valid_message() | {"route": "page"}
    with pytest.raises(ProtocolError, match="Unknown envelope field"):
        validate_envelope(message)


def test_read_message_validates_the_frame_payload() -> None:
    encoded = json.dumps(valid_message(), separators=(",", ":")).encode("utf-8")
    stream = io.BytesIO(len(encoded).to_bytes(4, "little") + encoded)
    assert read_message(stream) == valid_message()



@pytest.mark.parametrize("field", ["message_id", "job_id", "type", "payload", "protocol_version"])
def test_validate_envelope_rejects_missing_required_fields(field: str) -> None:
    message = valid_message()
    del message[field]
    with pytest.raises(ProtocolError, match=field):
        validate_envelope(message)


def test_validate_envelope_requires_protocol_version_and_rejects_schema_version() -> None:
    message = valid_message() | {"schema_version": 1}
    with pytest.raises(ProtocolError, match="Unknown envelope field|protocol_version"):
        validate_envelope(message)


def test_python_allowlist_matches_canonical_resource() -> None:
    from flow_automation.native_host.protocol import MESSAGE_TYPES

    resource = Path(__file__).parents[1] / "extension" / "shared" / "message_types.json"
    assert MESSAGE_TYPES == frozenset(json.loads(resource.read_text(encoding="utf-8")))
    assert len(MESSAGE_TYPES) == 15
