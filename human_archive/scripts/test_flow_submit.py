# -*- coding: utf-8 -*-
"""Click Agree modal and submit generation prompt in Google Flow."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def test_submit():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        flow_page = [page for page in browser.contexts[0].pages if "flow" in page.url][0]

        # 1. Click Agree modal button
        agree_btn = await flow_page.query_selector("button:has-text('Agree')")
        if agree_btn and await agree_btn.is_visible():
            print("Clicking Agree modal button...")
            await agree_btn.click()
            await flow_page.wait_for_timeout(1000)

        # 2. Find textbox and input prompt
        textbox = await flow_page.query_selector("div[role='textbox'], [contenteditable='true']")
        if not textbox:
            print("Textbox not found.")
            return

        prompt = "Cinematic epic wide shot, National Geographic documentary. Mount Vesuvius violently erupting in background with a colossal 30km black ash plume rising into clear blue sky over ancient Roman Pompeii AD 79, photorealistic 8k."

        print("Focusing textbox and typing prompt...")
        await textbox.click()
        await flow_page.wait_for_timeout(300)
        await flow_page.keyboard.type(prompt, delay=10)
        await flow_page.wait_for_timeout(500)

        # 3. Click 만들기 (arrow_forward) button
        submit_btn = await flow_page.query_selector("button:has-text('arrow_forward')")
        if submit_btn:
            print("Clicking 'arrow_forward' 만들기 button...")
            await submit_btn.click()
            print("Successfully clicked submit! Waiting 20s for generation...")
            await flow_page.wait_for_timeout(20000)

        # 4. Take screenshot of result
        ss_path = Path(r"C:\Users\shs\.gemini\antigravity\brain\a0949ae3-8f9f-4702-af2f-0b95fe1fdedc\flow_generated_result.png")
        await flow_page.screenshot(path=str(ss_path))
        print(f"Result screenshot saved: {ss_path}")


if __name__ == "__main__":
    asyncio.run(test_submit())
