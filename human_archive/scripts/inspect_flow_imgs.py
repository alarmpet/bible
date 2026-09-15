# -*- coding: utf-8 -*-
"""Inspect Google Flow images in the current open session."""
from __future__ import annotations

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
        flow_page = next((pg for pg in browser.contexts[0].pages if "flow" in pg.url), None)
        if not flow_page:
            print("Flow page not found in open tabs")
            return

        print(f"Connected to Flow page: {flow_page.url}")

        # Extract all image elements with src and bounding box
        imgs = await flow_page.evaluate("""() => {
            const list = [];
            document.querySelectorAll('img, [role="img"]').forEach((el, i) => {
                const rect = el.getBoundingClientRect();
                list.push({
                    index: i,
                    tagName: el.tagName,
                    src: el.src || el.currentSrc || el.getAttribute('src') || '',
                    width: rect.width,
                    height: rect.height,
                    alt: el.alt || ''
                });
            });
            return list;
        }""")

        print(f"Found {len(imgs)} images on Flow page:")
        for im in imgs:
            if im["width"] > 100 or "labs.google" in im["src"] or "googleusercontent" in im["src"]:
                print(f"  [{im['index']}] {im['width']}x{im['height']} | {im['src'][:100]} | Alt: {im['alt']}")


if __name__ == "__main__":
    asyncio.run(main())
