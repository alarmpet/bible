# -*- coding: utf-8 -*-
"""
Port of hermes/electron/services/capcut-single-line-caption.mjs
splitCaptionSrtForSingleLine — keep algorithm identical for contract parity.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


def parse_timestamp(value: str) -> int:
    m = re.match(r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})$", value)
    if not m:
        raise ValueError("CAPCUT_SINGLE_LINE_CAPTION_SRT_INVALID")
    h, mi, s, ms = map(int, m.groups())
    return ((h * 60 + mi) * 60 + s) * 1000 + ms


def format_timestamp(milliseconds: int) -> str:
    value = int(round(milliseconds))
    hours = value // 3_600_000
    minutes = (value % 3_600_000) // 60_000
    seconds = (value % 60_000) // 1000
    millis = value % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def parse_srt(srt_text: str) -> list[dict]:
    blocks = [b for b in re.split(r"\r?\n\s*\r?\n", (srt_text or "").strip()) if b.strip()]
    if not blocks:
        raise ValueError("CAPCUT_SINGLE_LINE_CAPTION_SRT_INVALID")
    out = []
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines()]
        timing_index = next((i for i, ln in enumerate(lines) if "-->" in ln), -1)
        if timing_index < 0:
            raise ValueError("CAPCUT_SINGLE_LINE_CAPTION_SRT_INVALID")
        timing = re.match(r"^(.+)\s+-->\s+(.+)$", lines[timing_index] or "")
        text = " ".join(ln for ln in lines[timing_index + 1 :] if ln).strip()
        text = re.sub(r"\s+", " ", text)
        if not timing or not text:
            raise ValueError("CAPCUT_SINGLE_LINE_CAPTION_SRT_INVALID")
        start_ms = parse_timestamp(timing.group(1).strip())
        end_ms = parse_timestamp(timing.group(2).strip())
        if end_ms <= start_ms:
            raise ValueError("CAPCUT_SINGLE_LINE_CAPTION_SRT_INVALID")
        out.append({"startMs": start_ms, "endMs": end_ms, "text": text})
    return out


def split_text(text: str, max_display_characters: int) -> list[str]:
    words = [w for w in re.split(r"\s+", text) if w]
    phrases: list[str] = []
    current = ""
    for word in words:
        nxt = f"{current} {word}" if current else word
        if len(nxt) <= max_display_characters:
            current = nxt
            if re.search(r'[.!?…][”"\')\]]?$', word):
                phrases.append(current)
                current = ""
            continue
        if current:
            phrases.append(current)
        if len(word) <= max_display_characters:
            current = word
            continue
        for offset in range(0, len(word), max_display_characters):
            phrases.append(word[offset : offset + max_display_characters])
        current = ""
    if current:
        phrases.append(current)
    return phrases


def allocate_timing(
    phrases: list[str], start_ms: int, end_ms: int, min_display_seconds: float
) -> list[dict]:
    total_ms = end_ms - start_ms
    min_ms = int(round(min_display_seconds * 1000))
    if len(phrases) * min_ms > total_ms:
        # soft fallback: shrink min so we never hard-fail on dense Korean
        min_ms = max(200, total_ms // max(len(phrases), 1))
    weights = [max(1, len(re.sub(r"\s+", "", p))) for p in phrases]
    total_weight = sum(weights)
    distributable_ms = total_ms - len(phrases) * min_ms
    cumulative_weight = 0
    cursor = start_ms
    cues = []
    for index, text in enumerate(phrases):
        cumulative_weight += weights[index]
        reserved_end = start_ms + (index + 1) * min_ms
        if index == len(phrases) - 1:
            end = end_ms
        else:
            end = reserved_end + int(round(distributable_ms * cumulative_weight / total_weight))
        cues.append({"text": text, "startMs": cursor, "endMs": end})
        cursor = end
    return cues


def split_caption_srt_for_single_line(
    srt_text: str, max_display_characters: int = 16, min_display_seconds: float = 0.65
) -> dict:
    if not isinstance(max_display_characters, int) or max_display_characters < 1:
        raise ValueError("CAPCUT_SINGLE_LINE_CAPTION_POLICY_INVALID")
    if not (min_display_seconds and min_display_seconds > 0):
        raise ValueError("CAPCUT_SINGLE_LINE_CAPTION_POLICY_INVALID")
    source_cues = parse_srt(srt_text)
    cues = []
    for cue in source_cues:
        phrases = split_text(cue["text"], max_display_characters)
        if not phrases:
            continue
        cues.extend(
            allocate_timing(phrases, cue["startMs"], cue["endMs"], min_display_seconds)
        )
    srt = (
        "\n\n".join(
            f"{i+1}\n{format_timestamp(c['startMs'])} --> {format_timestamp(c['endMs'])}\n{c['text']}"
            for i, c in enumerate(cues)
        )
        + "\n"
    )
    return {
        "srt": srt,
        "cueCount": len(cues),
        "sourceText": "".join(c["text"] for c in source_cues),
        "cues": cues,
    }


def split_plain_text_window(
    text: str,
    start_ms: int,
    end_ms: int,
    max_display_characters: int = 12,
    min_display_seconds: float = 0.65,
) -> list[dict]:
    """Convenience: one source window → timed phrases (absolute ms)."""
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text or end_ms <= start_ms:
        return []
    srt = f"1\n{format_timestamp(start_ms)} --> {format_timestamp(end_ms)}\n{text}\n"
    return split_caption_srt_for_single_line(
        srt, max_display_characters, min_display_seconds
    )["cues"]
