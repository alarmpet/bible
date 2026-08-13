# -*- coding: utf-8 -*-
"""
Insert calm still+silence pads between units so total runtime approaches target.

Does NOT re-run TTS. Uses existing scene_N_synced.mp4 + new pad clips.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths_bh import MODULE_ROOT  # noqa: E402

FFMPEG = Path(
    os.environ.get("FFMPEG_BIN")
    or r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe"
)
FFPROBE = Path(
    os.environ.get("FFPROBE_BIN")
    or r"C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe"
)


def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        err = (r.stderr or b"").decode("utf-8", errors="replace")[-2500:]
        raise RuntimeError(err)


def probe_dur(path: Path) -> float:
    cmd = [
        str(FFPROBE),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return float(out)


def wav_dur(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate() or 1)


def unit_of(sc: dict) -> str:
    meta = sc.get("meta") or {}
    if meta.get("unit"):
        return str(meta["unit"])
    sid = str(sc.get("scene_id") or "")
    if sid.startswith("open"):
        return "opening"
    if sid.startswith("close"):
        return "closing"
    # u01_n0 → u01
    if sid.startswith("u") and "_" in sid:
        return sid.split("_", 1)[0]
    return sid or "unknown"


def make_pad(job: Path, seconds: float, bg: Path, out: Path, ff: str) -> Path:
    if out.exists() and out.stat().st_size > 1000:
        try:
            if abs(probe_dur(out) - seconds) < 0.35:
                return out
        except Exception:
            pass
    # still + silence
    cmd = [
        ff,
        "-y",
        "-loop",
        "1",
        "-i",
        str(bg),
        "-f",
        "lavfi",
        "-i",
        f"anullsrc=r=44100:cl=stereo",
        "-t",
        f"{seconds:.3f}",
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(out),
    ]
    run(cmd)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--target-minutes", type=float, default=100.0)
    ap.add_argument("--min-pad", type=float, default=8.0, help="min silence between units")
    ap.add_argument("--max-pad", type=float, default=45.0)
    ap.add_argument("--final-name", default="final-bible-healing-ep01-100m.mp4")
    args = ap.parse_args()

    job = Path(args.job).resolve()
    ff = str(FFMPEG if FFMPEG.exists() else "ffmpeg")
    scenes = json.loads((job / "scenes.json").read_text(encoding="utf-8"))
    scenes = sorted(scenes, key=lambda s: int(s["order"]))

    # measure current total from wavs (authoritative for speech)
    total = 0.0
    for sc in scenes:
        o = int(sc["order"])
        wav = job / f"scene_{o}.wav"
        total += wav_dur(wav)

    target = args.target_minutes * 60.0
    need = max(0.0, target - total)

    # unit boundaries: after last scene of each unit (except final closing end)
    boundary_after_orders: list[int] = []
    prev_u = None
    for i, sc in enumerate(scenes):
        u = unit_of(sc)
        if prev_u is not None and u != prev_u:
            boundary_after_orders.append(int(scenes[i - 1]["order"]))
        prev_u = u
    # also pad lightly after opening into first unit already covered by boundary
    # drop last boundary if it's before closing only once
    # keep pads between content units + after opening
    n_pads = len(boundary_after_orders)
    if n_pads == 0:
        raise SystemExit("no unit boundaries found")

    # distribute need across pads, clamp
    raw = need / n_pads if need > 0 else args.min_pad
    pad_sec = max(args.min_pad, min(args.max_pad, raw if need > 0 else args.min_pad))
    # if still short after clamp, bump to max
    if need > 0 and pad_sec * n_pads < need * 0.95:
        pad_sec = min(args.max_pad, need / n_pads)

    pad_dir = job / "pads"
    pad_dir.mkdir(exist_ok=True)
    bg = job / "scene_1_flow.jpg"
    if not bg.exists():
        bgs = list((job / "media" / "backgrounds").glob("*.jpg"))
        bg = bgs[0] if bgs else None
    if bg is None or not bg.exists():
        raise SystemExit("no background for pad")

    pad_clip = pad_dir / f"unit_pad_{pad_sec:.1f}s.mp4"
    make_pad(job, pad_sec, bg, pad_clip, ff)

    # ensure synced scenes exist
    missing = [int(s["order"]) for s in scenes if not (job / f"scene_{int(s['order'])}_synced.mp4").exists()]
    if missing:
        raise SystemExit(f"missing synced scenes e.g. {missing[:5]}; run render_simple_longform first")

    boundary_set = set(boundary_after_orders)
    lst = job / "_concat_list_100m.txt"
    lines = []
    for sc in scenes:
        o = int(sc["order"])
        p = (job / f"scene_{o}_synced.mp4").resolve().as_posix()
        lines.append(f"file '{p}'")
        if o in boundary_set:
            lines.append(f"file '{pad_clip.resolve().as_posix()}'")
    lst.write_text("\n".join(lines), encoding="utf-8")

    out = job / args.final_name
    cmd = [
        ff,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(lst),
        "-c",
        "copy",
        str(out),
    ]
    try:
        run(cmd)
    except RuntimeError:
        cmd = [
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
            "-movflags",
            "+faststart",
            str(out),
        ]
        run(cmd)

    final_dur = probe_dur(out)
    report = {
        "ok": True,
        "speech_seconds": round(total, 1),
        "target_seconds": target,
        "pad_seconds_each": round(pad_sec, 2),
        "pad_count": n_pads,
        "pad_total_seconds": round(pad_sec * n_pads, 1),
        "final_seconds": round(final_dur, 1),
        "final_minutes": round(final_dur / 60, 1),
        "final": str(out),
        "bytes": out.stat().st_size,
    }
    (job / "reports" / "extend_duration_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
