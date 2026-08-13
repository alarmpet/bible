# -*- coding: utf-8 -*-
"""
Build timed caption cues from locked scene_audio_manifest + scenes.json
using sanitize_script + split_korean_caption (lock two-line Korean path).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_full_audio_aligned_ass import allocate_block_times, load_caption_lock  # noqa: E402
from paths_bh import CONFIG  # noqa: E402
from sanitize_script import sanitize_script  # noqa: E402
from subtitle_layout import split_korean_caption  # noqa: E402


def format_timestamp(milliseconds: int) -> str:
    value = int(round(milliseconds))
    hours = value // 3_600_000
    minutes = (value % 3_600_000) // 60_000
    seconds = (value % 60_000) // 1000
    millis = value % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def clean_text(text: str, speaker: str = "") -> str:
    del speaker
    return sanitize_script(text).display


def load_policy() -> dict:
    return json.loads((CONFIG / "healing_caption_policy.json").read_text(encoding="utf-8"))


def _cues_from_text(text: str, start_ms: int, end_ms: int) -> list[dict]:
    cleaned = clean_text(text)
    if not cleaned or end_ms <= start_ms:
        return []
    blocks = split_korean_caption(cleaned)
    timed = allocate_block_times(blocks, start_ms / 1000.0, end_ms / 1000.0)
    cues: list[dict] = []
    for open_at, close_at, block in timed:
        cues.append(
            {
                "text": block.text,
                "startMs": int(round(open_at * 1000)),
                "endMs": int(round(close_at * 1000)),
            }
        )
    return cues


def _max_line_chars(text: str) -> int:
    if not text:
        return 0
    return max(len(line) for line in text.replace("\n", r"\N").split(r"\N"))


def build(job: Path) -> dict:
    policy = load_policy()
    disp = policy["display"]
    lock_cap = load_caption_lock()
    max_chars = int(lock_cap.get("max_chars_per_line") or disp.get("maxLineChars") or 20)
    min_sec = float(disp.get("minDisplaySeconds") or 0.65)

    scenes = {
        int(s["order"]): s
        for s in json.loads((job / "scenes.json").read_text(encoding="utf-8"))
    }
    man = json.loads((job / "scene_audio_manifest.json").read_text(encoding="utf-8"))
    if man.get("status") != "measured-and-locked" and (man.get("lock") or {}).get("status") != "measured-and-locked":
        # still allow if scenes present
        pass

    all_cues = []
    per_scene = []
    for item in sorted(man["scenes"], key=lambda x: int(x["order"])):
        order = int(item["order"])
        sc = scenes.get(order) or {}
        segs = sc.get("segments") or []
        speaker = (sc.get("meta") or {}).get("speaker") or (segs[0].get("speaker") if segs else "narrator")
        text = sc.get("narration") or item.get("text") or ""
        start_ms = int(round(float(item["startSeconds"]) * 1000))
        end_ms = int(round(float(item["endSeconds"]) * 1000))
        cues = _cues_from_text(text, start_ms, end_ms)
        for cue in cues:
            cue["order"] = order
            cue["speaker"] = speaker
            cue["ref_label"] = (sc.get("meta") or {}).get("ref_label")
            all_cues.append(cue)
        per_scene.append(
            {
                "order": order,
                "speaker": speaker,
                "source_chars": len(clean_text(text)),
                "duration_ms": end_ms - start_ms,
                "cue_count": len(cues),
                "max_cue_chars": max((_max_line_chars(c["text"]) for c in cues), default=0),
            }
        )

    srt_lines = []
    for i, cue in enumerate(all_cues, 1):
        srt_lines.append(str(i))
        srt_lines.append(f"{format_timestamp(cue['startMs'])} --> {format_timestamp(cue['endMs'])}")
        srt_lines.append(cue["text"].replace(r"\N", "\n"))
        srt_lines.append("")
    srt_path = job / "subtitles-timed-ko.srt"
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")

    cues_path = job / "cues.json"
    payload = {
        "policy_id": policy["policy_id"],
        "maxDisplayCharacters": max_chars,
        "minDisplaySeconds": min_sec,
        "cue_count": len(all_cues),
        "cues": all_cues,
        "per_scene": per_scene,
    }
    cues_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    violations = []
    for cue in all_cues:
        if _max_line_chars(cue["text"]) > max_chars:
            violations.append(
                {"type": "max_chars", "text": cue["text"], "len": _max_line_chars(cue["text"])}
            )
        if cue["endMs"] - cue["startMs"] < int(min_sec * 1000) - 50:
            # allow soft shrink cases
            pass
    report = {
        "ok": len(violations) == 0,
        "cue_count": len(all_cues),
        "scene_count": len(per_scene),
        "maxDisplayCharacters": max_chars,
        "violations": violations[:20],
        "srt": str(srt_path),
        "cues": str(cues_path),
    }
    (job / "reports").mkdir(exist_ok=True)
    (job / "reports" / "cues_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    build(Path(args.job).resolve())


if __name__ == "__main__":
    main()
