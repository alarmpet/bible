# -*- coding: utf-8 -*-
"""
Prepare Hermes job media for bible_healing:
  - draft.json from scenes.json
  - scene_{n}_flow.jpg calm backgrounds (Pillow gradients, cycled)
  - render-options.json / provenance stubs
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

# Soft night palettes (RGB)
PALETTES = [
    ((8, 12, 32), (28, 48, 88)),  # deep navy → soft blue
    ((12, 10, 28), (48, 32, 72)),  # indigo
    ((18, 12, 24), (64, 40, 48)),  # warm dusk
    ((6, 16, 28), (20, 56, 72)),  # teal night
    ((14, 14, 22), (40, 36, 56)),  # charcoal violet
    ((10, 18, 20), (24, 48, 44)),  # forest night
]


def gradient_image(w: int, h: int, c0: tuple, c1: tuple, seed: int = 0) -> Image.Image:
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        # slight horizontal wave for less flat look
        for x in range(w):
            tw = t + 0.04 * math.sin((x + seed * 17) * 0.01)
            tw = max(0.0, min(1.0, tw))
            r = int(c0[0] + (c1[0] - c0[0]) * tw)
            g = int(c0[1] + (c1[1] - c0[1]) * tw)
            b = int(c0[2] + (c1[2] - c0[2]) * tw)
            px[x, y] = (r, g, b)
    # soft vignette
    overlay = Image.new("RGB", (w, h), (0, 0, 0))
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse((-w * 0.1, -h * 0.1, w * 1.1, h * 1.1), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=min(w, h) // 8))
    # invert-ish: edges darker
    # composite: img with darkened edges
    dark = Image.blend(img, overlay, 0.35)
    img = Image.composite(img, dark, mask)
    # subtle center glow (warm)
    glow = Image.new("RGB", (w, h), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = w // 2, int(h * 0.45)
    for i, alpha in enumerate((40, 25, 12)):
        r = int(min(w, h) * (0.18 + i * 0.08))
        col = (255, 220, 180)
        # draw ring approx via ellipse on separate then blend
        layer = Image.new("RGB", (w, h), (0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
        layer = layer.filter(ImageFilter.GaussianBlur(radius=r // 2 + 20))
        img = Image.blend(img, ImageChops_screen(img, layer), alpha / 100.0)
    return img


def ImageChops_screen(a: Image.Image, b: Image.Image) -> Image.Image:
    from PIL import ImageChops

    return ImageChops.screen(a, b)


def make_palette_set(out_dir: Path, w: int = 1920, h: int = 1080) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, (c0, c1) in enumerate(PALETTES):
        p = out_dir / f"bg_{i:02d}.jpg"
        if not p.exists():
            im = gradient_image(w, h, c0, c1, seed=i * 13)
            im.save(p, quality=88, optimize=True)
        paths.append(p)
    return paths


def prepare(job: Path) -> dict:
    scenes_path = job / "scenes.json"
    if not scenes_path.exists():
        raise SystemExit(f"missing {scenes_path}")
    scenes = json.loads(scenes_path.read_text(encoding="utf-8"))

    # draft.json
    draft_scenes = []
    for sc in scenes:
        draft_scenes.append(
            {
                "order": int(sc["order"]),
                "narration": sc.get("narration") or "",
                "outputMode": "image",
                "flowOutputMode": "image",
                "section": "main",
                "chapter": int(sc.get("chapter") or 1),
                "scene_id": sc.get("scene_id"),
                "title": sc.get("title"),
            }
        )
    draft = {
        "title": "불안한 밤을 위한 말씀 · 구약 힐링 낭독",
        "scenes": draft_scenes,
    }
    (job / "draft.json").write_text(
        json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # backgrounds
    bg_dir = job / "media" / "backgrounds"
    bgs = make_palette_set(bg_dir)
    for sc in scenes:
        order = int(sc["order"])
        src = bgs[(order - 1) % len(bgs)]
        dst = job / f"scene_{order}_flow.jpg"
        if not dst.exists() or dst.stat().st_size < 1000:
            # copy bytes
            dst.write_bytes(src.read_bytes())

    job_meta = {
        "schema_version": "1.0",
        "job_id": f"bible_healing_ep01_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "run_id": "ep01_anxious_night",
        "mode": job.name,
        "title": draft["title"],
        "aspect": "16:9",
        "intro_mode": "NONE",
        "caption_policy": "DETERMINISTIC_FROM_NARRATION",
        "scene_count": len(scenes),
        "multi_voice": True,
        "type": "bible_healing",
        "translation": "KRV",
    }
    (job / "job.json").write_text(
        json.dumps(job_meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    render_opts = {
        "aspectRatio": "16:9",
        "engineVoice": "F3",
        "voiceId": "F3",
        "speechSpeed": 0.78,
        "motionIntensity": "light",
        "transitionPreset": "scene-fade",
        "videoFormat": "longform",
        "stylePresetId": "healing_scripture",
        "multiVoice": True,
        "jobId": job_meta["job_id"],
    }
    (job / "render-options.json").write_text(
        json.dumps(render_opts, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    prov = {
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "backgrounds": [str(p.name) for p in bgs],
        "scene_flow_count": len(scenes),
        "note": "Calm gradient stills for sleep/healing longform; not photographic stock.",
    }
    (job / "provenance.json").write_text(
        json.dumps(prov, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    report = {
        "ok": True,
        "scenes": len(scenes),
        "flow_images": len(list(job.glob("scene_*_flow.jpg"))),
        "draft": True,
    }
    (job / "reports").mkdir(exist_ok=True)
    (job / "reports" / "prepare_media_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    prepare(Path(args.job).resolve())


if __name__ == "__main__":
    main()
