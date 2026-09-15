# -*- coding: utf-8 -*-
"""SSOT Semantic Subtitle Engine for History-Ida Documentaries (Expanded 52pt / 36-char Standard).

Tri-Model Consensus Specifications:
1. Font: Pretendard 52pt, Style DocuNarrator_v4, MarginL=50, MarginR=50, MarginV=55.
2. Max line length: <= 36 characters (+50% expansion from legacy 24 chars).
3. Max lines per event: Strictly <= 2 lines (at most one '\\N').
4. Max clause chars: <= 70 characters (2 lines of 35 chars).
5. Number comma protection: numbers like '1,100만', '3,100m', '1,200톤' are never split.
6. Semantic balance: 1:1 line length ratio, connective ending cuts, no isolated particles.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ISOLATED_PARTICLES = {"은", "는", "이", "가", "을", "를", "의", "에", "로", "과", "와", "도", "만", "서"}
CONNECTING_ENDINGS = [
    "면서", "지만", "는데", "다면", "으로", "에서", "하고", "이며", "으며",
    "기에", "으니", "므로", "고", "며", "서", "도", "어서", "하여", "되어", "수록"
]


def seconds_to_ass(s: float) -> str:
    """Convert seconds float to ASS timestamp format H:MM:SS.cs."""
    cs_total = int(round(s * 100))
    hours = cs_total // (3600 * 100)
    rem = cs_total % (3600 * 100)
    minutes = rem // (60 * 100)
    rem = rem % (60 * 100)
    secs = rem // 100
    cs = rem % 100
    if cs >= 100:
        cs = 99
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def split_korean_two_lines(text: str, max_line_chars: int = 36) -> str:
    """Split Korean text into at most two balanced lines with semantic awareness."""
    text = unicodedata.normalize("NFC", text.strip())
    if not text:
        return ""

    # If text already fits on one line and is short enough
    # But if text is > 26 chars, splitting into 2 balanced lines is often visually better
    # if it doesn't break a word.
    if len(text) <= max_line_chars and len(text) <= 28:
        return text

    words = text.split()
    if len(words) <= 1:
        return text

    best_split_idx = -1
    best_score = -999999.0

    for i in range(1, len(words)):
        l1 = " ".join(words[:i]).strip()
        l2 = " ".join(words[i:]).strip()
        len1 = len(l1)
        len2 = len(l2)

        score = 0.0

        # Heavy penalty if either line exceeds max_line_chars
        if len1 > max_line_chars:
            score -= (len1 - max_line_chars) * 40.0
        if len2 > max_line_chars:
            score -= (len2 - max_line_chars) * 40.0

        # Balance penalty (1:1 ratio preferred)
        score -= abs(len1 - len2) * 2.0

        # Prevent isolated particles at the start of line 2
        first_w_l2 = words[i]
        if first_w_l2 in ISOLATED_PARTICLES:
            score -= 100.0

        # Prevent isolated 1-character modifier at end of line 1 (e.g. '피', '더', '잘')
        last_w_l1 = words[i - 1]
        if len(last_w_l1) == 1 and not last_w_l1.endswith((",", ".", "!", "?")):
            score -= 50.0

        # Bonus for punctuation comma (sentence comma) at the end of line 1
        if last_w_l1.endswith(",") and not re.search(r"\d,$", last_w_l1):
            score += 50.0
        elif any(last_w_l1.endswith(p) for p in [".", "!", "?"]):
            score += 40.0

        # Bonus for connective verb endings
        for ending in CONNECTING_ENDINGS:
            if last_w_l1.endswith(ending):
                score += 25.0
                break

        if score > best_score:
            best_score = score
            best_split_idx = i

    if best_split_idx != -1:
        line1 = " ".join(words[:best_split_idx]).strip()
        line2 = " ".join(words[best_split_idx:]).strip()
        return line1 + r"\N" + line2

    mid_idx = len(words) // 2
    return " ".join(words[:mid_idx]).strip() + r"\N" + " ".join(words[mid_idx:]).strip()


def split_sentence_into_clauses(text: str, max_chars: int = 70, min_clause_chars: int = 15) -> List[str]:
    """Subdivide an excessively long sentence (>70 chars) into 2 micro-clauses."""
    text = unicodedata.normalize("NFC", text.strip())
    if len(text) <= max_chars:
        return [text]

    # 1. Sentence comma near center (excluding commas inside numbers like 1,100)
    comma_matches = [m.end() for m in re.finditer(r"(?<!\d),(?!\d)\s*", text)]
    mid = len(text) / 2.0
    best_split = -1
    min_diff = 9999.0

    for pos in comma_matches:
        diff = abs(pos - mid)
        if diff < min_diff and min_clause_chars <= pos <= len(text) - min_clause_chars:
            min_diff = diff
            best_split = pos

    # 2. Connective verb endings near center
    if best_split <= 0:
        conn_matches = [
            m.end()
            for m in re.finditer(
                r"(?:면서|지만|는데|다면|으로|에서|하고|이며|으며|기에|으니|므로|어서|하여|되어|수록|고|며|서|도)\s+",
                text,
            )
        ]
        for pos in conn_matches:
            diff = abs(pos - mid)
            if diff < min_diff and min_clause_chars <= pos <= len(text) - min_clause_chars:
                min_diff = diff
                best_split = pos

    # 3. Balanced word boundary near center
    if best_split <= 0:
        words = text.split()
        if len(words) <= 1:
            return [text]
        best_idx = 1
        min_diff = 9999.0
        for i in range(1, len(words)):
            w1 = " ".join(words[:i])
            w2 = " ".join(words[i:])
            diff = abs(len(w1) - len(w2))
            if len(words[i - 1]) == 1 and not words[i - 1].endswith((",", ".", "!", "?")):
                diff += 15.0
            if words[i] in ISOLATED_PARTICLES:
                diff += 50.0
            if diff < min_diff:
                min_diff = diff
                best_idx = i
        best_split = len(" ".join(words[:best_idx]))

    c1 = text[:best_split].strip()
    c2 = text[best_split:].strip()

    result = []
    for c in [c1, c2]:
        if len(c) > max_chars:
            result.extend(split_sentence_into_clauses(c, max_chars=max_chars, min_clause_chars=min_clause_chars))
        elif c:
            result.append(c)

    return result


class SemanticSubtitleEngine:
    """Production SSOT Subtitle Engine generating 52pt 2-line ASS subtitles (max 36 chars/line)."""

    def __init__(
        self,
        font_size: int = 52,
        font_name: str = "Pretendard",
        play_res_x: int = 1920,
        play_res_y: int = 1080,
        margin_l: int = 50,
        margin_r: int = 50,
        margin_v: int = 55,
        max_line_chars: int = 36,
        max_clause_chars: int = 70,
    ):
        self.font_size = font_size
        self.font_name = font_name
        self.play_res_x = play_res_x
        self.play_res_y = play_res_y
        self.margin_l = margin_l
        self.margin_r = margin_r
        self.margin_v = margin_v
        self.max_line_chars = max_line_chars
        self.max_clause_chars = max_clause_chars

    def generate_header(self, title: str = "History-Ida Master Subtitles") -> str:
        """Generate ASS script header with high-readability DocuNarrator styles."""
        return f"""[Script Info]
