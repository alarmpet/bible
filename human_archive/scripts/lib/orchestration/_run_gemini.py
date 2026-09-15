# -*- coding: utf-8 -*-
"""Gemini (agy/antigravity CLI) participant adapter -- §5.6 of the 2026-09-15
overhaul plan: a documented extension point for a fourth orchestration
participant, for the vision-heavy rounds (scene visual briefs, motion QA)
§5.1's role table calls for.

Not wired into run_consensus_round.py's PARTICIPANTS / _invoke() yet. Two
independent reasons, both already true as of Task 3 (2026-09-15):

1. No real `agy`/`antigravity` binary is installed on this machine -- only an
   old npm `gemini-cli` wrapper whose free tier has been discontinued (see
   tri_model_debate_engine.py's Task 3 commit notes). Wiring PARTICIPANTS to
   include "gemini" without a way to actually invoke it would either silently
   fail every round's fourth seat or require faking a response -- exactly the
   "simulated fixture without labeling" failure mode this plan's fail-closed
   rules exist to prevent.
2. escalate_claim()'s contract is "exactly two subprocess participants"
   (`subs = [p for p in PARTICIPANTS if p != "claude"][:2]`) and its
   agreement/disagreement semantics (`len(verdicts) == 1` == agreed) are
   built around a pair, not a quorum. Growing to four seats changes what
   "agreement" and "2 of N succeeded" mean and needs its own design pass,
   not a one-line PARTICIPANTS edit.

This module follows the exact same shape as run_consensus_round.py's
_run_codex()/_run_grok() (mirrors lib/visual_brief_provider.py's
AntigravityCliVisualBriefProvider CLI invocation: `agy generate --format json
[--model X]` with the prompt on stdin) so that wiring it in later -- once a
real binary is available and the pair-vs-quorum question is answered -- is a
matter of adding a branch to _invoke(), not writing new provider code.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GeminiRun:
    """Same shape as run_consensus_round.Run (ok/text/detail/stderr) so a
    caller there can use this interchangeably without a cross-module import."""
    ok: bool
    text: str
    detail: str = ""
    stderr: str = ""


def gemini_cmd(model: str | None = None, exe: str = "agy") -> list[str]:
    args = [exe, "generate", "--format", "json"]
    if model:
        args.extend(["--model", model])
    return args


def _exe(name: str) -> str | None:
    return shutil.which(name)


def run_gemini(prompt: str, timeout: int, *, model: str | None = None) -> GeminiRun:
    """Invoke agy/antigravity with `prompt` on stdin. Fails closed (ok=False with a
    clear detail message), never silently returns simulated content, if the
    binary can't be found or the call doesn't succeed -- matching
    run_consensus_round.py's _run_codex()/_run_grok() behavior exactly, so a
    caller that later wires this in gets the same fail-closed guarantees for
    free.
    """
    exe = _exe("agy") or _exe("antigravity")
    if not exe:
        return GeminiRun(False, "", "agy/antigravity is not on PATH")

    cmd = gemini_cmd(model=model, exe=exe)
    try:
        proc = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return GeminiRun(False, "", f"timed out after {timeout}s")
    except Exception as exc:  # noqa: BLE001 - one provider failing must not lose the others
        return GeminiRun(False, "", f"{type(exc).__name__}: {exc}")

    if proc.returncode != 0 or not proc.stdout.strip():
        return GeminiRun(False, "", f"exit {proc.returncode}; no output", proc.stderr)
    return GeminiRun(True, proc.stdout, "", proc.stderr)
