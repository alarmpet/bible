# -*- coding: utf-8 -*-
"""Compose scene frame: background plate + on-screen text (verse / narration / title)."""
from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
BG_DIR = ROOT / "assets" / "backgrounds" / "ep01"
FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\malgun.ttf"),
    Path(r"C:\Windows\Fonts\malgunbd.ttf"),
    Path(r"C:\Windows\Fonts\NotoSansKR-VF.ttf"),
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    paths = FONT_CANDIDATES
    if bold:
        paths = [Path(r"C:\Windows\Fonts\malgunbd.ttf")] + FONT_CANDIDATES
    for p in paths:
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def clean_scripture_text(text: str) -> str:
    """Drop OSIS headings like (다윗의 시...) for on-screen readability."""
    import re

    t = " ".join((text or "").split())
    # remove parenthetical headings at start / mid repeatedly
    t = re.sub(r"\([^)]{0,80}\)", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def wrap_ko(text: str, width: int) -> list[str]:
    text = " ".join((text or "").split())
    if not text:
        return []
    # character-ish wrap for Korean
    lines = []
    cur = ""
    for ch in text:
        cur += ch
        if len(cur) >= width and ch in " .,，。、!?;:」』）)]":
            lines.append(cur.strip())
            cur = ""
        elif len(cur) >= width + 6:
            lines.append(cur.strip())
            cur = ""
    if cur.strip():
        lines.append(cur.strip())
    return lines


def load_bg(name: str | None, order: int) -> Image.Image:
    bgs = sorted(BG_DIR.glob("*.jpg"))
    if not bgs:
        raise FileNotFoundError(f"No backgrounds in {BG_DIR}; run make_background_bank.py")
    if name:
        p = BG_DIR / f"{name}.jpg"
        if p.exists():
            return Image.open(p).convert("RGB")
    return Image.open(bgs[(order - 1) % len(bgs)]).convert("RGB")


def dim_center(im: Image.Image, strength: float = 0.45) -> Image.Image:
    """Darken for text readability while keeping scene visible."""
    overlay = Image.new("RGB", im.size, (0, 0, 0))
    return Image.blend(im, overlay, strength)


def draw_text_block(
    im: Image.Image,
    lines: list[str],
    *,
    center: bool,
    y_ratio: float,
    fnt: ImageFont.ImageFont,
    fill=(245, 245, 245),
    box: bool = True,
) -> None:
    if not lines:
        return
    d = ImageDraw.Draw(im)
    w, h = im.size
    sizes = [d.textbbox((0, 0), ln, font=fnt) for ln in lines]
    line_h = max(s[3] - s[1] for s in sizes) + 14
    block_h = line_h * len(lines)
    block_w = max(s[2] - s[0] for s in sizes)
    y0 = int(h * y_ratio) - block_h // 2
    if center:
        x0 = (w - block_w) // 2
    else:
        x0 = int(w * 0.08)
        block_w = max(block_w, int(w * 0.84))
    pad = 32
    if box:
        box_img = Image.new("RGBA", im.size, (0, 0, 0, 0))
        bd = ImageDraw.Draw(box_img)
        left = x0 - pad if center else int(w * 0.06)
        right = x0 + block_w + pad if center else int(w * 0.94)
        bd.rounded_rectangle(
            (left, y0 - pad, right, y0 + block_h + pad),
            radius=18,
            fill=(0, 0, 0, 165),
        )
        im_rgba = im.convert("RGBA")
        im_rgba = Image.alpha_composite(im_rgba, box_img)
        im.paste(im_rgba.convert("RGB"))
        d = ImageDraw.Draw(im)
    y = y0
    for ln in lines:
        bb = d.textbbox((0, 0), ln, font=fnt)
        tw = bb[2] - bb[0]
        x = (w - tw) // 2 if center else int(w * 0.08)
        d.text((x + 2, y + 2), ln, font=fnt, fill=(0, 0, 0))
        d.text((x, y), ln, font=fnt, fill=fill)
        y += line_h


def compose(
    order: int,
    speaker: str,
    text: str,
    title: str | None = None,
    ref_label: str | None = None,
    bg_name: str | None = None,
    out_path: Path | None = None,
) -> Image.Image:
    im = load_bg(bg_name, order)
    # keep background readable (not pure black)
    im = dim_center(im, 0.28 if speaker == "scripture" else 0.32)

    if speaker == "scripture":
        body = clean_scripture_text(text)
        if ref_label:
            draw_text_block(
                im,
                [ref_label],
                center=True,
                y_ratio=0.16,
                fnt=font(40, bold=True),
                fill=(230, 210, 160),
                box=False,
            )
        lines = wrap_ko(body, 18)[:6]
        if len(wrap_ko(body, 18)) > 6:
            if lines:
                lines[-1] = lines[-1].rstrip("…") + "…"
        draw_text_block(
            im,
            lines,
            center=True,
            y_ratio=0.52,
            fnt=font(52, bold=True),
            fill=(255, 252, 245),
        )
    else:
        body_lines = wrap_ko(text, 24)[:5]
        # unit title chip
        if title and title not in ("오프닝", "클로징") and not title.endswith("쉼"):
            draw_text_block(
                im,
                [title],
                center=True,
                y_ratio=0.12,
                fnt=font(34, bold=True),
                fill=(210, 200, 180),
                box=False,
            )
        draw_text_block(
            im,
            body_lines,
            center=False,
            y_ratio=0.74,
            fnt=font(42),
            fill=(245, 245, 248),
        )

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        im.save(out_path, quality=90, optimize=True)
    return im


def compose_job(job: Path) -> dict:
    scenes = json.loads((job / "scenes.json").read_text(encoding="utf-8"))
    n = 0
    for sc in scenes:
        order = int(sc["order"])
        segs = sc.get("segments") or []
        speaker = (segs[0].get("speaker") if segs else None) or sc.get("meta", {}).get("speaker") or "narrator"
        text = sc.get("narration") or (segs[0].get("text") if segs else "")
        ref = None
        if segs:
            ref = segs[0].get("ref")
        ref_label = (sc.get("meta") or {}).get("ref_label")
        if not ref_label and ref:
            ref_label = ref
        out = job / f"scene_{order}_flow.jpg"
        compose(
            order,
            speaker,
            text,
            title=sc.get("title"),
            ref_label=ref_label,
            out_path=out,
        )
        n += 1
    report = {"ok": True, "frames": n, "job": str(job)}
    (job / "reports").mkdir(exist_ok=True)
    (job / "reports" / "compose_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    r = compose_job(Path(args.job).resolve())
    print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