Title: {title}
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {self.play_res_x}
PlayResY: {self.play_res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: DocuNarrator_v4,{self.font_name},{self.font_size},&H00FFFFFF,&H000000FF,&H000C0C12,&H90000000,-1,0,0,0,100,100,0,0,1,3.5,2.0,2,{self.margin_l},{self.margin_r},{self.margin_v},1
Style: DocuNarrator_Exact,{self.font_name},44,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,3,2.0,0,2,40,40,65,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def process_shot_to_events(
        self,
        shot: Dict[str, Any],
        style_name: str = "DocuNarrator_v4",
        highlight_keywords: bool = False,
    ) -> List[str]:
        """Convert a single shot dictionary into 1 or more timed ASS Dialogue lines."""
        display_text = (shot.get("display_text") or shot.get("narration") or shot.get("spoken_text") or "").strip()
        if not display_text:
            return []

        # Determine timestamps (SSOT priority order)
        if "global_start_sec" in shot and "global_end_sec" in shot:
            t_start = float(shot["global_start_sec"])
            t_end = float(shot["global_end_sec"])
        elif "start_sec" in shot and "end_sec" in shot:
            t_start = float(shot["start_sec"])
            t_end = float(shot["end_sec"])
        elif "start_sec" in shot and "duration_sec" in shot:
            t_start = float(shot["start_sec"])
            t_end = t_start + float(shot["duration_sec"])
        elif "speech_start" in shot and "speech_end" in shot:
            t_start = float(shot["speech_start"])
            t_end = float(shot["speech_end"])
        elif "start_time" in shot and "speech_duration" in shot:
            t_start = float(shot["start_time"])
            t_end = t_start + float(shot["speech_duration"])
        elif "start_time" in shot and "duration_sec" in shot:
            t_start = float(shot["start_time"])
            t_end = t_start + float(shot["duration_sec"])
        elif "startSeconds" in shot and "endSeconds" in shot:
            t_start = float(shot["startSeconds"])
            t_end = float(shot["endSeconds"])
        elif "speech_start" in shot and "speech_duration" in shot:
            t_start = float(shot["speech_start"])
            t_end = t_start + float(shot["speech_duration"])
        elif "start_time" in shot and "end_time" in shot:
            t_start = float(shot["start_time"])
            t_end = float(shot["end_time"])
        else:
            t_start = float(shot.get("start_time", shot.get("start_sec", 0.0)))
            t_end = t_start + float(shot.get("scene_duration", shot.get("duration_sec", 5.0)))

        duration = max(1.0, t_end - t_start)

        # Split into raw sentences if multiple distinct sentences exist
        raw_sents = [s.strip() for s in re.split(r"(?<=[.?!])\s+", display_text) if s.strip()]
        if not raw_sents:
            raw_sents = [display_text]

        clauses_with_weights = []
        for sent in raw_sents:
            if len(sent) > self.max_clause_chars:
                sub_clauses = split_sentence_into_clauses(sent, max_chars=self.max_clause_chars)
                for c in sub_clauses:
                    clauses_with_weights.append(c)
            else:
                clauses_with_weights.append(sent)

        def _format_clause(c: str) -> str:
            res = split_korean_two_lines(c, max_line_chars=self.max_line_chars)
            if highlight_keywords:
                # Highlight numbers, measurements, and key punchlines in vivid yellow
                pat = r"(\b\d+[만억천백십]?(?:\s*(?:년|cm|센티미터|도|퍼센트|%|m|개|명))?|인종이 없었습니다|산소가 반밖에|전염병에|에어컨|라디에이터|EPAS1|데니소바인)"
                res = re.sub(pat, r"{\\c&H003BEBFF&}\1{\\c&H00FFFFFF&}", res)
            return res

        # If only 1 clause, format directly into <= 2 lines
        if len(clauses_with_weights) == 1:
            formatted = _format_clause(clauses_with_weights[0])
            start_ass = seconds_to_ass(t_start)
            end_ass = seconds_to_ass(t_end)
            return [f"Dialogue: 0,{start_ass},{end_ass},{style_name},,0,0,0,,{formatted}"]

        # Multiple clauses: apportion duration proportionally by character count
        total_chars = sum(len(c) for c in clauses_with_weights)
        cur_t = t_start
        events = []

        for idx, clause in enumerate(clauses_with_weights):
            ratio = len(clause) / max(1, total_chars)
            c_dur = duration * ratio
            c_start = cur_t
            c_end = cur_t + c_dur if idx < len(clauses_with_weights) - 1 else t_end

            formatted = _format_clause(clause)
            start_ass = seconds_to_ass(c_start)
            end_ass = seconds_to_ass(c_end)
            events.append(f"Dialogue: 0,{start_ass},{end_ass},{style_name},,0,0,0,,{formatted}")

            cur_t = c_end

        return events

    def compile_ass_subtitles(
        self,
        shots: List[Dict[str, Any]],
        output_path: Path,
        title: str = "History-Ida Master Subtitles",
        style_name: str = "DocuNarrator_v4",
        highlight_keywords: bool = False,
    ) -> Path:
        """Compile full ASS file from a list of shots and write to disk."""
        header = self.generate_header(title=title)
        dialogue_events = []

        for shot in shots:
            events = self.process_shot_to_events(
                shot, style_name=style_name, highlight_keywords=highlight_keywords
            )
            dialogue_events.extend(events)

        content = header + "\n".join(dialogue_events) + "\n"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        return output_path

    @staticmethod
    def audit_ass_file(ass_path: Path, max_line_chars: int = 36) -> Dict[str, Any]:
        """Audit an ASS file for formatting invariants (<= 36 chars/line, <= 2 lines)."""
        content = ass_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        violations = []
        dialogue_count = 0

        for idx, line in enumerate(lines):
            if not line.startswith("Dialogue:"):
                continue
            dialogue_count += 1
            parts = line.split(",", 9)
            if len(parts) < 10:
                violations.append({"line_no": idx + 1, "error": "Malformed Dialogue format", "content": line})
                continue

            text = parts[9]

            # Invariant 1: Number comma splitting check
            if re.search(r"\d+,\s*\\N\s*\d+", text):
                violations.append({
                    "line_no": idx + 1,
                    "error": "Number comma split across lines",
                    "content": text
                })

            # Invariant 2: Max 2 lines (at most one \N)
            n_count = text.count(r"\N")
            if n_count > 1:
                violations.append({
                    "line_no": idx + 1,
                    "error": f"More than 2 lines (\\N count: {n_count})",
                    "content": text
                })

            # Invariant 3: Line length <= max_line_chars
            sublines = text.split(r"\N")
            for s_idx, subline in enumerate(sublines):
                cleaned_subline = re.sub(r"\{.*?\}", "", subline).strip()
                if len(cleaned_subline) > max_line_chars:
                    violations.append({
                        "line_no": idx + 1,
                        "subline_idx": s_idx + 1,
                        "error": f"Line length {len(cleaned_subline)} > {max_line_chars}",
                        "content": cleaned_subline
                    })

            # Invariant 4: No isolated particle at start of line 2
            if len(sublines) > 1:
                l2_words = sublines[1].strip().split()
                if l2_words and l2_words[0] in ISOLATED_PARTICLES:
                    violations.append({
                        "line_no": idx + 1,
                        "error": f"Line 2 starts with isolated particle '{l2_words[0]}'",
                        "content": sublines[1]
                    })

        return {
            "file": str(ass_path),
            "status": "PASS" if len(violations) == 0 else "FAIL",
            "dialogue_events": dialogue_count,
            "violations_count": len(violations),
            "violations": violations,
        }
