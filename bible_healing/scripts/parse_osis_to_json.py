# -*- coding: utf-8 -*-
"""Parse OSIS XML into verse JSON index for lookup."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from paths_bh import RAW, VERSES, DATA

# OSIS often uses namespaces
NS = {"o": "http://www.bibletechnologies.net/2003/OSIS/namespace"}

# Map common OSIS book IDs → Korean labels
BOOK_KO = {
    "Gen": "창세기",
    "Exod": "출애굽기",
    "Lev": "레위기",
    "Num": "민수기",
    "Deut": "신명기",
    "Josh": "여호수아",
    "Judg": "사사기",
    "Ruth": "룻기",
    "1Sam": "사무엘상",
    "2Sam": "사무엘하",
    "1Kgs": "열왕기상",
    "2Kgs": "열왕기하",
    "1Chr": "역대상",
    "2Chr": "역대하",
    "Ezra": "에스라",
    "Neh": "느헤미야",
    "Esth": "에스더",
    "Job": "욥기",
    "Ps": "시편",
    "Prov": "잠언",
    "Eccl": "전도서",
    "Song": "아가",
    "Isa": "이사야",
    "Jer": "예레미야",
    "Lam": "예레미야애가",
    "Ezek": "에스겔",
    "Dan": "다니엘",
    "Hos": "호세아",
    "Joel": "요엘",
    "Amos": "아모스",
    "Obad": "오바댜",
    "Jonah": "요나",
    "Mic": "미가",
    "Nah": "나훔",
    "Hab": "하박국",
    "Zeph": "스바냐",
    "Hag": "학개",
    "Zech": "스가랴",
    "Mal": "말라기",
    "Matt": "마태복음",
    "Mark": "마가복음",
    "Luke": "누가복음",
    "John": "요한복음",
    "Acts": "사도행전",
    "Rom": "로마서",
    "1Cor": "고린도전서",
    "2Cor": "고린도후서",
    "Gal": "갈라디아서",
    "Eph": "에베소서",
    "Phil": "빌립보서",
    "Col": "골로새서",
    "1Thess": "데살로니가전서",
    "2Thess": "데살로니가후서",
    "1Tim": "디모데전서",
    "2Tim": "디모데후서",
    "Titus": "디도서",
    "Phlm": "빌레몬서",
    "Heb": "히브리서",
    "Jas": "야고보서",
    "1Pet": "베드로전서",
    "2Pet": "베드로후서",
    "1John": "요한일서",
    "2John": "요한이서",
    "3John": "요한삼서",
    "Jude": "유다서",
    "Rev": "요한계시록",
}

# Also accept full names / alternate ids
BOOK_ALIASES = {
    "Psalm": "Ps",
    "Psalms": "Ps",
    "Isaiah": "Isa",
    "Genesis": "Gen",
}


def local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    return s


def parse_osis_id(osis_id: str) -> tuple[str, int, int] | None:
    """Parse 'Ps.23.1' or 'Bible.Ps.23.1' → (book, chapter, verse)."""
    if not osis_id:
        return None
    parts = osis_id.split(".")
    # drop leading 'Bible' if present
    if parts and parts[0].lower() == "bible":
        parts = parts[1:]
    if len(parts) < 3:
        return None
    book, ch, vs = parts[0], parts[1], parts[2]
    # verse may be '1!' or range start only
    vs = re.sub(r"[^0-9].*$", "", vs)
    ch = re.sub(r"[^0-9].*$", "", ch)
    if not ch.isdigit() or not vs.isdigit():
        return None
    book = BOOK_ALIASES.get(book, book)
    return book, int(ch), int(vs)


def extract_verses(root: ET.Element) -> list[dict]:
    verses: list[dict] = []
    # Method 1: <verse osisID="Ps.23.1">text</verse>
    for el in root.iter():
        if local(el.tag) != "verse":
            continue
        osis_id = el.get("osisID") or el.get("osisId") or ""
        # some files use sID/eID milestone empty verses
        if el.get("sID") or el.get("eID"):
            continue
        parsed = parse_osis_id(osis_id.split(" ")[0] if osis_id else "")
        if not parsed:
            continue
        book, ch, vs = parsed
        text = clean_text("".join(el.itertext()))
        if not text:
            continue
        verses.append(
            {
                "book": book,
                "book_ko": BOOK_KO.get(book, book),
                "chapter": ch,
                "verse": vs,
                "osis_id": f"{book}.{ch}.{vs}",
                "text": text,
                "translation": "KRV",
            }
        )
    if verses:
        return verses

    # Method 2: milestone verses — walk chapter, collect text between verse markers
    return extract_milestone(root)


def extract_milestone(root: ET.Element) -> list[dict]:
    verses: list[dict] = []
    current: dict | None = None
    buf: list[str] = []

    def flush():
        nonlocal current, buf
        if current and buf:
            text = clean_text("".join(buf))
            if text:
                current["text"] = text
                verses.append(current)
        current = None
        buf = []

    for el in root.iter():
        tag = local(el.tag)
        if tag == "verse":
            sid = el.get("sID")
            eid = el.get("eID")
            osis_id = el.get("osisID") or el.get("osisId") or ""
            if sid or (osis_id and not eid):
                flush()
                oid = (osis_id or sid or "").split(" ")[0]
                parsed = parse_osis_id(oid)
                if parsed:
                    book, ch, vs = parsed
                    current = {
                        "book": book,
                        "book_ko": BOOK_KO.get(book, book),
                        "chapter": ch,
                        "verse": vs,
                        "osis_id": f"{book}.{ch}.{vs}",
                        "translation": "KRV",
                    }
                    buf = []
            elif eid:
                flush()
        elif tag in ("note", "title", "header"):
            continue
        else:
            if current is not None and el.text:
                buf.append(el.text)
            if current is not None and el.tail:
                buf.append(el.tail)
    flush()
    return verses


def build_index(verses: list[dict]) -> dict:
    """osis_id → verse; also nested book → chapter → verse."""
    by_id = {}
    nested: dict = {}
    for v in verses:
        by_id[v["osis_id"]] = v
        nested.setdefault(v["book"], {}).setdefault(str(v["chapter"]), {})[str(v["verse"])] = v
    return {"by_id": by_id, "nested": nested, "count": len(verses)}


def main() -> None:
    src = RAW / "kor-korean.osis.xml"
    if not src.exists():
        raise SystemExit(f"Missing {src}; run download_bible.py first")
    print(f"Parsing {src} ...")
    # large file — ET.parse is fine for typical bible size
    tree = ET.parse(src)
    root = tree.getroot()
    verses = extract_verses(root)
    if not verses:
        raise SystemExit("No verses extracted — check OSIS structure")
    VERSES.mkdir(parents=True, exist_ok=True)
    all_path = VERSES / "krv_all.json"
    all_path.write_text(json.dumps(verses, ensure_ascii=False, indent=0), encoding="utf-8")
    index = build_index(verses)
    idx_path = VERSES / "krv_index.json"
    # nested only for size; by_id full
    idx_path.write_text(
        json.dumps(
            {"count": index["count"], "by_id": index["by_id"], "books": sorted(index["nested"].keys())},
            ensure_ascii=False,
            indent=0,
        ),
        encoding="utf-8",
    )
    # OT-only slim for healing pipeline
    ot_books = set(list(BOOK_KO.keys())[:39])  # Gen..Mal order in dict is insertion order py3.7+
    # Safer explicit OT set
    ot_books = {
        "Gen", "Exod", "Lev", "Num", "Deut", "Josh", "Judg", "Ruth",
        "1Sam", "2Sam", "1Kgs", "2Kgs", "1Chr", "2Chr", "Ezra", "Neh", "Esth",
        "Job", "Ps", "Prov", "Eccl", "Song", "Isa", "Jer", "Lam", "Ezek", "Dan",
        "Hos", "Joel", "Amos", "Obad", "Jonah", "Mic", "Nah", "Hab", "Zeph", "Hag", "Zech", "Mal",
    }
    ot = [v for v in verses if v["book"] in ot_books]
    (VERSES / "krv_ot.json").write_text(json.dumps(ot, ensure_ascii=False, indent=0), encoding="utf-8")
    meta = {
        "total_verses": len(verses),
        "ot_verses": len(ot),
        "books": sorted({v["book"] for v in verses}),
        "sample": verses[:3],
    }
    (DATA / "parse_report.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"OK verses={len(verses)} ot={len(ot)} → {VERSES}")


if __name__ == "__main__":
    main()
