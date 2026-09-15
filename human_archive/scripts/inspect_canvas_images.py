# -*- coding: utf-8 -*-
"""Inspect generated images on canvas."""
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

        imgs = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('img')).map(i => ({
                src: i.src || i.currentSrc || '',
                w: i.naturalWidth || i.width,
                h: i.naturalHeight || i.height
            })).filter(i => (i.src.includes('googleusercontent.com') || i.src.includes('blob:') || i.src.includes('labs.google/fx')) && !i.src.includes('favicon'));
        }""")

        print(f"Found {len(imgs)} generated images on canvas:")
        for i, im in enumerate(imgs):
            print(f"[{i:02d}] {im['w']}x{im['h']} | {im['src'][:90]}...")


if __name__ == "__main__":
    asyncio.run(main())
