from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import starlette.routing

# The legacy server applies this compatibility shim at import time. Keep the
# extracted router test isolated while retaining the same supported runtime.
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

from routes.flow_routes import create_flow_router


class _BatchManager:
    def start_batch(self, items, overwrite=False):
        return {"status": "STARTED", "count": len(items), "overwrite": overwrite}

    def get_status(self):
        return {"status": "IDLE"}

    def stop(self):
        return {"status": "STOPPED"}


def test_flow_router_factory_exposes_routes_without_server_import() -> None:
    async def cdp_status():
        return {"connected": True}

    async def generate(scene_id, prompt):
        return {"status": "SUCCESS", "scene_id": scene_id, "prompt": prompt}

    app = FastAPI()
    app.include_router(
        create_flow_router(
            get_current_ep_dir=lambda: Path("D:/module/bible/human_archive/runs/test"),
            check_cdp_status=cdp_status,
            generate_single_scene_cdp=generate,
            batch_manager=_BatchManager(),
        )
    )
    client = TestClient(app)
    assert client.get("/api/flow/status").json() == {"connected": True}
    assert client.post("/api/flow/generate_single", json={"scene_id": "S1", "prompt": "p"}).json()["status"] == "SUCCESS"
    assert client.get("/api/flow/batch_status").json()["status"] == "IDLE"
    assert client.post("/api/flow/batch_stop").json()["status"] == "STOPPED"
