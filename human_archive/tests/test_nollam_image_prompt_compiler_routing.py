# -*- coding: utf-8 -*-
"""Task 1 item 3: compile_nollam_prompt() (photorealistic nollam_file_v1 visual
policy) was already built and tested in isolation
(tests/test_nollam_prompt_profile.py) but generate_visual_briefs.py always
called compile_aligned_prompt() instead -- whose STYLE constant is literally
"Korean editorial ink-doodle illustration...", the doodle_seonbi_v1 house
style, applied unconditionally to every profile including nollam_file_v1.
These tests pin the routing: --channel-profile is opt-in (omitting it keeps
compile_aligned_prompt, unchanged, for existing seonbi callers), and
nollam_file_v1 routes to compile_nollam_prompt via channel_profiles.yaml's
image_prompt_compiler field.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from generate_visual_briefs import (  # noqa: E402
    _brief_to_nollam_request_fields,
    resolve_image_prompt_compiler_id,
)
from lib.aligned_prompt_compiler import compile_aligned_prompt, compile_nollam_prompt  # noqa: E402


def test_omitting_channel_profile_keeps_the_aligned_compiler():
    assert resolve_image_prompt_compiler_id(None) == "aligned"


def test_nollam_file_v1_routes_to_the_nollam_compiler():
    assert resolve_image_prompt_compiler_id("nollam_file_v1") == "nollam"


def test_doodle_seonbi_v1_keeps_the_aligned_compiler():
    assert resolve_image_prompt_compiler_id("doodle_seonbi_v1") == "aligned"


def test_unknown_profile_falls_back_to_aligned():
    assert resolve_image_prompt_compiler_id("no_such_profile") == "aligned"


_CLI_V5_BRIEF = {
    "shot_id": "ha_nollam_shot_003",
    "visual_mode": "scientific_diagram_3d",
    "semantic_anchors": ["JWST", "early galaxy"],
    "focal_subject": "a 3D rendered early-universe galaxy cluster",
    "action": "light bends around a gravitational lens",
    "place": "deep field survey region",
    "era": "13 billion years ago",
    "camera": "wide establishing, static",
    "motion_profile": "subpixel_push_in",
}
_SHOT_INPUTS_BY_ID = {
    "ha_nollam_shot_003": {"shot_id": "ha_nollam_shot_003", "order": 3, "claim_ids": ["CLM-JWST-001"]},
}


def test_brief_adapter_maps_cli_v5_fields_to_nollam_prompt_input_shape():
    adapted = _brief_to_nollam_request_fields(_CLI_V5_BRIEF, _SHOT_INPUTS_BY_ID)
    assert adapted["shot_id"] == "ha_nollam_shot_003"
    assert adapted["order"] == 3
    assert adapted["subject"] == _CLI_V5_BRIEF["focal_subject"]
    assert adapted["action"] == _CLI_V5_BRIEF["action"]
    assert adapted["place"] == _CLI_V5_BRIEF["place"]
    assert adapted["visual_claim_ids"] == ["CLM-JWST-001"]


def test_adapted_brief_compiles_through_compile_nollam_prompt_without_ink_doodle_style():
    adapted = _brief_to_nollam_request_fields(_CLI_V5_BRIEF, _SHOT_INPUTS_BY_ID)
    request = compile_nollam_prompt(adapted)

    assert request["shot_id"] == "ha_nollam_shot_003"
    assert "look_id" in request
    assert "policy_id" in request
    assert "ink-doodle" not in request["submission_prompt"].lower()


def test_aligned_prompt_still_carries_the_seonbi_ink_doodle_style_for_legacy_profile():
    """Negative control: confirms compile_aligned_prompt (the default, unchanged
    path) really is the seonbi/doodle house style -- this is exactly why it must
    not be used unconditionally for nollam_file_v1."""
    legacy_brief = {
        "shot_id": "SHOT_001",
        "visual_mode": "historical_reconstruction",
        "semantic_anchors": ["closed archive box"],
        "focal_subject": "a closed archival box",
        "action": "sits on a shelf",
        "place": "a records room",
        "era": "Joseon period",
        "camera": "static medium shot",
    }
    request = compile_aligned_prompt(legacy_brief)
    assert "ink-doodle" in request["submission_prompt"].lower()
