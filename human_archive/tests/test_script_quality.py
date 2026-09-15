from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from audit_episode_quality import audit_episode


def test_audit_reports_repeated_sentences_and_prompt_reuse(tmp_path: Path):
    script = tmp_path / "script.json"
    script.write_text(json.dumps({"sentences": [
        {"sentence_id": "s001", "text": "같은 문장"},
        {"sentence_id": "s002", "text": "같은 문장"},
        {"sentence_id": "s003", "text": "다른 문장"},
    ]}, ensure_ascii=False), encoding="utf-8")
    manifest = tmp_path / "asset_manifest.json"
    manifest.write_text(json.dumps({"assets": [
        {"shot_id": "sh001", "prompt_sha256": "p1", "duration_sec": 27.0},
        {"shot_id": "sh002", "prompt_sha256": "p1", "duration_sec": 4.0},
    ]}), encoding="utf-8")

    report = audit_episode(script_path=script, manifest_path=manifest)

    assert report["script"]["sentence_count"] == 3
    assert report["script"]["unique_sentence_count"] == 2
    assert report["script"]["duplicate_occurrences"] == 1
    assert report["visual"]["unique_prompt_count"] == 1
    assert report["visual"]["duration_over_25_sec"] == 1
