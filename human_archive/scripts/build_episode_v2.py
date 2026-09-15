# -*- coding: utf-8 -*-
"""Full episode rebuild orchestrator enforcing end-to-end immutable hash chain gates."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from build_audio_master_v2 import build_audio_master
from build_contact_sheet import create_contact_sheet
from build_motion_clips_v2 import build_motion_clips
from build_subtitles_v2 import build_ass_subtitles
from generate_flow_assets_v2 import generate_assets
from postflight_release import verify_postflight
from render_episode_v2 import render_build
from verify_visual_assets import verify_visual_build
from audit_episode_quality import repetition_gate

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def orchestrate_episode_build(
    contract_path: Path,
    build_id: str,
    output_root: Path,
    mode: str = "fixture",
    stop_after: str | None = None,
) -> Path:
    contract_path = Path(contract_path).resolve()
    output_root = Path(output_root).resolve()
    build_dir = output_root / build_id
    build_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 65}")
    print(f"🎬 ORCHESTRATING FULL EPISODE REBUILD: {build_id}")
    print(f"{'=' * 65}\n")

    # Step 1: Assets Generation
    print("[1/6] Generating verified visual assets...")
    c_data = json.loads(contract_path.read_text(encoding="utf-8"))
    script_path = contract_path.parent / "script_seonbi_v2.json"
    if not script_path.exists():
        script_path = contract_path.parent / "script_seonbi_v3.json"
    if script_path.exists():
        script_data = json.loads(script_path.read_text(encoding="utf-8"))
        gate = repetition_gate(script_data.get("sentences", []), production=mode != "fixture")
        if gate["status"] != "PASS":
            raise SystemExit(f"Script repetition gate failed: {gate['errors']}")
    fixture_cards = {s["shot_id"]: {"card_id": f"CARD-FULL-{s['shot_id']}", "status": "COMPLETED"} for s in c_data.get("shots", [])}
    manifest = generate_assets(
        contract_path=contract_path,
        build_id=build_id,
        output_root=output_root,
        mode=mode,
        fixture_cards=fixture_cards,
    )
    create_contact_sheet(build_dir)

    if stop_after == "visual-contact-sheet":
        print(f"✋ Stopped after visual-contact-sheet as requested.")
        return build_dir

    # Step 2: Visual QA Gate
    print("\n[2/6] Running pixel QA and duplicate check...")
    ok, errors = verify_visual_build(manifest_path=build_dir / "asset_manifest.json")
    if not ok:
        raise SystemExit(f"Visual asset gate failed: {errors}")

    # Step 3: Audio Master and Subtitles Generation
    print("\n[3/6] Building normalized audio master and subtitles...")
    build_audio_master(build_dir)
    build_ass_subtitles(build_dir)

    # Step 4: Motion Clips Generation (Using measured audio durations)
    print("\n[4/6] Generating 25 CFR motion clips aligned to audio timeline...")
    build_motion_clips(build_dir)

    # Step 5: Render Episode
    print("\n[5/6] Rendering candidate video...")
    final_mp4 = render_build(build_dir)

    if stop_after == "candidate":
        print(f"✋ Stopped after candidate render as requested.")
        return final_mp4

    # Step 6: Postflight Release Gate
    print("\n[6/6] Executing machine postflight release gate...")
    post_ok, report = verify_postflight(
        final_mp4,
        contract_path=contract_path,
        report_output=build_dir / "release_report.json",
        duration_mode="pilot" if "pilot" in build_id else "full",
    )
    if not post_ok:
        raise SystemExit(f"Postflight gate failed: {report.get('errors')}")

    print(f"\n{'=' * 65}")
    print(f"🏆 SUCCESS: Full Episode Build '{build_id}' passed all gates!")
    print(f"   Output MP4: {final_mp4}")
    print(f"   Release Report: {build_dir / 'release_report.json'}")
    print(f"{'=' * 65}\n")

    return final_mp4


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--build-id", required=True, type=str)
    parser.add_argument("--output-root", default="human_archive/runs/ep01_pompeii_rebuild_v2", type=Path)
    parser.add_argument("--mode", default="fixture", choices=["fixture", "cdp"])
    parser.add_argument("--stop-after", choices=["visual-contact-sheet", "candidate"])
    args = parser.parse_args()

    orchestrate_episode_build(
        args.contract,
        args.build_id,
        args.output_root,
        mode=args.mode,
        stop_after=args.stop_after,
    )


if __name__ == "__main__":
    main()
