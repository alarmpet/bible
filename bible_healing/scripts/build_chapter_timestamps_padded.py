# -*- coding: utf-8 -*-
"""Chapter timestamps including inter-unit silence pads (100m final)."""
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


def unit_of(sc: dict) -> str:
    return str((sc.get("meta") or {}).get("unit") or sc.get("scene_id") or "")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    job = Path(args.job).resolve()
    scenes = sorted(
        json.loads((job / "scenes.json").read_text(encoding="utf-8")),
        key=lambda s: int(s["order"]),
    )
    er = json.loads((job / "reports" / "extend_duration_report.json").read_text(encoding="utf-8"))
    pad = float(er["pad_seconds_each"])

    cursor = 0.0
    chapters = []
    prev_u = None
    for sc in scenes:
        o = int(sc["order"])
        u = unit_of(sc)
        title = sc.get("title") or u
        sid = sc.get("scene_id") or ""
        if u != prev_u:
            if sid.startswith("open_") or str(sid).endswith("_n0") or sid.startswith("close_"):
                chapters.append({"t": cursor, "time": fmt(cursor), "title": title, "order": o, "unit": u})
            prev_u = u
        cursor += wav_dur(job / f"scene_{o}.wav")
        # pad after unit ends (same logic as extend script)
    # recompute with pads properly
    cursor = 0.0
    chapters = []
    prev_u = None
    boundary_after = []
    for i, sc in enumerate(scenes):
        u = unit_of(sc)
        if prev_u is not None and u != prev_u:
            boundary_after.append(int(scenes[i - 1]["order"]))
        prev_u = u
    bset = set(boundary_after)

    prev_u = None
    for sc in scenes:
        o = int(sc["order"])
        u = unit_of(sc)
        title = sc.get("title") or u
        sid = sc.get("scene_id") or ""
        if u != prev_u:
            if sid.startswith("open_") or str(sid).endswith("_n0") or sid.startswith("close_"):
                chapters.append({"t": cursor, "time": fmt(cursor), "title": title, "order": o, "unit": u})
            prev_u = u
        cursor += wav_dur(job / f"scene_{o}.wav")
        if o in bset:
            cursor += pad

    out = {
        "total_seconds": round(cursor, 1),
        "total_time": fmt(cursor),
        "pad_seconds_each": pad,
        "chapters": chapters,
        "youtube_description_block": "\n".join(f"{c['time']} {c['title']}" for c in chapters),
    }
    (job / "reports" / "chapter_timestamps_100m.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # also overwrite main chapters used by upload package if we point to this
    (job / "reports" / "chapter_timestamps.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"ok": True, "total": out["total_time"], "chapters": len(chapters)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
