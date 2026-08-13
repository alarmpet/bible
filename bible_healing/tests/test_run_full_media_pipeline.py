# -*- coding: utf-8 -*-
"""Unit tests for the single full-media pipeline entrypoint (mocked subprocess)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_full_media_pipeline as pipe  # noqa: E402


class FakeCompleted:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _job(tmp_path: Path) -> Path:
    job = tmp_path / "hermes_jobs" / "full"
    job.mkdir(parents=True)
    return job


def test_build_steps_order_and_names():
    job = Path("bible_healing/runs/ep01_anxious_night/hermes_jobs/full")
    steps = pipe.build_steps(
        job,
        python="python",
        tts_python="tts-python",
        final_mp4=Path(r"D:\bible_healing_ep01\final\deploy-ep01-authoritative-audio-aligned.mp4"),
    )
    names = [name for _, name, _ in steps]
    assert names == [
        "media_rules_preflight",
        "build_full_job",
        "tts_multi_voice",
        "verify_voice_provenance",
        "rebuild_authoritative_full_audio",
        "verify_authoritative_audio",
        "build_full_audio_aligned_ass",
        "ass_qa",
        "render_authoritative_full",
        "media_rules_postflight",
    ]
    assert [n for n, _, _ in steps] == list(range(1, 11))


def test_tts_step_never_passes_skip_existing():
    job = Path("job")
    steps = pipe.build_steps(
        job,
        python="python",
        tts_python="tts-python",
        final_mp4=Path("out.mp4"),
    )
    tts_cmd = next(cmd for _, name, cmd in steps if name == "tts_multi_voice")
    assert "--skip-existing" not in tts_cmd
    assert "--job" in tts_cmd
    assert any("tts_multi_voice.py" in str(part) for part in tts_cmd)


def test_run_pipeline_writes_json_and_full_order(tmp_path: Path):
    job = _job(tmp_path)
    work = tmp_path / "pipeline"
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return FakeCompleted(0, stdout='{"ok": true}')

    result = pipe.run_pipeline(
        job,
        work_root=work,
        run_cmd=fake_run,
        final_mp4=tmp_path / "final.mp4",
        python_exe="py",
        tts_python_exe="tts-py",
    )
    assert result["ok"] is True
    assert result["completed_steps"] == 10
    assert len(calls) == 10

    script_basenames = [Path(str(c[1])).name for c in calls]
    assert script_basenames == [
        "media_rules_preflight.py",
        "build_full_job.py",
        "tts_multi_voice.py",
        "verify_voice_provenance.py",
        "rebuild_authoritative_full_audio.py",
        "verify_authoritative_audio.py",
        "build_full_audio_aligned_ass.py",
        "build_full_audio_aligned_ass.py",  # ass_qa reuses builder CLI
        "render_authoritative_full.py",
        "media_rules_postflight.py",
    ]

    reports = sorted(work.glob("step_*.json"))
    assert len(reports) == 10
    first = json.loads(reports[0].read_text(encoding="utf-8"))
    assert first["step"] == 1
    assert first["name"] == "media_rules_preflight"
    assert first["returncode"] == 0
    assert first["ok"] is True

    tts_call = calls[2]
    assert tts_call[0] == "tts-py"
    assert "--skip-existing" not in tts_call


def test_halt_on_first_nonzero_exit(tmp_path: Path):
    job = _job(tmp_path)
    work = tmp_path / "pipeline"
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        # Fail on step 3 (tts)
        if len(calls) == 3:
            return FakeCompleted(7, stderr="tts boom")
        return FakeCompleted(0)

    result = pipe.run_pipeline(
        job,
        work_root=work,
        run_cmd=fake_run,
        final_mp4=tmp_path / "final.mp4",
    )
    assert result["ok"] is False
    assert result["failed_step"] == 3
    assert result["failed_name"] == "tts_multi_voice"
    assert len(calls) == 3  # stopped; no steps 4–10
    assert len(list(work.glob("step_*.json"))) == 3
    fail_report = json.loads((work / "step_03_tts_multi_voice.json").read_text(encoding="utf-8"))
    assert fail_report["ok"] is False
    assert fail_report["returncode"] == 7


def test_main_uses_work_root_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    job = _job(tmp_path)
    work = tmp_path / "custom_work"
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return FakeCompleted(0)

    monkeypatch.setattr(pipe.subprocess, "run", fake_run)
    rc = pipe.main(
        [
            "--job",
            str(job),
            "--work-root",
            str(work),
            "--final-mp4",
            str(tmp_path / "out.mp4"),
        ]
    )
    assert rc == 0
    assert len(calls) == 10
    assert (work / "step_01_media_rules_preflight.json").is_file()
    assert "--skip-existing" not in " ".join(" ".join(map(str, c)) for c in calls)


def test_main_nonzero_when_step_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    job = _job(tmp_path)
    work = tmp_path / "work"

    def fake_run(cmd, **kwargs):
        return FakeCompleted(1, stderr="preflight failed")

    monkeypatch.setattr(pipe.subprocess, "run", fake_run)
    rc = pipe.main(["--job", str(job), "--work-root", str(work)])
    assert rc == 1
    assert (work / "step_01_media_rules_preflight.json").is_file()
