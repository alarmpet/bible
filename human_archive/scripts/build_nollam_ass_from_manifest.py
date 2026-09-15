from __future__ import annotations

import json
from pathlib import Path
import sys


def ass_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int(seconds % 3600 // 60)
    remainder = seconds % 60
    return f"{hours}:{minutes:02d}:{remainder:05.2f}"


def main() -> None:
    build = Path(sys.argv[1])
    timeline = json.loads((build / "sentence_audio_manifest.json").read_text(encoding="utf-8"))
    script = json.loads((build / "trend_verified_script_v1.json").read_text(encoding="utf-8"))
    text_by_id = {row["sentence_id"]: row["text"] for row in script["sentences"]}
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        "Style: Default,Noto Sans CJK KR,48,&H00FFFFFF,&H000000FF,&H00101010,&H80101010,0,0,1,3,1,2,80,80,60,1",
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Text",
    ]
    for row in timeline["sentences"]:
        text = text_by_id.get(row["sentence_id"], row["tts_text"])
        lines.append(
            f"Dialogue: 0,{ass_time(row['start_sec'])},{ass_time(row['end_sec'])},Default,{text}"
        )
    (build / "subtitles.ass").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(build / "subtitles.ass")


if __name__ == "__main__":
    main()
