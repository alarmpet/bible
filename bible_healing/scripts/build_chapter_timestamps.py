# -*- coding: utf-8 -*-
"""Build YouTube chapter timestamps from locked/measured scene durations."""
from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path


def wav_dur(p: Path) -> float:
    with wave.open(str(p), "rb") as w:
        return w.getnframes() / float(w.getframerate() or 1)


def fmt(t: float) -> str:
    t = int(t)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    job = Path(args.job).resolve()
    scenes = json.loads((job / "scenes.json").read_text(encoding="utf-8"))

    cursor = 0.0
    chapters = []
    last_title = None
    for sc in sorted(scenes, key=lambda x: int(x["order"])):
        order = int(sc["order"])
        wav = job / f"scene_{order}.wav"
        if not wav.exists():
            raise SystemExit(f"missing {wav}")
        dur = wav_dur(wav)
        title = sc.get("title") or sc.get("scene_id") or f"scene {order}"
        # new chapter when unit title changes (ignore · 쉼 suffix for grouping? keep as is)
        unit = (sc.get("meta") or {}).get("unit") or ""
        key = unit or title
        if key != last_title and not str(sc.get("scene_id", "")).endswith("_rest"):
            # chapter at unit start (n0 / open / close)
            sid = sc.get("scene_id") or ""
            if sid.startswith("open_") or sid.endswith("_n0") or sid.startswith("close_"):
                chapters.append({"t": cursor, "time": fmt(cursor), "title": title, "order": order})
                last_title = key
        cursor += dur

    out = {
        "total_seconds": round(cursor, 1),
        "total_time": fmt(cursor),
        "chapters": chapters,
        "youtube_description_block": "\n".join(f"{c['time']} {c['title']}" for c in chapters),
    }
    reports = job / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "chapter_timestamps.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"ok": True, "total": out["total_time"], "chapters": len(chapters)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
