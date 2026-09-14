# -*- coding: utf-8 -*-
"""Production SSOT Clean Subtitle Compiler for Rank 2 Exact Replication.

Resolves D-2 (Stuttering/Rolling Caption Loops), D-3 (STT Typos & Comma Splitting),
and D-5 (Opaque Black Tape Subtitle Box):
- Uses master_script_clean.json (274 clean, non-stuttering sentences)
- Splits into 510~550 balanced single-line clauses (max_chars <= 25, avg duration ~2.6s)
- Comprehensive STT typo correction (40+ historical and speech errors)
  - High-visibility 72pt Pretendard style (BorderStyle=3, semi-transparent box)
- Preserves commas inside numbers for yellow keyword highlighting
- Enforces strict audit invariants (0 multiline, 0 overlap, 0 zero-start, >= 507 events)
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = Path(r"D:\module\bible\human_archive\scripts")
LIB_DIR = SCRIPTS_DIR / "lib"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(LIB_DIR))

from lib.exact_release_verifier import audit_ass_strict

EP_DIR = Path(r"D:\module\bible\human_archive\runs\human_library_replica\rank2_forgotten_civilization")
SCRIPT_PATH = EP_DIR / "script" / "master_script_clean.json"
OUTPUT_ASS = EP_DIR / "subtitles" / "rank2_exact_master_subtitles.ass"

TYPO_REPLACEMENTS = [
    # Historical names / terms
    ("스스라고 불리는", "힉소스라고 불리는"),
    ("스스한테서", "힉소스한테서"),
    ("스스의", "힉소스의"),
    ("아만이 진짜 신", "아톤만이 진짜 신"),
    ("아흐세라는", "아흐모세라는"),
    ("신앙국에서", "신왕국에서"),
    ("신앙국", "신왕국"),
    ("신라 석꾸람이", "신라 석굴암이"),
    ("신라 석꾸람", "신라 석굴암"),

    # Common speech misrecognitions
    ("지부상에서", "지구상에서"),
    ("먹여 사귀였습니다", "먹여 살렸습니다"),
    ("투경이 확 바뀝니다", "풍경이 확 바뀝니다"),
    ("투경이 확", "풍경이 확"),
    ("생과 사가 달리는 겁니다", "생과 사가 갈리는 겁니다"),
    ("생과 사가 달리는", "생과 사가 갈리는"),
    ("생명체라고 온", "생명체라고는"),
    ("통째로 이르면서요", "통째로 잃으면서요"),
    ("통채로", "통째로"),
    ("한핵 한획", "한 획 한 획"),
    ("이 이 서제에서", "이 서재에서"),
    ("이 서제에서", "이 서재에서"),
    ("서제에서", "서재에서"),

    # Number fixes
    ("3,년이요", "3천 년이요"),
    ("3,년을", "3천 년을"),
    ("3,년 된", "3천 년 된"),
    ("3,년 동안", "3천 년 동안"),
    ("3,년", "3천 년"),
    ("5,년 전", "5천 년 전"),
    ("5,년", "5천 년"),

    # Spacing and conjunction cleanup
    ("집단인데이", "집단인데 이"),
    ("문명인데이", "문명인데 이"),
    ("있는데이", "있는데 이"),
    ("있었는데요.이", "있었는데요. 이"),
    ("입니다.이 이", "입니다. 이"),
    ("입니다.이", "입니다. 이"),
    ("있습니다.이", "있습니다. 이"),
    ("겁니다.이", "겁니다. 이"),
    ("였어요.이", "였어요. 이"),
    ("거든요.이", "거든요. 이"),
    ("거예요.이", "거예요. 이"),
    ("왔어요.이", "왔어요. 이"),
    ("있을까요?이 이", "있을까요? 이"),
    ("있을까요?이", "있을까요? 이"),
    ("나르메르예요.이", "나르메르예요. 이"),
    ("그리고이", "그리고 이"),
    ("지금까지이", "지금까지 이"),
]

HIGHLIGHT_PATTERN = re.compile(
    r"("
    r"\b(?:\d{1,3}(?:,\d{3})+|\d+)(?:만|억|천)?\s*(?:년|km|m|층|명|개|%|퍼센트)?\b|"
    r"3천 년이요|3천 년|5천 년 전|5천 년|"
    r"클레오파트라|피라미드|나일강|상형문자|로제타석|나르메르|람세스|힉소스|알렉산드로스|샹폴리옹"
    r")"
)


def seconds_to_ass(s: float) -> str:
    cs_total = int(round(s * 100))
    hours = cs_total // (3600 * 100)
    rem = cs_total % (3600 * 100)
    minutes = rem // (60 * 100)
    rem = rem % (60 * 100)
    secs = rem // 100
    cs = rem % 100
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def clean_text(t: str) -> str:
    t = unicodedata.normalize("NFC", t.strip())
    for old, new in TYPO_REPLACEMENTS:
        t = t.replace(old, new)
    t = re.sub(r"([.?!])([가-힣])", r"\1 \2", t)
    return t.strip()


def split_into_clean_clauses(text: str, max_chars: int = 24) -> list[str]:
    text = clean_text(text)
    if len(text) <= max_chars:
        return [text]

    words = text.split()
    if len(words) <= 1:
        return [text]

    num_parts = 2 if len(text) <= max_chars * 2 else (3 if len(text) <= max_chars * 3 else 4)

    if num_parts == 2:
        best_i = 1
        best_score = -999999.0
        for i in range(1, len(words)):
            w1 = " ".join(words[:i])
            w2 = " ".join(words[i:])
            len1, len2 = len(w1), len(w2)
            score = -abs(len1 - len2) * 2.0
            if len1 > max_chars:
                score -= (len1 - max_chars) * 30.0
            if len2 > max_chars:
                score -= (len2 - max_chars) * 30.0
            last_w1 = words[i - 1]
            if last_w1.endswith((",", ".", "!", "?")):
                score += 50.0
            for end in ["면서", "지만", "는데", "다면", "으로", "에서", "하고", "이며", "으며", "고", "며", "서", "도", "때"]:
                if last_w1.endswith(end):
                    score += 30.0
                    break
            if score > best_score:
                best_score = score
                best_i = i
        return [" ".join(words[:best_i]).strip(), " ".join(words[best_i:]).strip()]
    else:
        # Multi-part split
        parts2 = split_into_clean_clauses(text, max_chars=max_chars * 2)
        res = []
        for p in parts2:
            if len(p) > max_chars:
                res.extend(split_into_clean_clauses(p, max_chars=max_chars))
            else:
                res.append(p)
        return res


def highlight_keywords_safe(text: str) -> str:
    """Highlight numbers and key nouns in vivid yellow without splitting commas."""
    def _repl(match: re.Match) -> str:
        word = match.group(1)
        return rf"{{\c&H003BEBFF&}}{word}{{\c&H00FFFFFF&}}"
    return HIGHLIGHT_PATTERN.sub(_repl, text)


def build_rank2_clean_ass(output_ass: Path = OUTPUT_ASS) -> Path:
    script_data = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))
    sentences = script_data["sentences"]
    print(f"Loaded {len(sentences)} clean sentences from {SCRIPT_PATH}")

    all_events = []
    for s in sentences:
        clauses = split_into_clean_clauses(s["text"], max_chars=24)
        s_start = s["start"]
        s_end = s["end"]
        s_dur = s_end - s_start
        total_len = sum(len(c) for c in clauses)

        cur_t = s_start
        for idx, c in enumerate(clauses):
            ratio = len(c) / max(1, total_len)
            c_dur = round(s_dur * ratio, 2)
            c_start = cur_t
            c_end = round(cur_t + c_dur, 2) if idx < len(clauses) - 1 else s_end

            # Safety clamp
            if c_end <= c_start:
                c_end = c_start + 0.50

            highlighted = highlight_keywords_safe(c)

            all_events.append({
                "start_sec": c_start,
                "end_sec": c_end,
                "text": highlighted,
                "raw_text": c,
            })
            cur_t = c_end

    # Fix any contiguous boundary gaps/overlaps
    for i in range(1, len(all_events)):
        prev_end = all_events[i - 1]["end_sec"]
        curr_start = all_events[i]["start_sec"]
        if abs(prev_end - curr_start) > 0.001:
            all_events[i]["start_sec"] = prev_end

    header = """[Script Info]
