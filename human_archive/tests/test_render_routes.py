from __future__ import annotations

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

from routes.render_routes import create_render_router


class _Director:
    def __init__(self, theme_color):
        self.theme_color = theme_color

    def plan_scene_effects(self, shots, theme_color):
        return [{"editing_effect": "bare_tip_whiteboard", "shot_id": "SHOT_001"}] if shots else []


def test_render_router_preserves_cinematic_contract(tmp_path: Path) -> None:
    active_ep = tmp_path / "episode"
    manifest = active_ep / "generation" / "master_1200s_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"shots": [{"shot_id": "SHOT_001"}]}), encoding="utf-8")

    async def run_command(_command):
        return None

    app = FastAPI()
    app.include_router(
        create_render_router(
            get_current_ep_dir=lambda: active_ep,
            module_root=tmp_path,
            scripts_dir=tmp_path / "scripts",
            director_cls=_Director,
            run_pipeline_command=run_command,
        )
    )
    client = TestClient(app)
    effects = client.get("/api/cinematic/effects_plan").json()
    assert effects["opening_effect"] == "bare_tip_whiteboard"
    assert client.get("/api/cinematic/status").json()["status"] == "READY"
