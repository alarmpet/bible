# -*- coding: utf-8 -*-
"""Single full-media (본편) pipeline entrypoint.

Runs preflight → job rebuild → TTS → provenance → authoritative audio → ASS →
render → postflight via subprocess. Stops on the first nonzero exit.
Does not reimplement step logic; only orchestrates existing scripts.

Usage (from module root):
  python bible_healing/scripts/run_full_media_pipeline.py \\
    --job bible_healing/runs/ep01_anxious_night/hermes_jobs/full
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

_SCRIPTS = Path(__file__).resolve().parent
_MODULE_ROOT = _SCRIPTS.parents[1]
_MODERN_SCRIPTS = _MODULE_ROOT / "modern" / "scripts"
_DEFAULT_WORK_ROOT = Path(r"D:\bible_healing_ep01\work\pipeline")
_DEFAULT_FINAL_MP4 = Path(
    r"D:\bible_healing_ep01\final\deploy-ep01-authoritative-audio-aligned.mp4"
)

if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

try:
    from paths_bh import TTS_PYTHON as _TTS_PYTHON_PATH
except Exception:  # pragma: no cover - paths_bh always present in tree
    _TTS_PYTHON_PATH = None


def _resolve_tts_python() -> str:
    if _TTS_PYTHON_PATH is not None:
        p = Path(_TTS_PYTHON_PATH)
        if p.is_file():
            return str(p)
    return sys.executable


def build_steps(
    job: Path,
    *,
    python: str,
    tts_python: str,
    final_mp4: Path,
) -> list[tuple[int, str, list[str]]]:
    """Return ordered (step_number, name, argv) triples for the full pipeline."""
    job_s = str(job)
    return [
        (
            1,
            "media_rules_preflight",
            # Config/lock only (speakers, lock voices, D:, background, skip-existing).
            # Job scenes/ASS/provenance/auth WAV/stale voice_map are later steps.
            [python, str(_SCRIPTS / "media_rules_preflight.py"), "--job", job_s],
        ),
        (
            2,
            "build_full_job",
            [
                python,
                str(_SCRIPTS / "build_full_job.py"),
                "--job",
                job_s,
            ],
        ),
        (
            3,
            "tts_multi_voice",
            # Never pass --skip-existing (lock + provenance forbid stale WAVs).
            [
                tts_python,
                str(_MODERN_SCRIPTS / "tts_multi_voice.py"),
                "--job",
                job_s,
            ],
        ),
        (
            4,
            "verify_voice_provenance",
            [python, str(_SCRIPTS / "verify_voice_provenance.py"), "--job", job_s],
        ),
        (
            5,
            "rebuild_authoritative_full_audio",
            [
                python,
                str(_SCRIPTS / "rebuild_authoritative_full_audio.py"),
                "--job",
                job_s,
            ],
        ),
        (
            6,
            "verify_authoritative_audio",
            [
                python,
                str(_SCRIPTS / "verify_authoritative_audio.py"),
                "--job",
                job_s,
            ],
        ),
        (
            7,
            "build_full_audio_aligned_ass",
            [
                python,
                str(_SCRIPTS / "build_full_audio_aligned_ass.py"),
                "--job",
                job_s,
            ],
        ),
        (
            8,
            "ass_qa",
            [
                python,
                str(_SCRIPTS / "build_full_audio_aligned_ass.py"),
                "--job",
                job_s,
                "--qa-only",
            ],
        ),
        (
            9,
            "render_authoritative_full",
            [
                python,
                str(_SCRIPTS / "render_authoritative_full.py"),
                "--job",
                job_s,
                "--output",
                str(final_mp4),
            ],
        ),
        (
            10,
            "media_rules_postflight",
            [
                python,
                str(_SCRIPTS / "media_rules_postflight.py"),
                str(final_mp4),
                "--job",
                job_s,
            ],
        ),
    ]


def write_step_report(work_root: Path, payload: dict) -> Path:
    work_root.mkdir(parents=True, exist_ok=True)
    path = work_root / f"step_{int(payload['step']):02d}_{payload['name']}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run_pipeline(
    job: Path,
    *,
    work_root: Path,
    run_cmd: Callable[..., object] | None = None,
    final_mp4: Path | None = None,
    python_exe: str | None = None,
    tts_python_exe: str | None = None,
) -> dict:
    """Execute steps 1–10; halt on first nonzero exit. Write per-step JSON reports."""
    job = Path(job).resolve()
    work_root = Path(work_root)
    final = Path(final_mp4) if final_mp4 is not None else _DEFAULT_FINAL_MP4
    python = python_exe or sys.executable
    tts_python = tts_python_exe or _resolve_tts_python()
    runner = run_cmd or subprocess.run

    steps = build_steps(
        job,
        python=python,
        tts_python=tts_python,
        final_mp4=final,
    )
    completed: list[dict] = []
    for step_num, name, cmd in steps:
        # Guardrail: TTS must never receive skip-existing from this orchestrator.
        if name == "tts_multi_voice" and "--skip-existing" in cmd:
            raise RuntimeError("orchestrator must not pass --skip-existing to TTS")

        started = datetime.now(timezone.utc).isoformat()
        completed_proc = runner(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        returncode = int(getattr(completed_proc, "returncode", 1))
        stdout = getattr(completed_proc, "stdout", "") or ""
        stderr = getattr(completed_proc, "stderr", "") or ""
        ok = returncode == 0
        payload = {
            "step": step_num,
            "name": name,
            "cmd": [str(c) for c in cmd],
            "returncode": returncode,
            "ok": ok,
            "started_at": started,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "stdout_tail": stdout[-4000:],
            "stderr_tail": stderr[-4000:],
            "job": str(job),
        }
        report_path = write_step_report(work_root, payload)
        payload["report"] = str(report_path)
        completed.append(payload)
        if not ok:
            summary = {
                "ok": False,
                "failed_step": step_num,
                "failed_name": name,
                "returncode": returncode,
                "completed_steps": len(completed),
                "job": str(job),
                "work_root": str(work_root),
                "final_mp4": str(final),
                "steps": completed,
            }
            summary_path = work_root / "pipeline_summary.json"
            work_root.mkdir(parents=True, exist_ok=True)
            summary_path.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return summary

    summary = {
        "ok": True,
        "failed_step": None,
        "failed_name": None,
        "returncode": 0,
        "completed_steps": len(completed),
        "job": str(job),
        "work_root": str(work_root),
        "final_mp4": str(final),
        "steps": completed,
    }
    work_root.mkdir(parents=True, exist_ok=True)
    (work_root / "pipeline_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Single full-media pipeline entrypoint (stop on first failure)"
    )
    ap.add_argument(
        "--job",
        required=True,
        help="Hermes full job dir (e.g. bible_healing/runs/.../hermes_jobs/full)",
    )
    ap.add_argument(
        "--work-root",
        default=str(_DEFAULT_WORK_ROOT),
        help="Directory for per-step JSON reports (default: D:\\bible_healing_ep01\\work\\pipeline)",
    )
    ap.add_argument(
        "--final-mp4",
        default=str(_DEFAULT_FINAL_MP4),
        help="Expected final MP4 path for render + postflight",
    )
    args = ap.parse_args(list(argv) if argv is not None else None)

    summary = run_pipeline(
        Path(args.job),
        work_root=Path(args.work_root),
        final_mp4=Path(args.final_mp4),
    )
    print(json.dumps({k: summary[k] for k in summary if k != "steps"}, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