Title: Forgotten Civilization Exact Subtitles (Clean Remaster)
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: DocuNarrator_v4,Pretendard,72,&H00FFFFFF,&H000000FF,&H800C0C12,&H80000000,-1,0,0,0,100,100,0,0,3,2.0,0,2,50,50,72,1
Style: DocuNarrator_Exact,Pretendard,72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,3,2.0,0,2,50,50,72,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    dialogue_lines = []
    for ev in all_events:
        s_ass = seconds_to_ass(ev["start_sec"])
        e_ass = seconds_to_ass(ev["end_sec"])
        dialogue_lines.append(
            f"Dialogue: 0,{s_ass},{e_ass},DocuNarrator_Exact,,0,0,0,,{ev['text']}"
        )

    content = header + "\n".join(dialogue_lines) + "\n"
    output_ass = Path(output_ass)
    output_ass.parent.mkdir(parents=True, exist_ok=True)
    output_ass.write_text(content, encoding="utf-8")
    print(f"✅ Generated clean ASS: {output_ass} ({output_ass.stat().st_size:,} bytes, {len(dialogue_lines)} events)")

    # Audit
    audit_res = audit_ass_strict(output_ass, target_duration_sec=1440.0)
    print(f"Audit Result: status={audit_res['status']}, events={audit_res['dialogue_events']}, errors={audit_res['errors']}")
    assert audit_res["status"] == "PASS", f"Audit failed: {audit_res['errors']}"
    assert audit_res["dialogue_events"] >= 507, f"Too few events: {audit_res['dialogue_events']} < 507"
    assert audit_res["multiline_events"] == 0, "Multiline events found!"
    assert audit_res["zero_start_events"] == 0, "Zero start events found!"
    assert audit_res["overlap_events"] == 0, "Overlap events found!"

    # Yellow highlight count
    yellow_count = sum(1 for l in dialogue_lines if r"\c&H003BEBFF&" in l)
    print(f"Yellow highlighted lines: {yellow_count}/50 required")
    assert yellow_count >= 50, f"Too few yellow lines: {yellow_count}"

    return output_ass


if __name__ == "__main__":
    build_rank2_clean_ass()
