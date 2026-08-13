# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    plates = ROOT / "assets" / "generated" / "ep01" / "plates"
    gen = ROOT / "assets" / "generated" / "ep01"
    print("=== plates/ ===")
    for p in sorted(plates.glob("P*.jpg")):
        im = Image.open(p)
        print(f"{p.name:10} {im.size[0]}x{im.size[1]}  {p.stat().st_size // 1024}KB")

    print("\n=== motif base ===")
    for p in sorted(gen.glob("motif*.jpg")):
        im = Image.open(p)
        print(f"{p.name:30} {im.size[0]}x{im.size[1]}  {p.stat().st_size // 1024}KB")

    job = ROOT / "runs" / "ep01_anxious_night" / "hermes_jobs" / "full"
    flows = list(job.glob("scene_*_flow.jpg"))
    print(f"\nscene_flow count {len(flows)}")
    hashes: dict[str, list[str]] = {}
    for p in flows:
        h = hashlib.md5(p.read_bytes()).hexdigest()[:12]
        hashes.setdefault(h, []).append(p.name)
    print(f"unique images among flow: {len(hashes)}")
    for h, names in sorted(hashes.items(), key=lambda x: -len(x[1])):
        print(f"  used {len(names):3}x  e.g. {names[0]}  hash={h}")

    tl = job / "plate_timeline.json"
    if tl.exists():
        t = json.loads(tl.read_text(encoding="utf-8"))
        print(f"\nplates in timeline: {len(t.get('plates') or [])}")
        for p in t.get("plates") or []:
            a_path = ROOT / p["asset"] if p.get("asset") else None
            f_path = ROOT / p["fallback_asset"] if p.get("fallback_asset") else None
            a_ok = a_path.exists() if a_path else False
            f_ok = f_path.exists() if f_path else False
            # which was actually used in assign: compare first scene hash of this plate
            print(
                f"  {p['id']} asset_ok={a_ok} fallback_ok={f_ok} "
                f"motif={p.get('motif')} duration={p.get('duration_sec')}s"
            )


if __name__ == "__main__":
    main()
