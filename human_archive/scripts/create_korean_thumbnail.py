# -*- coding: utf-8 -*-
"""Generate high-CTR YouTube thumbnail with Korean typography for Pompeii episode."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

base_img_path = Path(r"C:\Users\shs\.gemini\antigravity\brain\a0949ae3-8f9f-4702-af2f-0b95fe1fdedc\pompeii_thumb_clean_visual_1787146065907.jpg")
out_dir = Path("human_archive/runs/ep01_pompeii_18hours")
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "thumbnail_pompeii_final.jpg"

img = Image.open(base_img_path).convert("RGBA")
W, H = img.size

# Dim the left/top side slightly with a gradient mask for text readability
overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
draw_ol = ImageDraw.Draw(overlay)

# Left dark vignette gradient
for x in range(int(W * 0.55)):
    alpha = int(180 * (1 - (x / (W * 0.55)) ** 1.5))
    draw_ol.line([(x, 0), (x, H)], fill=(0, 0, 0, alpha))

img = Image.alpha_composite(img, overlay)
draw = ImageDraw.Draw(img)

# Font loading
font_path = "C:/Windows/Fonts/malgunbd.ttf"  # Malgun Gothic Bold
if not Path(font_path).exists():
    font_path = "C:/Windows/Fonts/malgun.ttf"

font_badge = ImageFont.truetype(font_path, 42)
font_sub = ImageFont.truetype(font_path, 68)
font_main = ImageFont.truetype(font_path, 108)
font_sub_main = ImageFont.truetype(font_path, 96)

def draw_text_with_outline_shadow(draw, pos, text, font, fill_color, outline_color, shadow_color, outline_w=6, shadow_offset=(8, 8)):
    x, y = pos
    sx, sy = shadow_offset
    # Shadow
    for dx in range(-outline_w, outline_w + 1):
        for dy in range(-outline_w, outline_w + 1):
            draw.text((x + sx + dx, y + sy + dy), text, font=font, fill=shadow_color)
    # Outline
    for dx in range(-outline_w, outline_w + 1):
        for dy in range(-outline_w, outline_w + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    # Fill
    draw.text((x, y), text, font=font, fill=fill_color)

# 1. Top Category Badge
badge_x, badge_y = 90, 90
draw.rectangle([(badge_x - 15, badge_y - 10), (badge_x + 360, badge_y + 60)], fill=(220, 20, 20, 240), outline=(255, 255, 255), width=3)
draw.text((badge_x + 10, badge_y), "🔥 인류사 미스터리", font=font_badge, fill=(255, 255, 255))

# 2. Hook line 1: 18시간의 골든타임
draw_text_with_outline_shadow(
    draw,
    pos=(90, 180),
    text="18시간의 골든타임",
    font=font_sub,
    fill_color=(255, 220, 50),
    outline_color=(20, 5, 5),
    shadow_color=(0, 0, 0),
    outline_w=6,
    shadow_offset=(8, 8)
)

# 3. Main Hook Line 2: 왜 아무도
draw_text_with_outline_shadow(
    draw,
    pos=(90, 275),
    text="왜 아무도",
    font=font_main,
    fill_color=(255, 255, 255),
    outline_color=(10, 10, 15),
    shadow_color=(0, 0, 0),
    outline_w=8,
    shadow_offset=(10, 10)
)

# 4. Main Hook Line 3: 도망치지 않았을까?
draw_text_with_outline_shadow(
    draw,
    pos=(90, 405),
    text="도망치지 않았을까?",
    font=font_sub_main,
    fill_color=(255, 60, 40),
    outline_color=(255, 255, 255),
    shadow_color=(0, 0, 0),
    outline_w=5,
    shadow_offset=(10, 10)
)

# 5. Bottom Channel Branding
draw.rectangle([(90, H - 120), (520, H - 60)], fill=(10, 15, 25, 220), outline=(255, 200, 50), width=2)
draw.text((115, H - 110), "📚 인류의 서재 · 폼페이 편", font=font_badge, fill=(240, 240, 240))

# Convert to RGB and save
final_img = img.convert("RGB")
final_img.save(out_path, quality=98)
print(f"Final YouTube Thumbnail created: {out_path}")
