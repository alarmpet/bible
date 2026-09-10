from __future__ import annotations

import json
from pathlib import Path

import starlette.routing
from fastapi import FastAPI
from fastapi.testclient import TestClient

_router_init = starlette.routing.Router.__init__


def _compat_router_init(self, *args, **kwargs):
    kwargs.pop("on_startup", None)
    kwargs.pop("on_shutdown", None)
    result = _router_init(self, *args, **kwargs)
    if not hasattr(self, "on_startup"):
        self.on_startup = []
    if not hasattr(self, "on_shutdown"):
        self.on_shutdown = []
    return result


starlette.routing.Router.__init__ = _compat_router_init

from routes.history_routes import create_history_router


def test_history_router_lists_active_master_and_streams_valid_ranges(tmp_path: Path) -> None:
    episode = tmp_path / "episode"
    master = episode / "candidate" / "NOLLAM-NEANDERTHAL-MASTER.mp4"
    master.parent.mkdir(parents=True)
    master.write_bytes(b"0123456789")
    history_db = tmp_path / "history.json"
    history_db.write_text("[]", encoding="utf-8")

    app = FastAPI()
    app.include_router(
        create_history_router(
            get_current_ep_dir=lambda: episode,
            runs_base_dir=tmp_path / "runs",
            history_db_path=history_db,
        )
    )
    client = TestClient(app)

    listing = client.get("/api/history/videos")
    assert listing.status_code == 200
    video_id = listing.json()["videos"][0]["video_id"]

    partial = client.get(
        f"/api/history/stream/{video_id}",
        headers={"Range": "bytes=2-5"},
    )
    assert partial.status_code == 206
    assert partial.content == b"2345"

    invalid = client.get(
        f"/api/history/stream/{video_id}",
        headers={"Range": "bytes=99-100"},
    )
    assert invalid.status_code == 416


def test_history_router_preserves_injected_production_history_collector(tmp_path: Path) -> None:
    history_db = tmp_path / "history.json"
    history_db.write_text("[]", encoding="utf-8")
    projects = [{
        "video_id": "legacy-id",
        "file_path": str(tmp_path / "legacy.mp4"),
        "file_name": "legacy.mp4",
        "file_size_mb": 1.0,
        "date_created": "2026-09-10 00:00",
    }]

    app = FastAPI()
    app.include_router(
        create_history_router(
            get_current_ep_dir=lambda: tmp_path,
            runs_base_dir=tmp_path / "runs",
            history_db_path=history_db,
            collect_projects=lambda: projects,
        )
    )

    response = TestClient(app).get("/api/history/videos")
    assert response.status_code == 200
    assert response.json()["videos"] == projects
