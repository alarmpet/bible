# -*- coding: utf-8 -*-
"""Render authoritative full MP4: ambient pingpong BG + full WAV + aligned ASS.

Thin CLI around the locked D: final path. Prefer calling via
run_full_media_pipeline.py rather than ad-hoc one-offs.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

_MODULE_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_JOB = (
    _MODULE_ROOT
    / "bible_healing"
    / "runs"
    / "ep01_anxious_night"
    / "hermes_jobs"
    / "full"
)
_D_ROOT = Path(r"D:\bible_healing_ep01")
_DEFAULT_OUTPUT = _D_ROOT / "final" / "deploy-ep01-authoritative-audio-aligned.mp4"
_DEFAULT_WORK = _D_ROOT / "work" / "authoritative_audio_rebuild"


def _ffmpeg() -> str:
    env = os.environ.get("FFMPEG_BIN")
    if env and Path(env).exists():
        return env
    hermes = Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")
    if hermes.exists():
        return str(hermes)
    return "ffmpeg"


def _ffprobe() -> str:
    env = os.environ.get("FFPROBE_BIN")
    if env and Path(env).exists():
        return env
    hermes = Path(
        r"C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe"
    )
    if hermes.exists():
        return str(hermes)
    return "ffprobe"


def render_authoritative_full(
    job: Path,
    *,
    output: Path | None = None,
    work_dir: Path | None = None,
    module_root: Path | None = None,
    ffmpeg: str | None = None,
    ffprobe: str | None = None,
) -> dict:
    """Concat ambient 1-min samples, burn ASS, mux authoritative WAV → D: final MP4."""
    job = Path(job)
    root = Path(module_root) if module_root is not None else _MODULE_ROOT
    out = Path(output) if output is not None else _DEFAULT_OUTPUT
    work = Path(work_dir) if work_dir is not None else _DEFAULT_WORK

    bg = root / "bible_healing" / "assets" / "movie-sample" / "pingpong-1min"
    audio = job / "authoritative_audio_rebuild" / "full-authoritative-audio.wav"
    ass = job / "subtitles-full-audio-aligned.ass"
    if not audio.is_file():
        raise SystemExit(f"missing authoritative audio: {audio}")
    if not ass.is_file():
        raise SystemExit(f"missing ASS: {ass}")
    if not bg.is_dir():
        raise SystemExit(f"missing background bank: {bg}")

    work.mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)

    fp = ffprobe or _ffprobe()
    ff = ffmpeg or _ffmpeg()
    dur = float(
        subprocess.check_output(
            [
                fp,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(audio),
            ],
            text=True,
        ).strip()
    )
    samples = sorted(bg.glob("*.mp4"))
    if not samples:
        raise SystemExit(f"no pingpong samples in {bg}")
    lst = work / "background_concat.txt"
    lst.write_text(
        "\n".join(f"file '{p.as_posix()}'" for _ in range(6) for p in samples),
        encoding="utf-8",
    )
    esc = str(ass).replace("\\", "/").replace(":", "\\:")
    vf = f"setpts=3*PTS,trim=duration={dur:.3f},subtitles='{esc}'"
    subprocess.run(
        [
            ff,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-i",
            str(audio),
            "-vf",
            vf,
            "-t",
            str(dur),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "30",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(out),
        ],
        check=True,
    )
    return {
        "ok": True,
        "output": str(out),
        "duration": dur,
        "samples": len(samples),
        "audio_source": str(audio),
        "ass": str(ass),
        "job": str(job),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Render authoritative full MP4 to D:\\bible_healing_ep01\\final"
    )
    ap.add_argument(
        "--job",
        default=str(_DEFAULT_JOB),
        help="Hermes full job directory",
    )
    ap.add_argument(
        "--output",
        default=str(_DEFAULT_OUTPUT),
        help="Final MP4 path (must be under D: for release)",
    )
    ap.add_argument(
        "--work-dir",
        default=str(_DEFAULT_WORK),
        help="Work dir for concat list",
    )
    args = ap.parse_args(argv)
    info = render_authoritative_full(
        Path(args.job),
        output=Path(args.output),
        work_dir=Path(args.work_dir),
    )
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0 if info.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
