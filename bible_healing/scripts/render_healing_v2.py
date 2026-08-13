# -*- coding: utf-8 -*-
"""
Healing render v2:
  - uses composed scene_N_flow.jpg (text already on frame)
  - scene_N.wav
  - short crossfade optional
  - NO long silence pads
  - hardsub already baked into frames via compose_scene_frame
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        err = (r.stderr or b"").decode("utf-8", errors="replace")[-2000:]
        raise RuntimeError(err)


def probe(path: Path) -> float:
    out = subprocess.check_output(
        [
            str(FFPROBE),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def render_one(job: Path, order: int, ff: str) -> Path:
    img = job / f"scene_{order}_flow.jpg"
    wav = job / f"scene_{order}.wav"
    out = job / f"scene_{order}_synced.mp4"
    if not img.exists():
        raise FileNotFoundError(img)
    if not wav.exists():
        raise FileNotFoundError(wav)
    # mild zoompan for  life (slow); if too slow fallback still
    # stillimage encode is reliable/fast
    cmd = [
        ff,
        "-y",
        "-loop",
        "1",
        "-i",
        str(img),
        "-i",
        str(wav),
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(out),
    ]
    run(cmd)
    return out


def concat(job: Path, orders: list[int], ff: str, final_name: str) -> Path:
    lst = job / "_concat_v2.txt"
    lines = [f"file '{(job / f'scene_{o}_synced.mp4').resolve().as_posix()}'" for o in orders]
    lst.write_text("\n".join(lines), encoding="utf-8")
    out = job / final_name
    cmd = [ff, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)]
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
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--final-name", default="final-healing-v2.mp4")
    args = ap.parse_args()
    job = Path(args.job).resolve()
    ff = str(FFMPEG if FFMPEG.exists() else "ffmpeg")
    scenes = json.loads((job / "scenes.json").read_text(encoding="utf-8"))
    orders = sorted(int(s["order"]) for s in scenes)

    # prefer locked manifest order if present
    man = job / "scene_audio_manifest.json"
    if man.exists():
        m = json.loads(man.read_text(encoding="utf-8"))
        if m.get("scenes"):
            orders = sorted(int(s["order"]) for s in m["scenes"])

    print(f"render v2 scenes={len(orders)} workers={args.workers}")
    ok = 0
    fails = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(render_one, job, o, ff): o for o in orders}
        for fut in as_completed(futs):
            o = futs[fut]
            try:
                fut.result()
                ok += 1
                if ok % 5 == 0 or ok == len(orders):
                    print(f"  {ok}/{len(orders)}")
            except Exception as e:
                fails.append((o, str(e)[:200]))
                print("FAIL", o, e)
    if fails:
        raise SystemExit(f"failed {len(fails)}: {fails[:3]}")

    final = concat(job, orders, ff, args.final_name)
    dur = probe(final)
    report = {
        "ok": True,
        "final": str(final),
        "duration_sec": round(dur, 1),
        "duration_min": round(dur / 60, 2),
        "scenes": len(orders),
        "bytes": final.stat().st_size,
        "hardsub": "baked_into_frames",
        "long_silence_pads": False,
    }
    (job / "reports").mkdir(exist_ok=True)
    (job / "reports" / "render_v2_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
