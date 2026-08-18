# -*- coding: utf-8 -*-
"""HTTP SuperTonic client resolution. No live server required."""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
MODERN = Path(__file__).resolve().parents[2] / "modern" / "scripts"
sys.path.insert(0, str(MODERN))

from supertonic3_http import prefer_http, resolve_supertonic_http_url  # noqa: E402


def test_default_url_is_local_3093():
    assert resolve_supertonic_http_url(env={}, lock={}) == "http://127.0.0.1:3093"


def test_env_overrides_lock_url():
    url = resolve_supertonic_http_url(
        env={"SUPERTONIC3_URL": "http://127.0.0.1:4093"},
        lock={"tts": {"http_url": "http://127.0.0.1:3093"}},
    )
    assert url == "http://127.0.0.1:4093"


def test_lock_url_used_when_env_empty():
    url = resolve_supertonic_http_url(
        env={},
        lock={"tts": {"http_url": "http://127.0.0.1:3093"}},
    )
    assert url == "http://127.0.0.1:3093"


def test_prefer_http_off_when_env_zero():
    assert prefer_http(env={"SUPERTONIC3_HTTP": "0"}, lock={"tts": {"prefer_http": True}}) is False


def test_prefer_http_on_by_lock_default():
    assert prefer_http(env={}, lock={"tts": {"prefer_http": True}}) is True


def test_canonical_lock_stays_on_supertonic_http():
    import json

    lock_path = Path(__file__).resolve().parents[1] / "config" / "media_rules_lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    assert lock["tts"]["engine"] == "supertonic3"
    assert lock["tts"]["prefer_http"] is True
    assert lock["tts"]["require_korean_numbers"] is True
    assert lock["voice"]["narrator"]["voice"] == "F5"
    assert lock["voice"]["scripture"]["voice"] == "M4"
    assert lock["voice"]["narrator"]["total_step"] == 8
    assert lock["voice"]["scripture"]["total_step"] == 10
