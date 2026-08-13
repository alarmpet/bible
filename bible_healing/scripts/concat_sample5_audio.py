# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess
from pathlib import Path

JOB = (
    Path(__file__).resolve().parents[1]
    / "runs"
    / "ep01_anxious_night"
    / "hermes_jobs"
    / "sample5_F10_M10"
)
FFMPEG = Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")
FFPROBE = Path(r"C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe")


def main() -> None:
    lines = []
    for i in range(1, 12):
        p = (JOB / f"scene_{i}.wav").resolve()
        if not p.exists():
            raise SystemExit(f"missing {p}")
        lines.append(f"file '{p.as_posix()}'")
    lst = JOB / "_concat_audio.txt"
    lst.write_text("\n".join(lines), encoding="utf-8")
    ff = str(FFMPEG if FFMPEG.exists() else "ffmpeg")
    mp3 = JOB / "sample5_F10_M10_full.mp3"
    wav = JOB / "sample5_F10_M10_full.wav"
    subprocess.run(
        [ff, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:a", "libmp3lame", "-b:a", "192k", str(mp3)],
        check=True,
    )
    subprocess.run(
        [ff, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:a", "pcm_s16le", str(wav)],
        check=True,
    )
    ffp = str(FFPROBE if FFPROBE.exists() else "ffprobe")
    d = subprocess.check_output(
        [ffp, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(mp3)],
        text=True,
    ).strip()
    print(f"ok duration_sec={d} min={float(d)/60:.2f} mp3={mp3} mb={mp3.stat().st_size/1e6:.2f}")


if __name__ == "__main__":
    main()
