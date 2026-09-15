"""Task 2, §5.6: the Gemini (agy/antigravity CLI) participant adapter is a
documented extension point, not yet wired into run_consensus_round.py's
PARTICIPANTS (see lib/orchestration/_run_gemini.py's module docstring for why:
no real agy binary on this machine, and escalate_claim()'s pair-based
agreement semantics need their own design pass before growing to four seats).
These tests exercise the adapter in isolation so it's ready to wire in once
both of those are resolved -- mocking subprocess.run/shutil.which, no real
agy/antigravity call, matching how _run_codex/_run_grok's own tests mock at
the _run_codex/_run_grok boundary rather than hitting a real CLI.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

_LIB_DIR = Path(__file__).resolve().parents[2] / "scripts" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from orchestration._run_gemini import GeminiRun, gemini_cmd, run_gemini  # noqa: E402


def test_gemini_cmd_includes_model_when_given():
    cmd = gemini_cmd(model="gemini-2.5-pro", exe="agy")
    assert cmd == ["agy", "generate", "--format", "json", "--model", "gemini-2.5-pro"]


def test_gemini_cmd_omits_model_flag_when_not_given():
    cmd = gemini_cmd(exe="agy")
    assert "--model" not in cmd


def test_run_gemini_fails_closed_when_binary_not_on_path(monkeypatch):
    monkeypatch.setattr("orchestration._run_gemini._exe", lambda name: None)
    result = run_gemini("prompt", timeout=10)
    assert result.ok is False
    assert "PATH" in result.detail


def test_run_gemini_returns_stdout_on_success(monkeypatch):
    monkeypatch.setattr("orchestration._run_gemini._exe", lambda name: r"C:\fake\agy.exe" if name == "agy" else None)

    def fake_run(cmd, **kwargs):
        return SimpleNamespace(returncode=0, stdout='{"result": "ok"}', stderr="")

    monkeypatch.setattr("orchestration._run_gemini.subprocess.run", fake_run)
    result = run_gemini("prompt", timeout=10)
    assert result.ok is True
    assert result.text == '{"result": "ok"}'


def test_run_gemini_fails_on_nonzero_exit(monkeypatch):
    monkeypatch.setattr("orchestration._run_gemini._exe", lambda name: r"C:\fake\agy.exe" if name == "agy" else None)

    def fake_run(cmd, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr("orchestration._run_gemini.subprocess.run", fake_run)
    result = run_gemini("prompt", timeout=10)
    assert result.ok is False
    assert result.stderr == "boom"


def test_run_gemini_fails_closed_on_timeout(monkeypatch):
    monkeypatch.setattr("orchestration._run_gemini._exe", lambda name: r"C:\fake\agy.exe" if name == "agy" else None)

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=10)

    monkeypatch.setattr("orchestration._run_gemini.subprocess.run", fake_run)
    result = run_gemini("prompt", timeout=10)
    assert result.ok is False
    assert "timed out" in result.detail


def test_gemini_run_shape_matches_run_consensus_round_run_for_drop_in_use():
    result = GeminiRun(ok=True, text="x", detail="", stderr="")
    assert hasattr(result, "ok") and hasattr(result, "text")
    assert hasattr(result, "detail") and hasattr(result, "stderr")
