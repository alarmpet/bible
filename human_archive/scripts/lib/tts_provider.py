# -*- coding: utf-8 -*-
"""TTS provider abstractions: real SuperTonic3 HTTP synthesis and test tone fixtures."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Protocol


class TTSProvider(Protocol):
    def synthesize_phrase(
        self,
        text: str,
        out_wav: Path,
        speed: float = 0.96,
        silence_duration: float = 0.0,
    ) -> dict[str, Any]:
        raise NotImplementedError


class ToneFixtureProvider:
    """Test-only: generates a 220Hz sine tone for CI/CD without needing a real TTS engine."""

    def synthesize_phrase(
        self,
        text: str,
        out_wav: Path,
        speed: float = 0.96,
        silence_duration: float = 0.0,
    ) -> dict[str, Any]:
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        dur = max(2.0, len(text) * 0.18)
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel", "error",
            "-f", "lavfi",
            "-i", f"sine=frequency=220:duration={dur:.3f}",
            "-af", "highpass=f=50,lowpass=f=7500,volume=-6dB",
            "-c:a", "pcm_s16le",
            "-ar", "48000",
            "-ac", "1",
            str(out_wav),
        ]
        subprocess.run(cmd, check=True)
        return {
            "provider": "tone_fixture",
            "voice": "sine_220hz",
            "speed": speed,
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest().upper(),
            "duration_sec": dur,
            "silence_duration_sec": silence_duration,
        }


_SUPERTONIC3_DEFAULT_URL = "http://127.0.0.1:3093"


def _supertonic3_health(base_url: str, timeout: float = 2.0) -> bool:
    url = base_url.rstrip("/") + "/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            if resp.status != 200:
                return False
            payload = json.loads(resp.read().decode("utf-8"))
            return bool(payload.get("ok"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return False


class SupertonicHttpProvider:
    """Production TTS: calls real SuperTonic3 M4 HTTP server.
    
    NEVER falls back to sine tone — raises RuntimeError if server is unreachable.
    """

    def __init__(self, base_url: str = _SUPERTONIC3_DEFAULT_URL, auto_start: bool = True):
        self.base_url = base_url.rstrip("/")
        self.auto_start = auto_start

    def synthesize_phrase(
        self,
        text: str,
        out_wav: Path,
        speed: float = 0.94,
        voice: str = "M4",
        total_step: int = 10,
        silence_duration: float = 0.0,
        max_chunk_length: int = 120,
    ) -> dict[str, Any]:
        out_wav.parent.mkdir(parents=True, exist_ok=True)

        # 1. Verify server is alive — auto-start if offline, fail-closed if unreachable
        if not _supertonic3_health(self.base_url):
            if self.auto_start:
                print(f"[*] SuperTonic3 TTS server offline at {self.base_url}. Auto-launching...")
                try:
                    from lib.external_service_manager import ensure_supertonic3_running
                except ImportError:
                    try:
                        from external_service_manager import ensure_supertonic3_running
                    except ImportError:
                        ensure_supertonic3_running = None
                if ensure_supertonic3_running:
                    try:
                        ensure_supertonic3_running()
                    except Exception as auto_err:
                        print(f"SuperTonic3 auto-launch failed: {auto_err}")

            if not _supertonic3_health(self.base_url):
                raise RuntimeError(
                    f"SuperTonic3 TTS server unreachable at {self.base_url}. "
                    f"Cannot synthesize audio without active server."
                )

        # 2. Call real TTS API
        payload = {
            "text": text,
            "voice": voice,
            "lang": "ko",
            "speed": float(speed),
            "total_step": int(total_step),
            "silence_duration": float(silence_duration),
            "max_chunk_length": int(max_chunk_length),
            "verbose": False,
        }
        req = urllib.request.Request(
            self.base_url + "/api/tts",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        if not body.get("ok"):
            raise RuntimeError(f"SuperTonic3 TTS failed: {body.get('error', 'unknown')}")

        # 3. Copy server output wav to target path
        raw_wav = Path(body["path"])
        if not raw_wav.exists():
            raise FileNotFoundError(f"SuperTonic3 server wav missing: {raw_wav}")

        # 4. Apply documentary broadcast EQ filter
        af = "highpass=f=50,lowpass=f=7500,equalizer=f=160:t=q:w=1:g=2.5,equalizer=f=3000:t=q:w=1:g=1.2"
        filtered_wav = out_wav.parent / f"_eq_{out_wav.name}"
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(raw_wav),
            "-af", af,
            "-c:a", "pcm_s16le",
            "-ar", "48000",
            "-ac", "1",
            str(filtered_wav),
        ]
        subprocess.run(cmd, check=True)

        # 5. Atomic rename
        if out_wav.exists():
            out_wav.unlink()
        shutil.move(str(filtered_wav), str(out_wav))

        # 6. Get actual duration
        dur_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(out_wav),
        ]
        dur_result = subprocess.run(dur_cmd, capture_output=True, text=True, check=True)
        actual_dur = float(dur_result.stdout.strip())

        return {
            "provider": "supertonic3_http",
            "voice": voice,
            "speed": speed,
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest().upper(),
            "duration_sec": actual_dur,
            "silence_duration_sec": silence_duration,
        }


def validate_audio_provenance(manifest: dict[str, Any], publishable: bool = False) -> list[str]:
    errors = []
    prov = manifest.get("provenance", {})
    kind = prov.get("audio_kind", "")
    if publishable and kind in ["tone_fixture", "non-speech"]:
        errors.append(f"publishable release rejects non-speech fixture: '{kind}'")
    return errors



