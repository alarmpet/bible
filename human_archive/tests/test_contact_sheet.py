import json
from PIL import Image
from build_contact_sheet import create_contact_sheet


def test_contact_sheet_can_select_one_v5_pilot_set(tmp_path):
    build = tmp_path / "build"
    (build / "images").mkdir(parents=True)
    for shot_id in ("S1", "S2"):
        Image.new("RGB", (64, 36), "white").save(build / "images" / f"{shot_id}.jpg")
    (build / "asset_manifest.json").write_text(json.dumps({
        "generation_scope": "pilot",
        "expected_ids": ["S1", "S2"],
        "pilot_sets": {"cold_open": ["S1"], "coverage": ["S2"]},
        "assets": [
            {"shot_id": "S1", "order": 1, "file_path": "S1.jpg"},
            {"shot_id": "S2", "order": 2, "file_path": "S2.jpg"},
        ],
    }), encoding="utf-8")
    output = create_contact_sheet(build, build / "cold.jpg", pilot_set="cold_open")
    with Image.open(output) as image:
        assert image.size == (1440, 270)
