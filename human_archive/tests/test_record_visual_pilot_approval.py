import json
from pathlib import Path

from record_visual_pilot_approval import build_pilot_approval


def test_pilot_approval_binds_current_manifest_and_all_pilot_images(tmp_path):
    build = tmp_path / "build"
    (build / "images").mkdir(parents=True)
    (build / "images" / "S1.jpg").write_bytes(b"image-one")
    manifest = {
        "pilot_sets": {"cold_open": ["S1"], "coverage": []},
        "assets": [{"shot_id": "S1", "file_path": "S1.jpg", "sha256": "IMG", "prompt_sha256": "PROMPT", "status": "COMPLETED", "bytes": 20000, "width": 1920, "height": 1080, "card_id": "FLOW-S1"}],
    }
    (build / "asset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (build / "image_request_manifest.json").write_text(json.dumps({"contract_sha256": "CONTRACT"}), encoding="utf-8")
    approval = build_pilot_approval(build, reviewer_id="user")
    assert approval["decision"] == "approved"
    assert approval["contract_sha256"] == "CONTRACT"
    assert approval["pilot_asset_fingerprint_sha256"]
    assert [row["shot_id"] for row in approval["shot_evaluations"]] == ["S1"]
    assert approval["shot_evaluations"][0]["image_sha256"] == "IMG"
