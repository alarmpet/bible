# -*- coding: utf-8 -*-
"""Finish full render: concat scene_*_synced.mp4 + burn ASS (skip re-encode scenes)."""
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


def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        err = (r.stderr or b"").decode("utf-8", errors="replace")[-2500:]
        raise RuntimeError(err)


def main() -> None:
    job = JOB
    ff = str(FFMPEG if FFMPEG.exists() else "ffmpeg")
    ffp = str(FFPROBE if FFPROBE.exists() else "ffprobe")
    man = json.loads((job / "scene_audio_manifest.json").read_text(encoding="utf-8"))
    orders = sorted(int(s["order"]) for s in man["scenes"])
    print(f"orders={len(orders)}")
    for o in orders:
        p = job / f"scene_{o}_synced.mp4"
        if not p.exists() or p.stat().st_size < 1000:
            raise SystemExit(f"missing {p.name}")
    print("all synced present")

    lst = job / "_concat_v3.txt"
    lst.write_text(
        "\n".join(f"file '{(job / f'scene_{o}_synced.mp4').resolve().as_posix()}'" for o in orders),
        encoding="utf-8",
    )
    bare = job / "_body_nosub.mp4"
    print("concat...")
    try:
        run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(bare)])
    except RuntimeError:
        print("re-encode concat...")
        run(
            [
                ff,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(lst),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(bare),
            ]
        )
    print(f"body bytes={bare.stat().st_size}")

    ass = job / "subtitles-timed-ko.ass"
    if not ass.exists():
        raise SystemExit("missing ASS")
    out = job / "final-ep01-full.mp4"
    ass_filter = str(ass.resolve()).replace("\\", "/").replace(":", "\\:")
    print("burn ASS...")
    try:
        run(
            [
                ff,
                "-y",
                "-i",
                str(bare),
                "-vf",
                f"ass='{ass_filter}'",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "copy",
                "-movflags",
                "+faststart",
                str(out),
            ]
        )
    except RuntimeError as e:
        print("ass filter failed, try subtitles=", e)
        run(
            [
                ff,
                "-y",
                "-i",
                str(bare),
                "-vf",
                f"subtitles='{ass_filter}'",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "copy",
                "-movflags",
                "+faststart",
                str(out),
            ]
        )

    d = subprocess.check_output(
        [
            ffp,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(out),
        ],
        text=True,
    ).strip()
    report = {
        "ok": True,
        "final": str(out),
        "duration_sec": float(d),
        "duration_min": round(float(d) / 60, 2),
        "scenes": len(orders),
        "bytes": out.stat().st_size,
        "captions": "ass_timed",
    }
    (job / "reports").mkdir(exist_ok=True)
    (job / "reports" / "render_v3_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import subprocess

    main()
