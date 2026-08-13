# -*- coding: utf-8 -*-
"""Build lock-typography two-line Korean ASS from a hermes job.

Importing this module does not read or write the production job.
Generation lives in build_full_audio_aligned_ass() and CLI main().
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from sanitize_script import sanitize_script
from subtitle_layout import CaptionBlock, split_korean_caption

_BH_ROOT = Path(__file__).resolve().parents[1]
_LOCK_PATH = _BH_ROOT / "config" / "media_rules_lock.json"

FORBIDDEN_CAPTION_RE = re.compile(r"다윗의 시|셀라|영장|\(")
DIALOGUE_PREFIX = "Dialogue:"


def load_caption_lock(lock_path: Path | None = None) -> dict:
    path = Path(lock_path) if lock_path else _LOCK_PATH
    lock = json.loads(path.read_text(encoding="utf-8"))
    return dict(lock.get("captions") or {})


def build_ass_header(captions: dict | None = None) -> str:
    cap = captions if captions is not None else load_caption_lock()
    font = cap.get("fontName") or "Malgun Gothic"
    size_n = int(cap.get("fontSizePx_narrator") or 96)
    size_s = int(cap.get("fontSizePx_scripture") or 100)
    outline = int(cap.get("outlinePx") or 6)
    shadow = int(cap.get("shadowPx") or 3)
    margin_v = int(cap.get("marginV_px") or 90)
    margin_l = int(cap.get("marginL_px") or 100)
    margin_r = int(cap.get("marginR_px") or 100)
    primary = "&H00FFFFFF"
    scripture_primary = "&H00F5F5FF"
    outline_c = "&H00000000"
    back = "&H80000000"
    return (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1920\n"
        "PlayResY: 1080\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Narrator,{font},{size_n},{primary},&H000000FF,{outline_c},"
        f"{back},-1,0,0,0,100,100,0,0,1,{outline},{shadow},2,"
        f"{margin_l},{margin_r},{margin_v},1\n"
        f"Style: Scripture,{font},{size_s},{scripture_primary},&H000000FF,{outline_c},"
        f"{back},-1,0,0,0,100,100,0,0,1,{outline},{shadow},2,"
        f"{margin_l},{margin_r},{margin_v},1\n"
        f"Style: Chapter,{font},36,&H00E8E0D0,&H00E8E0D0,{outline_c},"
        f"&H90000000,0,0,0,0,100,100,0,0,1,2,1,9,120,120,90,1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )


def seconds_to_ass(value: float) -> str:
    if value < 0:
        value = 0.0
    cs = int(round(float(value) * 100.0))
    hours = cs // 360000
    cs %= 360000
    minutes = cs // 6000
    cs %= 6000
    seconds = cs // 100
    cs %= 100
    return f"{hours}:{minutes:02d}:{seconds:02d}.{cs:02d}"


def ass_to_seconds(stamp: str) -> float:
    hours, minutes, rest = stamp.strip().split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(rest)


def block_visible_len(block: CaptionBlock) -> int:
    return max(1, len("".join(block.lines)))


def allocate_block_times(
    blocks: list[CaptionBlock],
    start: float,
    end: float,
) -> list[tuple[float, float, CaptionBlock]]:
    """Spread blocks across [start, end] by visible text length."""
    if not blocks:
        return []
    duration = float(end) - float(start)
    if duration <= 0:
        return []
    weights = [block_visible_len(block) for block in blocks]
    total = sum(weights) or 1
    out: list[tuple[float, float, CaptionBlock]] = []
    cursor = float(start)
    acc = 0
    for index, (block, weight) in enumerate(zip(blocks, weights)):
        acc += weight
        if index == len(blocks) - 1:
            close = float(end)
        else:
            close = float(start) + duration * acc / total
        out.append((cursor, close, block))
        cursor = close
    return out


def parse_ass_events(ass_text: str) -> list[dict]:
    events: list[dict] = []
    for raw in ass_text.splitlines():
        line = raw.strip()
        if not line.startswith(DIALOGUE_PREFIX):
            continue
        payload = line.split(":", 1)[1].strip()
        parts = payload.split(",", 9)
        if len(parts) < 10:
            continue
        start = ass_to_seconds(parts[1])
        end = ass_to_seconds(parts[2])
        events.append(
            {
                "start": start,
                "end": end,
                "style": parts[3],
                "text": parts[9],
                "start_raw": parts[1],
                "end_raw": parts[2],
            }
        )
    return events


def qa_ass(source: str | Path) -> dict:
    """Fail on liturgical leftovers, bangs, >2 lines, >20 chars, reversed times."""
    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8-sig")
    else:
        text = source
    events = parse_ass_events(text)
    errors: list[str] = []
    for index, event in enumerate(events):
        body = event["text"]
        match = FORBIDDEN_CAPTION_RE.search(body)
        if match:
            errors.append(
                f"forbidden caption token {match.group()!r} in event {index}: {body}"
            )
        if "!" in body:
            errors.append(f"! in event {index}: {body}")
        n_breaks = body.count(r"\N")
        if n_breaks > 1:
            errors.append(
                f"more than 2 lines (\\N={n_breaks}) in event {index}: {body}"
            )
        for line in body.split(r"\N"):
            if len(line) > 20:
                errors.append(
                    f"line exceeds 20 chars ({len(line)}) in event {index}: {line}"
                )
        if event["start"] >= event["end"]:
            errors.append(
                f"reversed times event {index}: {event['start_raw']} >= {event['end_raw']}"
            )
    last_end = events[-1]["end"] if events else 0.0
    return {
        "ok": not errors,
        "errors": errors,
        "event_count": len(events),
        "last_end_seconds": last_end,
        "events": events,
    }


def _load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_provenance_pieces(job: Path) -> list[dict]:
    path = Path(job) / "reports" / "tts_provenance.json"
    if not path.is_file():
        return []
    try:
        data = _load_json(path)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    return list(data.get("pieces") or [])


def _piece_duration(piece: dict) -> float | None:
    for key in ("duration", "duration_seconds", "durationSeconds"):
        raw = piece.get(key)
        if raw is None:
            continue
        try:
            duration = float(raw)
        except (TypeError, ValueError):
            continue
        if duration > 0:
            return duration
    start = piece.get("startSeconds", piece.get("start"))
    end = piece.get("endSeconds", piece.get("end"))
    if start is None or end is None:
        return None
    try:
        duration = float(end) - float(start)
    except (TypeError, ValueError):
        return None
    return duration if duration > 0 else None


def _pieces_for_order(pieces: list[dict], order: int) -> list[dict]:
    matched: list[dict] = []
    for piece in pieces:
        raw = piece.get("scene_order", piece.get("order"))
        if raw is None:
            continue
        try:
            if int(raw) == order:
                matched.append(piece)
        except (TypeError, ValueError):
            continue
    return matched


def _piece_window(piece: dict, cursor: float) -> tuple[float, float] | None:
    start = piece.get("startSeconds", piece.get("start"))
    end = piece.get("endSeconds", piece.get("end"))
    if start is not None and end is not None:
        try:
            start_f = float(start)
            end_f = float(end)
        except (TypeError, ValueError):
            return None
        if end_f > start_f:
            return start_f, end_f
    duration = _piece_duration(piece)
    if duration is None:
        return None
    return cursor, cursor + duration


def _scene_speaker(scene: dict, fallback: str = "narrator") -> str:
    meta = scene.get("meta") or {}
    if meta.get("speaker"):
        return str(meta["speaker"])
    segments = scene.get("segments") or []
    if segments and segments[0].get("speaker"):
        return str(segments[0]["speaker"])
    return fallback


def _scene_text(scene: dict, item: dict) -> str:
    return scene.get("narration") or item.get("text") or ""


def _escape_ass_text(text: str) -> str:
    return (text or "").replace("{", "(").replace("}", ")")


def _dialogue_line(start: float, end: float, speaker: str, text: str) -> str:
    style = "Scripture" if speaker == "scripture" else "Narrator"
    body = _escape_ass_text(text)
    return (
        f"Dialogue: 0,{seconds_to_ass(start)},{seconds_to_ass(end)},"
        f"{style},,0,0,0,,{body}"
    )


def events_for_window(text: str, start: float, end: float, speaker: str) -> list[str]:
    cleaned = sanitize_script(text).display
    if not cleaned:
        return []
    blocks = split_korean_caption(cleaned)
    lines: list[str] = []
    for open_at, close_at, block in allocate_block_times(blocks, start, end):
        lines.append(_dialogue_line(open_at, close_at, speaker, block.text))
    return lines


def _windows_from_pieces(
    pieces: list[dict],
    scene_start: float,
) -> list[dict] | None:
    if not pieces:
        return None
    if any(_piece_duration(piece) is None and _piece_window(piece, 0.0) is None for piece in pieces):
        return None
    cursor = float(scene_start)
    windows: list[dict] = []
    for piece in pieces:
        span = _piece_window(piece, cursor)
        if span is None:
            return None
        start, end = span
        windows.append(
            {
                "start": start,
                "end": end,
                "text": piece.get("text") or "",
                "speaker": piece.get("speaker") or "narrator",
            }
        )
        cursor = end
    return windows


def build_full_audio_aligned_ass(job: Path, output: Path | None = None) -> Path:
    job = Path(job)
    scenes_raw = _load_json(job / "scenes.json")
    scenes = {
        int(scene["order"]): scene
        for scene in scenes_raw
        if isinstance(scene, dict) and scene.get("order") is not None
    }
    manifest = _load_json(job / "scene_audio_manifest.json")
    items = list(manifest.get("scenes") or [])
    pieces = _load_provenance_pieces(job)
    header = build_ass_header()
    events: list[str] = []
    for item in sorted(items, key=lambda row: int(row["order"])):
        order = int(item["order"])
        scene = scenes.get(order) or {}
        start = float(item["startSeconds"])
        end = float(item["endSeconds"])
        speaker = _scene_speaker(scene)
        scene_pieces = _pieces_for_order(pieces, order)
        windows = _windows_from_pieces(scene_pieces, start)
        if windows:
            for window in windows:
                events.extend(
                    events_for_window(
                        window["text"],
                        window["start"],
                        window["end"],
                        window.get("speaker") or speaker,
                    )
                )
            continue
        events.extend(events_for_window(_scene_text(scene, item), start, end, speaker))

    out = Path(output) if output else job / "subtitles-full-audio-aligned.ass"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(header + "\n".join(events) + ("\n" if events else ""), encoding="utf-8-sig")
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Build lock-typography two-line Korean ASS from a job"
    )
    parser.add_argument("--job", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    out = build_full_audio_aligned_ass(Path(args.job).resolve(), output=args.output)
    report = qa_ass(out)
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "ass": str(out),
                "events": report["event_count"],
                "last_end": report["last_end_seconds"],
                "errors": report["errors"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
