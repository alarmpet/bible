# -*- coding: utf-8 -*-
"""
Fast longform renderer for bible_healing:
  still image (scene_N_flow.jpg) + scene_N.wav → scene_N_synced.mp4
  then concat → final mp4

Uses system/hermes ffmpeg. Much faster than Hermes motion pipeline for still healing content.
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

# Prefer hermes ffmpeg-static
FFMPEG = Path(
    os.environ.get("FFMPEG_BIN")
    or (MODULE_ROOT.parent / "hermes" / "node_modules" / "ffmpeg-static" / "ffmpeg.exe")
)
if not FFMPEG.exists():
    FFMPEG = Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")


def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        err = (r.stderr or b"").decode("utf-8", errors="replace")[-2000:]
        raise RuntimeError(f"cmd failed: {' '.join(cmd[:6])}...\n{err}")


def render_scene(job: Path, order: int, ff: str) -> Path:
    img = job / f"scene_{order}_flow.jpg"
    wav = job / f"scene_{order}.wav"
    out = job / f"scene_{order}_synced.mp4"
    if not img.exists():
        raise FileNotFoundError(img)
    if not wav.exists():
        raise FileNotFoundError(wav)
    if out.exists() and out.stat().st_size > 1000:
        # skip if already done and newer than sources
        if out.stat().st_mtime >= max(img.stat().st_mtime, wav.stat().st_mtime):
            return out
    # slow zoom via zoompan is expensive; use static still for speed + soft fade
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
    lst = job / "_concat_list.txt"
    lines = []
    for o in orders:
        p = (job / f"scene_{o}_synced.mp4").resolve().as_posix()
        lines.append(f"file '{p}'")
    lst.write_text("\n".join(lines), encoding="utf-8")
    out = job / final_name
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
        # re-encode fallback
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


def write_srt(job: Path, orders: list[int]) -> Path:
    """Simple full-scene captions from draft/scenes."""
    scenes = {int(s["order"]): s for s in json.loads((job / "scenes.json").read_text(encoding="utf-8"))}
    manifest = json.loads((job / "scene_audio_manifest.json").read_text(encoding="utf-8"))
    by_order = {int(s["order"]): s for s in manifest["scenes"]}

    def ts(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int(round((sec - int(sec)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    idx = 1
    for o in orders:
        m = by_order[o]
        text = (scenes.get(o) or {}).get("narration") or m.get("text") or ""
        text = " ".join(text.split())
        if len(text) > 80:
            # soft wrap every ~40 chars
            parts = []
            cur = ""
            for ch in text:
                cur += ch
                if len(cur) >= 40 and ch in " .，。、":
                    parts.append(cur.strip())
                    cur = ""
            if cur.strip():
                parts.append(cur.strip())
            text = "\n".join(parts[:6])
        start = float(m["startSeconds"])
        end = float(m["endSeconds"])
        lines.append(str(idx))
        lines.append(f"{ts(start)} --> {ts(end)}")
        lines.append(text)
        lines.append("")
        idx += 1
    srt = job / "subtitles-ko.srt"
    srt.write_text("\n".join(lines), encoding="utf-8")
    return srt


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--final-name", default="final-bible-healing-ep01.mp4")
    ap.add_argument("--skip-existing", action="store_true")
    args = ap.parse_args()
    job = Path(args.job).resolve()
    ff = str(FFMPEG if FFMPEG.exists() else "ffmpeg")
    print(f"ffmpeg={ff}")

    manifest = json.loads((job / "scene_audio_manifest.json").read_text(encoding="utf-8"))
    orders = sorted(int(s["order"]) for s in manifest["scenes"])
    print(f"scenes={len(orders)} workers={args.workers}")

    ok = 0
    fail = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(render_scene, job, o, ff): o for o in orders}
        for fut in as_completed(futs):
            o = futs[fut]
            try:
                p = fut.result()
                ok += 1
                if ok % 10 == 0 or ok == len(orders):
                    print(f"rendered {ok}/{len(orders)} last=scene_{o}")
            except Exception as e:
                fail.append((o, str(e)))
                print(f"FAIL scene_{o}: {e}")

    if fail:
        raise SystemExit(f"{len(fail)} scenes failed: {fail[:3]}")

    srt = write_srt(job, orders)
    final = concat(job, orders, ff, args.final_name)
    report = {
        "ok": True,
        "final": str(final),
        "bytes": final.stat().st_size,
        "scenes": len(orders),
        "srt": str(srt),
        "durationSeconds": manifest.get("durationSeconds"),
    }
    (job / "reports" / "simple_render_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
