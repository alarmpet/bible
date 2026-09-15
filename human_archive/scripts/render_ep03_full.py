# -*- coding: utf-8 -*-
"""Update EP03 manifest, build motion clips and render candidate video."""
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.provenance import compute_file_sha256
from build_motion_clips_v2 import build_motion_clips
from render_episode_v2 import render_build
from postflight_release import verify_postflight

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    bdir = Path("human_archive/runs/ep03_maecheon/full-v3-001")
    im_dir = bdir / "images"
    contract = json.loads((bdir.parent / "source" / "shot_contract.json").read_text(encoding="utf-8"))
    shots = contract["shots"]

    assets = []
    for s in shots:
        sid = s["shot_id"]
        im_p = im_dir / f"{sid}.jpg"
        if im_p.exists():
            file_sha = compute_file_sha256(im_p)
            assets.append({
                "shot_id": sid,
                "order": s["order"],
                "card_id": f"FLOW-{sid}-{file_sha[:8]}",
                "file_path": im_p.name,
                "sha256": file_sha,
                "bytes": im_p.stat().st_size,
                "width": 1920,
                "height": 1080,
                "status": "COMPLETED"
            })

    manifest = {
        "schema_version": 2,
        "build_id": bdir.name,
        "provider": "google_flow_cdp",
        "assets": assets
    }
    (bdir / "asset_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Asset manifest updated with {len(assets)} assets!")

    # 1. Build motion clips
    print("\n--- 1. Rendering 45 Ken Burns Motion Clips ---")
    build_motion_clips(bdir)

    # 2. Render Candidate Video
    print("\n--- 2. Synthesizing Candidate Full Documentary Video ---")
    cand_path = render_build(bdir)
    print(f"✅ Candidate rendered: {cand_path}")

    # 3. Postflight QA
    print("\n--- 3. Running Postflight QA Verification ---")
    rep_path = bdir / "release_report.json"
    rep = verify_postflight(cand_path, rep_path, duration_mode="full")
    print(f"✅ Postflight status: {rep.get('overall_status')}")


if __name__ == "__main__":
    main()
