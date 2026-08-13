# -*- coding: utf-8 -*-
"""Pack a full Hermes job from script segments and voice defaults."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_EPISODE = "ep01_anxious_night"
_EPISODE_FROM_JOB_RE = re.compile(
    r"[/\\]runs[/\\]([^/\\]+)[/\\]hermes_jobs[/\\]", re.IGNORECASE
)


def load_voice_cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "voice_healing.yaml").read_text(encoding="utf-8"))


def speaker_entry(voice_cfg: dict, key: str) -> dict:
    """Copy yaml speaker fields, including audio_filter (never force empty)."""
    c = voice_cfg["speakers"][key]
    d = {
        "label": c["label"],
        "voice": c["voice"],
        "speed": c["speed"],
        "total_step": c["total_step"],
        "silence_duration": c["silence_duration"],
        "audio_filter": c.get("audio_filter", ""),
    }
    if c.get("max_chunk_length") is not None:
        d["max_chunk_length"] = c["max_chunk_length"]
    return d


def spk(key: str, voice_cfg: dict | None = None) -> dict:
    return speaker_entry(voice_cfg or load_voice_cfg(), key)


def scene_from_segment(segment: dict, order: int) -> dict:
    """Build one full-job scene while retaining timing/QA metadata."""
    meta = {
        "unit": segment["unit"],
        "speaker": segment["speaker"],
        "ref": segment.get("ref"),
        "ref_label": segment.get("ref_label"),
    }
    if segment.get("hook_phase") is not None:
        meta["hook_phase"] = segment["hook_phase"]
    return {
        "scene_id": segment["seg_id"],
        "order": order,
        "source_order": order,
        "chapter": 1,
        "title": segment.get("title") or segment["seg_id"],
        "outputMode": "image",
        "narration": segment["text"],
        "segments": [
            {
                "speaker": segment["speaker"],
                "text": segment["text"],
                "seg_id": f"{segment['seg_id']}_01",
                "ref": segment.get("ref"),
            }
        ],
        "image": f"scene_{order}_flow.jpg",
        "meta": meta,
    }


def infer_episode_from_job(job: Path) -> str | None:
    """Return episode id when job path looks like runs/<ep>/hermes_jobs/..."""
    m = _EPISODE_FROM_JOB_RE.search(str(Path(job)))
    return m.group(1) if m else None


def build_full_job(
    out: Path,
    *,
    episode: str = _DEFAULT_EPISODE,
    root: Path | None = None,
) -> dict:
    """Write scenes/voice_map/draft/job under ``out`` from episode script segments.

    Uses module-level ROOT (and load_voice_cfg/spk) when ``root`` is None so
    monkeypatched ROOT in tests keeps working.
    """
    base = Path(root) if root is not None else ROOT
    segs_path = base / "runs" / episode / "script_segments.json"
    segs = json.loads(segs_path.read_text(encoding="utf-8"))
    segs = [s for s in segs if not str(s.get("seg_id", "")).endswith("_rest")]
    if root is None:
        vc = load_voice_cfg()
        narr = spk("narrator", vc)
        scri = spk("scripture", vc)
    else:
        vc = yaml.safe_load(
            (base / "config" / "voice_healing.yaml").read_text(encoding="utf-8")
        )
        narr = speaker_entry(vc, "narrator")
        scri = speaker_entry(vc, "scripture")

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    scenes = [scene_from_segment(s, i) for i, s in enumerate(segs, 1)]

    vm = {
        "schema_version": "1.0",
        "engine": "supertonic3",
        "preview_approved": True,
        "notes": "bible_healing: narrator=여성 점잖음, scripture=말씀 보이스. 공유 금지.",
        "speakers": {"narrator": narr, "scripture": scri},
        "rules": {
            "narration_default_speaker": "narrator",
            "narrator_must_not_share_voice_with_characters": True,
        },
        "sample_lines": vc.get("sample_lines") or {},
    }
    (out / "scenes.json").write_text(
        json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "voice_map.json").write_text(
        json.dumps(vm, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    draft = {
        "title": "불안한 밤을 위한 말씀",
        "scenes": [
            {
                "order": sc["order"],
                "narration": sc["narration"],
                "outputMode": "image",
                "flowOutputMode": "image",
                "section": "main",
                "chapter": 1,
                "scene_id": sc["scene_id"],
                "title": sc["title"],
            }
            for sc in scenes
        ],
    }
    (out / "draft.json").write_text(
        json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "job.json").write_text(
        json.dumps(
            {
                "type": "bible_healing_full",
                "episode": episode,
                "scene_count": len(scenes),
                "chars": sum(len(s["text"]) for s in segs),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (out / "reports").mkdir(exist_ok=True)
    return {
        "ok": True,
        "job": str(out),
        "episode": episode,
        "scenes": len(scenes),
        "chars": sum(len(s["text"]) for s in segs),
    }


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description="Pack full Hermes job (scenes + voice_map) from script segments"
    )
    ap.add_argument(
        "--job",
        "--out",
        dest="job",
        default=None,
        help="Output job directory (default: runs/<episode>/hermes_jobs/full)",
    )
    ap.add_argument(
        "--episode",
        default=None,
        help=(
            "Episode id for script_segments "
            f"(default: infer from --job or {_DEFAULT_EPISODE})"
        ),
    )
    # Empty list when called as main() from tests; CLI passes sys.argv[1:].
    args = ap.parse_args([] if argv is None else list(argv))

    if args.job:
        out = Path(args.job)
        episode = args.episode or infer_episode_from_job(out) or _DEFAULT_EPISODE
    else:
        episode = args.episode or _DEFAULT_EPISODE
        out = ROOT / "runs" / episode / "hermes_jobs" / "full"

    # root=None → use module ROOT so monkeypatched tests still work.
    info = build_full_job(out, episode=episode, root=None)
    print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
