# -*- coding: utf-8 -*-
"""
Pack a modern run into a Hermes-compatible job directory.

Usage:
  python pack_hermes_job.py --run smoke_g1 --mode preview
  python pack_hermes_job.py --run smoke_g1 --mode full
  python pack_hermes_job.py --run smoke_g1 --mode preview --dry-run

Next agent: do not invent new media filenames; Hermes expects scene_{order}_flow.jpg
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from paths import MODERN_ROOT, as_dict, job_dir, run_dir


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_shot_plan(rd: Path, plan_path: str = "") -> dict:
    if plan_path:
        p = Path(plan_path)
        if not p.is_absolute():
            p = (rd / plan_path) if (rd / plan_path).exists() else Path(plan_path)
        if not p.exists():
            raise SystemExit(f"shot plan not found: {plan_path}")
        return json.loads(p.read_text(encoding="utf-8"))
    for candidate in (
        rd / "shot_plan_upload.json",
        rd / "shot_plan.json",
        rd / "hermes_bridge" / "shot_plan_upload.json",
        rd / "hermes_bridge" / "shot_plan.json",
    ):
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    raise SystemExit("shot_plan.json missing. Run: python scripts/build_shot_plan_json.py --run <id>")


def load_voice_map(rd: Path) -> dict:
    p = rd / "hermes_bridge" / "voice_map.json"
    if not p.exists():
        raise SystemExit(f"missing {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def check_voice_map(vm: dict) -> list[str]:
    errors = []
    speakers = vm.get("speakers") or {}
    if "narrator" not in speakers:
        errors.append("voice_map missing narrator")
    narr_v = (speakers.get("narrator") or {}).get("voice")
    used = set()
    for sid, conf in speakers.items():
        v = conf.get("voice")
        if not v:
            errors.append(f"{sid} missing voice")
            continue
        if sid != "narrator":
            used.add(v)
    if narr_v and narr_v in used:
        errors.append(f"BLOCK VOICE_MAP_DISTINCT: narrator voice {narr_v} shared with character")
    return errors


def pack(run_id: str, mode: str, dry_run: bool, plan_path: str = "") -> Path:
    rd = run_dir(run_id)
    # upload mode prefers fulltext plan
    if mode == "upload" and not plan_path:
        plan_path = str(rd / "shot_plan_upload.json")
    plan = load_shot_plan(rd, plan_path=plan_path)
    vm = load_voice_map(rd)
    v_err = check_voice_map(vm)
    if v_err:
        raise SystemExit("; ".join(v_err))

    shots = plan["shots"]
    if mode == "preview":
        shots = [s for s in shots if int(s["chapter"]) == 1]
    elif mode == "upload":
        # all shots from fulltext plan
        pass
    elif mode != "full":
        raise SystemExit("mode must be preview|full|upload")

    # folder name: upload uses hermes_jobs/upload
    jd = job_dir(run_id, mode if mode != "upload" else "upload")
    if not dry_run:
        if jd.exists():
            # never overwrite in place — stamp new folder
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            jd = jd.parent / f"{mode}_{stamp}"
        jd.mkdir(parents=True, exist_ok=False)
        (jd / "media").mkdir()
        (jd / "audio").mkdir()
        (jd / "captions").mkdir()
        (jd / "reports").mkdir()
        (jd / "segments").mkdir()

    media_manifest = []
    scenes = []
    draft_scenes = []
    missing = []

    for s in shots:
        order = int(s["order"])
        # renumber order 1..n for preview jobs so Hermes scene_1_flow matches
        # Keep original order in scene_id; use sequential pack_order for files
        pass

    # sequential orders for hermes file contract
    for i, s in enumerate(shots, start=1):
        src = rd / s["image"]
        dst_name = f"scene_{i}_flow.jpg"
        if not src.exists():
            missing.append(str(src))
            continue
        if not dry_run:
            dst = jd / dst_name
            # also put at job root for render-youtube-with-tts imageSceneSource
            shutil.copy2(src, dst)
            shutil.copy2(src, jd / dst_name)
            digest = sha256_file(dst)
            # probe size via optional pillow
            w = h = None
            try:
                from PIL import Image

                with Image.open(dst) as im:
                    w, h = im.size
            except Exception:
                pass
            media_manifest.append(
                {
                    "scene_id": s["scene_id"],
                    "order": i,
                    "source_order": s["order"],
                    "path": dst_name,
                    "source": s["image"],
                    "sha256": digest,
                    "width": w,
                    "height": h,
                }
            )
        segs = s.get("segments") or [{"speaker": "narrator", "text": s.get("narration") or s.get("title") or " "}]
        # ensure seg_ids
        for j, seg in enumerate(segs, 1):
            seg.setdefault("seg_id", f"{s['scene_id']}_{j:02d}")
            seg.setdefault("speaker", "narrator")
        narration = s.get("narration") or " ".join(x.get("text", "") for x in segs)
        scene_obj = {
            "scene_id": s["scene_id"],
            "order": i,
            "source_order": s["order"],
            "chapter": s["chapter"],
            "title": s.get("title"),
            "outputMode": "image",
            "narration": narration,
            "segments": segs,
            "image": dst_name,
        }
        scenes.append(scene_obj)
        draft_scenes.append(
            {
                "order": i,
                "narration": narration,
                "outputMode": "image",
                "flowOutputMode": "image",
                "section": f"ch{s['chapter']}",
                "chapter": s["chapter"],
                "scene_id": s["scene_id"],
            }
        )

    if missing:
        raise SystemExit(f"missing {len(missing)} images: {missing[:5]}")

    job_id = f"{run_id}_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    job = {
        "schema_version": "1.0",
        "job_id": job_id if not dry_run else f"{run_id}_{mode}_dry",
        "run_id": run_id,
        "mode": mode,
        "title": "smoke_g1 modern drama",
        "aspect": "16:9",
        "intro_mode": "PRE_ROLL_VIDEO",
        "intro_video_rel": "videos/intro.mp4",
        "caption_policy": "DETERMINISTIC_FROM_NARRATION",
        "scene_count": len(scenes),
        "multi_voice": True,
        "source_run_dir": str(rd),
    }
    render_options = {
        "aspectRatio": "16:9",
        "engineVoice": "M2",
        "voiceId": "M2",
        "speechSpeed": 1.05,
        "motionIntensity": "light",
        "transitionPreset": "scene-fade",
        "videoFormat": "longform",
        "stylePresetId": "explainer",
        "multiVoice": True,
        "jobId": job["job_id"],
    }
    draft = {"title": job["title"], "scenes": draft_scenes}
    provenance = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "paths": as_dict(),
        "source_run": str(rd),
        "shot_plan_total": plan.get("total_shots"),
        "packed_scenes": len(scenes),
    }

    report = {
        "status": "pass" if not missing else "fail",
        "mode": mode,
        "scene_count": len(scenes),
        "missing_images": missing,
        "dry_run": dry_run,
        "job_dir": str(jd),
    }

    if dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return jd

    # intro copy
    intro_src = rd / "videos" / "intro.mp4"
    if intro_src.exists():
        shutil.copy2(intro_src, jd / "intro.mp4")

    (jd / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    (jd / "shot_plan.json").write_text(json.dumps({"shots": shots_min(shots)}, ensure_ascii=False, indent=2), encoding="utf-8")
    (jd / "scenes.json").write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")
    (jd / "draft.json").write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    (jd / "render-options.json").write_text(json.dumps(render_options, ensure_ascii=False, indent=2), encoding="utf-8")
    (jd / "voice_map.json").write_text(json.dumps(vm, ensure_ascii=False, indent=2), encoding="utf-8")
    (jd / "scene-media-manifest.json").write_text(
        json.dumps({"ok": True, "items": media_manifest}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (jd / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    (jd / "reports" / "pack_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    # Hermes single-voice input helper (debug only)
    (jd / "tts-scenes-input.json").write_text(
        json.dumps([{"order": s["order"], "narration": s["narration"]} for s in draft_scenes], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"packed job -> {jd}")
    print(f"scenes={len(scenes)} mode={mode}")
    return jd


def shots_min(shots: list) -> list:
    return [
        {
            "scene_id": s["scene_id"],
            "order": s["order"],
            "chapter": s["chapter"],
            "image": s["image"],
            "title": s.get("title"),
        }
        for s in shots
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="smoke_g1")
    ap.add_argument("--mode", choices=["preview", "full", "upload"], default="preview")
    ap.add_argument("--plan", default="", help="optional shot_plan json path")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    pack(args.run, args.mode, args.dry_run, plan_path=args.plan)


if __name__ == "__main__":
    main()
