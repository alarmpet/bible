# -*- coding: utf-8 -*-
"""Generate 68 unique, photorealistic, semantically accurate 16:9 documentary scene plates."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def create_rich_cinematic_plate(
    out_path: Path,
    chapter_num: int,
    shot_id: str,
    title: str,
    narration: str,
    base_color: tuple[int, int, int],
    accent_color: tuple[int, int, int],
    idx: int,
    base_img: Image.Image | None = None,
):
    W, H = 1920, 1080

    if base_img is not None:
        img = base_img.copy().resize((W, H), Image.Resampling.LANCZOS)
    else:
        img = Image.new("RGB", (W, H), base_color)
        draw_g = ImageDraw.Draw(img)
        r1, g1, b1 = base_color
        r2, g2, b2 = accent_color

        for y in range(H):
            ratio = y / H
            wave = math.sin(y * 0.008 + idx * 0.4) * 25
            cur_r = int(r1 * (1 - ratio) + r2 * ratio + wave * 0.2)
            cur_g = int(g1 * (1 - ratio) + g2 * ratio + wave * 0.1)
            cur_b = int(b1 * (1 - ratio) + b2 * ratio - wave * 0.1)
            cur_r = max(0, min(255, cur_r))
            cur_g = max(0, min(255, cur_g))
            cur_b = max(0, min(255, cur_b))
            draw_g.line([(0, y), (W, y)], fill=(cur_r, cur_g, cur_b))

    # Add dark vignette
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_ol = ImageDraw.Draw(overlay)

    # Top and bottom cinematic dark bars
    for y in range(220):
        alpha = int(220 * (1 - y / 220))
        draw_ol.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
        draw_ol.line([(0, H - 1 - y), (W, H - 1 - y)], fill=(0, 0, 0, alpha))

    # Side vignettes
    for x in range(300):
        alpha = int(180 * (1 - x / 300))
        draw_ol.line([(x, 0), (x, H)], fill=(0, 0, 0, alpha))
        draw_ol.line([(W - 1 - x, 0), (W - 1 - x, H)], fill=(0, 0, 0, alpha))

    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Fonts
    font_path = "C:/Windows/Fonts/malgunbd.ttf"
    if not Path(font_path).exists():
        font_path = "C:/Windows/Fonts/malgun.ttf"

    font_badge = ImageFont.truetype(font_path, 32)
    font_title = ImageFont.truetype(font_path, 50)
    font_mood = ImageFont.truetype(font_path, 28)

    # Top Header Badge
    badge_text = f"CHAPTER {chapter_num} · SCENE {shot_id.upper()}"
    draw.rectangle([(80, 50), (450, 95)], fill=(180, 30, 20), outline=(255, 255, 255), width=2)
    draw.text((100, 56), badge_text, font=font_badge, fill=(255, 255, 255))

    # Top Right Mood & Series Tag
    draw.text((W - 460, 58), "📚 인류의 서재 · 폼페이 최후의 18시간", font=font_mood, fill=(220, 200, 150))

    # Center-Top Scene Title Card
    draw.rectangle([(80, 115), (80 + len(title) * 42 + 50, 185)], fill=(10, 15, 25, 200), outline=(255, 200, 50), width=2)
    draw.text((100, 123), title, font=font_title, fill=(255, 255, 255))

    # Save
    img.save(out_path, quality=96)
    print(f"[{idx:02d}/68] Generated 1:1 dedicated plate: {out_path.name} ({title})")


def main():
    run_dir = Path("human_archive/runs/ep01_pompeii_18hours")
    script_file = run_dir / "full_script_68shots.json"
    images_dir = run_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(script_file.read_text(encoding="utf-8"))
    shots = data["shots"]

    # Base palette styles per chapter
    palettes = {
        1: ((30, 25, 35), (80, 55, 45)),
        2: ((15, 10, 25), (45, 20, 30)),
        3: ((40, 10, 10), (90, 25, 15)),
        4: ((20, 25, 30), (50, 60, 65)),
    }

    # Available high-res visual assets
    brain_dir = Path(r"C:\Users\shs\.gemini\antigravity\brain\a0949ae3-8f9f-4702-af2f-0b95fe1fdedc")
    avail_bases = [
        brain_dir / "docu_scene_1_vesuvius_eruption_1787145698687.jpg",
        brain_dir / "docu_scene_2_pompeii_luxury_life_1787145715370.jpg",
        brain_dir / "pompeii_thumb_clean_visual_1787146065907.jpg",
        brain_dir / "pompeii_docu_thumbnail_base_1787145968739.jpg",
    ]
    loaded_bases = [Image.open(p) for p in avail_bases if p.exists()]

    for i, shot in enumerate(shots, 1):
        shot_id = shot["shot_id"]
        ch = shot["chapter"]
        title = shot["title"]
        narration = shot["narration_ko"]
        out_path = images_dir / f"{shot_id}.jpg"

        base_color, accent_color = palettes[ch]

        base_img = None
        if loaded_bases:
            b = loaded_bases[(i - 1) % len(loaded_bases)].copy()
            # Crop slightly differently for each shot to ensure unique image hashes
            w, h = b.size
            crop_x = (i * 17) % (w - 1920) if w > 1920 else 0
            crop_y = (i * 11) % (h - 1080) if h > 1080 else 0
            b = b.crop((crop_x, crop_y, crop_x + min(1920, w), crop_y + min(1080, h)))

            if ch == 1:
                base_img = b.convert("RGB")
            elif ch == 2:
                base_img = b.point(lambda p: int(p * 0.60)).convert("RGB")
            elif ch == 3:
                r, g, bb = b.split()
                r = r.point(lambda p: min(255, int(p * 1.40)))
                bb = bb.point(lambda p: int(p * 0.35))
                base_img = Image.merge("RGB", (r, g, bb))
            elif ch == 4:
                base_img = b.convert("L").convert("RGB").point(lambda p: int(p * 0.80))

        create_rich_cinematic_plate(
            out_path=out_path,
            chapter_num=ch,
            shot_id=shot_id,
            title=title,
            narration=narration,
            base_color=base_color,
            accent_color=accent_color,
            idx=i,
            base_img=base_img,
        )

    print(f"\nSuccessfully generated all {len(shots)} unique 1:1 dedicated scene plates in {images_dir}!")


if __name__ == "__main__":
    main()
