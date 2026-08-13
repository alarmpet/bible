# -*- coding: utf-8 -*-
"""Generic media-rules postflight for a finished MP4 + job ASS.

Usage:
  python media_rules_postflight.py <output.mp4> [--job <jobDir>] [--ass path] [--lock path]

Stream checks use ffprobe; if the MP4 exists but probe cannot be obtained,
postflight fails with ffprobe_unavailable (fail closed). Tests may inject probe=.
Does not require a real D: deploy MP4 for unit tests.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from build_full_audio_aligned_ass import ass_to_seconds, parse_ass_events, qa_ass
from sanitize_script import sanitize_script

_BH_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_LOCK = _BH_ROOT / "config" / "media_rules_lock.json"

_HERMES_FFPROBE = Path(
    r"C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe"
)


def load_lock(path: Path | None = None) -> dict:
    p = Path(path) if path else _DEFAULT_LOCK
    return json.loads(p.read_text(encoding="utf-8"))


def resolve_ffprobe() -> str | None:
    if _HERMES_FFPROBE.is_file():
        return str(_HERMES_FFPROBE)
    which = shutil.which("ffprobe")
    return which


def ffprobe_media(path: Path, ffprobe: str | None = None) -> dict | None:
    """Return ffprobe JSON or None if ffprobe is missing / fails."""
    fp = ffprobe if ffprobe is not None else resolve_ffprobe()
    if not fp:
        return None
    try:
        raw = subprocess.check_output(
            [
                fp,
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,codec_name",
                "-of",
                "json",
                str(path),
            ],
            text=True,
        )
        return json.loads(raw)
    except (subprocess.CalledProcessError, OSError, json.JSONDecodeError):
        return None


def check_streams(probe: dict) -> list[str]:
    """Require h264 video, aac audio, and a readable duration (moov present)."""
    errors: list[str] = []
    if not probe:
        return ["probe: empty"]
    fmt = probe.get("format") or {}
    duration_raw = fmt.get("duration")
    if duration_raw is None or duration_raw == "":
        errors.append("missing_duration_or_moov")
    streams = probe.get("streams") or []
    video_codecs = {
        (s.get("codec_name") or "").lower()
        for s in streams
        if s.get("codec_type") == "video"
    }
    audio_codecs = {
        (s.get("codec_name") or "").lower()
        for s in streams
        if s.get("codec_type") == "audio"
    }
    types = {s.get("codec_type") for s in streams}
    if "video" not in types:
        errors.append("missing_video_stream")
    if "audio" not in types:
        errors.append("missing_audio_stream")
    h264_ok = bool(video_codecs & {"h264", "avc1", "avc"})
    if video_codecs and not h264_ok:
        errors.append(f"missing_h264: video codecs={sorted(video_codecs)}")
    if not video_codecs and "video" in types:
        errors.append("missing_h264")
    aac_ok = bool(audio_codecs & {"aac"})
    if audio_codecs and not aac_ok:
        errors.append(f"missing_aac: audio codecs={sorted(audio_codecs)}")
    if not audio_codecs and "audio" in types:
        errors.append("missing_aac")
    if not video_codecs and "video" not in types:
        errors.append("missing_h264")
    if not audio_codecs and "audio" not in types:
        errors.append("missing_aac")
    return errors


def check_duration_delta(
    media_duration: float,
    last_ass_end: float,
    delta_limit: float,
) -> list[str]:
    errors: list[str] = []
    if abs(float(media_duration) - float(last_ass_end)) > float(delta_limit):
        errors.append(
            f"subtitle_duration_delta: ass_last={last_ass_end:.3f} "
            f"media={float(media_duration):.3f} limit={delta_limit}"
        )
    return errors


def _strip_ass_overrides(text: str) -> str:
    # Remove {\...} override tags
    t = re.sub(r"\{[^}]*\}", "", text or "")
    t = t.replace(r"\N", " ").replace(r"\n", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def check_first_caption(ass_text: str, first_script: str) -> list[str]:
    """First ASS dialogue must prefix-align with the sanitized first script.

    Accept only:
      - exact match
      - caption.startswith(head)  (caption starts with script head)
      - sanitized.startswith(caption)  (first-line split is a prefix of full script)
    Reject mid-string containment of head (e.g. filler + head + filler).
    """
    errors: list[str] = []
    events = parse_ass_events(ass_text)
    if not events:
        return ["first_caption: no ASS dialogue events"]
    caption = _strip_ass_overrides(events[0]["text"])
    sanitized = sanitize_script(first_script or "").display
    sanitized_norm = re.sub(r"\s+", " ", sanitized).strip()
    if not caption:
        return ["first_caption: empty first dialogue"]
    if not sanitized_norm:
        return ["first_caption: empty sanitized first script"]
    if caption == sanitized_norm:
        return errors
    head = sanitized_norm[: max(4, min(10, len(sanitized_norm)))]
    if caption.startswith(head) or sanitized_norm.startswith(caption):
        return errors
    errors.append(
        f"first_caption_mismatch: caption={caption!r} expected_start={head!r} "
        f"sanitized={sanitized_norm!r}"
    )
    return errors


def check_ass_qa(ass_text: str | Path) -> list[str]:
    """Reuse build_full_audio_aligned_ass.qa_ass (selah/!/20chars/>2 lines)."""
    result = qa_ass(ass_text)
    return list(result.get("errors") or [])


def _first_scene_text(job: Path) -> str | None:
    scenes_path = Path(job) / "scenes.json"
    if not scenes_path.is_file():
        return None
    scenes = json.loads(scenes_path.read_text(encoding="utf-8-sig"))
    if not isinstance(scenes, list) or not scenes:
        return None
    # Prefer lowest order
    def order_key(s: dict) -> int:
        try:
            return int(s.get("order") or 0)
        except (TypeError, ValueError):
            return 0

    scenes_sorted = sorted(scenes, key=order_key)
    first = scenes_sorted[0]
    if first.get("narration"):
        return str(first["narration"])
    segs = first.get("segments") or []
    if segs and segs[0].get("text"):
        return str(segs[0]["text"])
    return first.get("text")


def resolve_ass_path(job: Path | None, ass: Path | None, output: Path) -> Path | None:
    if ass is not None:
        return Path(ass)
    if job is not None:
        candidate = Path(job) / "subtitles-full-audio-aligned.ass"
        if candidate.is_file():
            return candidate
        # common alternate names
        for name in (
            "subtitles-timed-ko.ass",
            "deploy_ambient_chapters.ass",
        ):
            alt = Path(job) / name
            if alt.is_file():
                return alt
    sibling = output.with_suffix(".ass")
    if sibling.is_file():
        return sibling
    return None


def run_postflight(
    output: Path,
    job: Path | None = None,
    ass: Path | None = None,
    lock: dict | None = None,
    lock_path: Path | None = None,
    probe: dict | None = None,
) -> dict:
    """Validate finished MP4 against ASS/job. probe= skips ffprobe (for tests)."""
    output = Path(output)
    lock = lock if lock is not None else load_lock(lock_path)
    errors: list[str] = []
    notes: list[str] = []

    if not output.is_file():
        errors.append(f"missing_output: {output}")

    duration: float | None = None
    if probe is None and output.is_file():
        probe = ffprobe_media(output)

    if probe is None:
        # Fail closed when the MP4 exists but streams cannot be verified.
        if output.is_file():
            errors.append("ffprobe_unavailable")
        else:
            notes.append("ffprobe_skipped_missing_output")
    else:
        stream_errors = check_streams(probe)
        errors.extend(stream_errors)
        try:
            duration = float((probe.get("format") or {}).get("duration"))
        except (TypeError, ValueError):
            duration = None

    ass_path = resolve_ass_path(job, ass, output)
    ass_text = ""
    last_end = 0.0
    if ass_path is None or not Path(ass_path).is_file():
        errors.append("missing_ass")
    else:
        ass_text = Path(ass_path).read_text(encoding="utf-8-sig")
        qa_errors = check_ass_qa(ass_text)
        errors.extend(qa_errors)
        events = parse_ass_events(ass_text)
        if events:
            last_end = float(events[-1]["end"])
        if duration is not None:
            delta = float(
                (lock.get("release_gates") or {}).get("duration_delta_seconds") or 0.5
            )
            errors.extend(check_duration_delta(duration, last_end, delta))

        gates = lock.get("release_gates") or {}
        if gates.get("require_first_caption_matches_first_script", True):
            first_script = None
            if job is not None:
                first_script = _first_scene_text(Path(job))
            if first_script:
                errors.extend(check_first_caption(ass_text, first_script))
            else:
                notes.append("first_script_unavailable")

    return {
        "ok": not errors,
        "output": str(output),
        "job": str(job) if job else None,
        "ass": str(ass_path) if ass_path else None,
        "duration": duration,
        "subtitle_last_seconds": last_end,
        "errors": errors,
        "notes": notes,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Media rules postflight for output MP4")
    ap.add_argument("output", help="Finished MP4 path")
    ap.add_argument("--job", default=None, help="Job dir (for ASS + first scene text)")
    ap.add_argument("--ass", default=None, help="ASS path override")
    ap.add_argument("--lock", default=str(_DEFAULT_LOCK), help="media_rules_lock.json")
    args = ap.parse_args(argv)
    result = run_postflight(
        Path(args.output),
        job=Path(args.job) if args.job else None,
        ass=Path(args.ass) if args.ass else None,
        lock_path=Path(args.lock),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
