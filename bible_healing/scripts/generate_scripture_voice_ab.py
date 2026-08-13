"""Generate comparable male scripture voice candidates without touching the full job."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TTS_ROOT = Path(r"C:\Users\amd\supertonic3-local-tts-20260517-r4\supertonic3-local-tts")
OUT = ROOT / "runs" / "ep01_anxious_night" / "voice_ab"

SAMPLES = {
    "psalm4": "내가 평안히 눕고 자기도 하리니 나를 안전히 살게 하시는 이는 오직 주님이시니이다.",
    "psalm46": "너희는 가만히 있어 내가 하나님 됨을 알지어다. 내가 뭇 나라 중에서 높임을 받으리라.",
    "bridge": "오늘 밤 모든 답을 찾지 않아도 됩니다. 지금은 듣기만 해도 괜찮습니다.",
}
CANDIDATES = [
    {"id": "M5_slow", "voice": "M5", "speed": 0.76, "total_step": 20, "silence": 0.48},
    {"id": "M3_slow", "voice": "M3", "speed": 0.76, "total_step": 20, "silence": 0.48},
    {"id": "M4_slow", "voice": "M4", "speed": 0.78, "total_step": 20, "silence": 0.45},
]


def main() -> None:
    sys.path.insert(0, str(TTS_ROOT / "src"))
    from supertonic3_engine import Supertonic3Engine  # type: ignore

    OUT.mkdir(parents=True, exist_ok=True)
    engine = Supertonic3Engine(output_dir=OUT)
    catalog = []
    for candidate in CANDIDATES:
        for sample_id, text in SAMPLES.items():
            path = OUT / f"{candidate['id']}_{sample_id}.wav"
            info = engine.synthesize_to_file(
                text=text,
                output_path=path,
                voice=candidate["voice"],
                lang="ko",
                speed=candidate["speed"],
                total_step=candidate["total_step"],
                silence_duration=candidate["silence"],
                verbose=False,
            )
            catalog.append({**candidate, "sample": sample_id, "text": text, "path": str(path), "duration": info.get("duration")})
    (OUT / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "LISTEN_GUIDE.md").write_text(
        "# 성경 남성 음성 A/B 샘플\n\n"
        "후보별로 psalm4, psalm46, bridge를 같은 조건에서 비교한다.\n\n"
        "| 후보 | voice | speed | silence |\n|---|---|---:|---:|\n"
        + "\n".join(f"| {c['id']} | {c['voice']} | {c['speed']} | {c['silence']} |" for c in CANDIDATES)
        + "\n\n선정 기준: 빠르지 않음, 공격적이지 않음, 문장 끝의 여유, 장시간 청취 피로도.\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "output": str(OUT), "samples": len(catalog)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
