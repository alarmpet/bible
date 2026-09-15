# -*- coding: utf-8 -*-
"""Generate 116pt Bold Dynamic ASS subtitles with strict <= 2 lines invariant,
micro-clause time slicing for 116pt spatial limits, and clause-aware syntactic line breaking."""
from __future__ import annotations
import json
import re
from pathlib import Path

EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
MANIFEST_PATH = EP_DIR / "generation" / "master_1200s_manifest.json"
OUT_ASS = EP_DIR / "candidate" / "pilot_subtitles_1200s.ass"
QA_REPORT = EP_DIR / "candidate" / "subtitles_qa_report.json"

def seconds_to_ass(s: float) -> str:
    cs = int(round(s * 100))
    m, cs = divmod(cs, 6000)
    h, m = divmod(m, 60)
    s_int, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s_int:02d}.{cs:02d}"

def split_sentence_into_clauses(text: str, max_chars: int = 22) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    # 1. Punctuation comma near middle (avoiding numbers like 5,000)
    comma_matches = [m.end() for m in re.finditer(r"(?<!\d),(?!\d)\s*", text)]
    mid = len(text) / 2.0
    best_split = -1
    min_diff = 9999

    for pos in comma_matches:
        diff = abs(pos - mid)
        if diff < min_diff and pos <= len(text) - 4 and pos >= 4:
            min_diff = diff
            best_split = pos

    # 2. Connective verb endings (~면, ~고, ~며, ~지만, ~는데, ~어서, ~하여, ~되어, ~수록, ~면서, ~하고, ~되고, ~이며, ~이나)
    if best_split <= 0:
        conn_matches = [m.end() for m in re.finditer(r"(?:면|고|며|지만|는데|어서|하여|되어|수록|면서|하고|되고|이며|이나)\s+", text)]
        for pos in conn_matches:
            diff = abs(pos - mid)
            if diff < min_diff and pos <= len(text) - 4 and pos >= 4:
                min_diff = diff
                best_split = pos

    # 3. Whitespace nearest to middle
    if best_split <= 0:
        words = text.split()
        if len(words) <= 1:
            return [text]

        best_idx = 1
        min_diff = 9999
        for i in range(1, len(words)):
            w1 = " ".join(words[:i])
            w2 = " ".join(words[i:])
            diff = abs(len(w1) - len(w2))
            if diff < min_diff:
                min_diff = diff
                best_idx = i
        best_split = len(" ".join(words[:best_idx]))

    c1 = text[:best_split].strip()
    c2 = text[best_split:].strip()

    res = []
    for c in [c1, c2]:
        if len(c) > max_chars:
            res.extend(split_sentence_into_clauses(c, max_chars=max_chars))
        else:
            res.append(c)
    return res

def split_clause_two_lines(text: str, max_line_chars: int = 11) -> str:
    text = text.strip()
    if len(text) <= max_line_chars:
        return text

    # Check comma split
    comma_matches = [m.end() for m in re.finditer(r"(?<!\d),(?!\d)\s*", text)]
    mid = len(text) / 2.0
    best_split = -1
    min_diff = 9999

    for pos in comma_matches:
        diff = abs(pos - mid)
        if diff < min_diff and pos <= len(text) - 3 and pos >= 3:
            min_diff = diff
            best_split = pos

    if best_split > 0:
        l1 = text[:best_split].strip()
        l2 = text[best_split:].strip()
        return l1 + r"\N" + l2

    # Split by whitespace balanced near middle
    words = text.split()
    if len(words) <= 1:
        return text

    best_idx = 1
    min_diff = 9999
    for i in range(1, len(words)):
        l1 = " ".join(words[:i])
        l2 = " ".join(words[i:])
        diff = abs(len(l1) - len(l2))
        if diff < min_diff:
            min_diff = diff
            best_idx = i

    l1 = " ".join(words[:best_idx]).strip()
    l2 = " ".join(words[best_idx:]).strip()
    return l1 + r"\N" + l2

def main():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    shots = manifest["shots"]
    print(f"Loaded {len(shots)} shots for 116pt subtitle compilation.")

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: DocuNarrator_v4,Pretendard,116,&H00FFFFFF,&H000000FF,&H000C0C12,&H90000000,-1,0,0,0,100,100,0,0,1,7.5,4.0,2,120,120,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    dialogue_events = []
    total_sents = 0
    violations = []

    for s in shots:
        sid = s["shot_id"]
        display_text = s["display_text"]
        speech_start = s["speech_start"]
        speech_dur = s["speech_duration"]

        # Extract sentences
        raw_sents = [st.strip() for st in re.split(r"(?<=[.?!])\s+", display_text) if st.strip()]
        if not raw_sents:
            raw_sents = [display_text.strip()]

        total_chars = sum(len(st) for st in raw_sents)
        cur_t = speech_start

        for idx, sent in enumerate(raw_sents):
            total_sents += 1
            ratio = len(sent) / max(1, total_chars)
            sent_dur = max(1.5, round(speech_dur * ratio, 3))
            
            # Subdivide into micro-clauses (max 22 chars for 116pt)
            clauses = split_sentence_into_clauses(sent, max_chars=22)
            total_clause_chars = sum(len(c) for c in clauses)
            
            clause_t = cur_t
            for c_idx, clause in enumerate(clauses):
                c_ratio = len(clause) / max(1, total_clause_chars)
                c_dur = round(sent_dur * c_ratio, 3)
                
                sub_start = max(0.0, clause_t - 0.04)
                sub_end = min(1560.0, clause_t + c_dur)

                # Format clause into <= 2 lines (max 11 chars/line)
                formatted_text = split_clause_two_lines(clause, max_line_chars=11)
                
                # Strict QA Checks
                lines = formatted_text.split(r"\N")
                if len(lines) > 2:
                    violations.append({"shot_id": sid, "clause": clause, "formatted": formatted_text, "error": f"Lines {len(lines)} > 2"})
                for line in lines:
                    if len(line) > 14:
                        violations.append({"shot_id": sid, "clause": clause, "formatted": formatted_text, "error": f"Line length {len(line)} > 14"})

                start_ass = seconds_to_ass(sub_start)
                end_ass = seconds_to_ass(sub_end)
                dialogue_events.append(f"Dialogue: 0,{start_ass},{end_ass},DocuNarrator_v4,,0,0,0,,{formatted_text}")

                clause_t += c_dur

            # Breathing pause between sentences
            cur_t = cur_t + sent_dur + 0.12

    ass_content = header + "\n".join(dialogue_events) + "\n"
    OUT_ASS.write_text(ass_content, encoding="utf-8")
    print(f"Generated {len(dialogue_events)} 116pt subtitle events into: {OUT_ASS}")

    qa_data = {
        "qa_status": "PASS" if len(violations) == 0 else "FAIL",
        "font_size": 116,
        "style_name": "DocuNarrator_v4",
        "total_dialogue_events": len(dialogue_events),
        "total_sentences": total_sents,
        "max_lines_per_event": 2,
        "max_chars_per_line": 14,
        "violations_count": len(violations),
        "violations": violations
    }
    QA_REPORT.write_text(json.dumps(qa_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"QA Status: {qa_data['qa_status']} (Violations: {len(violations)})")

    if violations:
        print(f"Found {len(violations)} subtitle violations:")
        for v in violations[:5]:
            print(v)
        raise ValueError(f"Found {len(violations)} subtitle violations exceeding limits!")

if __name__ == "__main__":
    main()
