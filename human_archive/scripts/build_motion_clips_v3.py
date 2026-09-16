# -*- coding: utf-8 -*-
"""Render motion clips for a build using motion_engine_v3 (content-aware trajectory,
lossless FFV1/MKV intermediate). Drop-in replacement for build_motion_clips_v2.py with
the same --build/--limit CLI.

Motion selection priority (resolve_shot_motion): explicit `motion_intent` > the visual
brief's authored `camera` text > brief `motion_profile` family hint > narration keyword
classifier > `static`. Never a round-robin preset. Each shot also gets a Hard Gate 5
fixed-seconds ramp and a shot_scale-derived focal anchor.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
_LIB_DIR = _SCRIPTS_DIR / "lib"
for p in (_SCRIPTS_DIR, _LIB_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from motion_engine_v3 import render_motion_clip_v3, ramp_frac_for_duration, MOTION_INTENTS  # noqa: E402
from verify_visual_assets import verify_visual_build  # noqa: E402

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Interim content classifier -- only used when no explicit motion_intent is present.
# Deliberately small and conservative: an unmatched sentence gets "static", never a
# guess dressed up as a decision.
#
# 2026-09-16: the original 4 buckets were tuned for disaster/archaeology
# scripts (Pompeii, ice-age extinction) and left a real general-history
# episode (samurai/bushido) at 19/24 shots static -- not because static was
# the right call, but because none of its narration matched any bucket.
# Extended with buckets for conflict, discovery/reveal, artifacts/objects,
# and era/time-passage narration, which are common across historical
# documentary topics generally (not specific to any one episode's vocabulary).
_KEYWORD_INTENTS: list[tuple[tuple[str, ...], str]] = [
    (("솟구", "화산", "분연", "치솟", "번개", "화쇄류", "충격파"), "tilt_up"),
    (("눈빛", "초상", "얼굴", "표정", "클로즈업", "마크로", "유물", "증거",
      "예복", "갑옷", "무기", "장신구", "소장품"), "detail_crop"),
    (("도시", "전경", "거리", "시장", "포럼", "항구", "해안", "성문", "군중"), "pan_right"),
    (("폐허", "매몰", "묻혀", "붕괴", "무너", "사라"), "pull_out"),
    (("전투", "전쟁", "공격", "싸우", "돌격", "맞서", "저항", "침략"), "push_in"),
    (("발견", "밝혀졌", "드러났", "드러나", "공개", "비밀", "진실"), "push_in"),
    (("시대", "유신", "왕조", "제국", "세기", "전환기"), "pan_left"),
]


_TILT_UP_RE = re.compile(r"\b(upward tilt|tilts? up(ward)?|tilting up(ward)?)\b")
_TILT_DOWN_RE = re.compile(r"\b(downward tilt|tilts? down(ward)?|tilting down(ward)?)\b")
_PULL_OUT_RE = re.compile(r"\b(retreat\w*|pulls? (back|out)|pulling (back|out)|dolly out|recede\w*|withdraw\w*)\b")
_PUSH_RE = re.compile(r"\b(forward|push(es|ing)?|dolly in)\b")
_LATERAL_RE = re.compile(r"\b(pan(s|ning)?|lateral|track(s|ing)?|sweep(s|ing)?|orbit(s|ing)?|arc(s|ing)?)\b")
_LEFT_RE = re.compile(r"\bleft(ward)?\b")
_RIGHT_RE = re.compile(r"\bright(ward)?\b")
_FOLLOW_RE = re.compile(r"\bfollow(s|ing)?\b")
_REVEAL_RE = re.compile(r"\breveal(s|ing)?\b")
_CLOSE_SCALE_RE = re.compile(r"\b(close|macro|detail)\b")

# Only consulted when the brief's camera text names no parseable axis. motion_profile
# is almost a 1:1 alias of visual_mode, so it is a weak family hint, not camera design.
_MOTION_PROFILE_FALLBACK = {
    "reenactment_push": "push_in",
    "artifact_close_push": "detail_crop",
    "diagram_reveal": "pull_out",
    "character_follow": "push_in",
    "analogy_pan": "pan",
    "place_sweep": "pan",
    "route_pan": "pan",
}


def _alternating_pan(shot_order: int) -> str:
    # The camera text says "lateral"/"sweep" but never which way; alternating by shot
    # order keeps consecutive lateral shots from all drifting the same direction.
    return "pan_left" if shot_order % 2 == 0 else "pan_right"


def classify_camera_axis(camera_text: str, shot_scale: str = "", shot_order: int = 0) -> str | None:
    text = (camera_text or "").lower()
    if not text.strip():
        return None
    if _TILT_UP_RE.search(text):
        return "tilt_up"
    if _TILT_DOWN_RE.search(text):
        return "tilt_down"
    if _PULL_OUT_RE.search(text):
        return "pull_out"
    if _PUSH_RE.search(text):
        return "detail_crop" if _CLOSE_SCALE_RE.search((shot_scale or "").lower()) else "push_in"
    if _LATERAL_RE.search(text):
        if _LEFT_RE.search(text):
            return "pan_left"
        if _RIGHT_RE.search(text):
            return "pan_right"
        return _alternating_pan(shot_order)
    if _FOLLOW_RE.search(text):
        return "push_in"
    if _REVEAL_RE.search(text):
        return "pull_out"
    return None


def derive_focal_anchor(shot_scale: str) -> tuple[float, float] | None:
    # Briefs carry no subject coordinates. A full-body figure's head/torso sits above
    # frame center, so zooming on exact center lands on legs/ground; bias upward there.
    scale = (shot_scale or "").lower()
    if "full-body" in scale:
        return (0.5, 0.42)
    return None


def resolve_shot_motion(item: dict, brief: dict | None, shot_order: int) -> tuple[str, str]:
    """(motion_intent, source) with priority: explicit intent > brief camera text >
    brief motion_profile > narration keywords > static."""
    explicit = item.get("motion_intent")
    if explicit in MOTION_INTENTS:
        return explicit, "explicit"
    if brief:
        axis = classify_camera_axis(brief.get("camera", ""), brief.get("shot_scale", ""), shot_order)
        if axis:
            return axis, "camera"
        family = _MOTION_PROFILE_FALLBACK.get(brief.get("motion_profile", ""))
        if family:
            return (_alternating_pan(shot_order) if family == "pan" else family), "motion_profile"
    intent = classify_motion_intent(item)
    return intent, ("keyword" if intent != "static" else "default_static")


def classify_motion_intent(item: dict) -> str:
    explicit = item.get("motion_intent")
    if explicit in MOTION_INTENTS:
        return explicit
    text = (item.get("display_text") or item.get("narration") or item.get("tts_text") or "").lower()
    for keywords, intent in _KEYWORD_INTENTS:
        if any(k in text for k in keywords):
            return intent
    return "static"


def _load_shot_durations(build_dir: Path) -> dict[str, float]:
    """Real per-shot durations, keyed by shot_id. Prefers shot_timing_manifest.json
    (the current nollam_file_v1/doodle_seonbi_v1 pipeline's own output --
    plan_narration_shots.py already computes duration_sec per shot directly) and
    falls back to the older scene_audio_manifest.json shape (startSeconds deltas)
    for builds that only have that.

    2026-09-16 finding: this used to look ONLY for scene_audio_manifest.json. A
    real nollam_file_v1 build never writes that file (it writes
    shot_timing_manifest.json instead) -- the duration lookup silently stayed
    empty for the whole build, so every shot fell back to a hardcoded 6.0s
    default regardless of its real timed duration (some shots in this build
    needed 11+ seconds), which would have desynced the final render from the
    narration/subtitles with nothing flagging it."""
    timing_path = build_dir / "shot_timing_manifest.json"
    if timing_path.exists():
        timing_data = json.loads(timing_path.read_text(encoding="utf-8"))
        durations = {
            str(shot["shot_id"]): max(0.5, float(shot["duration_sec"]))
            for shot in timing_data.get("shots", [])
            if "duration_sec" in shot
        }
        if durations:
            return durations

    audio_manifest_path = build_dir / "scene_audio_manifest.json"
    durations = {}
    if audio_manifest_path.exists():
        audio_data = json.loads(audio_manifest_path.read_text(encoding="utf-8"))
        st_list = audio_data.get("shots", [])
        total_dur = audio_data.get("total_duration_sec", 0.0)
        for i, st in enumerate(st_list):
            if i + 1 < len(st_list):
                shot_dur = round(st_list[i + 1]["startSeconds"] - st["startSeconds"], 3)
            else:
                shot_dur = round(total_dur - st["startSeconds"], 3)
            durations[st["shot_id"]] = max(0.5, shot_dur)
    return durations


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

    audio_durations = _load_shot_durations(build_dir)

    # asset_manifest.json's rows never carried narration text (or any motion
    # hint) at all -- classify_motion_intent()'s keyword classifier had
    # nothing to match against, so every single shot fell through to
    # "static" regardless of its actual content (2026-09-16 finding: a real
    # 24-shot build rendered 100% static, visibly with zero camera movement
    # anywhere in the finished episode). The narration text does exist one
    # step upstream, on each shot's own visual brief.
    narration_by_shot_id: dict[str, str] = {}
    brief_by_shot_id: dict[str, dict] = {}
    brief_manifest_path = build_dir / "visual_brief_manifest.json"
    if brief_manifest_path.exists():
        brief_data = json.loads(brief_manifest_path.read_text(encoding="utf-8"))
        for brief in brief_data.get("briefs", []):
            brief_by_shot_id[str(brief["shot_id"])] = brief
            digest = brief.get("narration_digest")
            if digest:
                narration_by_shot_id[str(brief["shot_id"])] = digest

    order_by_shot_id: dict[str, int] = {}
    timing_path = build_dir / "shot_timing_manifest.json"
    if timing_path.exists():
        for shot in json.loads(timing_path.read_text(encoding="utf-8")).get("shots", []):
            if "order" in shot:
                order_by_shot_id[str(shot["shot_id"])] = int(shot["order"])

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
        if "display_text" not in item and "narration" not in item and "tts_text" not in item:
            item = {**item, "display_text": narration_by_shot_id.get(shot_id, "")}
        img_path = images_dir / item["file_path"]
        out_clip = clips_dir / f"{shot_id}_motion{ext}"

        if not img_path.exists():
            print(f"[WARN] image missing for {shot_id}, skipping")
            continue

        brief = brief_by_shot_id.get(shot_id)
        shot_order = order_by_shot_id.get(shot_id, idx + 1)
        motion_intent, source = resolve_shot_motion(item, brief, shot_order)
        focal_anchor = derive_focal_anchor((brief or {}).get("shot_scale", ""))
        duration_sec = audio_durations.get(shot_id, 6.0)
        ramp_frac = ramp_frac_for_duration(duration_sec)

        render_motion_clip_v3(
            image_path=img_path,
            output_path=out_clip,
            duration_sec=duration_sec,
            motion_intent=motion_intent,
            fps=fps,
            focal_anchor=focal_anchor,
            ramp_frac=ramp_frac,
            lossless=lossless,
        )
        rendered_clips.append(out_clip)
        print(f"[{idx + 1:03d}/{len(assets)}] rendered {out_clip.name} "
              f"({duration_sec:.2f}s, motion_intent={motion_intent} via {source}, "
              f"anchor={focal_anchor or 'center'}, ramp={ramp_frac * duration_sec:.2f}s)")

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
