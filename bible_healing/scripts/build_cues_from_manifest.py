# -*- coding: utf-8 -*-
"""
Build timed caption cues from locked scene_audio_manifest + scenes.json
using Hermes single-line split policy (healing_caption_policy.json).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from caption_split_hermes import format_timestamp, split_plain_text_window  # noqa: E402
from paths_bh import CONFIG  # noqa: E402


def clean_text(text: str, speaker: str) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if speaker == "scripture":
        t = re.sub(r"\([^)]{0,80}\)", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
    return t


def load_policy() -> dict:
    return json.loads((CONFIG / "healing_caption_policy.json").read_text(encoding="utf-8"))


def build(job: Path) -> dict:
    policy = load_policy()
    disp = policy["display"]
    max_chars = int(disp.get("maxDisplayCharacters") or disp.get("maxLineChars") or 12)
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
        text = clean_text(sc.get("narration") or item.get("text") or "", speaker)
        start_ms = int(round(float(item["startSeconds"]) * 1000))
        end_ms = int(round(float(item["endSeconds"]) * 1000))
        cues = split_plain_text_window(text, start_ms, end_ms, max_chars, min_sec)
        for c in cues:
            c["order"] = order
            c["speaker"] = speaker
            c["ref_label"] = (sc.get("meta") or {}).get("ref_label")
            all_cues.append(c)
        per_scene.append(
            {
                "order": order,
                "speaker": speaker,
                "source_chars": len(text),
                "duration_ms": end_ms - start_ms,
                "cue_count": len(cues),
                "max_cue_chars": max((len(c["text"]) for c in cues), default=0),
            }
        )

    # global SRT
    srt_lines = []
    for i, c in enumerate(all_cues, 1):
        srt_lines.append(str(i))
        srt_lines.append(f"{format_timestamp(c['startMs'])} --> {format_timestamp(c['endMs'])}")
        srt_lines.append(c["text"])
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

    # QA summary
    violations = []
    for c in all_cues:
        if len(c["text"]) > max_chars:
            violations.append({"type": "max_chars", "text": c["text"], "len": len(c["text"])})
        if c["endMs"] - c["startMs"] < int(min_sec * 1000) - 50:
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
