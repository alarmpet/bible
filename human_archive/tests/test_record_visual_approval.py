from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from record_visual_approval import build_full_approval


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_full_approval_binds_contract_manifest_contact_sheet_and_every_image(tmp_path: Path):
    build = tmp_path / "build"
    (build / "images").mkdir(parents=True)
    for name, payload in (("S1.jpg", b"image-one"), ("S2.jpg", b"image-two")):
        (build / "images" / name).write_bytes(payload)
    contact_sheet = build / "contact_sheet.jpg"
    contact_sheet.write_bytes(b"contact-sheet")
    manifest = {
        "generation_scope": "all",
        "assets": [
            {"shot_id": "S1", "file_path": "S1.jpg", "sha256": _sha(build / "images" / "S1.jpg"), "status": "COMPLETED"},
            {"shot_id": "S2", "file_path": "S2.jpg", "sha256": _sha(build / "images" / "S2.jpg"), "status": "COMPLETED"},
        ],
    }
    requests = {
        "contract_sha256": "V5-CONTRACT",
        "requests": [{"scene_id": "S1"}, {"scene_id": "S2"}],
    }
    (build / "asset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (build / "image_request_manifest.json").write_text(json.dumps(requests), encoding="utf-8")
    (build / "visual_content_report.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")

    approval = build_full_approval(build, reviewer_id="user")

    assert approval["decision"] == "approved"
    assert approval["review_scope"] == "full_episode"
    assert approval["contract_sha256"] == "V5-CONTRACT"
    assert approval["contact_sheet_sha256"] == _sha(contact_sheet)
    assert [row["shot_id"] for row in approval["shot_evaluations"]] == ["S1", "S2"]
    assert [row["image_sha256"] for row in approval["shot_evaluations"]] == [
        _sha(build / "images" / "S1.jpg"),
        _sha(build / "images" / "S2.jpg"),
    ]


def test_full_approval_rejects_incomplete_or_unverified_build(tmp_path: Path):
    build = tmp_path / "build"
    (build / "images").mkdir(parents=True)
    manifest = {"generation_scope": "all", "assets": [{"shot_id": "S1", "status": "FAILED"}]}
    requests = {"contract_sha256": "V5-CONTRACT", "requests": [{"scene_id": "S1"}]}
    (build / "asset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (build / "image_request_manifest.json").write_text(json.dumps(requests), encoding="utf-8")

    with pytest.raises(ValueError):
        build_full_approval(build, reviewer_id="user")
