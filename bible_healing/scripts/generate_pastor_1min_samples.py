# -*- coding: utf-8 -*-
"""Ten ~1 min mid-low pastor scripture samples. SuperTonic3 only. M1/M4 only."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

_BH = Path(__file__).resolve().parents[1]
_SCRIPTS = Path(__file__).resolve().parent
_MODERN = _BH.parent / "modern" / "scripts"
for p in (_SCRIPTS, _MODERN):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from apply_audio_filter import ffmpeg_bin  # noqa: E402
from sanitize_script import sanitize_script  # noqa: E402
from scripture_tts_prep import split_into_speech_units  # noqa: E402
from trim_tts_padding import trim_engine_padding  # noqa: E402
from tts_assembly import assembly_gap_seconds, load_assembly_policy  # noqa: E402
from paths import TTS_ROOT  # noqa: E402
from supertonic3_http import (  # noqa: E402
    HttpSupertonicEngine,
    resolve_supertonic_http_url,
    server_is_up,
)

OUT = _BH / "runs" / "ep01_anxious_night" / "voice_ab" / "pastor_1min_20260815"

PSALM23 = (
    "여호와는 나의 목자시니 내가 부족함이 없으리로다 "
    "그가 나를 푸른 초장에 누이시며 쉴만한 물 가으로 인도하시는도다 "
    "내 영혼을 소생시키시고 자기 이름을 위하여 의의 길로 인도하시는도다 "
    "내가 사망의 음침한 골짜기로 다닐지라도 해를 두려워하지 않을것은 "
    "주께서 나와 함께 하심이라 주의 지팡이와 막대기가 나를 안위하시나이다 "
    "주께서 내 원수의 목전에서 내게 상을 베푸시고 기름으로 내 머리에 바르셨으니 "
    "내 잔이 넘치나이다 나의 평생에 선하심과 인자하심이 정녕 나를 따르리니 "
    "내가 여호와의 집에 영원히 거하리로다"
)

# Allowed production males only. M2/M3/M5 never used.
VARIANTS = [
    {
        "id": "01_lock_M4",
        "label": "현재 lock (대조군)",
        "voice": "M4",
        "speed": 0.95,
        "step": 10,
        "pitch": -14,
        "lowpass": 7000,
        "g180": 2.5,
        "g120": 0.0,
        "note": "본편 기본. 화난 억양 문제가 나온 설정.",
    },
    {
        "id": "02_M4_deeper",
        "label": "M4 더 낮은 목회자",
        "voice": "M4",
        "speed": 0.95,
        "step": 10,
        "pitch": -18,
        "lowpass": 6500,
        "g180": 3.5,
        "g120": 2.0,
        "note": "피치 -18, 120·180Hz 보강.",
    },
    {
        "id": "03_M4_slow_sermon",
        "label": "M4 느린 설교",
        "voice": "M4",
        "speed": 0.90,
        "step": 10,
        "pitch": -16,
        "lowpass": 6000,
        "g180": 3.0,
        "g120": 1.5,
        "note": "속도 0.90. 한 절 한 절 짚는 톤.",
    },
    {
        "id": "04_M4_chapel_warm",
        "label": "M4 따뜻한 예배당",
        "voice": "M4",
        "speed": 0.95,
        "step": 10,
        "pitch": -14,
        "lowpass": 5000,
        "g180": 4.0,
        "g120": 2.5,
        "note": "고음 자르고 저역만 살림.",
    },
    {
        "id": "05_M4_steady12",
        "label": "M4 안정 step12",
        "voice": "M4",
        "speed": 0.88,
        "step": 12,
        "pitch": -14,
        "lowpass": 7000,
        "g180": 2.5,
        "g120": 1.0,
        "note": "step 12 + 느린 속도. 억양 덜 튀게.",
    },
    {
        "id": "06_M4_midnight",
        "label": "M4 심야 기도회",
        "voice": "M4",
        "speed": 0.92,
        "step": 10,
        "pitch": -20,
        "lowpass": 4500,
        "g180": 3.0,
        "g120": 3.0,
        "note": "가장 낮고 어두운 쪽.",
    },
    {
        "id": "07_M1_pulpit",
        "label": "M1 중저음 강단",
        "voice": "M1",
        "speed": 0.95,
        "step": 10,
        "pitch": -12,
        "lowpass": 6500,
        "g180": 2.5,
        "g120": 1.5,
        "note": "M1 자체 베이스 + 약한 피치.",
    },
    {
        "id": "08_M1_old_minister",
        "label": "M1 연세 있는 목사",
        "voice": "M1",
        "speed": 0.90,
        "step": 10,
        "pitch": -16,
        "lowpass": 5500,
        "g180": 3.5,
        "g120": 2.5,
        "note": "느리고 낮음. 나이 든 목회자.",
    },
    {
        "id": "09_M4_less_thin",
        "label": "M4 얇음 완화",
        "voice": "M4",
        "speed": 0.95,
        "step": 10,
        "pitch": -10,
        "lowpass": 6000,
        "g180": 3.0,
        "g120": 2.0,
        "note": "피치를 덜 내려 기계음·얇음을 줄임.",
    },
    {
        "id": "10_M4_very_low",
        "label": "M4 최저음 목사",
        "voice": "M4",
        "speed": 0.93,
        "step": 12,
        "pitch": -22,
        "lowpass": 4800,
        "g180": 3.5,
        "g120": 3.5,
        "note": "체감 가장 낮음. 너무 느리면 탈락.",
    },
]


def pastor_af(pitch: float, lowpass: int, g180: float, g120: float) -> str:
    rate = 1.0 + float(pitch) / 100.0
    parts = [
        "aresample=24000",
        f"asetrate=24000*{rate:.4g}",
        "aresample=24000",
        "highpass=f=60",
        f"lowpass=f={int(lowpass)}",
        f"equalizer=f=180:t=q:w=1:g={g180}",
    ]
    if abs(float(g120)) > 0.01:
        parts.append(f"equalizer=f=120:t=q:w=1:g={g120}")
    return ",".join(parts)


def apply_af(src: Path, dst: Path, af: str) -> None:
    cmd = [
        ffmpeg_bin(),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-af",
        af,
        "-c:a",
        "pcm_s16le",
        str(dst),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not dst.exists() or dst.stat().st_size <= 0:
        raise RuntimeError((res.stderr or res.stdout or "ffmpeg filter failed").strip())


def probe_duration(path: Path) -> float:
    from paths import FFPROBE

    probe = str(FFPROBE) if FFPROBE.exists() else shutil.which("ffprobe") or "ffprobe"
    r = subprocess.run(
        [
            probe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    try:
        return float((r.stdout or "").strip())
    except ValueError:
        return -1.0


def load_engine(out_dir: Path):
    url = resolve_supertonic_http_url(env=os.environ, lock=None)
    deadline = time.time() + 180
    while time.time() < deadline:
        if server_is_up(url, timeout=1.0):
            print(f"tts via http {url}")
            return HttpSupertonicEngine(base_url=url, output_dir=out_dir)
        time.sleep(3)
    print(f"tts http down ({url}), in-process fallback")
    sys.path.insert(0, str(TTS_ROOT / "src"))
    from supertonic3_engine import Supertonic3Engine  # type: ignore

    return Supertonic3Engine(output_dir=out_dir)


def concat_units(paths: list[Path], out: Path, gap: float) -> None:
    from tts_multi_voice import concat_wavs

    gaps = [gap] * (len(paths) - 1) if len(paths) > 1 else None
    if not concat_wavs(paths, out, gaps=gaps, sample_rate=24000):
        raise RuntimeError(f"concat failed: {out.name}")


def units_for_scripture() -> list[str]:
    spoken = sanitize_script(PSALM23).tts
    units = split_into_speech_units(spoken, max_len=90)
    if not units:
        raise SystemExit("empty scripture units")
    return units


def synth_variant(engine, variant: dict, units: list[str], work: Path) -> dict:
    vdir = work / variant["id"]
    vdir.mkdir(parents=True, exist_ok=True)
    pieces: list[Path] = []
    af = pastor_af(variant["pitch"], variant["lowpass"], variant["g180"], variant["g120"])
    for i, unit in enumerate(units):
        raw = vdir / f"u{i:02d}.raw.wav"
        filt = vdir / f"u{i:02d}.wav"
        engine.synthesize_to_file(
            text=unit,
            output_path=raw,
            voice=variant["voice"],
            lang="ko",
            speed=float(variant["speed"]),
            total_step=int(variant["step"]),
            silence_duration=0.25,
            max_chunk_length=90,
            verbose=False,
        )
        apply_af(raw, filt, af)
        trim_engine_padding(filt)
        if raw.exists():
            raw.unlink(missing_ok=True)
        pieces.append(filt)
    out = OUT / f"{variant['id']}.wav"
    policy = load_assembly_policy(
        {"tts": {"assembly_gap_same_speaker": 0.05, "assembly_gap_scene": 0.6}}
    )
    gap = assembly_gap_seconds("scripture", "scripture", policy)
    concat_units(pieces, out, gap)
    dur = probe_duration(out)
    rec = {
        **variant,
        "path": str(out),
        "duration": round(dur, 2),
        "units": len(pieces),
        "filter": af,
    }
    print(f"{variant['id']}: {dur:.1f}s -> {out.name}")
    return rec


def write_index(rows: list[dict], units: list[str]) -> None:
    lines = [
        "# 목회자 스타일 성경 낭독 1분 샘플 10종",
        "",
        "엔진: SuperTonic3. 화자: M1 / M4만. M2·M3·M5 없음. 새 TTS 없음.",
        "대본: 시편 23편 (표제 제거, 느낌표 없음, 절 단위 합성 후 트림·조립).",
        "",
        "## 대본",
        "",
        sanitize_script(PSALM23).display,
        "",
        "## 샘플",
        "",
        "| # | 파일 | 보이스 | speed | step | pitch | 길이 | 설명 |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['id'][:2]} | `{Path(row['path']).name}` | {row['voice']} | "
            f"{row['speed']} | {row['step']} | {row['pitch']} | {row['duration']}s | {row['label']} |"
        )
    lines.extend(["", "## 메모", ""])
    for row in rows:
        lines.append(f"- **{row['id']}** — {row['note']}")
    lines.extend(
        [
            "",
            "고를 때: 화난 억양, 얇은 기계음, 너무 느린 늘어짐, 목회자처럼 낮은지.",
            "본편 lock을 바꾸려면 고른 id를 알려 주세요. 전량 재합성됩니다.",
            "",
        ]
    )
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT / "samples.json").write_text(
        json.dumps({"ok": True, "units": units, "samples": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    work = OUT / "_work"
    work.mkdir(exist_ok=True)
    units = units_for_scripture()
    print(f"units={len(units)} chars={sum(len(u) for u in units)}")
    engine = load_engine(work)
    rows = []
    for variant in VARIANTS:
        rows.append(synth_variant(engine, variant, units, work))
    write_index(rows, units)
    print("done", OUT)


if __name__ == "__main__":
    main()
