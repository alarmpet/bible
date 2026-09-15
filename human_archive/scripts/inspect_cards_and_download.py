# -*- coding: utf-8 -*-
"""Inspect Google Flow generation cards, progress, and download mechanism."""
from __future__ import annotations

import asyncio
import base64
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def inspect_cards_and_download():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        flow_page = [page for page in browser.contexts[0].pages if "flow" in page.url][0]

        print("Inspecting Google Flow cards and images...")
        await flow_page.wait_for_timeout(5000)

        # Check all image elements on page
        images = await flow_page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('img, video, canvas, [role="img"]').forEach(el => {
                const rect = el.getBoundingClientRect();
                const src = el.src || el.getAttribute('data-src') || el.style.backgroundImage || '';
                results.push({
                    tag: el.tagName,
                    src: src.substring(0, 150),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height),
                    naturalW: el.naturalWidth || 0,
                    naturalH: el.naturalHeight || 0
                });
            });
            return results;
        }""")

        print(f"\nFound {len(images)} media elements:")
        for i, img in enumerate(images):
            if img['w'] > 50 or img['h'] > 50:
                print(f"[{i:02d}] <{img['tag']}> {img['w']}x{img['h']} (nat: {img['naturalW']}x{img['naturalH']}) | {img['src']}")

        # Check if there is a download button or context menu
        download_btns = await flow_page.query_selector_all("button[aria-label*='다운로드'], button[aria-label*='Download'], button:has-text('다운로드'), [aria-label*='more_vert']")
        print(f"\nFound {len(download_btns)} download/action buttons.")


if __name__ == "__main__":
    asyncio.run(inspect_cards_and_download())
