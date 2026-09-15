# -*- coding: utf-8 -*-
"""Single path resolver for module ↔ hermes bridge. Next agent: import this, don't hardcode."""
from __future__ import annotations

import os
from pathlib import Path

MODULE_ROOT = Path(os.environ.get("MODULE_ROOT") or Path(__file__).resolve().parents[2])
MODERN_ROOT = MODULE_ROOT / "modern"
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


def _find_hermes_root() -> Path:
    if "HERMES_ROOT" in os.environ:
        return Path(os.environ["HERMES_ROOT"])
    home_candidate = Path.home() / "hermes"
    if home_candidate.exists():
        return home_candidate
    legacy = Path(r"C:\Users\amd\hermes")
    if legacy.exists():
        return legacy
    return home_candidate


HERMES_ROOT = _find_hermes_root()
TTS_ROOT = _find_tts_root()
TTS_PYTHON = Path(
    os.environ.get("HERMES_TTS_PYTHON") or TTS_ROOT / ".venv-win" / "Scripts" / "python.exe"
)
HERMES_MAKE_TTS = HERMES_ROOT / "scripts" / "make-scenes-tts.py"
HERMES_RENDER = HERMES_ROOT / "scripts" / "render-youtube-with-tts.mjs"
CAPCUT_REASSEMBLE = (
    HERMES_ROOT / ".agents" / "skills" / "yadam-capcut-builder" / "scripts" / "reassemble_draft.mjs"
)
_BUNDLED_FFMPEG = HERMES_ROOT / "node_modules" / "ffmpeg-static" / "ffmpeg.exe"
_BUNDLED_FFPROBE = HERMES_ROOT / "node_modules" / "@ffprobe-installer" / "win32-x64" / "ffprobe.exe"

FFMPEG = Path(
    os.environ.get("FFMPEG_BIN")
    or (_BUNDLED_FFMPEG if _BUNDLED_FFMPEG.exists() else "ffmpeg")
)
FFPROBE = Path(
    os.environ.get("FFPROBE_BIN")
    or (_BUNDLED_FFPROBE if _BUNDLED_FFPROBE.exists() else "ffprobe")
)


def run_dir(run_id: str) -> Path:
    return MODERN_ROOT / "runs" / run_id


def job_dir(run_id: str, mode: str = "preview") -> Path:
    return run_dir(run_id) / "hermes_jobs" / mode


def as_dict() -> dict:
    return {
        "MODULE_ROOT": str(MODULE_ROOT),
        "MODERN_ROOT": str(MODERN_ROOT),
        "HERMES_ROOT": str(HERMES_ROOT),
        "TTS_ROOT": str(TTS_ROOT),
        "TTS_PYTHON": str(TTS_PYTHON),
        "HERMES_MAKE_TTS": str(HERMES_MAKE_TTS),
        "HERMES_RENDER": str(HERMES_RENDER),
        "CAPCUT_REASSEMBLE": str(CAPCUT_REASSEMBLE),
        "FFMPEG": str(FFMPEG),
        "FFPROBE": str(FFPROBE),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(as_dict(), ensure_ascii=False, indent=2))
