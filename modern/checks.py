# checks.py — v12 검증 실행 모듈 (scripts.md 구현)
from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modern.story_quality import (
    InsufficientStoryMaterial,
    check_filler_repetition,
    require_story_material,
)

FICTION_MARKERS = [
    "실제 인물·기관·사건과 무관한 창작물",
    "실제 인물·기관·사건과 무관",
    "허구 고지",
]

def _w(p: str) -> str:
    """한글 단어 경계 — 부분 문자열 오탐 방지 (예: 완전하진⊃전하)."""
    return rf"(?<![가-힣]){p}(?![가-힣])"


ERA_BANNED = [
    _w(r"대감"),
    _w(r"마님"),
    _w(r"아씨"),
    _w(r"소저"),
    _w(r"원님"),
    _w(r"사또"),
    _w(r"나으리"),
    _w(r"전하"),
    _w(r"상감"),
    _w(r"중전"),
    _w(r"한양"),
    _w(r"관아"),
    _w(r"포도청"),
    _w(r"사약"),
    _w(r"유배"),
    r"과거\s*급제",
    _w(r"어사"),
    _w(r"노비"),
    _w(r"머슴"),
    _w(r"기생"),
    _w(r"상투"),
    _w(r"도포"),
    _w(r"저고리"),
    _w(r"치맛자락"),
    _w(r"가마"),
    r"옛날\s*옛적",
    r"하옵",
    r"이옵",
    r"사옵",
    r"느니라",
    _w(r"옥패"),
    _w(r"어명"),
    _w(r"주상"),
]

ALLOW_BLOCK = re.compile(
    r"<!--\s*era_allow\s*-->.*?<!--\s*/era_allow\s*-->|\[era_allow\].*?\[/era_allow\]",
    re.S | re.I,
)


def check_fiction_disclaimer(*docs: str) -> tuple[bool, list[str]]:
    blob = "\n".join(docs)
    ok = any(m in blob for m in FICTION_MARKERS)
    return (ok, [] if ok else ["BLOCK: 허구 고지 누락"])


def strip_era_allow(text: str) -> str:
    return ALLOW_BLOCK.sub(" ", text)


def check_era_leak(text: str) -> tuple[bool, list[str], str]:
    body = strip_era_allow(text)
    hits: list[str] = []
    for p in ERA_BANNED:
        for m in re.finditer(p, body):
            hits.append(m.group(0))
    if not hits:
        return (True, [], "OK")
    return (False, hits[:20], "WARN")


def check_modern_anchor(intro_and_ch1: str) -> tuple[bool, list[str]]:
    year = bool(re.search(r"20\d{2}년|\d{2}년\s*(겨울|봄|여름|가을)", intro_and_ch1))
    place = bool(
        re.search(
            r"(서울|부산|인천|대구|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주|"
            r"아파트|병원|회사|편의점|고시원|공장|학교|구청|경찰서|요양)",
            intro_and_ch1,
        )
    )
    job = bool(
        re.search(
            r"(직원|간호사|기사|사장|과장|보호사|교사|형사|기자|알바|계약직|의사|변호사)",
            intro_and_ch1,
        )
    )
    warnings: list[str] = []
    if not (year or place):
        warnings.append("WARN: 첫 구간에 연도·장소 앵커 약함")
    if not job:
        warnings.append("WARN: 첫 구간에 직업·역할 신호 약함")
    # 몰아넣기: 연도+지명+직업에 *금액/정확한 시각 숫자*까지 한 짧은 문장에 겹칠 때만
    for s in re.split(r"(?<=[.!?])\s+|\n+", intro_and_ch1):
        s = s.strip()
        if not s or len(s) >= 100:
            continue
        has_year = bool(re.search(r"20\d{2}", s))
        has_place = bool(re.search(r"[가-힣]+(구|동|시|군)", s))
        has_job = bool(re.search(r"(직원|간호사|사장|기사|과장|보호사|교사|형사)", s))
        has_extra_num = bool(
            re.search(r"\d+\s*(억|만\s*원|원|층|호|시\s*\d|:\d{2})", s)
        )
        if has_year and has_place and has_job and has_extra_num:
            warnings.append(f"WARN: 앵커 몰아넣기 의심: {s[:40]}...")
            break
    return (len(warnings) == 0, warnings)


def selftest() -> None:
    ok, iss = check_fiction_disclaimer("허구 고지: 실제 인물·기관·사건과 무관한 창작물입니다.")
    assert ok, iss
    ok2, iss2 = check_fiction_disclaimer("아무 말")
    assert not ok2

    bad = "옛날 옛적 한양에 대감이 살았느니라"
    e_ok, hits, level = check_era_leak(bad)
    assert not e_ok and level == "WARN" and hits

    allowed = "박물관에서 <!-- era_allow -->대감의 갓<!-- /era_allow --> 을 보았다. 회사로 돌아왔다."
    e_ok2, hits2, _ = check_era_leak(allowed)
    assert e_ok2, hits2

    modern = "2019년 겨울, 서울 노원구 고시원 골목에서 계약직 직원이 걸었습니다."
    a_ok, a_w = check_modern_anchor(modern)
    assert a_ok, a_w

    print("checks.py selftest OK")


if __name__ == "__main__":
    selftest()
