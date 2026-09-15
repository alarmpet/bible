from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from validate_visual_contract import validate_visual_contract


def _contract():
    return {
        "schema_version": 1,
        "episode_id": "HA-TEST",
        "script_sha256": "script-hash",
        "captions": [{"caption_id": "cap-1", "sentence_id": "s-1", "text_span": "기록", "text_sha256": "t", "scene_id": "scene-1"}],
        "scenes": [{
            "scene_id": "scene-1", "order": 1, "visual_beat": "기록 문서를 살핀다",
            "subject_refs": [], "subject_lock": False, "place": "서고", "era": "조선 후기",
            "action": ["문서를 살핀다"], "depiction_mode": "documented", "tone": "차분함",
            "must_not": [], "disclosure": "사료에 근거한 문서 묘사"
        }],
    }


def test_valid_visual_contract_has_complete_caption_scene_coverage():
    errors = validate_visual_contract(_contract(), script_sentences={"s-1": "기록"})
    assert errors == []


def test_rejects_orphan_caption_and_generic_action():
    contract = _contract()
    contract["captions"][0]["scene_id"] = "missing"
    contract["scenes"][0]["action"] = ["Scene depicting historical context..."]
    errors = validate_visual_contract(contract, script_sentences={"s-1": "기록"})
    assert any("scene" in error.lower() for error in errors)
    assert any("generic" in error.lower() for error in errors)
