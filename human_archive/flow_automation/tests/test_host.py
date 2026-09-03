from __future__ import annotations
import json
from pathlib import Path
from uuid import uuid4
from flow_automation.native_host.host import HostContext, dispatch

def envelope(kind: str, job_id: str, payload: dict) -> dict:
    return {"protocol_version": 1, "message_id": str(uuid4()), "type": kind, "job_id": job_id, "payload": payload}

def host_context(tmp_path: Path) -> HostContext:
    job = {"job_id": "job-1", "retry_limit": 2, "shots": [{"shot_id": "SHOT_001", "prompt": "p", "prompt_sha256": "0"*64, "duration_sec": 1, "expected_filename": "SHOT_001__00000000.png"}]}
    return HostContext(job, tmp_path / "events.jsonl", extension_ids=frozenset({"allowed"}))

def test_hello_returns_current_job_state(tmp_path: Path) -> None:
    ctx = host_context(tmp_path)
    responses = dispatch(envelope("HELLO", "job-1", {"extension_id": "allowed"}), ctx)
    assert responses[0]["type"] == "JOB_STATE"

def test_start_is_rejected_for_unapproved_limits(tmp_path: Path) -> None:
    ctx = host_context(tmp_path)
    response = dispatch(envelope("JOB_START_REQUESTED", "job-1", {"mode": "missing", "retry_limit": 99}), ctx)
    assert response[0]["type"] == "JOB_PAUSED"
    assert response[0]["payload"]["code"] == "UNAPPROVED_LIMITS"

def test_unsupported_command_pauses(tmp_path: Path) -> None:
    ctx = host_context(tmp_path)
    response = dispatch(envelope("RUN_SHOT", "job-1", {}), ctx)
    assert response[0]["type"] == "JOB_PAUSED"
