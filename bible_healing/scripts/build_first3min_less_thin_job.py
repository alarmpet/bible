# -*- coding: utf-8 -*-
"""Create a fresh first3min job from locked F5/M4 less-thin voices. Does not overwrite old jobs."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "runs" / "ep01_anxious_night" / "hermes_jobs" / "first3min_speed095"
DST = ROOT / "runs" / "ep01_anxious_night" / "hermes_jobs" / "first3min_less_thin_20260816"
LOCK = ROOT / "config" / "media_rules_lock.json"


def main() -> None:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    voice = lock["voice"]
    DST.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC / "scenes.json", DST / "scenes.json")
    vm = {
        "schema_version": "1.0",
        "engine": "supertonic3",
        "preview_approved": True,
        "notes": "sample 3min: 09_F5_less_thin + 09_M4_less_thin",
        "speakers": {
            "narrator": {
                "label": "narrator_female_healing",
                "voice": voice["narrator"]["voice"],
                "speed": voice["narrator"]["speed"],
                "total_step": voice["narrator"]["total_step"],
                "silence_duration": voice["narrator"]["silence_seconds"],
                "audio_filter": voice["narrator"]["audio_filter"],
            },
            "scripture": {
                "label": "pastor_calm_low_male_scripture",
                "voice": voice["scripture"]["voice"],
                "speed": voice["scripture"]["speed"],
                "total_step": voice["scripture"]["total_step"],
                "silence_duration": voice["scripture"]["silence_seconds"],
                "max_chunk_length": voice["scripture"]["max_chunk_length"],
                "audio_filter": voice["scripture"]["audio_filter"],
            },
        },
        "rules": {
            "narration_default_speaker": "narrator",
            "narrator_must_not_share_voice_with_characters": True,
        },
    }
    (DST / "voice_map.json").write_text(
        json.dumps(vm, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (DST / "job.json").write_text(
        json.dumps(
            {
                "type": "first3min_sample",
                "voices": "09_F5_less_thin + 09_M4_less_thin",
                "source_scenes": str(SRC / "scenes.json"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (DST / "reports").mkdir(exist_ok=True)
    print(DST)


if __name__ == "__main__":
    main()
