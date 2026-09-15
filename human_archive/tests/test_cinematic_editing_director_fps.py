# -*- coding: utf-8 -*-
"""Task 6 (fps policy unification): cinematic_editing_director.py used to hardcode
`default_fps: int = 30` independently of config/channel_profiles.yaml, which has
declared `fps: 25` for every profile (nollam_file_v1, doodle_seonbi_v1,
human_archive_cinematic_v1) since before this fix -- CLAUDE.md and
postflight_release.py's own default (`ProductionProfile.from_fps(fps=25)`,
`verify_postflight(target_fps=25)`) already agreed on 25fps as canonical.
Only this module's Studio-side director diverged, and actually encoded at
that diverging fps in normalize_clip()'s ffmpeg -vf string, so it wasn't
just a stale docstring.

See docs/superpowers/plans/2026-09-15-human-archive-nollam-script-visual-motion-multi-llm-overhaul-plan.md
Task 6 / D1.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_LIB_DIR = Path(__file__).resolve().parents[1] / "scripts" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from cinematic_editing_director import CinematicEditingDirector, _resolve_default_fps  # noqa: E402


def test_resolve_default_fps_reads_25_from_channel_profiles_yaml_for_nollam_file_v1():
    assert _resolve_default_fps("nollam_file_v1") == 25


def test_resolve_default_fps_falls_back_to_25_for_unknown_profile():
    assert _resolve_default_fps("no_such_profile_id") == 25


def test_director_default_fps_is_25_not_the_old_hardcoded_30():
    director = CinematicEditingDirector()
    assert director.default_fps == 25


def test_director_explicit_fps_override_still_respected():
    director = CinematicEditingDirector(default_fps=30)
    assert director.default_fps == 30


def test_normalize_clip_actually_encodes_at_the_resolved_fps(tmp_path: Path, monkeypatch):
    raw_clip = tmp_path / "raw.mp4"
    raw_clip.write_bytes(b"not a real video, just needs to exist and be non-empty")
    out_clip = tmp_path / "out.mp4"

    captured_cmd = {}

    def fake_run(cmd, **kwargs):
        captured_cmd["cmd"] = cmd
        out_clip.write_bytes(b"fake output")

        class _Result:
            returncode = 0

        return _Result()

    monkeypatch.setattr("cinematic_editing_director.subprocess.run", fake_run)

    director = CinematicEditingDirector()
    director.normalize_clip(raw_clip, out_clip, duration=3.0, effect_type="subpixel_push_in")

    vf_arg = captured_cmd["cmd"][captured_cmd["cmd"].index("-vf") + 1]
    assert "fps=25" in vf_arg, f"expected fps=25 in ffmpeg -vf filter, got: {vf_arg}"
