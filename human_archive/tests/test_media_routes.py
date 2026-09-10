from __future__ import annotations

import asyncio
import json
import sys
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

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from routes.media_routes import create_media_router


def test_media_router_preserves_range_and_full_streaming(tmp_path: Path) -> None:
    episode = tmp_path / "episode"
    master = episode / "candidate" / "master.mp4"
    master.parent.mkdir(parents=True)
    master.write_bytes(b"0123456789")

    app = FastAPI()
    app.include_router(
        create_media_router(
            get_current_ep_dir=lambda: episode,
            get_manifest_path=lambda: episode / "generation" / "master.json",
            fallback_manifest_path=episode / "generation" / "fallback.json",
            history_db_path=tmp_path / "history.json",
            final_master_path=tmp_path / "final.mp4",
            canonical_master_path=master,
        )
    )
    client = TestClient(app)

    ranged = client.get("/api/media/master_video", headers={"Range": "bytes=2-5"})
    assert ranged.status_code == 206
    assert ranged.content == b"2345"
    assert ranged.headers["content-range"] == "bytes 2-5/10"

    full = client.get("/api/media/master_video")
    assert full.status_code == 200
    assert full.content == b"0123456789"

    invalid = client.get("/api/media/master_video", headers={"Range": "bytes=20-30"})
    assert invalid.status_code == 416


def test_media_router_resolves_thumbnail_and_audio_from_manifest(tmp_path: Path) -> None:
    episode = tmp_path / "episode"
    manifest_path = episode / "generation" / "master.json"
    manifest_path.parent.mkdir(parents=True)
    thumbnail = episode / "images" / "S1.jpg"
    audio = episode / "audio" / "S1.wav"
    thumbnail.parent.mkdir()
    audio.parent.mkdir()
    thumbnail.write_bytes(b"jpeg")
    audio.write_bytes(b"wav")
    manifest_path.write_text(
        json.dumps(
            {
                "shots": [
                    {
                        "shot_id": "S1",
                        "image_path": str(thumbnail),
                        "wav_path": str(audio),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    app = FastAPI()
    app.include_router(
        create_media_router(
            get_current_ep_dir=lambda: episode,
            get_manifest_path=lambda: manifest_path,
            fallback_manifest_path=tmp_path / "fallback.json",
            history_db_path=tmp_path / "history.json",
            final_master_path=tmp_path / "final.mp4",
            canonical_master_path=tmp_path / "canonical.mp4",
        )
    )
    client = TestClient(app)
    assert client.get("/api/media/thumbnail/S1").content == b"jpeg"
    assert client.get("/api/media/audio/S1").content == b"wav"
