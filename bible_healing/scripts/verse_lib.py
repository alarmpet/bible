# -*- coding: utf-8 -*-
"""Verse lookup helpers: 'Ps.23.1-6' → joined text."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from paths_bh import VERSES

BOOK_ALIASES = {
    "Psalm": "Ps",
    "Psalms": "Ps",
    "Isaiah": "Isa",
    "Genesis": "Gen",
}


@lru_cache(maxsize=1)
def load_index() -> dict:
    path = VERSES / "krv_index.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run parse_osis_to_json.py")
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_book(book: str) -> str:
    return BOOK_ALIASES.get(book, book)


def parse_ref(ref: str) -> tuple[str, int, int, int]:
    """
    'Ps.23.1-6' → (Ps, 23, 1, 6)
    'Ps.4.8' → (Ps, 4, 8, 8)
    'Ps.91.1-8' → ...
    """
    ref = ref.strip()
    m = re.match(
        r"^([A-Za-z0-9]+)\.(\d+)\.(\d+)(?:-(\d+))?$",
        ref,
    )
    if not m:
        raise ValueError(f"Bad ref: {ref}")
    book = normalize_book(m.group(1))
    ch = int(m.group(2))
    v1 = int(m.group(3))
    v2 = int(m.group(4) or m.group(3))
    if v2 < v1:
        v1, v2 = v2, v1
    return book, ch, v1, v2


def get_verses(ref: str) -> list[dict]:
    idx = load_index()["by_id"]
    book, ch, v1, v2 = parse_ref(ref)
    out = []
    missing = []
    for v in range(v1, v2 + 1):
        oid = f"{book}.{ch}.{v}"
        row = idx.get(oid)
        if not row:
            missing.append(oid)
        else:
            out.append(row)
    if missing:
        raise KeyError(f"Missing verses for {ref}: {missing[:5]}{'...' if len(missing) > 5 else ''}")
    return out


def get_text(ref: str, join_with: str = " ") -> str:
    verses = get_verses(ref)
    return join_with.join(v["text"] for v in verses)


def get_label_ko(ref: str) -> str:
    verses = get_verses(ref)
    bko = verses[0]["book_ko"]
    book, ch, v1, v2 = parse_ref(ref)
    if v1 == v2:
        return f"{bko} {ch}:{v1}"
    return f"{bko} {ch}:{v1}-{v2}"
