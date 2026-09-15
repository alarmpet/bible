# -*- coding: utf-8 -*-
"""Korean caption parsing, semantic phrase splitting, and ASS formatting."""
from __future__ import annotations

import re
import unicodedata

ISOLATED_PARTICLES = {"은", "는", "이", "가", "을", "를", "의", "에", "로", "과", "와", "도", "만", "서"}
CONNECTING_ENDINGS = ["면서", "지만", "는데", "다면", "으로", "에서", "하고", "이며", "으며", "기에", "으니", "므로", "고", "며", "서", "도"]


def format_ass_timestamp(seconds: float) -> str:
    """Format seconds into ASS time format H:MM:SS.CC (centiseconds)."""
    cs_total = int(round(seconds * 100))
    hours = cs_total // (3600 * 100)
    rem = cs_total % (3600 * 100)
    minutes = rem // (60 * 100)
    rem = rem % (60 * 100)
    secs = rem // 100
    cs = rem % 100
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def split_korean_two_lines(text: str, max_chars: int = 25) -> list[str]:
    """Split Korean text into at most two balanced lines without breaking phrases."""
    text = unicodedata.normalize("NFC", text.strip())
    if not text:
        return []

    words = text.split()
    if len(text) <= max_chars or len(words) <= 1:
        return [text]

    best_split_idx = -1
    best_score = -9999

    for i in range(1, len(words)):
        l1 = " ".join(words[:i])
        l2 = " ".join(words[i:])
        len1 = len(l1)
        len2 = len(l2)

        if len1 > max_chars or len2 > max_chars:
            continue

        # Prevent isolated particles at the start of line 2
        first_w_l2 = words[i]
        if first_w_l2 in ISOLATED_PARTICLES:
            continue

        score = 0
        last_w_l1 = words[i - 1]

        # Punctuation bonus
        if any(last_w_l1.endswith(p) for p in [".", ",", "!", "?"]):
            score += 40

        # Ending bonus
        for ending in CONNECTING_ENDINGS:
            if last_w_l1.endswith(ending):
                score += 20
                break

        # Balance bonus
        score -= abs(len1 - len2) * 2

        if score > best_score:
            best_score = score
            best_split_idx = i

    if best_split_idx != -1:
        return [" ".join(words[:best_split_idx]), " ".join(words[best_split_idx:])]

    # Fallback to simple middle split
    mid = len(words) // 2
    return [" ".join(words[:mid]), " ".join(words[mid:])]


def generate_ass_header(font_size: int = 90) -> str:
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: DocuMain,Malgun Gothic,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,3,2,140,140,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
