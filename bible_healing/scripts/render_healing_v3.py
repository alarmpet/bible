# -*- coding: utf-8 -*-
"""
Healing render v3:
  - scene_N_flow.jpg = NO text (plain backgrounds)
  - scene_N.wav = multi-voice TTS
  - subtitles-timed-ko.ass = Hermes-policy timed captions burned in at concat or per-scene
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
        err = (r.stderr or b"").decode("utf-8", errors="replace")[-2500:]
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


def render_scene(job: Path, order: int, ff: str, start_s: float, end_s: float, ass: Path) -> Path:
    img = job / f"scene_{order}_flow.jpg"
    wav = job / f"scene_{order}.wav"
    out = job / f"scene_{order}_synced.mp4"
    if not img.exists() or not wav.exists():
        raise FileNotFoundError(f"missing media order={order}")

    # ASS uses absolute timeline; for per-scene burn we shift by -start
    # Use ass force_style + subtitles filter with original_size
    # Escape path for ffmpeg filter on Windows
    ass_esc = str(ass.resolve()).replace("\\", "/").replace(":", "\\:")
    # Only show dialogue in this window by shifting timestamps via setpts on audio video
    # Simpler approach: burn ASS on full timeline after concat — more accurate
    # Here we render video+audio WITHOUT subtitles first
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


def concat_and_burn(job: Path, orders: list[int], ff: str, ass: Path, final_name: str) -> Path:
    lst = job / "_concat_v3.txt"
    lines = [f"file '{(job / f'scene_{o}_synced.mp4').resolve().as_posix()}'" for o in orders]
    lst.write_text("\n".join(lines), encoding="utf-8")
    bare = job / "_body_nosub.mp4"
    cmd = [ff, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(bare)]
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
            str(bare),
        ]
        run(cmd)

    out = job / final_name
    ass_path = str(ass.resolve()).replace("\\", "/")
    # ffmpeg subtitles filter: Windows path escaping
    ass_filter = ass_path.replace(":", "\\:")
    cmd = [
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
    try:
        run(cmd)
    except RuntimeError:
        # fallback: subtitles= filter
        cmd = [
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
        run(cmd)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--final-name", default="final-healing-v3.mp4")
    args = ap.parse_args()
    job = Path(args.job).resolve()
    ff = str(FFMPEG if FFMPEG.exists() else "ffmpeg")

    man = json.loads((job / "scene_audio_manifest.json").read_text(encoding="utf-8"))
    orders = sorted(int(s["order"]) for s in man["scenes"])
    by = {int(s["order"]): s for s in man["scenes"]}
    ass = job / "subtitles-timed-ko.ass"
    if not ass.exists():
        raise SystemExit("missing subtitles-timed-ko.ass — run build_cues + build_ass first")

    print(f"v3 scenes={len(orders)}")
    ok = 0
    fails = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {}
        for o in orders:
            s = by[o]
            futs[
                ex.submit(
                    render_scene,
                    job,
                    o,
                    ff,
                    float(s["startSeconds"]),
                    float(s["endSeconds"]),
                    ass,
                )
            ] = o
        for fut in as_completed(futs):
            o = futs[fut]
            try:
                fut.result()
                ok += 1
                if ok % 5 == 0 or ok == len(orders):
                    print(f"  video {ok}/{len(orders)}")
            except Exception as e:
                fails.append((o, str(e)[:300]))
    if fails:
        raise SystemExit(f"scene fail {fails[:2]}")

    final = concat_and_burn(job, orders, ff, ass, args.final_name)
    dur = probe(final)
    report = {
        "ok": True,
        "final": str(final),
        "duration_sec": round(dur, 1),
        "duration_min": round(dur / 60, 2),
        "scenes": len(orders),
        "bytes": final.stat().st_size,
        "captions": "ass_timed_hermes_split",
        "text_in_image": False,
        "long_silence_pads": False,
    }
    (job / "reports" / "render_v3_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
