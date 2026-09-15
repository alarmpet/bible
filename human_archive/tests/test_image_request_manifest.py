from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from compile_image_requests import compile_request_manifest


def test_manifest_has_one_request_per_scene():
    contract = {"schema_version": 1, "episode_id": "HA-TEST", "scenes": [{
        "scene_id": "scene-1", "visual_beat": "문서를 펼친다", "action": ["펼친다"], "place": "서고", "era": "조선 후기"
    }]}
    manifest = compile_request_manifest(contract)
    assert manifest["episode_id"] == "HA-TEST"
    assert len(manifest["requests"]) == 1
    assert manifest["requests"][0]["scene_id"] == "scene-1"
