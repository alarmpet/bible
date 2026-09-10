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

from routes.script_routes import SubtitleStyleUpdate, create_script_router


class _Checker:
    def audit_sentence(self, text: str):
        return {"grade": "A", "text": text}


def test_subtitle_style_default_matches_nollam_ssot() -> None:
    assert SubtitleStyleUpdate().font_size == 52


def test_script_router_audits_revises_and_updates_subtitle_style(tmp_path: Path) -> None:
    manifest_path = tmp_path / "generation" / "master.json"
    manifest_path.parent.mkdir()
    manifest_path.write_text(
        json.dumps({"shots": [{"shot_id": "S1", "order": 1, "display_text": "원문", "tts_text": "원문"}]}),
        encoding="utf-8",
    )
    ass_path = tmp_path / "candidate" / "subtitles.ass"
    ass_path.parent.mkdir()
    ass_path.write_text("Style: DocuNarrator_v4,Pretendard,52\n", encoding="utf-8")

    app = FastAPI()
    app.include_router(
        create_script_router(
            get_manifest_path=lambda: manifest_path,
            fallback_manifest_path=tmp_path / "fallback.json",
            get_ass_path=lambda: ass_path,
            fact_checker_factory=_Checker,
        )
    )
    client = TestClient(app)

    assert client.get("/api/manifest/full").json()["shots"][0]["shot_id"] == "S1"
    audit = client.get("/api/factcheck/sentence_audit").json()
    assert audit["statistics"]["grade_a_count"] == 1
    revised = client.post(
        "/api/factcheck/apply_revision",
        json={"shot_id": "S1", "revised_text": "보정문"},
    )
    assert revised.status_code == 200
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["shots"][0]["tts_text"] == "보정문"
    subtitle = client.post("/api/subtitles/update", json={"font_size": 60})
    assert subtitle.status_code == 200
    assert "DocuNarrator_v4,Pretendard,60" in ass_path.read_text(encoding="utf-8")


def test_script_router_returns_not_found_for_missing_manifest(tmp_path: Path) -> None:
    app = FastAPI()
    app.include_router(
        create_script_router(
            get_manifest_path=lambda: tmp_path / "missing.json",
            fallback_manifest_path=tmp_path / "also-missing.json",
            get_ass_path=lambda: tmp_path / "missing.ass",
            fact_checker_factory=_Checker,
        )
    )
    assert TestClient(app).get("/api/manifest/full").status_code == 404
