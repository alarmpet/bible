# -*- coding: utf-8 -*-
"""A/B: SuperTonic3 vs CosyVoice3 on the same three Korean sentences.

Does not overwrite production full-film renders.
Writes wavs + RTF report under D:\\bible_healing_ep01\\work\\cosyvoice3_ab.

    python modern/scripts/test_cosyvoice3_vs_supertonic3.py
    python modern/scripts/test_cosyvoice3_vs_supertonic3.py --skip-cosyvoice
    python modern/scripts/test_cosyvoice3_vs_supertonic3.py --skip-supertonic
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from paths import TTS_PYTHON, TTS_ROOT

SAMPLES = [
    {
        "id": "A_healing",
        "speaker": "narrator",
        "voice": "F5",
        "speed": 0.95,
        "text": "지친 하루 끝에 마주하는 깊은 평안의 시간입니다.",
    },
    {
        "id": "B_scripture",
        "speaker": "scripture",
        "voice": "M4",
        "speed": 0.95,
        "text": "여호와는 나의 목자시니 내게 부족함이 없으리로다.",
    },
    {
        "id": "C_comfort",
        "speaker": "narrator",
        "voice": "F5",
        "speed": 0.95,
        "text": "어두운 밤에도 빛은 항상 너를 향해 밝게 비추고 있단다.",
    },
]

OUT_ROOT = Path(r"D:\bible_healing_ep01\work\cosyvoice3_ab")


def _probe(wav: Path) -> float:
    import subprocess

    from paths import FFPROBE, FFMPEG

    probe = FFPROBE if FFPROBE.exists() else Path(str(FFMPEG).replace("ffmpeg.exe", "ffprobe.exe"))
    cmd = [
        str(probe if probe.exists() else "ffprobe"),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(wav),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float((r.stdout or "").strip())
    except ValueError:
        return 0.0


def run_supertonic(out_dir: Path) -> list[dict]:
    sys.path.insert(0, str(TTS_ROOT / "src"))
    from supertonic3_engine import Supertonic3Engine  # type: ignore

    engine = Supertonic3Engine(output_dir=out_dir)
    rows = []
    for sample in SAMPLES:
        wav = out_dir / f"{sample['id']}_supertonic3.wav"
        started = time.perf_counter()
        info = engine.synthesize_to_file(
            text=sample["text"],
            output_path=wav,
            voice=sample["voice"],
            lang="ko",
            speed=float(sample["speed"]),
            total_step=10 if sample["speaker"] == "scripture" else 8,
            silence_duration=0.25,
            max_chunk_length=90,
            verbose=False,
        )
        elapsed = time.perf_counter() - started
        duration = float(info.get("duration") or _probe(wav) or 0.0)
        rows.append(
            {
                "id": sample["id"],
                "engine": "supertonic3",
                "voice": sample["voice"],
                "text": sample["text"],
                "path": str(wav),
                "duration": round(duration, 3),
                "elapsed_seconds": round(elapsed, 3),
                "rtf": round(elapsed / duration, 3) if duration > 0 else None,
                "bytes": wav.stat().st_size if wav.exists() else 0,
            }
        )
        print(f"supertonic3 {sample['id']} dur={duration:.2f}s rtf={rows[-1]['rtf']}")
    return rows


def run_cosyvoice(out_dir: Path) -> list[dict]:
    from cosyvoice3_engine import CosyVoice3Engine, resolve_voice_spec, MODULE_ROOT

    engine = CosyVoice3Engine(output_dir=out_dir)
    rows = []
    for sample in SAMPLES:
        spec = resolve_voice_spec(sample["voice"], sample["speed"])
        ref = spec.get("ref_wav")
        if ref and not Path(ref).is_absolute():
            spec["ref_wav"] = str(MODULE_ROOT / ref)
        wav = out_dir / f"{sample['id']}_cosyvoice3.wav"
        started = time.perf_counter()
        info = engine.synthesize_to_file(
            text=sample["text"],
            output_path=wav,
            voice=sample["voice"],
            lang="ko",
            speed=float(sample["speed"]),
            total_step=10,
            silence_duration=0.25,
            max_chunk_length=90,
            verbose=True,
            ref_wav=spec.get("ref_wav"),
            instruct=spec.get("instruct"),
        )
        elapsed = time.perf_counter() - started
        duration = float(info.get("duration") or _probe(wav) or 0.0)
        rows.append(
            {
                "id": sample["id"],
                "engine": "cosyvoice3",
                "voice": sample["voice"],
                "text": sample["text"],
                "path": str(wav),
                "duration": round(duration, 3),
                "elapsed_seconds": round(elapsed, 3),
                "rtf": info.get("rtf") or (round(elapsed / duration, 3) if duration > 0 else None),
                "bytes": wav.stat().st_size if wav.exists() else 0,
                "mode": info.get("mode"),
            }
        )
        print(f"cosyvoice3 {sample['id']} dur={duration:.2f}s rtf={rows[-1]['rtf']}")
    return rows


def write_markdown(report: dict, dest: Path) -> None:
    lines = [
        "# CosyVoice3 vs SuperTonic3 A/B",
        "",
        "Production engine remains **SuperTonic3**. CosyVoice3 is an opt-in CPU test.",
        "",
        "| id | engine | voice | duration_s | elapsed_s | RTF | bytes |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for row in report.get("rows") or []:
        lines.append(
            f"| {row['id']} | {row['engine']} | {row['voice']} | "
            f"{row.get('duration')} | {row.get('elapsed_seconds')} | "
            f"{row.get('rtf')} | {row.get('bytes')} |"
        )
    lines.extend(["", "## Sentences", ""])
    for sample in SAMPLES:
        lines.append(f"- **{sample['id']}** ({sample['voice']}): {sample['text']}")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-cosyvoice", action="store_true")
    ap.add_argument("--skip-supertonic", action="store_true")
    ap.add_argument("--out", default=str(OUT_ROOT))
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    errors: list[str] = []
    if not args.skip_supertonic:
        if not TTS_PYTHON.exists():
            errors.append(f"SuperTonic python missing: {TTS_PYTHON}")
        else:
            try:
                rows.extend(run_supertonic(out_dir))
            except Exception as exc:
                errors.append(f"supertonic3: {type(exc).__name__}: {exc}")
    if not args.skip_cosyvoice:
        try:
            rows.extend(run_cosyvoice(out_dir))
        except Exception as exc:
            errors.append(f"cosyvoice3: {type(exc).__name__}: {exc}")
    report = {
        "ok": not errors and bool(rows),
        "production_engine": "supertonic3",
        "test_engine": "cosyvoice3",
        "rows": rows,
        "errors": errors,
        "out_dir": str(out_dir),
    }
    (out_dir / "ab_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = Path(__file__).resolve().parents[2] / "docs" / "cosyvoice3_benchmark.md"
    write_markdown(report, md)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
