# -*- coding: utf-8 -*-
"""Copy motif backgrounds to scene_N_flow.jpg WITHOUT burned text (Hermes image policy)."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BG_DIR = ROOT / "assets" / "backgrounds" / "ep01"


def prepare(job: Path) -> dict:
    scenes = json.loads((job / "scenes.json").read_text(encoding="utf-8"))
    bgs = sorted(BG_DIR.glob("*.jpg"))
    if not bgs:
        raise SystemExit(f"No backgrounds in {BG_DIR}; run make_background_bank.py")
    n = 0
    for sc in scenes:
        order = int(sc["order"])
        src = bgs[(order - 1) % len(bgs)]
        dst = job / f"scene_{order}_flow.jpg"
        shutil.copy2(src, dst)
        n += 1
    report = {
        "ok": True,
        "frames": n,
        "text_in_image": False,
        "note": "plain motif plates only; captions via ASS timeline",
    }
    (job / "reports").mkdir(exist_ok=True)
    (job / "reports" / "plain_bg_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    prepare(Path(args.job).resolve())


if __name__ == "__main__":
    main()
