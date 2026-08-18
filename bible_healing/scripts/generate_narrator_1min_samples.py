# -*- coding: utf-8 -*-
"""Ten ~1 min female healing-narrator samples. SuperTonic3 only. F1/F2/F4/F5."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from generate_pastor_1min_samples import (  # noqa: E402
    OUT as _PASTOR_OUT,
    apply_af,
    concat_units,
    load_engine,
    pastor_af,
    probe_duration,
)
from sanitize_script import sanitize_script  # noqa: E402
from scripture_tts_prep import split_into_speech_units  # noqa: E402
from trim_tts_padding import trim_engine_padding  # noqa: E402
from tts_assembly import assembly_gap_seconds, load_assembly_policy  # noqa: E402

OUT = _PASTOR_OUT.parent / "narrator_1min_20260816"

NARRATION = (
    "오늘 밤 모든 답을 찾지 않아도 됩니다. 편하다면 어깨의 힘만 조금 내려놓으세요. "
    "지금은 무언가를 해내지 않아도 됩니다. 듣기만 해도 괜찮습니다. "
    "문제가 남아 있어도, 그 한가운데서 숨을 맡길 곳이 있습니다. "
    "해결되지 않은 목록을 잠시 옆에 두어도 됩니다. "
    "목록이 사라지지 않아도, 당신은 눈을 감을 자격이 있습니다. "
    "완벽하지 않은 하루의 끝에도 쉼은 허락됩니다. 당신은 혼자가 아닙니다. "
    "손을 배에 얹고, 배가 위로 올라갔다 내려가는 움직임만 느껴 보세요. "
    "들이쉴 때 어깨가 올라가면, 내쉴 때 툭 내려놓습니다. "
    "아직 오지 않은 대화를 연습하지 않아도 됩니다. "
    "당신은 오늘도 애썼습니다. 그 애씀을 인정하는 일이 회복의 문입니다. "
    "서두르지 마세요. 밤은 아직 당신을 위해 남아 있습니다."
)

# F3 forbidden. Same 10-slot A/B shape as the male pastor set.
VARIANTS = [
    {
        "id": "01_lock_F5",
        "label": "현재 lock (대조군)",
        "voice": "F5",
        "speed": 0.95,
        "step": 8,
        "pitch": 0,
        "lowpass": 0,
        "g180": 0.0,
        "g120": 0.0,
        "note": "본편 기본. 필터 없음.",
    },
    {
        "id": "02_F5_warm",
        "label": "F5 따뜻한 힐링",
        "voice": "F5",
        "speed": 0.95,
        "step": 8,
        "pitch": 0,
        "lowpass": 6500,
        "g180": 2.5,
        "g120": 1.5,
        "note": "피치 없이 저역만 보강.",
    },
    {
        "id": "03_F5_slow",
        "label": "F5 느린 위로",
        "voice": "F5",
        "speed": 0.90,
        "step": 8,
        "pitch": 0,
        "lowpass": 6000,
        "g180": 2.0,
        "g120": 1.0,
        "note": "속도 0.90. 한 문장씩 천천히.",
    },
    {
        "id": "04_F5_step10",
        "label": "F5 안정 step10",
        "voice": "F5",
        "speed": 0.95,
        "step": 10,
        "pitch": 0,
        "lowpass": 0,
        "g180": 0.0,
        "g120": 0.0,
        "note": "step 10. 억양 덜 튀게.",
    },
    {
        "id": "05_F4_gentle",
        "label": "F4 부드러운 안내",
        "voice": "F4",
        "speed": 0.95,
        "step": 8,
        "pitch": 0,
        "lowpass": 6500,
        "g180": 2.0,
        "g120": 1.0,
        "note": "F4 기본 + 약한 온기.",
    },
    {
        "id": "06_F4_slow_warm",
        "label": "F4 느리고 따뜻함",
        "voice": "F4",
        "speed": 0.90,
        "step": 10,
        "pitch": -4,
        "lowpass": 5500,
        "g180": 3.0,
        "g120": 2.0,
        "note": "조금 낮고 느린 F4.",
    },
    {
        "id": "07_F2_clear",
        "label": "F2 또렷한 내레이션",
        "voice": "F2",
        "speed": 0.95,
        "step": 8,
        "pitch": 0,
        "lowpass": 0,
        "g180": 0.0,
        "g120": 0.0,
        "note": "F2 원음. 더 또렷한 쪽.",
    },
    {
        "id": "08_F2_soft",
        "label": "F2 부드러운 밤",
        "voice": "F2",
        "speed": 0.92,
        "step": 8,
        "pitch": -3,
        "lowpass": 6000,
        "g180": 2.0,
        "g120": 1.5,
        "note": "F2를 낮고 부드럽게.",
    },
    {
        "id": "09_F5_less_thin",
        "label": "F5 얇음 완화",
        "voice": "F5",
        "speed": 0.95,
        "step": 8,
        "pitch": -4,
        "lowpass": 6000,
        "g180": 3.0,
        "g120": 2.0,
        "note": "남성 09와 같은 레버. 피치 -4 + 저역.",
    },
    {
        "id": "10_F1_deeper",
        "label": "F1 중저음 여성",
        "voice": "F1",
        "speed": 0.93,
        "step": 10,
        "pitch": -6,
        "lowpass": 5500,
        "g180": 3.0,
        "g120": 2.0,
        "note": "가장 낮은 여성 후보.",
    },
]


def narrator_af(variant: dict) -> str:
    if int(variant.get("lowpass") or 0) <= 0 and abs(float(variant.get("pitch") or 0)) < 0.01:
        return ""
    pitch = float(variant.get("pitch") or 0)
    if abs(pitch) < 0.01:
        parts = [
            "aresample=24000",
            "highpass=f=70",
            f"lowpass=f={int(variant['lowpass'])}",
        ]
        if abs(float(variant["g180"])) > 0.01:
            parts.append(f"equalizer=f=180:t=q:w=1:g={variant['g180']}")
        if abs(float(variant["g120"])) > 0.01:
            parts.append(f"equalizer=f=120:t=q:w=1:g={variant['g120']}")
        return ",".join(parts)
    return pastor_af(pitch, variant["lowpass"] or 7000, variant["g180"], variant["g120"])


def units_for_narrator() -> list[str]:
    spoken = sanitize_script(NARRATION).tts
    units = split_into_speech_units(spoken, max_len=130)
    if not units:
        raise SystemExit("empty narrator units")
    return units


def synth_variant(engine, variant: dict, units: list[str], work: Path) -> dict:
    vdir = work / variant["id"]
    vdir.mkdir(parents=True, exist_ok=True)
    pieces: list[Path] = []
    af = narrator_af(variant)
    for i, unit in enumerate(units):
        raw = vdir / f"u{i:02d}.raw.wav"
        dest = vdir / f"u{i:02d}.wav"
        engine.synthesize_to_file(
            text=unit,
            output_path=raw,
            voice=variant["voice"],
            lang="ko",
            speed=float(variant["speed"]),
            total_step=int(variant["step"]),
            silence_duration=0.24,
            max_chunk_length=130,
            verbose=False,
        )
        if af:
            apply_af(raw, dest, af)
        else:
            dest.write_bytes(raw.read_bytes())
        trim_engine_padding(dest)
        if raw.exists() and raw.resolve() != dest.resolve():
            raw.unlink(missing_ok=True)
        pieces.append(dest)
    out = OUT / f"{variant['id']}.wav"
    policy = load_assembly_policy(
        {"tts": {"assembly_gap_same_speaker": 0.05, "assembly_gap_scene": 0.6}}
    )
    gap = assembly_gap_seconds("narrator", "narrator", policy)
    concat_units(pieces, out, gap)
    dur = probe_duration(out)
    rec = {
        **variant,
        "path": str(out),
        "duration": round(dur, 2),
        "units": len(pieces),
        "filter": af,
    }
    print(f"{variant['id']}: {dur:.1f}s -> {out.name}", flush=True)
    return rec


def write_index(rows: list[dict], units: list[str]) -> None:
    lines = [
        "# 여성 힐링 내레이터 1분 샘플 10종",
        "",
        "엔진: SuperTonic3. 화자: F1 / F2 / F4 / F5만. F3 없음. 새 TTS 없음.",
        "대본: 본편 내레이션 문체. 문장 단위 합성 후 트림·조립.",
        "남성 성경 목소리는 이미 `09_M4_less_thin`으로 lock 고정.",
        "",
        "## 대본",
        "",
        sanitize_script(NARRATION).display,
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
            "고를 때: 얇은 기계음, 너무 높은 톤, 너무 느린 늘어짐, 밤에 듣기 편한지.",
            "본편 lock을 바꾸려면 고른 id를 알려 주세요.",
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
    units = units_for_narrator()
    print(f"units={len(units)} chars={sum(len(u) for u in units)}", flush=True)
    engine = load_engine(work)
    rows = [synth_variant(engine, variant, units, work) for variant in VARIANTS]
    write_index(rows, units)
    print("done", OUT, flush=True)


if __name__ == "__main__":
    main()
