# -*- coding: utf-8 -*-
"""Groq Cloud as a genuinely-free fourth run_consensus_round.py participant
(2026-09-16): Gemini/agy is blocked at the Google account-tier level, and
Groq's free tier (no credit card, 14,400 requests/day on most models) fills
the same slot the plan reserved for gemini_flash/gemini_pro. A first attempt
with Cerebras Cloud worked end-to-end (auth, model listing, SDK call) but
that specific account returned HTTP 402 payment_required on every model, so
the user switched to Groq instead. These tests mock the SDK -- no real
network call, no real API key required to run the suite.

Note: "groq" (this participant, Groq Cloud) and "grok" (the existing
PARTICIPANTS entry, xAI's CLI) are two different companies with confusingly
similar names -- tests are named explicitly to avoid conflating them."""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import run_consensus_round as rcr  # noqa: E402


def _fake_groq_module(response_text: str | None = None, raise_exc: Exception | None = None):
    """Build a fake `groq` module so `from groq import Groq` resolves without
    the real package's network stack."""

    class _FakeMessage:
        def __init__(self, content):
            self.content = content

    class _FakeChoice:
        def __init__(self, content):
            self.message = _FakeMessage(content)

    class _FakeCompletion:
        def __init__(self, content):
            self.choices = [_FakeChoice(content)]

    class _FakeCompletions:
        def create(self, **kwargs):
            if raise_exc:
                raise raise_exc
            return _FakeCompletion(response_text)

    class _FakeChat:
        def __init__(self):
            self.completions = _FakeCompletions()

    class _FakeGroq:
        def __init__(self, api_key=None, timeout=None):
            self.api_key = api_key
            self.timeout = timeout
            self.chat = _FakeChat()

    groq_mod = types.ModuleType("groq")
    groq_mod.Groq = _FakeGroq
    return {"groq": groq_mod}


def test_run_groq_requires_api_key(monkeypatch):
    for name, mod in _fake_groq_module(response_text="unused").items():
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    run = rcr._run_groq("PROMPT", timeout=30)
    assert run.ok is False
    assert "GROQ_API_KEY" in run.detail


def test_run_groq_returns_provider_text_on_success(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")
    for name, mod in _fake_groq_module(response_text="ANSWER TEXT").items():
        monkeypatch.setitem(sys.modules, name, mod)
    run = rcr._run_groq("PROMPT", timeout=30)
    assert run.ok is True
    assert run.text == "ANSWER TEXT"


def test_run_groq_surfaces_empty_response_as_failure(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")
    for name, mod in _fake_groq_module(response_text="   ").items():
        monkeypatch.setitem(sys.modules, name, mod)
    run = rcr._run_groq("PROMPT", timeout=30)
    assert run.ok is False
    assert "empty" in run.detail.lower()


def test_run_groq_surfaces_sdk_exception_without_crashing(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")
    for name, mod in _fake_groq_module(raise_exc=RuntimeError("rate limit exceeded")).items():
        monkeypatch.setitem(sys.modules, name, mod)
    run = rcr._run_groq("PROMPT", timeout=30)
    assert run.ok is False
    assert "rate limit" in run.detail.lower()
    assert rcr.is_transient(run.detail) is True


def test_groq_is_dispatched_through_attempt(monkeypatch, tmp_path):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")
    contract_shaped_answer = "## VERDICT\nSOUND\n\n## FINDINGS\nnone\n"
    for name, mod in _fake_groq_module(response_text=contract_shaped_answer).items():
        monkeypatch.setitem(sys.modules, name, mod)
    run = rcr._attempt("groq", "proposer", "PROMPT", tmp_path, timeout=30)
    assert run.ok is True


def test_participants_includes_groq_not_cerebras():
    assert "groq" in rcr.PARTICIPANTS
    assert "cerebras" not in rcr.PARTICIPANTS
    # escalate_claim()'s existing codex+grok pairing (subs[:2]) must stay the
    # default -- adding a 4th participant must not silently change which two
    # get used by the 2-party fact-check escalation path.
    subs = [p for p in rcr.PARTICIPANTS if p != "claude"]
    assert subs[:2] == ["codex", "grok"]
