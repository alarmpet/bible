# -*- coding: utf-8 -*-
"""Convert Arabic digits in TTS text to Korean readings.

Display/caption text must keep digits. SuperTonic misreads 1814년 and 23편.
"""
from __future__ import annotations

import re

_SINO_DIGITS = ["영", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
_NATIVE_1_TO_99 = {
    1: "한",
    2: "두",
    3: "세",
    4: "네",
    5: "다섯",
    6: "여섯",
    7: "일곱",
    8: "여덟",
    9: "아홉",
    10: "열",
    20: "스물",
    30: "서른",
    40: "마흔",
    50: "쉰",
    60: "예순",
    70: "일흔",
    80: "여든",
    90: "아흔",
}
_NATIVE_COUNTERS = ("시간",)
_SINO_COUNTERS = ("년", "편", "장", "절", "호")
_NUM_RE = re.compile(r"(?<!\d)(\d{1,3}(?:,\d{3})+|\d+)(?!\d)")


def sino_int(n: int) -> str:
    """Read a non-negative integer in Sino-Korean (천팔백십사)."""
    if n < 0:
        return "마이너스 " + sino_int(-n)
    if n == 0:
        return "영"
    parts: list[str] = []
    units = [
        (100000000, "억"),
        (10000, "만"),
        (1000, "천"),
        (100, "백"),
        (10, "십"),
    ]
    rest = n
    for value, name in units:
        qty, rest = divmod(rest, value)
        if qty == 0:
            continue
        if qty == 1 and value >= 10:
            parts.append(name)
        else:
            parts.append(sino_int(qty) + name)
    if rest:
        parts.append(_SINO_DIGITS[rest])
    return "".join(parts)


def native_int(n: int) -> str:
    """Read 1..99 with native Korean counter forms (세, 스물네)."""
    if n <= 0 or n > 99:
        return sino_int(n)
    if n in _NATIVE_1_TO_99:
        return _NATIVE_1_TO_99[n]
    tens, ones = divmod(n, 10)
    head = _NATIVE_1_TO_99[tens * 10]
    if ones == 0:
        return head
    tail = _NATIVE_1_TO_99[ones]
    if ones == 4 and tens >= 2:
        tail = "네"
    return head + tail


def _parse_int(raw: str) -> int:
    return int(raw.replace(",", ""))


def numbers_to_korean_speech(text: str) -> str:
    """Replace digit runs with Korean readings. Leaves already-Hangul numbers."""
    if not text:
        return text

    def replace_counter(match: re.Match[str], reader) -> str:
        n = _parse_int(match.group(1))
        counter = match.group(2)
        space = " " if counter == "시간" else ""
        return f"{reader(n)}{space}{counter}"

    out = text
    for counter in _NATIVE_COUNTERS:
        out = re.sub(
            rf"(?<!\d)(\d{{1,3}}(?:,\d{{3}})+|\d+)\s*({re.escape(counter)})",
            lambda m: replace_counter(m, native_int),
            out,
        )
    for counter in _SINO_COUNTERS:
        out = re.sub(
            rf"(?<!\d)(\d{{1,3}}(?:,\d{{3}})+|\d+)\s*({re.escape(counter)})",
            lambda m: replace_counter(m, sino_int),
            out,
        )

    def _plain(match: re.Match[str]) -> str:
        return sino_int(_parse_int(match.group(1)))

    return _NUM_RE.sub(_plain, out)
