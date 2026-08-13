# -*- coding: utf-8 -*-
"""
Prepare scripture text for stable SuperTonic TTS.

Problems fixed:
- Long 400+ char blocks → chunked mid-sentence (prosody jumps)
- (셀라) / headers / ! → angry or broken delivery

Strategy:
- Prefer verse-by-verse synthesis when ref is known
- Strip liturgical headers and (셀라) for TTS only
- Soften exclamation for speech (display text can stay original)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verse_lib import get_verses  # noqa: E402


def strip_headers_and_selah(text: str) -> str:
    t = text or ""
    # drop parenthetical headers / selah (any length up to 80)
    t = re.sub(r"\([^)]{0,100}\)", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def soften_for_speech(text: str) -> str:
    """TTS-only softening; not for on-screen original quote fidelity."""
    t = strip_headers_and_selah(text)
    # exclamation → period (reduces shouty prosody)
    t = t.replace("!", ".")
    t = t.replace("！", ".")
    # multiple spaces
    t = re.sub(r"\s+", " ", t).strip()
    # trailing connectives cleanup
    t = re.sub(r"\s+\.", ".", t)
    return t


def split_into_speech_units(text: str, max_len: int = 90) -> list[str]:
    """
    Split cleaned text at Korean/clause boundaries under max_len.
    Prefer 。.!?  and then commas / spaces.
    """
    t = soften_for_speech(text)
    if not t:
        return []
    if len(t) <= max_len:
        return [t]

    units: list[str] = []
    # first split by strong punctuation
    parts = re.split(r"(?<=[.?!。])\s+", t)
    buf = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) > max_len:
            # flush buf
            if buf:
                units.append(buf.strip())
                buf = ""
            units.extend(_hard_split(part, max_len))
            continue
        cand = f"{buf} {part}".strip() if buf else part
        if len(cand) <= max_len:
            buf = cand
        else:
            if buf:
                units.append(buf.strip())
            buf = part
    if buf:
        units.append(buf.strip())
    return [u for u in units if u]


def _hard_split(text: str, max_len: int) -> list[str]:
    # try commas
    out: list[str] = []
    buf = ""
    tokens = re.split(r"(?<=[,，])\s*", text)
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        cand = f"{buf}{tok}".strip() if buf else tok
        if len(cand) <= max_len:
            buf = cand + (" " if not tok.endswith((",", "，")) else "")
            buf = cand
        else:
            if buf:
                out.append(buf.strip())
            if len(tok) <= max_len:
                buf = tok
            else:
                for i in range(0, len(tok), max_len):
                    out.append(tok[i : i + max_len].strip())
                buf = ""
    if buf:
        out.append(buf.strip())
    return [x for x in out if x]


def verses_to_speech_units(ref: str, max_len: int = 90) -> list[dict]:
    """
    Return list of {verse, text_display, text_tts} for a ref like Ps.4.1-8.
    Each verse is one unit unless still too long.
    """
    rows = get_verses(ref)
    units: list[dict] = []
    for v in rows:
        display = v["text"]
        tts = soften_for_speech(display)
        if not tts:
            continue
        if len(tts) <= max_len:
            units.append(
                {
                    "osis_id": v["osis_id"],
                    "text_display": display,
                    "text_tts": tts,
                }
            )
        else:
            for piece in split_into_speech_units(tts, max_len):
                units.append(
                    {
                        "osis_id": v["osis_id"],
                        "text_display": display,
                        "text_tts": piece,
                    }
                )
    return units


def expand_scripture_segment(seg: dict, max_len: int = 90) -> list[dict]:
    """
    Expand one scenes.json segment (speaker=scripture) into multiple TTS segments.
    """
    ref = seg.get("ref")
    base_id = seg.get("seg_id") or "scripture"
    if ref:
        try:
            units = verses_to_speech_units(ref, max_len=max_len)
            out = []
            for i, u in enumerate(units, 1):
                out.append(
                    {
                        "speaker": "scripture",
                        "text": u["text_tts"],
                        "text_display": u["text_display"],
                        "seg_id": f"{base_id}_v{i:02d}",
                        "ref": ref,
                        "osis_id": u.get("osis_id"),
                    }
                )
            if out:
                return out
        except Exception:
            pass
    # fallback: plain text split
    pieces = split_into_speech_units(seg.get("text") or "", max_len=max_len)
    return [
        {
            "speaker": "scripture",
            "text": p,
            "text_display": p,
            "seg_id": f"{base_id}_p{i:02d}",
            "ref": ref,
        }
        for i, p in enumerate(pieces, 1)
    ]


def expand_job_scenes(job_dir: Path, max_len: int = 90) -> dict:
    """In-place expand scripture segments in scenes.json for multi-segment TTS."""
    path = job_dir / "scenes.json"
    scenes = json.loads(path.read_text(encoding="utf-8"))
    expanded_count = 0
    for sc in scenes:
        segs = sc.get("segments") or []
        new_segs = []
        for seg in segs:
            if (seg.get("speaker") or "") == "scripture":
                parts = expand_scripture_segment(seg, max_len=max_len)
                new_segs.extend(parts)
                expanded_count += len(parts)
            else:
                # mild soften for narrator too? keep as-is for fidelity
                new_segs.append(seg)
        sc["segments"] = new_segs
        # narration field used by some tools — keep full display text
        # but TTS uses segments
    path.write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")
    report = {
        "ok": True,
        "scripture_tts_units": expanded_count,
        "max_len": max_len,
        "job": str(job_dir),
    }
    (job_dir / "reports").mkdir(exist_ok=True)
    (job_dir / "reports" / "scripture_expand_report.json").write_text(
        __import__("json").dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


import json  # noqa: E402  after functions for expand_job_scenes


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--max-len", type=int, default=90)
    args = ap.parse_args()
    print(json.dumps(expand_job_scenes(Path(args.job).resolve(), args.max_len), ensure_ascii=False, indent=2))
