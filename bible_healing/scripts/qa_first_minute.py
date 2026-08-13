# -*- coding: utf-8 -*-
"""CLI QA for the locked first-minute hook."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from first_minute import summarize_first_minute


def evaluate_job(job: Path) -> dict:
    manifest_path = job / "scene_audio_manifest.json"
    scenes_path = job / "scenes.json"
    if not manifest_path.exists():
        raise SystemExit(f"missing locked manifest: {manifest_path}")
    if not scenes_path.exists():
        raise SystemExit(f"missing scenes: {scenes_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scenes = json.loads(scenes_path.read_text(encoding="utf-8"))
    try:
        summary = summarize_first_minute(manifest, scenes)
    except ValueError as exc:
        summary = {"violations": [str(exc)]}

    report = {
        "ok": not summary.get("violations"),
        **summary,
        "job": str(job),
        "manifest": str(manifest_path),
    }
    reports = job / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "qa_first_minute.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    report = evaluate_job(Path(args.job).resolve())
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
