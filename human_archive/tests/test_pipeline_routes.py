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

from routes.pipeline_routes import create_pipeline_router


def test_pipeline_router_reports_dynamic_status_and_launches_actions(tmp_path: Path) -> None:
    episode = tmp_path / "episode"
    manifest_path = episode / "generation" / "master_1200s_manifest.json"
    manifest_path.parent.mkdir(parents=True)
    image_path = episode / "images" / "SHOT_001.jpg"
    audio_path = episode / "audio" / "SHOT_001.wav"
    image_path.parent.mkdir()
    audio_path.parent.mkdir()
    image_path.write_bytes(b"image")
    audio_path.write_bytes(b"audio")
    manifest_path.write_text(
        json.dumps({"shots": [{"image_path": str(image_path), "wav_path": str(audio_path)}]}),
        encoding="utf-8",
    )

    calls: list[list[str]] = []

    async def run_command(command):
        calls.append(command)

    app = FastAPI()
    app.include_router(
        create_pipeline_router(
            get_current_ep_dir=lambda: episode,
            scripts_dir=tmp_path / "scripts",
            run_pipeline_command=run_command,
            log_queue=asyncio.Queue(),
        )
    )
    client = TestClient(app)

    status = client.get("/api/pipeline/status").json()
    assert status["images_ready"] == "1/1"
    assert status["audio_ready"] == "1/1"
    assert status["master_video_ready"] is False

    launched = client.post("/api/pipeline/run_action", json={"action": "validate_qa"})
    assert launched.status_code == 200
    assert launched.json()["status"] == "LAUNCHED"
    assert launched.json()["command"].endswith("scripts\\validate_intro_videos.py")


def test_pipeline_router_discovers_active_episode_master_without_himalaya_name(tmp_path: Path) -> None:
    episode = tmp_path / "neanderthal"
    candidate_dir = episode / "candidate"
    candidate_dir.mkdir(parents=True)
    (candidate_dir / "NOLLAM-NEANDERTHAL-EXTINCTION-FULL-MASTER.mp4").write_bytes(
        b"master" * 200_000
    )

    async def run_command(_command):
        return None

    app = FastAPI()
    app.include_router(
        create_pipeline_router(
            get_current_ep_dir=lambda: episode,
            scripts_dir=tmp_path,
            run_pipeline_command=run_command,
            log_queue=asyncio.Queue(),
        )
    )

    status = TestClient(app).get("/api/pipeline/status").json()
    assert status["master_video_ready"] is True
    assert status["master_video_size_mb"] > 0


def test_pipeline_router_rejects_unknown_actions(tmp_path: Path) -> None:
    async def run_command(_command):
        return None

    app = FastAPI()
    app.include_router(
        create_pipeline_router(
            get_current_ep_dir=lambda: tmp_path,
            scripts_dir=tmp_path,
            run_pipeline_command=run_command,
            log_queue=asyncio.Queue(),
        )
    )
    response = TestClient(app).post("/api/pipeline/run_action", json={"action": "unknown"})
    assert response.status_code == 400
