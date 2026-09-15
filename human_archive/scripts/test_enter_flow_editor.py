# -*- coding: utf-8 -*-
"""Test entering the project editor and inspecting the prompt UI."""
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

        # 1. Close overlay if any
        close_btn = await page.query_selector("button:has-text('닫기'), button[aria-label='닫기']")
        if close_btn and await close_btn.is_visible():
            await close_btn.click()
            await page.wait_for_timeout(500)

        # 2. Click existing project or navigate to project
        proj_link = await page.query_selector("a[href*='/project/']")
        if proj_link:
            print("Found project link, clicking...")
            await proj_link.click()
            await page.wait_for_timeout(4000)

        print(f"Current URL: {page.url}")
        print(f"Current Title: {await page.title()}")

        # 3. Inspect editor UI elements
        elements = await page.evaluate("""() => {
            const res = [];
            document.querySelectorAll('button, textarea, input, div[role="button"], div[role="textbox"], [contenteditable="true"]').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    res.push({
                        tag: el.tagName,
                        text: (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('placeholder') || '').trim().substring(0, 80),
                        role: el.getAttribute('role') || '',
                        aria: el.getAttribute('aria-label') || '',
                        placeholder: el.getAttribute('placeholder') || '',
                        classes: el.className
                    });
                }
            });
            return res;
        }""")

        print(f"\n--- Found {len(elements)} Elements in Project Editor ---")
        for i, el in enumerate(elements[:35]):
            print(f"[{i:02d}] {el['tag']} | Role: {el['role']} | Text: {el['text']} | Aria: {el['aria']} | Ph: {el['placeholder']}")


if __name__ == "__main__":
    asyncio.run(main())
