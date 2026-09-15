# -*- coding: utf-8 -*-
"""Test generating 1 shot in live Google Flow and saving image."""
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

        shot_id = "jh_ch1_001"
        prompt = (
            "Historical Korean documentary cinematography: Joseon Seonbi studying royal chronicle at night with candle and ink brush, "
            "located at Changgyeonggung Palace during 1701 Joseon Dynasty. "
            "Art style joseon_cinematic_ink_wash_hanji, authentic traditional Hanbok clothing, dramatic chiaroscuro, volumetric dust, 8k resolution, photorealistic matte oil painting texture."
        )
        out_img = Path(f"human_archive/runs/ep02_jang_huibin/full-v2-001/images/{shot_id}.jpg")
        out_img.parent.mkdir(parents=True, exist_ok=True)

        print(f"Submitting prompt for {shot_id}...")
        print(f"Prompt: {prompt[:80]}...")

        # 1. Find textbox
        textbox = await page.query_selector("div[role='textbox'], [contenteditable='true']")
        if not textbox:
            print("❌ Textbox not found!")
            return

        await textbox.click(force=True)
        await page.wait_for_timeout(200)
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(100)
        await page.keyboard.type(prompt, delay=2)
        await page.wait_for_timeout(300)

        # 2. Click arrow_forward / 만들기
        submit_btn = await page.query_selector("button:has-text('arrow_forward'), button:has-text('만들기')")
        if submit_btn and await submit_btn.is_visible():
            print("Clicking submit button...")
            await submit_btn.click(force=True)
        else:
            print("Pressing Enter...")
            await page.keyboard.press("Enter")

        print("Waiting for Google Flow generation (20s)...")
        await page.wait_for_timeout(20000)

        # 3. Find newest generated image
        media_list = await page.evaluate("""() => {
            const list = [];
            document.querySelectorAll('img').forEach(el => {
                const src = el.src || el.currentSrc || '';
                if (src && (src.includes('labs.google/fx/api') || src.includes('getMediaUrlRedirect') || src.includes('googleusercontent.com') || src.includes('blob:'))) {
                    list.push(src);
                }
            });
            return list;
        }""")

        print(f"Found {len(media_list)} media URLs on page.")
        if media_list:
            cand_url = media_list[-1]
            print(f"Downloading latest image: {cand_url[:80]}...")
            part_img = out_img.with_suffix(".jpg.part")
            resp = await page.request.get(cand_url)
            if resp.status == 200:
                img_bytes = await resp.body()
                part_img.write_bytes(img_bytes)
                with Image.open(part_img) as im:
                    im_rgb = im.convert("RGB")
                    if im_rgb.size != (1920, 1080):
                        im_rgb = im_rgb.resize((1920, 1080), Image.Resampling.LANCZOS)
                    im_rgb.save(out_img, format="JPEG", quality=95)
                if part_img.exists():
                    part_img.unlink()
                print(f"🎉 SUCCESS! Saved real Google Flow image to {out_img} ({out_img.stat().st_size} bytes, 1920x1080)")


if __name__ == "__main__":
    asyncio.run(main())
