# -*- coding: utf-8 -*-
"""Validate a packed Hermes job. Exit 0=pass, 1=block, 2=warn-only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def check(job: Path) -> dict:
    checks = []

    def add(code, severity, status, details=None):
        checks.append({"code": code, "severity": severity, "status": status, "details": details or {}})

    def need(name: str) -> Path | None:
        p = job / name
        if not p.exists():
            add("MISSING_FILE", "block", "fail", {"file": name})
            return None
        add("FILE_EXISTS", "info", "pass", {"file": name})
        return p

    for fn in (
        "job.json",
        "scenes.json",
        "draft.json",
        "render-options.json",
        "voice_map.json",
        "scene-media-manifest.json",
        "provenance.json",
    ):
        need(fn)

    job_meta = {}
    scenes = []
    vm = {}
    media = {}
    if (job / "job.json").exists():
        job_meta = json.loads((job / "job.json").read_text(encoding="utf-8"))
    if (job / "scenes.json").exists():
        scenes = json.loads((job / "scenes.json").read_text(encoding="utf-8"))
    if (job / "voice_map.json").exists():
        vm = json.loads((job / "voice_map.json").read_text(encoding="utf-8"))
    if (job / "scene-media-manifest.json").exists():
        media = json.loads((job / "scene-media-manifest.json").read_text(encoding="utf-8"))

    # intro mode
    intro = job_meta.get("intro_mode")
    if intro != "PRE_ROLL_VIDEO":
        add("INTRO_MODE", "block", "fail", {"intro_mode": intro})
    else:
        add("INTRO_MODE", "block", "pass", {"intro_mode": intro})
    if intro == "PRE_ROLL_VIDEO" and not (job / "intro.mp4").exists():
        add("INTRO_FILE", "warn", "fail", {"expected": "intro.mp4"})
    else:
        add("INTRO_FILE", "warn", "pass")

    # scene count
    expected = int(job_meta.get("scene_count") or 0)
    if expected and expected != len(scenes):
        add("SCENE_COUNT_MATCH", "block", "fail", {"expected": expected, "actual": len(scenes)})
    else:
        add("SCENE_COUNT_MATCH", "block", "pass", {"count": len(scenes)})

    # media mapping
    items = media.get("items") or []
    by_order = {int(i["order"]): i for i in items}
    missing_media = []
    for sc in scenes:
        o = int(sc["order"])
        p = job / f"scene_{o}_flow.jpg"
        if not p.exists():
            missing_media.append(o)
        elif o not in by_order:
            add("MEDIA_MANIFEST_GAP", "warn", "fail", {"order": o})
    if missing_media:
        add("MEDIA_MAPPING", "block", "fail", {"missing_orders": missing_media[:20]})
    else:
        add("MEDIA_MAPPING", "block", "pass")

    # multi-voice segment length (BLOCK); full joined narration only WARN
    long_segs = []
    long_joined = []
    no_seg = []
    for sc in scenes:
        n = sc.get("narration") or ""
        if len(n) >= 111:
            long_joined.append({"order": sc["order"], "len": len(n)})
        segs = sc.get("segments") or []
        if not segs:
            no_seg.append(sc["order"])
        for seg in segs:
            t = seg.get("text") or ""
            if len(t) >= 111:
                long_segs.append({"order": sc["order"], "seg": seg.get("seg_id"), "len": len(t)})
    if long_segs:
        add("NARRATION_LENGTH", "block", "fail", {"long_segments": long_segs[:15]})
    else:
        add("NARRATION_LENGTH", "block", "pass")
    if long_joined:
        add("NARRATION_JOINED_LONG", "warn", "fail", {"items": long_joined[:10]})
    else:
        add("NARRATION_JOINED_LONG", "warn", "pass")
    if no_seg:
        add("SEGMENTS_PRESENT", "warn", "fail", {"orders": no_seg[:15]})
    else:
        add("SEGMENTS_PRESENT", "warn", "pass")

    # voice map distinct
    speakers = (vm.get("speakers") or {})
    narr_v = (speakers.get("narrator") or {}).get("voice")
    char_vs = {sid: c.get("voice") for sid, c in speakers.items() if sid != "narrator"}
    if narr_v and narr_v in char_vs.values():
        add("VOICE_MAP_DISTINCT", "block", "fail", {"narrator": narr_v, "characters": char_vs})
    else:
        add("VOICE_MAP_DISTINCT", "block", "pass", {"narrator": narr_v, "characters": char_vs})

    # multi voice required flag
    if job_meta.get("multi_voice") is not True:
        add("MULTI_VOICE_FLAG", "block", "fail", {"multi_voice": job_meta.get("multi_voice")})
    else:
        add("MULTI_VOICE_FLAG", "block", "pass")

    blocks = [c for c in checks if c["severity"] == "block" and c["status"] == "fail"]
    warns = [c for c in checks if c["severity"] == "warn" and c["status"] == "fail"]
    status = "fail" if blocks else ("warn" if warns else "pass")
    return {"status": status, "checks": checks, "block_count": len(blocks), "warn_count": len(warns)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True, help="path to packed job dir")
    args = ap.parse_args()
    job = Path(args.job)
    if not job.is_dir():
        raise SystemExit(f"not a directory: {job}")
    report = check(job)
    out = job / "validation-report.json"
    if job.exists():
        try:
            out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] == "fail":
        raise SystemExit(1)
    if report["status"] == "warn":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
