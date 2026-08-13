# -*- coding: utf-8 -*-
"""Create richer 16:9 night/healing background plates (not flat gradient-only)."""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parents[1] / "assets" / "backgrounds" / "ep01"
W, H = 1920, 1080


def stars(draw: ImageDraw.ImageDraw, n: int, seed: int, color=(220, 230, 255)) -> None:
    rng = random.Random(seed)
    for _ in range(n):
        x, y = rng.randint(0, W - 1), rng.randint(0, int(H * 0.65))
        r = rng.choice([1, 1, 1, 2])
        a = rng.randint(140, 255)
        c = (color[0], color[1], color[2])
        draw.ellipse((x - r, y - r, x + r, y + r), fill=c)


def vertical_grad(c0, c1) -> Image.Image:
    im = Image.new("RGB", (W, H))
    px = im.load()
    for y in range(H):
        t = y / (H - 1)
        r = int(c0[0] + (c1[0] - c0[0]) * t)
        g = int(c0[1] + (c1[1] - c0[1]) * t)
        b = int(c0[2] + (c1[2] - c0[2]) * t)
        for x in range(W):
            px[x, y] = (r, g, b)
    return im


def night_sky(seed: int = 1) -> Image.Image:
    im = vertical_grad((6, 10, 28), (18, 28, 52))
    d = ImageDraw.Draw(im)
    stars(d, 220, seed)
    # soft moon
    moon = Image.new("RGB", (W, H), (0, 0, 0))
    md = ImageDraw.Draw(moon)
    cx, cy, R = int(W * 0.78), int(H * 0.22), 70
    md.ellipse((cx - R, cy - R, cx + R, cy + R), fill=(240, 235, 210))
    moon = moon.filter(ImageFilter.GaussianBlur(8))
    im = Image.blend(im, moon, 0.35)
    # horizon mist
    mist = Image.new("RGB", (W, H), (0, 0, 0))
    md = ImageDraw.Draw(mist)
    md.rectangle((0, int(H * 0.72), W, H), fill=(30, 40, 55))
    mist = mist.filter(ImageFilter.GaussianBlur(40))
    im = Image.blend(im, mist, 0.45)
    return im


def candle_room(seed: int = 2) -> Image.Image:
    im = vertical_grad((12, 8, 6), (28, 18, 12))
    d = ImageDraw.Draw(im)
    # table band
    d.rectangle((0, int(H * 0.62), W, H), fill=(22, 14, 10))
    # candle body
    cx = W // 2
    d.rectangle((cx - 18, int(H * 0.48), cx + 18, int(H * 0.72)), fill=(235, 220, 190))
    # flame glow
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    fy = int(H * 0.42)
    gd.ellipse((cx - 120, fy - 120, cx + 120, fy + 120), fill=(255, 160, 60))
    gd.ellipse((cx - 25, fy - 40, cx + 25, fy + 20), fill=(255, 230, 160))
    glow = glow.filter(ImageFilter.GaussianBlur(30))
    im = Image.blend(im, glow, 0.4)
    return im


def lake_night(seed: int = 3) -> Image.Image:
    im = vertical_grad((8, 14, 30), (12, 40, 48))
    d = ImageDraw.Draw(im)
    stars(d, 160, seed, (200, 220, 240))
    # water
    d.rectangle((0, int(H * 0.55), W, H), fill=(10, 28, 40))
    # reflections
    for i in range(40):
        y = int(H * 0.55 + i * 8)
        shade = 20 + (i % 5) * 4
        d.line((0, y, W, y), fill=(shade, shade + 15, shade + 25), width=2)
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    return im


def window_rain(seed: int = 4) -> Image.Image:
    im = vertical_grad((10, 12, 18), (24, 28, 36))
    d = ImageDraw.Draw(im)
    # window panes
    m = 80
    d.rectangle((m, m, W - m, H - m), outline=(60, 70, 85), width=10)
    d.line((W // 2, m, W // 2, H - m), fill=(60, 70, 85), width=8)
    d.line((m, H // 2, W - m, H // 2), fill=(60, 70, 85), width=8)
    # rain drops
    rng = random.Random(seed)
    for _ in range(180):
        x = rng.randint(m + 10, W - m - 10)
        y = rng.randint(m + 10, H - m - 10)
        d.line((x, y, x - 2, y + 18), fill=(140, 160, 190), width=1)
    # soft outer vignette
    return im.filter(ImageFilter.GaussianBlur(0.4))


def forest_path(seed: int = 5) -> Image.Image:
    im = vertical_grad((6, 12, 10), (14, 28, 22))
    d = ImageDraw.Draw(im)
    # trees silhouettes
    rng = random.Random(seed)
    for _ in range(18):
        x = rng.randint(0, W)
        h = rng.randint(int(H * 0.35), int(H * 0.7))
        top = H - h
        d.polygon([(x, H), (x - 40, top), (x + 40, top)], fill=(4, 12, 8))
    # path
    d.polygon(
        [(int(W * 0.35), H), (int(W * 0.65), H), (int(W * 0.52), int(H * 0.55)), (int(W * 0.48), int(H * 0.55))],
        fill=(30, 28, 22),
    )
    # distant light
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((int(W * 0.42), int(H * 0.4), int(W * 0.58), int(H * 0.55)), fill=(255, 220, 150))
    glow = glow.filter(ImageFilter.GaussianBlur(35))
    return Image.blend(im, glow, 0.25)


def dawn_ridge(seed: int = 6) -> Image.Image:
    im = vertical_grad((20, 24, 48), (255, 180, 120))
    d = ImageDraw.Draw(im)
    # ridges
    for layer, col in (
        (0.72, (40, 50, 70)),
        (0.8, (30, 38, 55)),
        (0.88, (20, 26, 40)),
    ):
        pts = [(0, H)]
        y0 = int(H * layer)
        for x in range(0, W + 1, 40):
            pts.append((x, y0 + int(18 * math.sin(x * 0.01 + seed + layer * 10))))
        pts.append((W, H))
        d.polygon(pts, fill=col)
    return im


def soft_blue(seed: int = 7) -> Image.Image:
    im = vertical_grad((12, 20, 40), (40, 70, 100))
    d = ImageDraw.Draw(im)
    stars(d, 80, seed)
    return im


def warm_dusk(seed: int = 8) -> Image.Image:
    im = vertical_grad((30, 18, 40), (90, 50, 40))
    d = ImageDraw.Draw(im)
    # sun disc
    cx, cy, R = int(W * 0.5), int(H * 0.62), 90
    d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=(255, 200, 120))
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    return im


GENERATORS = [
    ("night_sky", night_sky),
    ("candle_room", candle_room),
    ("lake_night", lake_night),
    ("window_rain", window_rain),
    ("forest_path", forest_path),
    ("dawn_ridge", dawn_ridge),
    ("soft_blue", soft_blue),
    ("warm_dusk", warm_dusk),
    ("night_sky_b", lambda: night_sky(11)),
    ("lake_b", lambda: lake_night(12)),
    ("candle_b", lambda: candle_room(13)),
    ("forest_b", lambda: forest_path(14)),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    index = []
    for name, fn in GENERATORS:
        path = OUT / f"{name}.jpg"
        im = fn()
        im.save(path, quality=90, optimize=True)
        index.append(name)
        print("wrote", path.name)
    (OUT / "index.json").write_text(
        __import__("json").dumps({"backgrounds": index, "dir": str(OUT)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("count", len(index))


if __name__ == "__main__":
    main()
