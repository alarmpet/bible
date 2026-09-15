# -*- coding: utf-8 -*-
"""Generate single missing shot mc_ch1_001 on Google Flow."""
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

        shot_id = "mc_ch1_001"
        prompt = (
            "Masterpiece Korean historical webtoon style manhwa illustration: Joseon Seonbi Hwang Hyeon writing by candlelight in dark wooden study room, "
            "located at Gurye Seojae Study during 1864-1910 Late Joseon Dynasty. Fine delicate ink contour line work, rich Hanji color wash, dramatic chiaroscuro candle lighting with deep obsidian shadows and warm amber rim light, volumetric dust particles, 8k resolution, cinematic anime keyframe, trending on Webtoon, highly detailed"
        )
        out_img = Path(f"human_archive/runs/ep03_maecheon/full-v3-001/images/{shot_id}.jpg")
        part_img = out_img.with_suffix(".jpg.part")

        # Focus & Type
        tb = await page.query_selector("div[role='textbox'], [contenteditable='true']")
        if tb:
            await tb.click(force=True)
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await page.keyboard.type(prompt, delay=2)
            await page.mouse.click(1236, 854)
            await page.keyboard.press("Enter")
            print("Prompt submitted. Waiting 18s...")
            await page.wait_for_timeout(18000)

        # Download
        media_list = await page.evaluate("""() => Array.from(document.querySelectorAll('img')).map(i => i.src || '').filter(s => (s.includes('labs.google/fx/api') || s.includes('getMediaUrlRedirect') || s.includes('googleusercontent.com')) && !s.includes('flower-placeholder'))""")
        if media_list:
            resp = await page.request.get(media_list[-1])
            if resp.status == 200:
                part_img.write_bytes(await resp.body())
                with Image.open(part_img) as im:
                    rgb = im.convert("RGB")
                    if rgb.size != (1920, 1080):
                        rgb = rgb.resize((1920, 1080), Image.Resampling.LANCZOS)
                    rgb.save(out_img, format="JPEG", quality=95)
                if part_img.exists():
                    part_img.unlink()
                print(f"🎉 Saved {out_img} ({out_img.stat().st_size} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
