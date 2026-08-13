"""Validate rendered scene MP4s by decoding them with ffmpeg."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def validate(job: Path, start: int, end: int, ffmpeg: str) -> list[dict]:
    failures = []
    for order in range(start, end + 1):
        path = job / f"scene_{order}_synced.mp4"
        if not path.exists():
            failures.append({"order": order, "error": "missing"})
            continue
        result = subprocess.run([ffmpeg, "-v", "error", "-i", str(path), "-f", "null", "-"], capture_output=True)
        if result.returncode != 0:
            failures.append({"order": order, "error": result.stderr.decode("utf-8", errors="replace")[-500:]})
    return failures


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, required=True)
    ap.add_argument("--ffmpeg", required=True)
    args = ap.parse_args()
    failures = validate(Path(args.job).resolve(), args.start, args.end, args.ffmpeg)
    print({"ok": not failures, "checked": args.end - args.start + 1, "failures": failures})
    raise SystemExit(1 if failures else 0)
