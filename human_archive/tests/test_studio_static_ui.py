from __future__ import annotations

from pathlib import Path


def test_studio_ui_is_served_from_static_file() -> None:
    project_root = Path(__file__).resolve().parents[2]
    static_index = project_root / "human_archive" / "static" / "index.html"
    server = project_root / "human_archive" / "scripts" / "studio_gui_server.py"

    assert static_index.is_file()
    html = static_index.read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>")
    assert "NOLLAM 다큐멘터리 스튜디오" in html
    assert "105개 씬" not in html
    assert "target_shots: 56" not in html
    assert "STATIC_INDEX_PATH" in server.read_text(encoding="utf-8")
