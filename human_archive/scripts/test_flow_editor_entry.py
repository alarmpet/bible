# -*- coding: utf-8 -*-
"""Test clicking 'Create with Google Flow' to enter the editor."""
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
        await page.wait_for_timeout(3000)

        # 1. Click Agree on cookie banner
        agree_btn = await page.query_selector("button:has-text('Agree')")
        if agree_btn and await agree_btn.is_visible():
            await agree_btn.click()
            print("Clicked 'Agree' on cookie banner.")
            await page.wait_for_timeout(1000)

        # 2. Click 'Create with Google Flow'
        create_btn = await page.query_selector("button:has-text('Create with Google Flow')")
        if not create_btn:
            create_btn = await page.query_selector("button:has-text('Try in Google Flow')")

        if create_btn:
            print("Clicking 'Create with Google Flow' button...")
            await create_btn.click()
            await page.wait_for_timeout(5000)

        print(f"After Click URL: {page.url}")
        print(f"After Click Title: {await page.title()}")

        # Check editor elements
        editor_elements = await page.evaluate("""() => {
            const list = [];
            document.querySelectorAll('button, a, input, textarea, div[role="button"], div[role="textbox"], [contenteditable="true"]').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    list.push({
                        tag: el.tagName,
                        text: (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('placeholder') || '').trim().substring(0, 80),
                        role: el.getAttribute('role') || '',
                        aria: el.getAttribute('aria-label') || '',
                        placeholder: el.getAttribute('placeholder') || ''
                    });
                }
            });
            return list;
        }""")

        print(f"\n--- Found {len(editor_elements)} Editor Elements ---")
        for i, el in enumerate(editor_elements[:25]):
            print(f"[{i:02d}] {el['tag']} | Role: {el['role']} | Text: {el['text']} | Aria: {el['aria']} | Ph: {el['placeholder']}")

        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
