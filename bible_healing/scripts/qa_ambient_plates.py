# -*- coding: utf-8 -*-
"""QA V1–V5, V8 partial for plate_timeline + assignments."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    job = Path(args.job).resolve()

    blocks = []
    warns = []

    tl_path = job / "plate_timeline.json"
    man_path = job / "scene_audio_manifest.json"
    if not tl_path.exists():
        raise SystemExit("missing plate_timeline.json")
    if not man_path.exists():
        raise SystemExit("missing scene_audio_manifest.json")

    tl = json.loads(tl_path.read_text(encoding="utf-8"))
    man = json.loads(man_path.read_text(encoding="utf-8"))
    man_orders = sorted(int(s["order"]) for s in man["scenes"])
    assign = {int(a["order"]): a for a in tl["scene_assignments"]}
    plates = {p["id"]: p for p in tl["plates"]}

    # V2: every scene exactly one plate
    for o in man_orders:
        if o not in assign:
            blocks.append(f"V2 missing assignment order={o}")
    extra = set(assign) - set(man_orders)
    if extra:
        blocks.append(f"V2 extra assignments {sorted(extra)[:10]}")

    # V1: cover full audio without gap/overlap (plate ranges contiguous)
    ps = sorted(tl["plates"], key=lambda p: p["start_sec"])
    if ps:
        if abs(ps[0]["start_sec"] - 0.0) > 0.05:
            warns.append(f"V1 first plate starts at {ps[0]['start_sec']}")
        for i in range(1, len(ps)):
            if abs(ps[i]["start_sec"] - ps[i - 1]["end_sec"]) > 0.05:
                blocks.append(
                    f"V1 gap/overlap between {ps[i-1]['id']} and {ps[i]['id']}"
                )
        total = float(tl.get("locked_duration_sec") or man.get("durationSeconds") or 0)
        if total and abs(ps[-1]["end_sec"] - total) > 0.15:
            warns.append(f"V1 last end {ps[-1]['end_sec']} vs total {total}")

    # V3: scripture not split across plates within unit
    if tl.get("errors"):
        blocks.append(f"V3 timeline errors: {tl['errors']}")
    prev = None
    for o in man_orders:
        a = assign.get(o)
        if not a:
            continue
        if (
            prev
            and prev["speaker"] == "scripture"
            and a["speaker"] == "scripture"
            and prev["unit"] == a["unit"]
            and prev["plate_id"] != a["plate_id"]
        ):
            blocks.append(f"V3 scripture split unit={a['unit']} orders={prev['order']},{o}")
        prev = a

    # V4 dwell warnings already in timeline
    for w in tl.get("warnings") or []:
        warns.append(f"V4 {w}")

    # V5 images exist for assigned plates + flow files
    for a in tl["scene_assignments"]:
        flow = job / f"scene_{int(a['order'])}_flow.jpg"
        if not flow.exists() or flow.stat().st_size < 1000:
            blocks.append(f"V5 missing flow order={a['order']}")
            continue
        try:
            im = Image.open(flow)
            w, h = im.size
            if abs(w / h - 16 / 9) > 0.08:
                warns.append(f"V5 aspect order={a['order']} {w}x{h}")
            if w < 1280:
                warns.append(f"V5 low res order={a['order']} {w}x{h}")
        except Exception as e:
            blocks.append(f"V5 unreadable order={a['order']}: {e}")

    report = {
        "ok": len(blocks) == 0,
        "blocks": blocks,
        "warns": warns,
        "plates": len(tl["plates"]),
        "scenes": len(assign),
    }
    (job / "reports").mkdir(exist_ok=True)
    (job / "reports" / "qa_ambient_plates.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if blocks:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
