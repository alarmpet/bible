# -*- coding: utf-8 -*-
"""
Map plate assets onto scene_N_flow.jpg for render_healing_v3 compatibility.

Reads plate_timeline.json scene_assignments + plates[].asset/fallback.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from paths_bh import BH_ROOT


def resolve_asset(plate: dict, root: Path) -> Path:
    for key in ("asset", "fallback_asset"):
        rel = plate.get(key)
        if not rel:
            continue
        p = Path(rel)
        if not p.is_absolute():
            p = root / rel
        if p.exists():
            return p
    raise FileNotFoundError(f"no asset for plate {plate.get('id')}: {plate}")


def assign(job: Path) -> dict:
    tl_path = job / "plate_timeline.json"
    if not tl_path.exists():
        raise SystemExit("missing plate_timeline.json — run build_plate_timeline.py first")
    tl = json.loads(tl_path.read_text(encoding="utf-8"))
    plates = {p["id"]: p for p in tl["plates"]}
    root = BH_ROOT

    copied = []
    missing = []
    for a in tl["scene_assignments"]:
        order = int(a["order"])
        pid = a["plate_id"]
        plate = plates[pid]
        try:
            src = resolve_asset(plate, root)
        except FileNotFoundError as e:
            missing.append(str(e))
            continue
        dst = job / f"scene_{order}_flow.jpg"
        shutil.copy2(src, dst)
        copied.append({"order": order, "plate_id": pid, "src": str(src), "dst": str(dst.name)})

    report = {
        "ok": len(missing) == 0 and len(copied) == len(tl["scene_assignments"]),
        "copied": len(copied),
        "expected": len(tl["scene_assignments"]),
        "missing": missing,
        "items": copied,
    }
    (job / "reports").mkdir(exist_ok=True)
    (job / "reports" / "assign_plates_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: report[k] for k in ("ok", "copied", "expected", "missing")}, ensure_ascii=False, indent=2))
    if not report["ok"]:
        raise SystemExit(1)
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    assign(Path(args.job).resolve())


if __name__ == "__main__":
    main()
