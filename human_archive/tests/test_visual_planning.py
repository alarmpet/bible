from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from lib.visual_planning import build_visual_contract


def test_planner_copies_approved_text_without_rewriting_it():
    script = {"episode_id": "HA-TEST", "sentences": [{"sentence_id": "s-1", "display_text": "승인된 문장"}]}
    scenes = [{"scene_id": "scene-1", "sentence_ids": ["s-1"], "visual_beat": "문서를 살핀다", "place": "서고", "era": "조선 후기", "action": ["문서를 살핀다"]}]

    contract = build_visual_contract(script, scenes)

    assert contract["captions"][0]["text_span"] == "승인된 문장"
    assert contract["captions"][0]["text_sha256"]
    assert contract["scenes"][0]["depiction_mode"] == "documented"
