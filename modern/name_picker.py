# name_picker.py — 현대 계층 작명 추출 (v12)
# 사용: python name_picker.py [계층] [남|여] --used 이름1 이름2 --n 6
# 계층: 취약 서민 중산 전문 권력 청년 노인

from __future__ import annotations

import argparse
import random
import re
import unicodedata
from pathlib import Path

NAME_BANK = Path(__file__).resolve().parent / "name_bank.md"

HARD_BANNED = {
    "연이", "도화", "분이", "무휼", "막동", "춘향", "향단", "길동",
    "철수", "영희", "영수", "민수", "지영", "곰배",
}

SECTION_MAP = {
    ("취약", "여"): ("## 1. 취약", "### 여성"),
    ("취약", "남"): ("## 1. 취약", "### 남성"),
    ("서민", "여"): ("## 2. 서민", "### 여성"),
    ("서민", "남"): ("## 2. 서민", "### 남성"),
    ("중산", "여"): ("## 3. 중산", "### 여성"),
    ("중산", "남"): ("## 3. 중산", "### 남성"),
    ("전문", "여"): ("## 4. 전문", "### 여성"),
    ("전문", "남"): ("## 4. 전문", "### 남성"),
    ("권력", "여"): ("## 5. 권력", "### 여성"),
    ("권력", "남"): ("## 5. 권력", "### 남성"),
    ("청년", "여"): ("## 6. 청년", "### 여성"),
    ("청년", "남"): ("## 6. 청년", "### 남성"),
    ("노인", "여"): ("## 7. 노인", "### 여성"),
    ("노인", "남"): ("## 7. 노인", "### 남성"),
}


def norm(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def load_section(text: str, h2: str, h3: str | None) -> list[str]:
    start = text.find(h2)
    if start < 0:
        return []
    nxt = re.search(r"\n## ", text[start + len(h2) :])
    block = text[start : start + len(h2) + nxt.start()] if nxt else text[start:]
    if h3:
        s2 = block.find(h3)
        if s2 < 0:
            return []
        nxt2 = re.search(r"\n### ", block[s2 + len(h3) :])
        block = block[s2 : s2 + len(h3) + nxt2.start()] if nxt2 else block[s2:]
    names: list[str] = []
    for line in block.split("\n"):
        line = line.strip()
        if not line or line[0] in "#>-" or line.startswith("**") or "작명" in line:
            continue
        if line.startswith(">"):
            continue
        if "," in line:
            for tok in line.split(","):
                tok = re.sub(r"\(.*?\)", "", norm(tok)).strip()
                # "철수(차단…" 등 제거
                tok = re.sub(r"[—\-].*$", "", tok).strip()
                if tok and re.fullmatch(r"[가-힣]{2,4}", tok):
                    names.append(tok)
    return names


def pick(
    tier: str,
    gender: str,
    used: list[str] | None = None,
    n: int = 6,
    extra_banned: list[str] | None = None,
    seed: int | None = None,
) -> list[str]:
    used_set = {norm(u) for u in (used or [])}
    used_initials = {u[0] for u in used_set if u}
    banned = set(HARD_BANNED) | {norm(x) for x in (extra_banned or [])}
    key = (tier, gender)
    if key not in SECTION_MAP:
        raise SystemExit(f"지원 계층/성별 아님: {tier} {gender}. {list(SECTION_MAP)}")
    h2, h3 = SECTION_MAP[key]
    text = NAME_BANK.read_text(encoding="utf-8")
    pool = load_section(text, h2, h3)
    cands = [
        nm
        for nm in dict.fromkeys(pool)
        if nm not in banned and nm not in used_set and nm[0] not in used_initials
    ]
    rng = random.Random(seed)
    rng.shuffle(cands)
    return cands[:n]


def main() -> None:
    ap = argparse.ArgumentParser(description="현대 name_bank 추출")
    ap.add_argument("tier", help="취약|서민|중산|전문|권력|청년|노인")
    ap.add_argument("gender", help="남|여")
    ap.add_argument("--used", nargs="*", default=[], help="이미 쓴 이름")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    print(pick(a.tier, a.gender, a.used, a.n, seed=a.seed))


if __name__ == "__main__":
    main()
