from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


W, H = 1920, 1080


def make_placeholder(path: Path, kind: str) -> None:
    image = Image.new("RGB", (W, H), (14, 22, 30))
    draw = ImageDraw.Draw(image)
    if kind == "map":
        for x in range(0, W, 140):
            draw.line((x, 0, x - 240, H), fill=(35, 58, 67), width=3)
        for y in range(0, H, 130):
            draw.line((0, y, W, y + 180), fill=(28, 49, 58), width=3)
        draw.line((250, 850, 520, 620, 900, 690, 1240, 300, 1700, 220), fill=(76, 156, 173), width=24)
    elif kind == "powerhouse":
        draw.rectangle((300, 230, 1620, 880), outline=(175, 191, 194), width=8)
        draw.ellipse((520, 340, 1400, 900), outline=(95, 135, 145), width=8)
        for x in (650, 920, 1190):
            draw.line((x, 410, x, 820), fill=(205, 120, 45), width=12)
    elif kind == "water":
        for y in range(500, H, 55):
            draw.arc((120, y - 25, 1800, y + 45), 0, 180, fill=(68, 121, 136), width=10)
        for box in ((300, 690, 560, 900), (820, 570, 1060, 790), (1320, 710, 1600, 950)):
            draw.polygon([(box[0], box[3]), (box[0] + 70, box[1]), (box[2], box[1] + 50), (box[2] - 60, box[3])], fill=(83, 75, 65))
    elif kind == "sites":
        for i, color in enumerate(((198, 91, 52), (224, 174, 62), (70, 145, 122))):
            x = 260 + i * 500
            draw.rounded_rectangle((x, 270, x + 390, 810), radius=30, outline=color, width=12)
            draw.ellipse((x + 145, 470, x + 245, 570), fill=color)
    elif kind == "helicopter":
        draw.ellipse((700, 420, 1220, 670), outline=(198, 144, 67), width=14)
        draw.line((560, 390, 1370, 390), fill=(198, 144, 67), width=10)
        draw.line((960, 670, 960, 900), fill=(198, 144, 67), width=12)
        draw.rectangle((820, 860, 1100, 980), outline=(181, 181, 170), width=10)
    elif kind == "tunnel":
        draw.ellipse((520, 220, 1400, 980), outline=(120, 153, 158), width=14)
        draw.line((960, 360, 960, 900), fill=(232, 176, 72), width=16)
        draw.ellipse((860, 770, 1060, 970), fill=(33, 47, 54))
    elif kind == "door":
        draw.rectangle((650, 170, 1270, 920), fill=(46, 58, 63), outline=(196, 152, 74), width=12)
        draw.line((710, 860, 1210, 860), fill=(77, 171, 186), width=20)
    else:
        draw.rectangle((180, 180, 1740, 900), outline=(120, 153, 158), width=8)
    image.save(path)


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def main() -> None:
    build = Path(sys.argv[1]).resolve()
    assets = build / "assets"
    clips = build / "motion_clips"
    assets.mkdir(parents=True, exist_ok=True)
    clips.mkdir(parents=True, exist_ok=True)
    placeholders = {
        "A01": "map", "A04": "powerhouse", "A05": "map", "A07": "water",
        "A09": "sites", "A10": "helicopter", "A11": "tunnel", "A12": "door",
    }
    for asset_id, kind in placeholders.items():
        target = assets / f"{asset_id}.png"
        if not target.exists():
            make_placeholder(target, kind)
    timeline = json.loads((build / "sentence_audio_manifest.json").read_text(encoding="utf-8"))
    alignment = json.loads((build / "sentence_visual_alignment_v1.json").read_text(encoding="utf-8"))
    asset_for = {row["sentence_id"]: row["asset_id"] for row in alignment["rows"]}
    fallback = ["A02", "A03", "A06", "A08"]
    concat = build / "concat.txt"
    concat_lines: list[str] = []
    for i, row in enumerate(timeline["sentences"]):
        asset_id = asset_for.get(row["sentence_id"], fallback[i % len(fallback)])
        image = assets / f"{asset_id}.png"
        if not image.exists():
            image = assets / f"{fallback[i % len(fallback)]}.png"
        clip = clips / f"{i:03d}_{row['sentence_id']}.mp4"
        duration = max(0.5, float(row["duration_sec"]) + 0.35)
        run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-loop", "1", "-i", str(image), "-t", f"{duration:.3f}",
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-r", "25", "-an", str(clip),
        ])
        concat_lines.append(f"file '{clip.as_posix()}'")
    concat.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
    silent_video = build / "silent_video.mp4"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(silent_video)])
    output = build / "candidate" / f"nepal-tunnel-rescue-{build.name}.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(silent_video),
        "-i", str(build / "master_audio_48k.wav"), "-vf", f"subtitles={str(build / 'subtitles.ass').replace('\\', '/')}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", str(output),
    ])
    manifest = {
        "schema": "build_manifest_v1",
        "status": "draft_render",
        "video": str(output),
        "audio": str(build / "master_audio_48k.wav"),
        "subtitles": str(build / "subtitles.ass"),
        "assets": sorted(str(p) for p in assets.glob("*.png")),
        "sentence_count": len(timeline["sentences"]),
        "duration_sec": timeline["total_duration_sec"],
        "ai_reconstruction_disclosure": True,
    }
    (build / "build_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
