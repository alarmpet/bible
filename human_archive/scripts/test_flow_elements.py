# -*- coding: utf-8 -*-
"""Inspect Google Flow elements via Playwright."""
import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def main():
    async with async_playwright() as p:
        user_dir = Path("C:/Users/shs/.playwright_flow_profile")
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=user_dir,
            headless=False,
            channel="chrome",
            viewport={"width": 1920, "height": 1080},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://labs.google/fx/tools/flow?from=imagefx")
        await page.wait_for_timeout(6000)

        print(f"Final URL: {page.url}")
        print(f"Final Title: {await page.title()}")

        elements = await page.evaluate("""() => {
            const items = [];
            document.querySelectorAll('button, a, input, textarea, div[role="button"], div[role="textbox"], [contenteditable="true"]').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    items.push({
                        tag: el.tagName,
                        text: (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('placeholder') || '').trim().substring(0, 80),
                        role: el.getAttribute('role') || '',
                        aria: el.getAttribute('aria-label') || '',
                        placeholder: el.getAttribute('placeholder') || ''
                    });
                }
            });
            return items;
        }""")

        print(f"\n--- Found {len(elements)} Interactive Elements ---")
        for i, el in enumerate(elements[:35]):
            print(f"[{i:02d}] {el['tag']} | Role: {el['role']} | Text: {el['text']} | Aria: {el['aria']} | Ph: {el['placeholder']}")

        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
