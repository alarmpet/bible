# -*- coding: utf-8 -*-
"""Generate clean 1-2 line ASS subtitles aligned with authoritative audio manifest.

Splits multi-sentence shots into individual sentence cues so that viewers
only see 1-2 lines of readable text at a time, perfectly synchronized with speech.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.korean_caption import format_ass_timestamp, split_korean_two_lines

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def generate_clean_ass_header(font_size: int = 54) -> str:
    """Generate ASS header with standard documentary typography (54pt, crisp outline & shadow)."""
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: DocuMain,Malgun Gothic,{font_size},&H00FFFFFF,&H000000FF,&H000A0A10,&HB0000000,-1,0,0,0,100,100,0,0,1,4.5,2.0,2,160,160,70,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def split_into_sentence_units(text: str) -> list[str]:
    """Split text into distinct grammatical sentences by punctuation."""
    text = text.strip()
    if not text:
        return []
    
    # Split by sentence-ending punctuation followed by space or end
    pattern = r'(?<=[.?!])\s+'
    raw_sentences = re.split(pattern, text)
    sentences = [s.strip() for s in raw_sentences if s.strip()]
    return sentences if sentences else [text]


def split_caption_cues(text: str, max_chars_per_line: int) -> list[list[str]]:
    """Split a sentence into cues of at most two width-bounded lines."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > max_chars_per_line:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return [lines[index:index + 2] for index in range(0, len(lines), 2)]


def build_ass_subtitles(
    build_dir: Path,
    output_file: Path | None = None,
    *,
    font_size: int = 54,
    max_chars_per_line: int = 22,
) -> Path:
    build_dir = Path(build_dir).resolve()
    manifest_path = build_dir / "scene_audio_manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Audio manifest not found: {manifest_path}")

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    shots = manifest_data.get("shots", [])

    if not output_file:
        output_file = build_dir / "subtitles.ass"

    events = []

    for s in shots:
        shot_start = s["startSeconds"]
        shot_end = s["endSeconds"]
        shot_dur = max(0.1, shot_end - shot_start)
        full_text = s.get("display_text", "").strip()

        sentences = split_into_sentence_units(full_text)
        if not sentences:
            continue

        total_chars = sum(len(sent) for sent in sentences)
        if total_chars == 0:
            continue

        curr_time = shot_start
        for i, sent in enumerate(sentences):
            # Compute proportional time share for this sentence based on character count
            ratio = len(sent) / total_chars
            sent_dur = shot_dur * ratio
            sent_start = curr_time
            sent_end = curr_time + sent_dur if i < len(sentences) - 1 else shot_end

            cue_lines = split_caption_cues(sent, max_chars_per_line)
            cue_chars = [sum(len(line) for line in lines) for lines in cue_lines]
            cue_total = max(1, sum(cue_chars))
            cue_start = sent_start
            for cue_index, lines in enumerate(cue_lines):
                cue_ratio = cue_chars[cue_index] / cue_total
                cue_end = (
                    cue_start + sent_dur * cue_ratio
                    if cue_index < len(cue_lines) - 1
                    else sent_end
                )
                formatted_text = r"\N".join(lines)
                start_ass = format_ass_timestamp(cue_start)
                end_ass = format_ass_timestamp(cue_end)
                events.append(
                    f"Dialogue: 0,{start_ass},{end_ass},DocuMain,,0,0,0,,{formatted_text}"
                )
                cue_start = cue_end
            curr_time = sent_end

    full_ass_text = generate_clean_ass_header(font_size=font_size) + "\n".join(events) + "\n"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(full_ass_text, encoding="utf-8-sig")

    print(f"✅ Clean 1-2 line ASS subtitles created: {output_file} ({len(events)} cues from {len(shots)} shots)")
    return output_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--font-size", type=int, default=54)
    parser.add_argument("--max-chars-per-line", type=int, default=22)
    args = parser.parse_args()
    build_ass_subtitles(
        args.build,
        output_file=args.output,
        font_size=args.font_size,
        max_chars_per_line=args.max_chars_per_line,
    )


if __name__ == "__main__":
    main()
