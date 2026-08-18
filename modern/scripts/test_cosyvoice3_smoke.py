# -*- coding: utf-8 -*-
"""One-sentence Korean CosyVoice3 smoke. CPU-only. Does not touch SuperTonic jobs.

    python modern/scripts/test_cosyvoice3_smoke.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from cosyvoice3_engine import (
    CosyVoice3Engine,
    DEFAULT_COSY_ROOT,
    MODULE_ROOT,
    require_install,
    resolve_voice_spec,
)

OUT_DIR = Path(r"D:\bible_healing_ep01\work\cosyvoice3_smoke")
SMOKE_TEXT = "여호와는 나의 목자시니 내게 부족함이 없으리로다."


def main() -> int:
    try:
        require_install()
    except SystemExit as exc:
        print(exc)
        return 2
    spec = resolve_voice_spec("M4", 0.95)
    ref = spec.get("ref_wav")
    if ref and not Path(ref).is_absolute():
        ref = MODULE_ROOT / ref
        spec["ref_wav"] = str(ref)
    if not ref or not Path(ref).exists():
        print(f"reference wav missing: {ref}")
        return 2
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "smoke_m4_scripture.wav"
    engine = CosyVoice3Engine(output_dir=OUT_DIR)
    print(f"cosy_root={DEFAULT_COSY_ROOT}")
    print(f"ref={spec['ref_wav']}")
    print(f"text={SMOKE_TEXT}")
    result = engine.synthesize_to_file(
        text=SMOKE_TEXT,
        output_path=out,
        voice="M4",
        speed=0.95,
        total_step=10,
        silence_duration=0.25,
        max_chunk_length=90,
        verbose=True,
    )
    report = OUT_DIR / "smoke_report.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"wrote {out}")
    return 0 if result.get("ok") and out.exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
