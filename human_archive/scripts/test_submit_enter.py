# -*- coding: utf-8 -*-
"""Click the exact right arrow submit button at (1236, 854) and press Enter."""
import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = [pg for ctx in browser.contexts for pg in ctx.pages if "flow" in pg.url or "labs.google" in pg.url][0]

        print("Focusing prompt textbox...")
        tb = await page.query_selector("div[role='textbox'], [contenteditable='true']")
        if tb:
            await tb.click()
            await page.wait_for_timeout(200)

        # 1. Click exact arrow_forward button at right side (x: 1236, y: 854)
        print("Clicking right arrow submit button at (1236, 854)...")
        await page.mouse.click(1236, 854)
        await page.wait_for_timeout(300)

        # 2. Also press Enter in textbox
        print("Pressing Enter...")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(5000)

        print("Waiting 15s for generation...")
        await page.wait_for_timeout(15000)

        # Check images
        imgs = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('img')).map(i => ({
                src: i.src || i.currentSrc || '',
                w: i.naturalWidth || i.width,
                h: i.naturalHeight || i.height
            })).filter(i => (i.src.includes('googleusercontent.com') || i.src.includes('blob:') || i.src.includes('labs.google/fx')) && !i.src.includes('flower-placeholder') && !i.src.includes('favicon'));
        }""")

        print(f"Generated images count: {len(imgs)}")
        for i, im in enumerate(imgs):
            print(f"[{i:02d}] {im['w']}x{im['h']} | {im['src'][:90]}...")


if __name__ == "__main__":
    asyncio.run(main())
