# -*- coding: utf-8 -*-
import json
from pathlib import Path

r = json.loads(
    Path("runs/ep01_anxious_night/hermes_jobs/preview/reports/tts_report.json").read_text(
        encoding="utf-8"
    )
)
for it in r["items"]:
    for s in it.get("segments") or []:
        tl = s.get("text_len") or 0
        d = s.get("duration") or 0
        cpm = (tl / (d / 60)) if d else 0
        print(
            f"{s['speaker']:10} voice={s['voice']} speed={s['speed']} "
            f"chars={tl:4} dur={d:5.1f}s cpm={cpm:5.0f}"
        )
