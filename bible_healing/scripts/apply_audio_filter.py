# -*- coding: utf-8 -*-
"""Apply the locked scripture ffmpeg filter (asetrate pitch + atempo)."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

_BH_ROOT = Path(__file__).resolve().parents[1]
_LOCK_PATH = _BH_ROOT / "config" / "media_rules_lock.json"
_LOCK_FILTER_DEFAULT = (
    "asetrate=24000*0.92,aresample=24000,atempo=1.087,"
    "highpass=f=65,lowpass=f=8500,equalizer=f=250:t=q:w=1:g=1.5"
)


def load_media_lock(path: Path | None = None) -> dict:
    return json.loads((path or _LOCK_PATH).read_text(encoding="utf-8"))


def scripture_ffmpeg_filter(lock: dict | None = None, pitch_percent: float = -8.0) -> str:
    """Return the lock ffmpeg chain; rebuild asetrate/atempo if pitch differs."""
    lock = lock or load_media_lock()
    base = (lock.get("voice") or {}).get("scripture", {}).get("audio_filter") or _LOCK_FILTER_DEFAULT
    locked_pitch = float((lock.get("voice") or {}).get("scripture", {}).get("pitch", -8))
    if abs(float(pitch_percent) - locked_pitch) < 1e-6:
        return str(base)
    rate = 1.0 + float(pitch_percent) / 100.0
    atempo = 1.0 / rate
    return (
        f"asetrate=24000*{rate:.4g},aresample=24000,atempo={atempo:.4g},"
        "highpass=f=65,lowpass=f=8500,equalizer=f=250:t=q:w=1:g=1.5"
    )


def ffmpeg_bin() -> str:
    env = os.environ.get("FFMPEG_BIN")
    if env and Path(env).exists():
        return env
    modern = Path(__file__).resolve().parents[2] / "modern" / "scripts"
    if str(modern) not in sys.path:
        sys.path.insert(0, str(modern))
    try:
        from paths import FFMPEG  # type: ignore

        if FFMPEG.exists():
            return str(FFMPEG)
    except Exception:
        pass
    hermes = Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")
    if hermes.exists():
        return str(hermes)
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise FileNotFoundError("ffmpeg not found")


def apply_scripture_filter(src: Path, dst: Path, pitch_percent: float = -8.0) -> dict:
    """Pitch-shift scripture WAV with the lock asetrate chain, then restore duration."""
    src = Path(src)
    dst = Path(dst)
    if not src.exists() or src.stat().st_size <= 0:
        raise FileNotFoundError(f"scripture filter src missing: {src}")
    filt = scripture_ffmpeg_filter(pitch_percent=pitch_percent)
    # Lock chain assumes 24 kHz input; normalize first if the chain starts at asetrate=24000.
    af = filt if filt.startswith("aresample=") else f"aresample=24000,{filt}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp_out = dst
    if src.resolve() == dst.resolve():
        tmp_out = dst.with_suffix(".filt.wav")
    cmd = [
        ffmpeg_bin(),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-af",
        af,
        "-c:a",
        "pcm_s16le",
        str(tmp_out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        err = (res.stderr or res.stdout or "").strip()
        raise RuntimeError(f"ffmpeg scripture filter failed: {err}")
    if tmp_out != dst:
        tmp_out.replace(dst)
    return {
        "filter_applied": True,
        "filter": filt,
        "af": af,
        "pitch_percent": float(pitch_percent),
        "src": str(src),
        "dst": str(dst),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Apply locked scripture audio filter")
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--pitch", type=float, default=-8.0)
    args = ap.parse_args()
    info = apply_scripture_filter(Path(args.src), Path(args.dst), pitch_percent=args.pitch)
    print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    main()
