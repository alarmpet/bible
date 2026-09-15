from __future__ import annotations

from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from lib.host_overlay import composite_canonical_host, render_canonical_host_asset


def test_canonical_host_asset_has_transparency_and_full_costume(tmp_path: Path):
    asset = render_canonical_host_asset(tmp_path / "seonbi.png")
    with Image.open(asset) as image:
        assert image.mode == "RGBA"
        assert image.size == (760, 1080)
        alpha = image.getchannel("A")
        assert alpha.getextrema() == (0, 255)


def test_host_composite_is_deterministic_and_records_asset_hash(tmp_path: Path):
    base = tmp_path / "base.jpg"
    Image.new("RGB", (1920, 1080), "#f4efe4").save(base)
    asset = render_canonical_host_asset(tmp_path / "seonbi.png")
    first = composite_canonical_host(base, asset, tmp_path / "first.jpg")
    second = composite_canonical_host(base, asset, tmp_path / "second.jpg")
    assert first["overlay_sha256"] == second["overlay_sha256"]
    assert first["output_sha256"] == second["output_sha256"]
    assert first["costume"] == "white dopo with full torso, sleeves, collar, and waist tie"
