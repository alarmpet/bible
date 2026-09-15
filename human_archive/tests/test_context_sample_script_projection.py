from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compile_context_sample_script import compile_context_sample  # noqa: E402
from lib.context_sample import validate_context_sample_manifest  # noqa: E402


def _fixture_source(tmp_path: Path) -> Path:
    build = tmp_path / "full-v6-001"
    source = build / "source"
    source.mkdir(parents=True)
    sentences = []
    audio = []
    for i, text in enumerate(["승인 문장 하나", "승인 문장 둘"], start=1):
        sid = f"HA002-S{i:03d}"
        sentences.append({"sentence_id": sid, "order": i, "beat": "body", "display_text": text, "tts_text": text, "segments": [{"kind": "fact", "text": text}]})
        audio.append({"sentence_id": sid, "tts_text": text, "duration_sec": 3.0, "audio_file": f"{sid}.wav"})
    (source / "script_candidate.json").write_text(json.dumps({"sentences": sentences}, ensure_ascii=False), encoding="utf-8")
    (source / "script_expansion_v1.json").write_text(json.dumps({"blocks": []}), encoding="utf-8")
    (build / "sentence_audio_manifest.json").write_text(json.dumps({"sentences": audio}), encoding="utf-8")
    (build / "images").mkdir()
    image = build / "images" / "shot.jpg"
    image.write_bytes(b"fixture")
    asset = {
        "shot_id": "ha002_v6_shot_001",
        "file_path": "shot.jpg",
        "sha256": hashlib.sha256(b"fixture").hexdigest().upper(),
        "card_id": "CARD-1",
        "prompt_sha256": "A" * 64,
        "provenance": {"request_contract_sha256": "B" * 64, "review_approval_sha256": "C" * 64},
    }
    (build / "asset_manifest.json").write_text(json.dumps({"assets": [asset]}), encoding="utf-8")
    (build / "image_request_manifest.json").write_text(json.dumps({"requests": [{"shot_id": "ha002_v6_shot_001", "request_sha256": "B" * 64}]}), encoding="utf-8")
    (build / "approvals").mkdir()
    (build / "approvals" / "visual_approval.json").write_text("{}", encoding="utf-8")
    for name in ["claim_inventory_v2.json", "fact_check_report_v2.json", "persona_report_v2.json", "source_snapshot_manifest_v2.json"]:
        (source / name).write_text("{}", encoding="utf-8")
    (source / "approvals").mkdir()
    (source / "approvals" / "fact_review_approval_v1.json").write_text("{}", encoding="utf-8")
    return build


def test_projection_preserves_exact_source_and_lineage(tmp_path: Path) -> None:
    source = _fixture_source(tmp_path)
    output = tmp_path / "sample-3m-v2-001"
    manifest_path = compile_context_sample(source, output, count=2)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["segments"]) == 2
    assert manifest["segments"][0]["edit_mode"] == "exact"
    assert manifest["segments"][0]["visual"]["source_request_sha256"] == "B" * 64
    assert validate_context_sample_manifest(manifest, source) == []


def test_projection_rejects_missing_provenance(tmp_path: Path) -> None:
    source = _fixture_source(tmp_path)
    (source / "image_request_manifest.json").write_text(json.dumps({"requests": []}), encoding="utf-8")
    asset_manifest = json.loads((source / "asset_manifest.json").read_text(encoding="utf-8"))
    asset_manifest["assets"][0]["provenance"].pop("request_contract_sha256")
    (source / "asset_manifest.json").write_text(json.dumps(asset_manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="request SHA"):
        compile_context_sample(source, tmp_path / "sample-3m-v2-001", count=1)
