# -*- coding: utf-8 -*-
"""Inspect prompt box and submit button on live Google Flow."""
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

        print("Inspecting buttons in the prompt container...")
        buttons = await page.evaluate("""() => {
            const list = [];
            document.querySelectorAll('button, [role="button"]').forEach(b => {
                const rect = b.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    list.push({
                        text: (b.innerText || '').trim(),
                        aria: b.getAttribute('aria-label') || '',
                        classes: b.className,
                        html: b.outerHTML.substring(0, 150),
                        rect: { x: rect.x, y: rect.y, w: rect.width, h: rect.height }
                    });
                }
            });
            return list;
        }""")

        for i, b in enumerate(buttons):
            print(f"[{i:02d}] Text: '{b['text']}' | Aria: '{b['aria']}' | HTML: {b['html']} | Rect: {b['rect']}")


if __name__ == "__main__":
    asyncio.run(main())
