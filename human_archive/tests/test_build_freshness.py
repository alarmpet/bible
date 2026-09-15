from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from lib.build_manifest import verify_upstream_hash_freshness
from lib.provenance import compute_object_sha256


def _write(path: Path, value: str = "{}") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def test_rejects_existing_build_when_upstream_hash_is_stale(tmp_path: Path):
    build = tmp_path / "run" / "candidate"
    source = build.parent / "source"
    contract = source / "shot_contract.json"
    _write(contract, '{"version": 1}')
    _write(build / "asset_manifest.json", '{"contract_sha256": "wrong"}')
    _write(build / "scene_audio_manifest.json")
    _write(build / "subtitles.ass", "")

    ok, errors = verify_upstream_hash_freshness(build)

    assert ok is False
    assert any("hash" in error.lower() for error in errors)


def test_rejects_build_without_human_visual_approval(tmp_path: Path):
    build = tmp_path / "run" / "candidate"
    _write(build.parent / "source" / "shot_contract.json")
    _write(build / "asset_manifest.json", '{"assets": []}')
    _write(build / "scene_audio_manifest.json")
    _write(build / "subtitles.ass", "")

    ok, errors = verify_upstream_hash_freshness(build)

    assert ok is False
    assert any("approval" in error.lower() for error in errors)


def test_accepts_compiler_self_hashed_contract(tmp_path: Path):
    build = tmp_path / "run" / "candidate"
    source = build.parent / "source"
    contract_body = {"schema_version": 1, "episode_id": "TEST", "shots": []}
    contract = dict(contract_body, contract_sha256=compute_object_sha256(contract_body))
    _write(source / "shot_contract.json", json.dumps(contract))
    _write(build / "asset_manifest.json", json.dumps({"contract_sha256": contract["contract_sha256"]}))
    _write(build / "scene_audio_manifest.json")
    _write(build / "subtitles.ass", "")
    (build / "approvals").mkdir(parents=True)
    _write(build / "approvals" / "visual_approval.json")

    ok, errors = verify_upstream_hash_freshness(build)

    assert ok is True, errors
