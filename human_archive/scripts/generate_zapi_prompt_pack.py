from __future__ import annotations

import json
from pathlib import Path


EPISODE_DIR = Path(
    r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis"
)


def main() -> None:
    source = json.loads(
        (EPISODE_DIR / "source" / "scene_script_manifest_v2.json").read_text(
            encoding="utf-8"
        )
    )
    scenes = [scene for scene in source["scenes"] if scene["end_sec"] <= 120.0]
    if len(scenes) != 20:
        raise ValueError(f"Expected 20 pilot scenes, got {len(scenes)}")

    lines = []
    for scene in scenes:
        prompt = scene["midjourney_prompt"].split("--ar", 1)[0].strip()
        lines.append(
            f"{scene['shot_id']} | {prompt} photorealistic Himalayan documentary, "
            "no text, letters, numerals, watermarks"
        )

    output = EPISODE_DIR / "generation" / "pilot_prompt_pack_zapi_flow.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    print(f"lines={len(lines)}")


if __name__ == "__main__":
    main()
