# -*- coding: utf-8 -*-
"""SuperTonic3 local HTTP client. Same machine, model stays loaded.

Falls back to in-process engine when the server is down.
Does not install or call CosyVoice.
"""
from __future__ import annotations

import json
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_URL = "http://127.0.0.1:3093"


def resolve_supertonic_http_url(env: dict | None = None, lock: dict | None = None) -> str:
    env = env if env is not None else {}
    raw = (env.get("SUPERTONIC3_URL") or "").strip()
    if raw:
        return raw.rstrip("/")
    lock_url = (((lock or {}).get("tts") or {}).get("http_url") or "").strip()
    if lock_url:
        return lock_url.rstrip("/")
    return DEFAULT_URL


def prefer_http(env: dict | None = None, lock: dict | None = None) -> bool:
    env = env if env is not None else {}
    flag = (env.get("SUPERTONIC3_HTTP") or "").strip().lower()
    if flag in {"0", "false", "off", "no"}:
        return False
    if flag in {"1", "true", "on", "yes"}:
        return True
    tts = (lock or {}).get("tts") or {}
    if "prefer_http" in tts:
        return bool(tts["prefer_http"])
    return True


def server_is_up(base_url: str, timeout: float = 0.4) -> bool:
    url = base_url.rstrip("/") + "/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            if resp.status != 200:
                return False
            payload = json.loads(resp.read().decode("utf-8"))
            return bool(payload.get("ok"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return False


class HttpSupertonicEngine:
    """POST /api/tts and copy the local wav the server already wrote."""

    def __init__(self, base_url: str = DEFAULT_URL, output_dir: Path | None = None):
        self.base_url = base_url.rstrip("/")
        self.output_dir = Path(output_dir) if output_dir else Path(".")

    def synthesize_to_file(
        self,
        *,
        text: str,
        output_path: str | Path | None = None,
        voice: str = "M1",
        lang: str | None = "ko",
        speed: float = 1.05,
        total_step: int = 8,
        max_chunk_length: int | None = None,
        silence_duration: float = 0.3,
        verbose: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        dest = Path(output_path) if output_path else self.output_dir / "supertonic3.wav"
        dest.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "text": text,
            "voice": voice,
            "lang": lang or "ko",
            "speed": float(speed),
            "total_step": int(total_step),
            "silence_duration": float(silence_duration),
            "verbose": bool(verbose),
        }
        if max_chunk_length is not None:
            payload["max_chunk_length"] = int(max_chunk_length)
        req = urllib.request.Request(
            self.base_url + "/api/tts",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if not body.get("ok"):
            raise RuntimeError(body.get("error") or "supertonic http tts failed")
        src = Path(body["path"])
        if not src.exists():
            raise FileNotFoundError(f"server wav missing: {src}")
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        info = dict(body)
        info["path"] = str(dest)
        info["via"] = "http"
        return info
