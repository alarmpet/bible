# -*- coding: utf-8 -*-
"""Paths for bible_healing package."""
from __future__ import annotations

import os
from pathlib import Path

BH_ROOT = Path(__file__).resolve().parents[1]
MODULE_ROOT = BH_ROOT.parent
MODERN_SCRIPTS = MODULE_ROOT / "modern" / "scripts"
CONFIG = BH_ROOT / "config"
DATA = BH_ROOT / "data"
RAW = DATA / "raw"
VERSES = DATA / "verses"
RUNS = BH_ROOT / "runs"
PROMPTS = BH_ROOT / "prompts"

def _find_tts_root() -> Path:
    if "HERMES_TTS_ROOT" in os.environ:
        return Path(os.environ["HERMES_TTS_ROOT"])
    home_candidate = Path.home() / "supertonic3-local-tts-20260517-r4" / "supertonic3-local-tts"
    if home_candidate.exists():
        return home_candidate
    legacy = Path(r"C:\Users\amd\supertonic3-local-tts-20260517-r4\supertonic3-local-tts")
    if legacy.exists():
        return legacy
    return home_candidate


TTS_ROOT = _find_tts_root()
TTS_PYTHON = Path(
    os.environ.get("HERMES_TTS_PYTHON") or TTS_ROOT / ".venv-win" / "Scripts" / "python.exe"
)



def episode_dir(episode_id: str) -> Path:
    return RUNS / episode_id


def job_dir(episode_id: str, mode: str = "full") -> Path:
    return episode_dir(episode_id) / "hermes_jobs" / mode
