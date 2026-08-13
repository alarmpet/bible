# -*- coding: utf-8 -*-
"""Concat PRE_ROLL intro.mp4 before body final mp4.

Normalizes both clips to the same video/audio layout so concat is reliable when
intro has no audio track.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

HERMES_FFMPEG = Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")


def resolve_ffmpeg() -> str:
    if HERMES_FFMPEG.exists():
        return str(HERMES_FFMPEG)
    return "ffmpeg"


def run_ff(ffmpeg: str, args: list[str]) -> None:
    r = subprocess.run([ffmpeg, *args], capture_output=True, text=True)
    if r.returncode != 0:
        err = (r.stderr or r.stdout or "")[-3000:]
        print(err)
        raise SystemExit(r.returncode)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--body", default="", help="body mp4 path; default: search final*.mp4 in job")
    ap.add_argument("--intro", default="", help="default job/intro.mp4")
    ap.add_argument("--out", default="")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    args = ap.parse_args()
    job = Path(args.job)
    intro = Path(args.intro) if args.intro else job / "intro.mp4"
    if not intro.exists():
        raise SystemExit(f"missing intro: {intro}")
    body = Path(args.body) if args.body else None
    if not body:
        cands = (
            sorted(job.glob("final-preview*.mp4"))
            + sorted(job.glob("final-youtube*.mp4"))
            + sorted(job.glob("final*.mp4"))
            + sorted(job.glob("*tts*.mp4"))
            + sorted(job.glob("merged-scenes*.mp4"))
        )
        cands = [c for c in cands if "with_intro" not in c.name]
        if not cands:
            raise SystemExit("no body mp4 found; pass --body")
        body = cands[0]
    out = Path(args.out) if args.out else job / "final_with_intro.mp4"
    ffmpeg = resolve_ffmpeg()
    w, h = args.width, args.height
    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p"
    )

    tmp_intro = job / "_preroll_intro_norm.mp4"
    tmp_body = job / "_preroll_body_norm.mp4"
    try:
        # intro: force silent mono audio matching duration via -shortest
        run_ff(
            ffmpeg,
            [
                "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(intro),
                "-f", "lavfi", "-i", "anullsrc=channel_layout=mono:sample_rate=48000",
                "-filter_complex", f"[0:v]{vf}[v]",
                "-map", "[v]", "-map", "1:a",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                "-movflags", "+faststart",
                str(tmp_intro),
            ],
        )
        # body: keep original audio (mono-resample), normalize video
        run_ff(
            ffmpeg,
            [
                "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(body),
                "-vf", vf,
                "-af", "aresample=48000,aformat=channel_layouts=mono",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart",
                str(tmp_body),
            ],
        )
        lst = job / "_preroll_list.txt"
        lst.write_text(
            f"file '{tmp_intro.resolve().as_posix()}'\n"
            f"file '{tmp_body.resolve().as_posix()}'\n",
            encoding="utf-8",
        )
        run_ff(
            ffmpeg,
            [
                "-y", "-hide_banner", "-loglevel", "error",
                "-f", "concat", "-safe", "0", "-i", str(lst),
                "-c", "copy",
                "-movflags", "+faststart",
                str(out),
            ],
        )
        lst.unlink(missing_ok=True)
        print("wrote", out)
        print("body", body)
    finally:
        for p in (tmp_intro, tmp_body):
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass


if __name__ == "__main__":
    main()
