# -*- coding: utf-8 -*-
"""
Build dual-speaker episode script from themes.yaml + verse DB + narration bank.

Produces:
  runs/<ep>/episode_manifest.json
  runs/<ep>/script_segments.json
  runs/<ep>/script_readable.md
  runs/<ep>/verses_used.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths_bh import CONFIG, DATA, episode_dir  # noqa: E402
from verse_lib import get_label_ko, get_text, get_verses  # noqa: E402


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def clean(s: str) -> str:
    return " ".join((s or "").split())


def expand_unit(pick: dict, bank_unit: dict) -> list[dict]:
    uid = pick["id"]
    ref = pick["ref"]
    scripture = get_text(ref)
    label = pick.get("label") or get_label_ko(ref)
    title = bank_unit.get("title") or label
    segs: list[dict] = []

    segs.append(
        {
            "seg_id": f"{uid}_n0",
            "unit": uid,
            "speaker": "narrator",
            "ref": None,
            "text": clean(bank_unit["before"]),
            "title": title,
        }
    )
    segs.append(
        {
            "seg_id": f"{uid}_s0",
            "unit": uid,
            "speaker": "scripture",
            "ref": ref,
            "ref_label": label,
            "text": scripture,
            "title": title,
        }
    )
    if bank_unit.get("mid"):
        segs.append(
            {
                "seg_id": f"{uid}_n_mid",
                "unit": uid,
                "speaker": "narrator",
                "ref": None,
                "text": clean(bank_unit["mid"]),
                "title": title,
            }
        )
    segs.append(
        {
            "seg_id": f"{uid}_n1",
            "unit": uid,
            "speaker": "narrator",
            "ref": None,
            "text": clean(bank_unit["after"]),
            "title": title,
        }
    )
    return segs


def maybe_rest(uid: str, rest_map: dict | None, title: str) -> dict | None:
    if not rest_map or uid not in rest_map:
        return None
    return {
        "seg_id": f"{uid}_rest",
        "unit": uid,
        "speaker": "narrator",
        "ref": None,
        "text": clean(rest_map[uid]),
        "title": f"{title} · 쉼",
    }


def build(episode_id: str) -> Path:
    themes = load_yaml(CONFIG / "themes.yaml")
    if episode_id not in themes["episodes"]:
        raise SystemExit(f"Unknown episode: {episode_id}")
    ep = themes["episodes"][episode_id]

    bank_path = DATA / "narration_banks" / f"{episode_id}.yaml"
    if not bank_path.exists():
        raise SystemExit(f"Missing narration bank: {bank_path}")
    bank = load_yaml(bank_path)

    rest_path = DATA / "narration_banks" / "ep01_rest_layer.yaml"
    rest_map = None
    if episode_id == "ep01_anxious_night" and rest_path.exists():
        rest_map = load_yaml(rest_path).get("rests") or {}

    segments: list[dict] = []
    for i, row in enumerate(bank["opening"], 1):
        segments.append(
            {
                "seg_id": f"open_{i:02d}",
                "unit": "opening",
                "speaker": row["speaker"],
                "ref": None,
                "text": clean(row["text"]),
                "title": "오프닝",
            }
        )

    verses_used = []
    for pick in ep["verse_picks"]:
        uid = pick["id"]
        if uid not in bank["units"]:
            raise SystemExit(f"Unit {uid} missing in narration bank")
        segs = expand_unit(pick, bank["units"][uid])
        title = bank["units"][uid].get("title") or pick.get("label") or uid
        rest = maybe_rest(uid, rest_map, title)
        if rest:
            segs.append(rest)
        segments.extend(segs)
        for v in get_verses(pick["ref"]):
            verses_used.append(v)

    for i, row in enumerate(bank["closing"], 1):
        segments.append(
            {
                "seg_id": f"close_{i:02d}",
                "unit": "closing",
                "speaker": row["speaker"],
                "ref": None,
                "text": clean(row["text"]),
                "title": "클로징",
            }
        )

    out_dir = episode_dir(episode_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "script_segments.json").write_text(
        json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "verses_used.json").write_text(
        json.dumps(verses_used, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        f"# {ep['title_ko']}",
        "",
        f"theme: {ep['theme']} · target: {ep['target_minutes']}분",
        "",
    ]
    for s in segments:
        sp = s["speaker"]
        head = f"### [{sp}]"
        if s.get("ref_label"):
            head += f" {s['ref_label']}"
        elif s.get("title"):
            head += f" {s['title']}"
        lines.append(head)
        lines.append(s["text"])
        lines.append("")
    (out_dir / "script_readable.md").write_text("\n".join(lines), encoding="utf-8")

    total_chars = sum(len(s["text"]) for s in segments)
    manifest = {
        "episode_id": episode_id,
        "title_ko": ep["title_ko"],
        "theme": ep["theme"],
        "target_minutes": ep["target_minutes"],
        "tolerance": [80, 120],
        "translation": "KRV",
        "segment_count": len(segments),
        "unit_count": len(ep["verse_picks"]),
        "total_chars": total_chars,
        "status": "draft",
        "voice_config": "config/voice_healing.yaml",
        "narration_bank": str(bank_path.relative_to(bank_path.parents[2])),
    }
    (out_dir / "episode_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "ok": True,
                "episode": episode_id,
                "segments": len(segments),
                "total_chars": total_chars,
                "out": str(out_dir),
            },
            ensure_ascii=False,
        )
    )
    return out_dir


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", default="ep01_anxious_night")
    args = ap.parse_args()
    build(args.episode)


if __name__ == "__main__":
    main()
