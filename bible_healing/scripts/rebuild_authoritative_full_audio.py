# -*- coding: utf-8 -*-
"""Rebuild full authoritative audio by concatenating verified sanitized scene WAVs."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from verify_authoritative_audio import (  # noqa: E402
    backup_unsanitized_wavs,
    verify_authoritative_audio,
)

_DEFAULT_JOB = (
    Path(__file__).resolve().parents[1]
    / "runs"
    / "ep01_anxious_night"
    / "hermes_jobs"
    / "full"
)


def ffmpeg_bin() -> str:
    env = os.environ.get("FFMPEG_BIN")
    if env and Path(env).exists():
        return env
    hermes = Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")
    if hermes.exists():
        return str(hermes)
    return "ffmpeg"


def rebuild_authoritative_audio(
    job: Path,
    *,
    ffmpeg: str | None = None,
    work_dir: Path | None = None,
    output_name: str = "full-authoritative-audio.wav",
) -> dict:
    """
    Verify then concat job-root scene_*.wav into authoritative full WAV.

    Scene count comes from scenes.json (not a hardcoded 110).
    Only runs concat when verify_authoritative_audio reports ok.
    """
    job = Path(job)
    result = verify_authoritative_audio(job)
    if not result["ok"]:
        msg = "authoritative audio verify failed: " + "; ".join(result["errors"])
        raise SystemExit(msg)

    wavs: list[Path] = list(result["wavs"])
    if not wavs:
        raise SystemExit("authoritative audio verify passed but no wavs to concat")

    work = Path(work_dir) if work_dir is not None else job / "authoritative_audio_rebuild"
    work.mkdir(parents=True, exist_ok=True)
    lst = work / "scene_audio_concat.txt"
    lst.write_text(
        "\n".join(f"file '{p.resolve().as_posix()}'" for p in wavs),
        encoding="utf-8",
    )
    out = work / output_name
    ff = ffmpeg or ffmpeg_bin()
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
            "-vn",
            "-ac",
            "2",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s16le",
            str(out),
        ],
        check=True,
    )
    info = {
        "ok": True,
        "output": str(out),
        "scenes": len(wavs),
        "scene_count": result["scene_count"],
        "job": str(job),
        "concat_list": str(lst),
    }
    return info


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description="Verify sanitized M4 scene WAVs and rebuild authoritative full audio"
    )
    ap.add_argument(
        "--job",
        default=str(_DEFAULT_JOB),
        help="Hermes job directory (default: ep01 full)",
    )
    ap.add_argument(
        "--backup-unsanitized",
        action="store_true",
        help="Move unsanitized scene WAVs to audio_pre_sanitize_backup_20260813/ first",
    )
    ap.add_argument(
        "--dry-run-backup",
        action="store_true",
        help="With --backup-unsanitized, only report planned moves (no filesystem change)",
    )
    args = ap.parse_args(argv)
    job = Path(args.job)
    if args.backup_unsanitized:
        moved = backup_unsanitized_wavs(job, dry_run=bool(args.dry_run_backup))
        print(json.dumps({"backup": moved}, ensure_ascii=False, indent=2))
    info = rebuild_authoritative_audio(job)
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
