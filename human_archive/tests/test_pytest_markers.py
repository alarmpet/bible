from __future__ import annotations

from pathlib import Path


def test_media_heavy_marker_is_registered() -> None:
    config = Path(__file__).resolve().parents[2] / "pytest.ini"
    assert "media_heavy:" in config.read_text(encoding="utf-8")
