# -*- coding: utf-8 -*-
"""Inspect Google Flow page over CDP."""
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
        pages = [pg for ctx in browser.contexts for pg in ctx.pages if "flow" in pg.url or "labs.google" in pg.url]
        if not pages:
            print("No Google Flow tab found!")
            return

        page = pages[0]
        print(f"Connected Page URL: {page.url}")
        print(f"Connected Page Title: {await page.title()}")

        elements = await page.evaluate("""() => {
            const res = [];
            document.querySelectorAll('button, a, input, textarea, div[role="button"], div[role="textbox"], [contenteditable="true"]').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    res.push({
                        tag: el.tagName,
                        text: (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('placeholder') || '').trim().substring(0, 80),
                        role: el.getAttribute('role') || '',
                        aria: el.getAttribute('aria-label') || '',
                        placeholder: el.getAttribute('placeholder') || '',
                        href: el.getAttribute('href') || ''
                    });
                }
            });
            return res;
        }""")

        print(f"\n--- Found {len(elements)} Elements on Active Tab ---")
        for i, el in enumerate(elements[:30]):
            print(f"[{i:02d}] {el['tag']} | Role: {el['role']} | Text: {el['text']} | Aria: {el['aria']} | Href: {el['href']}")


if __name__ == "__main__":
    asyncio.run(main())
