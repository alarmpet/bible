# -*- coding: utf-8 -*-
"""Render motion clips for a build using motion_engine_v3 (content-aware trajectory,
lossless FFV1/MKV intermediate). Drop-in replacement for build_motion_clips_v2.py with
the same --build/--limit CLI.

Motion selection: uses `item["motion_intent"]` when present (the field
docs/superpowers/plans/2026-08-26-human-archive-script-image-motion-upgrade.md's
`episode_visual_contract.scenes[]` design calls for). That contract is not yet produced
by the current pipeline (Task 1/7/8 of the 2026-09-15 overhaul plan), so this script
also accepts `item["display_text"]`/`item["narration"]` and falls back to a small
keyword classifier -- and, when nothing matches, to `static` rather than a round-robin
preset. `static` is a normal, intended profile (Aug26 principle), not a failure mode, so
this fallback cannot reproduce the "100% of shots hit an arbitrary preset" defect the
legacy `SHOT_MOTION_MAP` id-mismatch bug caused.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
_LIB_DIR = _SCRIPTS_DIR / "lib"
for p in (_SCRIPTS_DIR, _LIB_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from motion_engine_v3 import render_motion_clip_v3, MOTION_INTENTS  # noqa: E402
from verify_visual_assets import verify_visual_build  # noqa: E402

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Interim content classifier -- only used when no explicit motion_intent is present.
# Deliberately small and conservative: an unmatched sentence gets "static", never a
# guess dressed up as a decision.
_KEYWORD_INTENTS: list[tuple[tuple[str, ...], str]] = [
    (("솟구", "화산", "분연", "치솟", "번개", "화쇄류", "충격파"), "tilt_up"),
    (("눈빛", "초상", "얼굴", "표정", "클로즈업", "마크로", "유물", "증거"), "detail_crop"),
    (("도시", "전경", "거리", "시장", "포럼", "항구", "해안", "성문", "군중"), "pan_right"),
    (("폐허", "매몰", "묻혀", "붕괴", "무너", "사라"), "pull_out"),
]


def classify_motion_intent(item: dict) -> str:
    explicit = item.get("motion_intent")
    if explicit in MOTION_INTENTS:
        return explicit
    text = (item.get("display_text") or item.get("narration") or item.get("tts_text") or "").lower()
    for keywords, intent in _KEYWORD_INTENTS:
        if any(k in text for k in keywords):
            return intent
    return "static"


def build_motion_clips_v3(build_dir: Path, limit: int | None = None,
                           lossless: bool = True) -> list[Path]:
    build_dir = Path(build_dir).resolve()
    visual_ok, visual_errors = verify_visual_build(build_dir=build_dir)
    if not visual_ok:
        detail = "; ".join(visual_errors[:5])
        raise SystemExit(f"Visual QA gate failed before motion rendering: {detail}")

    manifest_path = build_dir / "asset_manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = manifest_data.get("assets", [])

    audio_manifest_path = build_dir / "scene_audio_manifest.json"
    audio_durations: dict[str, float] = {}
    if audio_manifest_path.exists():
        audio_data = json.loads(audio_manifest_path.read_text(encoding="utf-8"))
        st_list = audio_data.get("shots", [])
        total_dur = audio_data.get("total_duration_sec", 0.0)
        for i, st in enumerate(st_list):
            if i + 1 < len(st_list):
                shot_dur = round(st_list[i + 1]["startSeconds"] - st["startSeconds"], 3)
            else:
                shot_dur = round(total_dur - st["startSeconds"], 3)
            audio_durations[st["shot_id"]] = max(0.5, shot_dur)

    images_dir = build_dir / "images"
    clips_dir = build_dir / "motion_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    rendered_clips = []
    fps = 25
    ext = ".mkv" if lossless else ".mp4"

    for idx, item in enumerate(assets):
        if limit and idx >= limit:
            break

        shot_id = item["shot_id"]
        img_path = images_dir / item["file_path"]
        out_clip = clips_dir / f"{shot_id}_motion{ext}"

        if not img_path.exists():
            print(f"[WARN] image missing for {shot_id}, skipping")
            continue

        motion_intent = classify_motion_intent(item)
        duration_sec = audio_durations.get(shot_id, 6.0)

        render_motion_clip_v3(
            image_path=img_path,
            output_path=out_clip,
            duration_sec=duration_sec,
            motion_intent=motion_intent,
            fps=fps,
            lossless=lossless,
        )
        rendered_clips.append(out_clip)
        print(f"[{idx + 1:03d}/{len(assets)}] rendered {out_clip.name} "
              f"({duration_sec:.2f}s, motion_intent={motion_intent})")

    print(f"\nRendered {len(rendered_clips)} v3 motion clips in {clips_dir}")
    return rendered_clips


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--no-lossless", action="store_true",
                         help="write H.264 CRF18 instead of FFV1/MKV -- previews only, "
                              "never for a build that will ship (reintroduces the extra "
                              "lossy encode this engine exists to remove)")
    args = parser.parse_args()
    build_motion_clips_v3(args.build, limit=args.limit, lossless=not args.no_lossless)


if __name__ == "__main__":
    main()
