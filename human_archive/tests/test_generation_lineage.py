from __future__ import annotations

from pathlib import Path
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from generate_visual_assets_v3 import bind_existing_assets


def test_existing_asset_is_bound_to_request_and_disk_hash(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    Image.new("RGB", (1920, 1080), (20, 30, 40)).save(image_dir / "scene-1.jpg")
    requests = [{"request_id": "req-scene-1", "scene_id": "scene-1", "request_sha256": "abc"}]

    result = bind_existing_assets(requests, image_dir)

    assert result["assets"][0]["status"] == "COMPLETED"
    assert result["assets"][0]["request_sha256"] == "abc"
    assert len(result["assets"][0]["sha256"]) == 64


def test_missing_asset_is_not_marked_completed(tmp_path: Path):
    result = bind_existing_assets([{"request_id": "req-scene-1", "scene_id": "scene-1", "request_sha256": "abc"}], tmp_path)
    assert result["assets"][0]["status"] == "MISSING"
