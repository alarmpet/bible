# -*- coding: utf-8 -*-
"""Korean eojel-aware two-line caption layout.

Split priority (locked):
1. sentence end  . ? ! 。
2. clause end    , ，
3. eojel (space)
4. keep josa/eomi attached to the previous eojel
Never hard-slice a token with s[i:i+20]. Oversized single eojels go alone.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Particles that must stay on the preceding eojel (not a split point before them).
_JOSA = frozenset(
    {
        "은",
        "는",
        "이",
        "가",
        "을",
        "를",
        "에",
        "에서",
        "으로",
        "로",
        "와",
        "과",
        "도",
        "만",
        "부터",
        "까지",
        "께서",
        "이여",
        "여",
    }
)

_SENTENCE_END = re.compile(r'[.?!\u3002][”"\')\]]?$')
_CLAUSE_END = re.compile(r'[,，][”"\')\]]?$')
# Attributive/adnominal endings — avoid leaving these as line-final alone.
_MODIFIER_END = re.compile(r"(한|된|던|운|인)$")


@dataclass(frozen=True)
class CaptionBlock:
    """One on-screen caption: 1–2 lines, each at most hard_max chars."""

    lines: list[str]  # 1~2 items, each <= 20 chars (hard_max)
    text: str  # "줄1\\N줄2" or a single line


def _make_block(lines: list[str]) -> CaptionBlock:
    clean = [ln for ln in lines if ln]
    if not clean:
        raise ValueError("CaptionBlock requires at least one non-empty line")
    if len(clean) > 2:
        raise ValueError("CaptionBlock supports at most 2 lines")
    text = r"\N".join(clean) if len(clean) > 1 else clean[0]
    return CaptionBlock(lines=clean, text=text)


def _strip_trail_punct(token: str) -> str:
    return re.sub(r'[,，.?!\u3002”"\')\]]+$', "", token)


def _merge_standalone_josa(eojels: list[str]) -> list[str]:
    """Attach bare josa tokens to the previous eojel (no mid-josa break)."""
    out: list[str] = []
    for tok in eojels:
        bare = _strip_trail_punct(tok)
        if out and bare in _JOSA:
            # Keep trailing punct on the merged unit.
            out[-1] = out[-1] + tok
        else:
            out.append(tok)
    return out


def _is_sentence_end(token: str) -> bool:
    return bool(_SENTENCE_END.search(token))


def _is_clause_end(token: str) -> bool:
    return bool(_CLAUSE_END.search(token))


def _is_modifier(token: str) -> bool:
    bare = _strip_trail_punct(token)
    return bool(_MODIFIER_END.search(bare))


def _joined_len(parts: list[str]) -> int:
    if not parts:
        return 0
    return len(" ".join(parts))


def _split_into_phrases(
    text: str,
    target_min: int,
    target_max: int,
    hard_max: int,
) -> list[str]:
    """Break text into single-line phrases (each ideally target_min–target_max, ≤ hard_max)."""
    raw = [w for w in re.split(r"\s+", (text or "").strip()) if w]
    if not raw:
        return []
    eojels = _merge_standalone_josa(raw)
    phrases: list[str] = []
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        if current:
            phrases.append(" ".join(current))
            current = []

    for eojel in eojels:
        # Oversized single eojel: never s[i:i+20]; place alone as exception.
        if len(eojel) > hard_max:
            flush()
            phrases.append(eojel)
            continue

        trial = _joined_len(current + [eojel])
        if trial <= hard_max:
            current.append(eojel)
            clen = _joined_len(current)
            # Prefer sentence end once we have enough content.
            if _is_sentence_end(eojel) and clen >= min(target_min, hard_max):
                flush()
            # Prefer clause end in/near target band.
            elif _is_clause_end(eojel) and clen >= target_min:
                flush()
            # Prefer target band: flush at target_max unless last token is a modifier
            # (keep 환한+밤이 together rather than ending a line on 환한).
            elif clen >= target_max and not _is_modifier(eojel):
                flush()
            continue

        # Current + eojel exceeds hard_max → break at eojel boundary.
        if not current:
            phrases.append(eojel)
            continue

        # Don't leave a bare modifier (e.g. 환한) as phrase-final if we can
        # carry it with the next eojel under hard_max.
        if (
            len(current) > 1
            and _is_modifier(current[-1])
            and len(current[-1]) + 1 + len(eojel) <= hard_max
        ):
            mod = current.pop()
            flush()
            current = [mod, eojel]
        else:
            flush()
            current = [eojel]

        clen = _joined_len(current)
        if _is_sentence_end(eojel) and clen >= min(target_min, hard_max):
            flush()
        elif _is_clause_end(eojel) and clen >= target_min:
            flush()

    flush()

    # Second pass: if a phrase still exceeds hard_max only because of spaces
    # between eojels, re-pack by eojel (should already be ≤ hard_max except
    # oversized single tokens).
    final: list[str] = []
    for ph in phrases:
        if len(ph) <= hard_max or " " not in ph:
            final.append(ph)
            continue
        parts = ph.split()
        buf: list[str] = []
        for p in parts:
            if not buf:
                buf = [p]
                continue
            if _joined_len(buf + [p]) <= hard_max:
                buf.append(p)
            else:
                final.append(" ".join(buf))
                buf = [p]
        if buf:
            final.append(" ".join(buf))
    return final


def pack_two_lines(phrases: list[str]) -> list[CaptionBlock]:
    """Pack single-line phrases into CaptionBlocks of 1–2 lines each."""
    blocks: list[CaptionBlock] = []
    i = 0
    n = len(phrases)
    while i < n:
        if i + 1 < n:
            blocks.append(_make_block([phrases[i], phrases[i + 1]]))
            i += 2
        else:
            blocks.append(_make_block([phrases[i]]))
            i += 1
    return blocks


def split_korean_caption(
    text: str,
    target_min: int = 14,
    target_max: int = 18,
    hard_max: int = 20,
    max_lines: int = 2,
) -> list[CaptionBlock]:
    """Layout Korean caption text into eojel-aware 1–2 line blocks.

    Parameters match media_rules_lock captions:
    target 14–18, hard max 20, max 2 lines. Does not call caption_split_hermes.
    """
    if max_lines < 1:
        max_lines = 1
    if max_lines > 2:
        max_lines = 2

    phrases = _split_into_phrases(text, target_min, target_max, hard_max)
    if not phrases:
        return []

    if max_lines == 1:
        return [_make_block([p]) for p in phrases]

    # One phrase that fits hard_max → single-line block (≤20 → 1 line).
    if len(phrases) == 1:
        return [_make_block([phrases[0]])]

    # Pair phrases into up to max_lines per on-screen block.
    if max_lines == 2:
        return pack_two_lines(phrases)

    blocks: list[CaptionBlock] = []
    i = 0
    while i < len(phrases):
        chunk = phrases[i : i + max_lines]
        blocks.append(_make_block(chunk))
        i += len(chunk)
    return blocks
