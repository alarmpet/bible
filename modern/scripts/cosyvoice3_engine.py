# -*- coding: utf-8 -*-
"""SuperTonic-compatible CosyVoice3 adapter (opt-in test path).

Production TTS stays SuperTonic3. This engine is used only when
`--engine cosyvoice3` is passed or `tts_multi_voice_cosyvoice.py` is run.

CosyVoice3 needs Python 3.10, so synthesis is always a subprocess into
`D:\\Fun-CosyVoice3\\.venv-cosy3`. This file itself can import from
Python 3.14 / SuperTonic venv.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

MODULE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COSY_ROOT = Path(os.environ.get("COSYVOICE3_ROOT") or r"D:\Fun-CosyVoice3")
DEFAULT_COSY_PYTHON = Path(
    os.environ.get("COSYVOICE3_PYTHON")
    or Path(r"C:\Users\amd\.venvs\cosyvoice3-py310\Scripts\python.exe")
)
DEFAULT_MODEL_DIR = Path(
    os.environ.get("COSYVOICE3_MODEL_DIR")
    or (DEFAULT_COSY_ROOT / "pretrained_models" / "Fun-CosyVoice3-0.5B")
)
DEFAULT_VOICE_MAP = Path(
    os.environ.get("COSYVOICE3_VOICE_MAP")
    or (MODULE_ROOT / "bible_healing" / "config" / "cosyvoice3_voices.json")
)
WORKER = Path(__file__).resolve().parent / "cosyvoice3_worker.py"


def default_instruct_for(voice: str, speed: float) -> str:
    """Map SuperTonic voice+speed to a CosyVoice3 instruct2 prompt."""
    speed = float(speed)
    if voice.upper().startswith("M"):
        tone = (
            "Speak Korean. You are a calm, low, kind elderly male pastor "
            "reading Scripture. Steady, gentle, never angry or rushed."
        )
    else:
        tone = (
            "Speak Korean. You are a calm, warm female narrator for a "
            "healing Bible video. Gentle, clear, never theatrical."
        )
    return (
        f"You are a helpful assistant. {tone} "
        f"Use speaking speed {speed:.2f}.<|endofprompt|>"
    )


def load_voice_map(path: Path | None = None) -> dict[str, Any]:
    src = path or DEFAULT_VOICE_MAP
    if not src.exists():
        return {"voices": {}}
    return json.loads(src.read_text(encoding="utf-8"))


def resolve_voice_spec(
    voice: str,
    speed: float,
    voice_map: dict[str, Any] | None = None,
    ref_wav: str | Path | None = None,
    instruct: str | None = None,
) -> dict[str, Any]:
    """Resolve SuperTonic voice id (F5/M4) to CosyVoice3 clone + instruct."""
    vm = voice_map if voice_map is not None else load_voice_map()
    voices = vm.get("voices") or {}
    spec = dict(voices.get(voice) or voices.get(voice.upper()) or {})
    if ref_wav:
        spec["ref_wav"] = str(ref_wav)
    raw_ref = spec.get("ref_wav")
    if raw_ref:
        ref_path = Path(raw_ref)
        if not ref_path.is_absolute():
            ref_path = MODULE_ROOT / ref_path
        spec["ref_wav"] = str(ref_path)
    if instruct:
        spec["instruct"] = instruct
    if not spec.get("instruct"):
        spec["instruct"] = default_instruct_for(voice, speed)
    if not spec.get("mode"):
        spec["mode"] = "instruct2"
    spec["voice"] = voice
    spec["speed"] = float(speed)
    return spec


def require_install(cosy_root: Path | None = None, cosy_python: Path | None = None) -> None:
    root = Path(cosy_root or DEFAULT_COSY_ROOT)
    py = Path(cosy_python or DEFAULT_COSY_PYTHON)
    model = DEFAULT_MODEL_DIR
    missing = []
    if not root.exists():
        missing.append(f"COSYVOICE3_ROOT missing: {root}")
    if not py.exists():
        missing.append(f"COSYVOICE3_PYTHON missing: {py}")
    if not model.exists():
        missing.append(f"COSYVOICE3_MODEL_DIR missing: {model}")
    if not WORKER.exists():
        missing.append(f"worker missing: {WORKER}")
    if missing:
        joined = "\n".join(missing)
        raise SystemExit(
            "CosyVoice3 test path is not installed.\n"
            f"{joined}\n"
            "Run: powershell -File bible_healing/scripts/install_cosyvoice3.ps1"
        )


class CosyVoice3Engine:
    """Drop-in stand-in for Supertonic3Engine.synthesize_to_file()."""

    DEFAULT_VOICES = ["M4", "F5", "M1", "F1"]

    def __init__(
        self,
        output_dir: str | Path | None = None,
        *,
        cosy_root: str | Path | None = None,
        cosy_python: str | Path | None = None,
        model_dir: str | Path | None = None,
        voice_map_path: str | Path | None = None,
        threads: int | None = None,
    ) -> None:
        self.output_dir = Path(output_dir or Path.cwd())
        self.cosy_root = Path(cosy_root or DEFAULT_COSY_ROOT)
        self.cosy_python = Path(cosy_python or DEFAULT_COSY_PYTHON)
        self.model_dir = Path(model_dir or DEFAULT_MODEL_DIR)
        self.voice_map = load_voice_map(Path(voice_map_path) if voice_map_path else None)
        self.threads = int(threads or os.environ.get("COSYVOICE3_THREADS") or max(1, (os.cpu_count() or 4) - 1))

    def list_voices(self) -> list[str]:
        mapped = list((self.voice_map.get("voices") or {}).keys())
        return mapped or list(self.DEFAULT_VOICES)

    def synthesize_to_file(
        self,
        *,
        text: str,
        output_path: str | Path | None = None,
        model: str | None = None,
        model_dir: str | Path | None = None,
        auto_download: bool | None = None,
        intra_op_num_threads: int | None = None,
        inter_op_num_threads: int | None = None,
        voice: str = "M4",
        voice_style: str | None = None,
        voice_style_path: str | Path | None = None,
        lang: str | None = "ko",
        speed: float = 0.95,
        total_step: int = 8,
        max_chunk_length: int | None = None,
        silence_duration: float = 0.3,
        verbose: bool = True,
        instruct: str | None = None,
        ref_wav: str | Path | None = None,
        mode: str | None = None,
    ) -> dict[str, Any]:
        del model, auto_download, inter_op_num_threads  # SuperTonic-only knobs
        text = (text or "").strip()
        if not text:
            raise ValueError("text is required")
        out = Path(output_path) if output_path else self.output_dir / "cosyvoice3.wav"
        out.parent.mkdir(parents=True, exist_ok=True)
        spec = resolve_voice_spec(
            voice=voice_style or voice,
            speed=float(speed),
            voice_map=self.voice_map,
            ref_wav=ref_wav or voice_style_path,
            instruct=instruct,
        )
        if mode:
            spec["mode"] = mode
        request = {
            "text": text,
            "output_path": str(out),
            "ref_wav": spec.get("ref_wav"),
            "prompt_text": spec.get("prompt_text") or "",
            "instruct": spec.get("instruct"),
            "mode": spec.get("mode") or "instruct2",
            "model_dir": str(model_dir or self.model_dir),
            "cosy_root": str(self.cosy_root),
            "threads": int(intra_op_num_threads or self.threads),
            "lang": lang or "ko",
            "speed": float(speed),
            "silence_duration": float(silence_duration),
            "max_chunk_length": int(max_chunk_length or 90),
            "voice": spec.get("voice"),
        }
        result = run_worker(request, cosy_python=self.cosy_python, verbose=verbose)
        result.setdefault("path", str(out))
        result.setdefault("voice", voice)
        result.setdefault("engine", "cosyvoice3")
        return result


def run_worker(
    request: dict[str, Any],
    *,
    cosy_python: Path | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    py = Path(cosy_python or DEFAULT_COSY_PYTHON)
    require_install(Path(request.get("cosy_root") or DEFAULT_COSY_ROOT), py)
    started = time.perf_counter()
    proc = subprocess.run(
        [str(py), str(WORKER), "--request-json", "-"],
        input=json.dumps(request, ensure_ascii=False),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(request.get("cosy_root") or DEFAULT_COSY_ROOT),
    )
    elapsed = time.perf_counter() - started
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"cosyvoice3_worker failed ({proc.returncode}): {err[-4000:]}")
    line = (proc.stdout or "").strip().splitlines()
    payload = {}
    for raw in reversed(line):
        raw = raw.strip()
        if raw.startswith("{") and raw.endswith("}"):
            payload = json.loads(raw)
            break
    if not payload.get("ok"):
        raise RuntimeError(f"cosyvoice3_worker returned error: {payload or proc.stdout}")
    payload["wall_seconds"] = round(elapsed, 3)
    if verbose:
        print(
            f"cosyvoice3 {payload.get('voice')} {Path(request['output_path']).name} "
            f"dur={payload.get('duration')} rtf={payload.get('rtf')}",
            file=sys.stderr,
        )
    return payload


def run_batch(
    items: list[dict[str, Any]],
    *,
    cosy_root: Path | None = None,
    cosy_python: Path | None = None,
    model_dir: Path | None = None,
    threads: int | None = None,
    verbose: bool = True,
) -> list[dict[str, Any]]:
    """Load the 0.5B model once and synthesize many short sentences."""
    request = {
        "batch": items,
        "model_dir": str(model_dir or DEFAULT_MODEL_DIR),
        "cosy_root": str(cosy_root or DEFAULT_COSY_ROOT),
        "threads": int(threads or os.environ.get("COSYVOICE3_THREADS") or max(1, (os.cpu_count() or 4) - 1)),
    }
    return run_worker(request, cosy_python=cosy_python or DEFAULT_COSY_PYTHON, verbose=verbose).get("items") or []
