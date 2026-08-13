# -*- coding: utf-8 -*-
"""
Generate 10 female + 10 male SuperTonic samples for listening pick.
Uses F1–F5 / M1–M5 with speed & silence variants (10 each).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# module modern paths
MODERN_SCRIPTS = Path(__file__).resolve().parents[2] / "modern" / "scripts"
sys.path.insert(0, str(MODERN_SCRIPTS))
from paths import TTS_ROOT  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "runs" / "ep01_anxious_night" / "voice_casting"
OUT.mkdir(parents=True, exist_ok=True)

# Sample lines — healing tone
LINE_NARRATOR = (
    "오늘 하루, 마음이 자꾸 앞일을 걱정했다면 — "
    "이 밤은 그 걱정을 잠시 내려놓아도 되는 시간입니다. "
    "괜찮아요, 당신은 혼자가 아닙니다."
)
LINE_SCRIPTURE = (
    "여호와는 나의 목자시니 내가 부족함이 없으리로다 "
    "그가 나를 푸른 초장에 누이시며 쉴 만한 물 가로 인도하시는도다"
)

# 10 female: F1–F5 × two styles
FEMALE = [
    {"id": "F_01", "voice": "F1", "speed": 0.90, "silence": 0.30, "step": 10, "style": "slow_warm", "line": "narrator"},
    {"id": "F_02", "voice": "F1", "speed": 0.96, "silence": 0.20, "step": 8, "style": "clear", "line": "narrator"},
    {"id": "F_03", "voice": "F2", "speed": 0.92, "silence": 0.28, "step": 10, "style": "gentle", "line": "narrator"},
    {"id": "F_04", "voice": "F2", "speed": 0.98, "silence": 0.18, "step": 8, "style": "natural", "line": "narrator"},
    {"id": "F_05", "voice": "F3", "speed": 0.90, "silence": 0.32, "step": 10, "style": "calm_deep", "line": "narrator"},
    {"id": "F_06", "voice": "F3", "speed": 0.96, "silence": 0.22, "step": 8, "style": "steady", "line": "narrator"},
    {"id": "F_07", "voice": "F4", "speed": 0.91, "silence": 0.30, "step": 10, "style": "soft", "line": "narrator"},
    {"id": "F_08", "voice": "F4", "speed": 0.97, "silence": 0.20, "step": 8, "style": "bright", "line": "narrator"},
    {"id": "F_09", "voice": "F5", "speed": 0.89, "silence": 0.34, "step": 10, "style": "slow_soft", "line": "narrator"},
    {"id": "F_10", "voice": "F5", "speed": 0.95, "silence": 0.24, "step": 8, "style": "balanced", "line": "narrator"},
]

# 10 male: M1–M5 × two styles (scripture-oriented, slower band)
MALE = [
    {"id": "M_01", "voice": "M1", "speed": 0.82, "silence": 0.34, "step": 10, "style": "slow_warm", "line": "scripture"},
    {"id": "M_02", "voice": "M1", "speed": 0.88, "silence": 0.26, "step": 8, "style": "clear", "line": "scripture"},
    {"id": "M_03", "voice": "M2", "speed": 0.84, "silence": 0.32, "step": 10, "style": "gentle", "line": "scripture"},
    {"id": "M_04", "voice": "M2", "speed": 0.90, "silence": 0.24, "step": 8, "style": "natural", "line": "scripture"},
    {"id": "M_05", "voice": "M3", "speed": 0.82, "silence": 0.34, "step": 10, "style": "calm_deep", "line": "scripture"},
    {"id": "M_06", "voice": "M3", "speed": 0.88, "silence": 0.26, "step": 8, "style": "steady", "line": "scripture"},
    {"id": "M_07", "voice": "M4", "speed": 0.83, "silence": 0.32, "step": 10, "style": "soft", "line": "scripture"},
    {"id": "M_08", "voice": "M4", "speed": 0.89, "silence": 0.24, "step": 8, "style": "firm_calm", "line": "scripture"},
    {"id": "M_09", "voice": "M5", "speed": 0.80, "silence": 0.36, "step": 10, "style": "slow_soft", "line": "scripture"},
    {"id": "M_10", "voice": "M5", "speed": 0.87, "silence": 0.28, "step": 8, "style": "balanced", "line": "scripture"},
]


def load_engine():
    sys.path.insert(0, str(TTS_ROOT / "src"))
    from supertonic3_engine import Supertonic3Engine  # type: ignore

    return Supertonic3Engine(output_dir=OUT)


def synth(engine, conf: dict, gender: str) -> dict:
    line = LINE_NARRATOR if conf["line"] == "narrator" else LINE_SCRIPTURE
    name = f"{conf['id']}_{conf['voice']}_{conf['style']}_sp{conf['speed']}.wav"
    path = OUT / gender / name
    path.parent.mkdir(parents=True, exist_ok=True)
    info = engine.synthesize_to_file(
        text=line,
        output_path=path,
        voice=conf["voice"],
        lang="ko",
        speed=float(conf["speed"]),
        total_step=int(conf["step"]),
        silence_duration=float(conf["silence"]),
        verbose=False,
    )
    return {
        **conf,
        "gender": gender,
        "file": str(path.relative_to(OUT.parent.parent.parent) if False else path),
        "path": str(path),
        "filename": name,
        "duration": info.get("duration"),
        "sample_text": line[:40] + "…",
    }


def main() -> None:
    engine = load_engine()
    catalog = {"female": [], "male": [], "lines": {"narrator": LINE_NARRATOR, "scripture": LINE_SCRIPTURE}}
    print("Generating 10 female…")
    for conf in FEMALE:
        row = synth(engine, conf, "female")
        catalog["female"].append(row)
        print(" ", row["id"], row["filename"], row.get("duration"))
    print("Generating 10 male…")
    for conf in MALE:
        row = synth(engine, conf, "male")
        catalog["male"].append(row)
        print(" ", row["id"], row["filename"], row.get("duration"))

    (OUT / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    # listening guide markdown
    lines = [
        "# 보이스 캐스팅 샘플 (각 10개)",
        "",
        f"폴더: `{OUT}`",
        "",
        "## 여성 나레이션 후보 (F_01 ~ F_10)",
        "",
        "| ID | 파일 | voice | speed | style |",
        "|----|------|-------|-------|-------|",
    ]
    for r in catalog["female"]:
        lines.append(
            f"| **{r['id']}** | `{r['filename']}` | {r['voice']} | {r['speed']} | {r['style']} |"
        )
    lines += [
        "",
        "## 남성 말씀 후보 (M_01 ~ M_10)",
        "",
        "| ID | 파일 | voice | speed | style |",
        "|----|------|-------|-------|-------|",
    ]
    for r in catalog["male"]:
        lines.append(
            f"| **{r['id']}** | `{r['filename']}` | {r['voice']} | {r['speed']} | {r['style']} |"
        )
    lines += [
        "",
        "## 고르는 법",
        "",
        "1. `female/` 폴더 10개 순서대로 청취 → 나레이션 1개 선택 (예: F_03)",
        "2. `male/` 폴더 10개 청취 → 말씀 1개 선택 (예: M_05)",
        "3. 채팅에 예: `여자 F_03 / 남자 M_05` 로 알려주세요.",
        "",
        "선택 후 `config/voice_healing.yaml` 에 반영하고 스모크 재합성합니다.",
        "",
    ]
    (OUT / "LISTEN_GUIDE.md").write_text("\n".join(lines), encoding="utf-8")
    print("OK", OUT)
    print("catalog", OUT / "catalog.json")


if __name__ == "__main__":
    import json

    main()
