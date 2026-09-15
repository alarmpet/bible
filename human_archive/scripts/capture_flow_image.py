# -*- coding: utf-8 -*-
"""Check and download generated images from Google Flow canvas."""
import asyncio
import json
import sys
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = [pg for ctx in browser.contexts for pg in ctx.pages if "flow" in pg.url or "labs.google" in pg.url][0]

        ss_path = Path("C:/Users/shs/.gemini/antigravity/brain/0d14dd2f-7ae7-4219-be5f-159ff1364917/flow_generated_state.png")
        await page.screenshot(path=str(ss_path))
        print(f"Screenshot saved: {ss_path}")

        imgs = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('img')).map(i => ({
                src: i.src || i.currentSrc || '',
                w: i.naturalWidth || i.width,
                h: i.naturalHeight || i.height
            })).filter(i => (i.src.includes('googleusercontent.com') || i.src.includes('blob:') || i.src.includes('labs.google/fx')) && !i.src.includes('favicon'));
        }""")

        print(f"Found {len(imgs)} candidate images:")
        for i, im in enumerate(imgs):
            print(f"[{i:02d}] {im['w']}x{im['h']} | {im['src'][:90]}...")

        # If there are canvas images (large images > 200px)
        large_imgs = [im for im in imgs if im['w'] > 200 or im['h'] > 200 or 'googleusercontent.com' in im['src']]
        if large_imgs:
            out_img = Path("human_archive/runs/ep02_jang_huibin/full-v2-001/images/jh_ch1_001.jpg")
            out_img.parent.mkdir(parents=True, exist_ok=True)
            cand_url = large_imgs[-1]['src']
            print(f"Downloading real AI image from {cand_url[:80]}...")
            resp = await page.request.get(cand_url)
            if resp.status == 200:
                img_bytes = await resp.body()
                part = out_img.with_suffix('.jpg.part')
                part.write_bytes(img_bytes)
                with Image.open(part) as opened_im:
                    rgb = opened_im.convert("RGB")
                    if rgb.size != (1920, 1080):
                        rgb = rgb.resize((1920, 1080), Image.Resampling.LANCZOS)
                    rgb.save(out_img, format="JPEG", quality=95)
                if part.exists():
                    part.unlink()
                print(f"🎉 Saved image to {out_img} ({out_img.stat().st_size} bytes, 1920x1080)")


if __name__ == "__main__":
    asyncio.run(main())
