# -*- coding: utf-8 -*-
"""Burn ASS onto _body_nosub.mp4 → final-ep01-full.mp4 (full re-encode video)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

JOB = (
    Path(__file__).resolve().parents[1]
    / "runs"
    / "ep01_anxious_night"
    / "hermes_jobs"
    / "full"
)
FFMPEG = Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")
FFPROBE = Path(
    r"C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe"
)


def main() -> None:
    job = JOB
    body = job / "_body_nosub.mp4"
    ass = job / "subtitles-timed-ko.ass"
    out = job / "final-ep01-full.mp4"
    tmp = job / "final-ep01-full.partial.mp4"
    if not body.exists():
        raise SystemExit(f"missing {body}")
    if not ass.exists():
        raise SystemExit(f"missing {ass}")

    ff = str(FFMPEG if FFMPEG.exists() else "ffmpeg")
    ffp = str(FFPROBE if FFPROBE.exists() else "ffprobe")

    # Use relative path from job cwd for subtitles filter reliability on Windows
    # Copy ass to simple name if needed
    ass_rel = "subtitles-timed-ko.ass"
    print(f"input body={body.stat().st_size} ass={ass.stat().st_size}")
    print("burning ASS (this takes a while for ~50min)...")

    # fontsdir for malgun
    fontsdir = r"C\:/Windows/Fonts"
    # subtitles filter with force_style optional
    vf = f"subtitles={ass_rel}:fontsdir='C\\:/Windows/Fonts'"

    cmd = [
        ff,
        "-y",
        "-i",
        str(body.name),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(tmp.name),
    ]
    print("cmd:", " ".join(cmd))
    r = subprocess.run(cmd, cwd=str(job))
    if r.returncode != 0:
        # fallback ass filter with escaped path
        ass_esc = str(ass.resolve()).replace("\\", "/").replace(":", "\\:")
        cmd2 = [
            ff,
            "-y",
            "-i",
            str(body),
            "-vf",
            f"ass='{ass_esc}'",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            str(tmp),
        ]
        print("retry ass filter...")
        r = subprocess.run(cmd2)
        if r.returncode != 0:
            raise SystemExit(f"ffmpeg failed code={r.returncode}")

    # validate
    d = subprocess.check_output(
        [
            ffp,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(tmp if tmp.exists() else job / tmp.name),
        ],
        text=True,
        cwd=str(job),
    ).strip()
    dur = float(d)
    if dur < 2000:  # expect ~3000s
        raise SystemExit(f"output too short: {dur}s")

    final_path = job / "final-ep01-full.mp4"
    partial = job / "final-ep01-full.partial.mp4"
    if not partial.exists():
        partial = job / tmp.name
    if final_path.exists():
        final_path.unlink()
    partial.replace(final_path)

    report = {
        "ok": True,
        "final": str(final_path),
        "duration_sec": dur,
        "duration_min": round(dur / 60, 2),
        "bytes": final_path.stat().st_size,
    }
    (job / "reports").mkdir(exist_ok=True)
    (job / "reports" / "final_burn_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
