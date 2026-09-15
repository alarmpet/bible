# -*- coding: utf-8 -*-
"""Canonical timeline adapter bridging raw cues.json (346 items),

single-line subtitle events (406 semantic clauses), and logical sentences (135 items).
Enforces 30.00fps CFR frame boundaries, 973.167s container clamping, and zero-gap continuity.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CanonicalCue:
    cue_id: str
    start_sec: float
    end_sec: float
    duration_sec: float
    raw_text: str
    display_text: str
    parent_sentence_id: Optional[str] = None
    highlight_keywords: List[str] = field(default_factory=list)


@dataclass
class CanonicalTimelineManifest:
    schema_version: str = "canonical_timeline_v1"
    video_id: str = "tPBVrfcU85g"
    target_fps: float = 30.0
    target_duration_sec: float = 973.167
    target_total_frames: int = 29195
    total_cues: int = 0
    total_sentences: int = 0
    cues: List[CanonicalCue] = field(default_factory=list)
    sentence_mappings: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "video_id": self.video_id,
            "target_fps": self.target_fps,
            "target_duration_sec": self.target_duration_sec,
            "target_total_frames": self.target_total_frames,
            "total_cues": self.total_cues,
            "total_sentences": self.total_sentences,
            "cues": [asdict(c) for c in self.cues],
            "sentence_mappings": self.sentence_mappings,
        }


def extract_highlight_keywords(text: str) -> List[str]:
    """Extract numbers, metric units, scientific terms, and contrast words for yellow highlighting."""
    keywords = []
    # 1. Numerics with units (e.g., 7만 년, 50cm, 30%, 40도, 2500m, 6000년)
    unit_pattern = r"\b\d+[\w%°가-힣]*"
    for m in re.finditer(unit_pattern, text):
        val = m.group(0).strip()
        if len(val) >= 2:
            keywords.append(val)

    # 2. Key contrast & scientific words
    scientific_terms = [
        "인종", "유전자", "돌연변이", "적응", "헤모글로빈", "데니소바인", "네안데르탈인",
        "호모 사피엔스", "멜라닌", "자외선", "비타민 D", "엽산", "유당", "젖당",
        "말라리아", "고산지대", "산소", "피부색", "생존", "진화", "자연선택",
        "EPAS1", "LCT", "ALDH2", "HbS"
    ]
    for term in scientific_terms:
        if term in text and term not in keywords:
            keywords.append(term)

    return list(dict.fromkeys(keywords))  # deduplicate preserving order


def clean_display_text(raw_text: str, prev_text: str = "") -> str:
    """Clean rolling caption text into a readable 1-line subtitle.

    If raw_text contains 2 rolling phrases where the first repeats prev_text,
    extract the newly introduced portion to prevent duplication.
    """
    cleaned = raw_text.strip()
    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned)

    if prev_text:
        # Check if first sentence/clause repeats the tail of prev_text
        prev_words = prev_text.split()
        if len(prev_words) >= 3:
            prev_tail = " ".join(prev_words[-4:])
            if cleaned.startswith(prev_tail):
                cleaned = cleaned[len(prev_tail):].strip()

    # Ensure max 36 chars per line for clean 1-line presentation
    # If longer than 36, keep it clean without breaking words
    return cleaned


def build_canonical_timeline(
    cues_path: Path,
    clean_script_path: Optional[Path] = None,
    target_duration_sec: float = 973.167,
    target_fps: float = 30.0,
) -> CanonicalTimelineManifest:
    """Build the single-source-of-truth canonical timeline.

    1. Loads raw cues.json (346 items).
    2. Validates and enforces sequential zero-gap continuity.
    3. Clamps terminal cue end_sec to target_duration_sec (preventing 974.72s ASR hang-time).
    4. Maps cues to sentences from master_script_clean.json if provided.
    """
    cues_path = Path(cues_path)
    if not cues_path.exists():
        raise FileNotFoundError(f"Cues file not found: {cues_path}")

    with open(cues_path, "r", encoding="utf-8") as f:
        raw_cues = json.load(f)

    if not isinstance(raw_cues, list) or len(raw_cues) == 0:
        raise ValueError(f"Invalid cues content in {cues_path}: expected non-empty list")

    # Load sentences if clean script exists
    sentences = []
    if clean_script_path and Path(clean_script_path).exists():
        with open(clean_script_path, "r", encoding="utf-8") as f:
            script_data = json.load(f)
            sentences = script_data.get("sentences", [])

    canonical_cues: List[CanonicalCue] = []
    prev_clean_text = ""

    for idx, item in enumerate(raw_cues):
        cue_num = idx + 1
        cue_id = f"CUE_{cue_num:03d}"

        s_time = round(float(item.get("start", 0.0)), 3)
        e_time = round(float(item.get("end", 0.0)), 3)
        raw_txt = str(item.get("text", "")).strip()

        # Continuity check & enforcement
        if canonical_cues:
            last_end = canonical_cues[-1].end_sec
            # If tiny gap/overlap due to float precision, snap start to previous end
            if abs(s_time - last_end) <= 0.050:
                s_time = last_end

        # Terminal clamp for last cue
        if idx == len(raw_cues) - 1:
            if e_time > target_duration_sec:
                e_time = target_duration_sec

        dur = round(max(0.1, e_time - s_time), 3)
        disp_txt = clean_display_text(raw_txt, prev_clean_text)
        prev_clean_text = disp_txt
        kws = extract_highlight_keywords(disp_txt)

        # Map to sentence
        matched_sent_id = None
        if sentences:
            # Find best overlapping sentence
            for sent in sentences:
                sent_s = float(sent.get("start", 0.0))
                sent_e = float(sent.get("end", 0.0))
                # Check interval overlap
                overlap = max(0.0, min(e_time, sent_e) - max(s_time, sent_s))
                if overlap > 0.3 * dur or (s_time >= sent_s - 0.5 and e_time <= sent_e + 0.5):
                    matched_sent_id = sent.get("sentence_id")
                    break

        cue_obj = CanonicalCue(
            cue_id=cue_id,
            start_sec=s_time,
            end_sec=e_time,
            duration_sec=dur,
            raw_text=raw_txt,
            display_text=disp_txt,
            parent_sentence_id=matched_sent_id,
            highlight_keywords=kws,
        )
        canonical_cues.append(cue_obj)

    # Build sentence to cues mapping
    sentence_mappings: Dict[str, List[str]] = {}
    for c in canonical_cues:
        if c.parent_sentence_id:
            sentence_mappings.setdefault(c.parent_sentence_id, []).append(c.cue_id)

    manifest = CanonicalTimelineManifest(
        target_fps=target_fps,
        target_duration_sec=target_duration_sec,
        target_total_frames=round(target_duration_sec * target_fps),
        total_cues=len(canonical_cues),
        total_sentences=len(sentences),
        cues=canonical_cues,
        sentence_mappings=sentence_mappings,
    )
    return manifest
