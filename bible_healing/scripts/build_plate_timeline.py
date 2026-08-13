# -*- coding: utf-8 -*-
"""
Build plate_timeline.json after audio lock.

Time authority: scene_audio_manifest.json only.
Metadata: scenes.json (unit, speaker).
Hard rule: never change plate inside consecutive scripture block.
Soft: ~10 min target / preferred_unit_ids from ambient_plates yaml.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths_bh import BH_ROOT, CONFIG  # noqa: E402

ROOT = BH_ROOT


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def target_plate_count(duration_sec: float, policy: dict) -> int:
    d_min = duration_sec / 60.0
    target_min = float(policy.get("minutes_per_plate_target") or 10)
    raw = max(1, math.ceil(d_min / target_min))
    if d_min < 60:
        return max(1, min(8, max(6, raw) if d_min >= 30 else raw))
    return max(8, min(12, raw))


def build(job: Path, plates_yaml: Path) -> dict:
    man_path = job / "scene_audio_manifest.json"
    scenes_path = job / "scenes.json"
    if not man_path.exists():
        raise SystemExit(f"missing locked manifest: {man_path}")
    if not scenes_path.exists():
        raise SystemExit(f"missing scenes: {scenes_path}")

    cfg = load_yaml(plates_yaml)
    policy = cfg.get("policy") or {}
    plate_defs = {p["id"]: p for p in cfg.get("plates") or []}
    plate_order = [p["id"] for p in cfg.get("plates") or []]

    man = json.loads(man_path.read_text(encoding="utf-8"))
    scenes = {int(s["order"]): s for s in json.loads(scenes_path.read_text(encoding="utf-8"))}
    items = sorted(man["scenes"], key=lambda x: int(x["order"]))

    # enrich rows
    rows = []
    for it in items:
        order = int(it["order"])
        sc = scenes.get(order) or {}
        meta = sc.get("meta") or {}
        segs = sc.get("segments") or []
        speaker = meta.get("speaker") or (segs[0].get("speaker") if segs else "narrator")
        # multi-seg scene: if any scripture, treat as scripture for hard rule
        if any((s.get("speaker") == "scripture") for s in segs):
            speaker = "scripture"
        unit = meta.get("unit") or "unknown"
        start = float(it["startSeconds"])
        end = float(it["endSeconds"])
        rows.append(
            {
                "order": order,
                "start_sec": start,
                "end_sec": end,
                "duration": end - start,
                "unit": unit,
                "speaker": speaker,
            }
        )

    if not rows:
        raise SystemExit("no scenes in manifest")

    total = rows[-1]["end_sec"]
    n_target = target_plate_count(total, policy)

    # Group into atomic blocks that cannot be split:
    # - consecutive same unit, OR
    # - consecutive scripture (even if unit same already)
    # Actually hard: scripture block = consecutive scripture rows as one atom
    # prefer unit integrity: group by unit runs
    atoms: list[dict] = []
    cur = None
    for r in rows:
        if cur is None:
            cur = {
                "unit": r["unit"],
                "speaker_set": {r["speaker"]},
                "has_scripture": r["speaker"] == "scripture",
                "start_sec": r["start_sec"],
                "end_sec": r["end_sec"],
                "orders": [r["order"]],
            }
            continue
        # merge if same unit (unit integrity)
        if r["unit"] == cur["unit"]:
            cur["end_sec"] = r["end_sec"]
            cur["orders"].append(r["order"])
            cur["speaker_set"].add(r["speaker"])
            if r["speaker"] == "scripture":
                cur["has_scripture"] = True
            continue
        # different unit: flush
        atoms.append(cur)
        cur = {
            "unit": r["unit"],
            "speaker_set": {r["speaker"]},
            "has_scripture": r["speaker"] == "scripture",
            "start_sec": r["start_sec"],
            "end_sec": r["end_sec"],
            "orders": [r["order"]],
        }
    if cur:
        atoms.append(cur)

    # Assign atoms to plates greedily toward ~target duration per plate
    target_each = total / n_target if n_target else total
    plates_out: list[dict] = []
    assignments: list[dict] = []
    plate_idx = 0
    atom_i = 0

    def pick_plate_id(units: list[str], idx: int) -> str:
        # preferred_unit_ids match
        for pid in plate_order:
            pref = plate_defs[pid].get("preferred_unit_ids") or []
            if any(u in pref for u in units):
                # avoid reusing same plate if already used unless only one left
                used = {p["id"] for p in plates_out}
                if pid not in used:
                    return pid
        # round-robin unused then any
        used = {p["id"] for p in plates_out}
        for pid in plate_order:
            if pid not in used:
                return pid
        return plate_order[idx % len(plate_order)]

    while atom_i < len(atoms):
        units: list[str] = []
        orders: list[int] = []
        start = atoms[atom_i]["start_sec"]
        end = atoms[atom_i]["end_sec"]
        units.append(atoms[atom_i]["unit"])
        orders.extend(atoms[atom_i]["orders"])
        atom_i += 1
        # pack more atoms until reach ~target_each (except last plate absorbs rest)
        remaining_atoms = len(atoms) - atom_i
        remaining_plates = n_target - len(plates_out)
        while atom_i < len(atoms) and remaining_plates > 1:
            # if adding would exceed 1.4 * target and we already have content, stop
            next_end = atoms[atom_i]["end_sec"]
            dur = next_end - start
            if dur >= target_each * 0.85 and (end - start) >= target_each * 0.55:
                break
            if dur > target_each * 1.45 and (end - start) > 60:
                break
            end = next_end
            units.append(atoms[atom_i]["unit"])
            orders.extend(atoms[atom_i]["orders"])
            atom_i += 1
            remaining_atoms = len(atoms) - atom_i
            # if few atoms left for remaining plates, break to leave some
            if remaining_plates > 1 and remaining_atoms < remaining_plates - 1:
                break

        # last plate: absorb all remaining
        if remaining_plates <= 1:
            while atom_i < len(atoms):
                end = atoms[atom_i]["end_sec"]
                units.append(atoms[atom_i]["unit"])
                orders.extend(atoms[atom_i]["orders"])
                atom_i += 1

        pid = pick_plate_id(units, plate_idx)
        pdef = plate_defs.get(pid) or {}
        asset = pdef.get("asset") or pdef.get("fallback_asset") or ""
        plates_out.append(
            {
                "id": pid,
                "start_sec": round(start, 3),
                "end_sec": round(end, 3),
                "duration_sec": round(end - start, 3),
                "unit_ids": list(dict.fromkeys(units)),
                "asset": asset,
                "fallback_asset": pdef.get("fallback_asset"),
                "motif": pdef.get("motif"),
                "motion": {"type": "still", "zoom_start": 1.0, "zoom_end": 1.0},
                "orders": orders,
            }
        )
        for o in orders:
            r = next(x for x in rows if x["order"] == o)
            assignments.append(
                {
                    "order": o,
                    "plate_id": pid,
                    "start_sec": round(r["start_sec"], 3),
                    "end_sec": round(r["end_sec"], 3),
                    "unit": r["unit"],
                    "speaker": r["speaker"],
                }
            )
        plate_idx += 1
        if plate_idx >= n_target and atom_i < len(atoms):
            # force remaining into last plate
            last = plates_out[-1]
            while atom_i < len(atoms):
                last["end_sec"] = round(atoms[atom_i]["end_sec"], 3)
                last["duration_sec"] = round(last["end_sec"] - last["start_sec"], 3)
                last["unit_ids"] = list(dict.fromkeys(last["unit_ids"] + [atoms[atom_i]["unit"]]))
                last["orders"].extend(atoms[atom_i]["orders"])
                for o in atoms[atom_i]["orders"]:
                    r = next(x for x in rows if x["order"] == o)
                    assignments.append(
                        {
                            "order": o,
                            "plate_id": last["id"],
                            "start_sec": round(r["start_sec"], 3),
                            "end_sec": round(r["end_sec"], 3),
                            "unit": r["unit"],
                            "speaker": r["speaker"],
                        }
                    )
                atom_i += 1

    # dwell warnings
    warn_min = float(policy.get("dwell_warn_min_sec") or 360)
    warn_max = float(policy.get("dwell_warn_max_sec") or 840)
    warnings = []
    for p in plates_out:
        d = p["duration_sec"]
        if d < warn_min:
            warnings.append({"plate_id": p["id"], "type": "dwell_short", "duration_sec": d})
        if d > warn_max:
            warnings.append({"plate_id": p["id"], "type": "dwell_long", "duration_sec": d})

    # verify scripture not split: if consecutive scripture orders have different plates -> error
    errors = []
    prev = None
    for a in sorted(assignments, key=lambda x: x["order"]):
        if a["speaker"] == "scripture" and prev and prev["speaker"] == "scripture":
            if a["plate_id"] != prev["plate_id"]:
                # only error if same unit (verse expand stays same unit)
                if a["unit"] == prev["unit"]:
                    errors.append(
                        {
                            "type": "scripture_split",
                            "orders": [prev["order"], a["order"]],
                            "plates": [prev["plate_id"], a["plate_id"]],
                        }
                    )
        prev = a

    timeline = {
        "schema_version": "1.0",
        "episode_id": cfg.get("episode_id") or "ep01_anxious_night",
        "audio_manifest_sha256": sha256_file(man_path),
        "locked_duration_sec": round(total, 3),
        "target_plate_count": n_target,
        "actual_plate_count": len(plates_out),
        "policy": {
            "minutes_per_plate_target": policy.get("minutes_per_plate_target"),
            "dwell_warn_min_sec": warn_min,
            "dwell_warn_max_sec": warn_max,
        },
        "plates": plates_out,
        "scene_assignments": sorted(assignments, key=lambda x: x["order"]),
        "warnings": warnings,
        "errors": errors,
    }

    out_path = job / "plate_timeline.json"
    out_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    (job / "reports").mkdir(exist_ok=True)
    (job / "reports" / "plate_timeline_report.json").write_text(
        json.dumps(
            {
                "ok": len(errors) == 0,
                "path": str(out_path),
                "plates": len(plates_out),
                "scenes": len(assignments),
                "duration_sec": total,
                "warnings": warnings,
                "errors": errors,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": len(errors) == 0,
                "plates": len(plates_out),
                "scenes": len(assignments),
                "duration_min": round(total / 60, 2),
                "warnings": len(warnings),
                "errors": errors,
                "out": str(out_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if errors:
        raise SystemExit(1)
    return timeline


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument(
        "--plates-yaml",
        default=str(ROOT / "config" / "ambient_plates_ep01.yaml"),
    )
    args = ap.parse_args()
    build(Path(args.job).resolve(), Path(args.plates_yaml).resolve())


if __name__ == "__main__":
    main()
