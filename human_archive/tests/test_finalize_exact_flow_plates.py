import hashlib
import json
import sys
from pathlib import Path

from PIL import Image

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from finalize_exact_flow_plates import finalize_plate_plan


def test_finalize_plate_plan_binds_flow_rows_to_physical_2304x1296_files(tmp_path: Path) -> None:
    source_dir = tmp_path / "generation" / "images"
    output_dir = tmp_path / "images_2d_master"
    source_dir.mkdir(parents=True)
    for plate_id, color in (("SHOT_001_A", (20, 30, 40)), ("SHOT_001_B", (40, 50, 60))):
        Image.new("RGB", (1920, 1080), color).save(source_dir / f"{plate_id}.jpg", quality=95)
    rows = []
    for plate_id in ("SHOT_001_A", "SHOT_001_B"):
        path = source_dir / f"{plate_id}.jpg"
        rows.append({
            "scene_id": plate_id,
            "file_path": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(),
            "bytes": path.stat().st_size,
            "width": 1920,
            "height": 1080,
            "card_id": f"FLOW-{plate_id}",
            "status": "COMPLETED",
        })
    asset_manifest = tmp_path / "asset_manifest.json"
    asset_manifest.write_text(json.dumps({"assets": rows}), encoding="utf-8")
    plan = tmp_path / "plates.json"
    plan.write_text(json.dumps({"plates": [
        {"plate_id": "SHOT_001_A", "parent_shot_id": "SHOT_001"},
        {"plate_id": "SHOT_001_B", "parent_shot_id": "SHOT_001"},
    ]}), encoding="utf-8")

    result = finalize_plate_plan(plan, asset_manifest, source_dir, output_dir, expected_count=2)
    data = json.loads(plan.read_text(encoding="utf-8"))

    assert result["status"] == "PASS"
    assert all(Path(row["path"]).is_file() for row in data["plates"])
    assert all(row["width"] == 2304 and row["height"] == 1296 for row in data["plates"])
