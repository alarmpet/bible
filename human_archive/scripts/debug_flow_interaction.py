# -*- coding: utf-8 -*-
"""Debug Google Flow prompt submission and take screenshot."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def debug_flow():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        flow_page = [page for page in browser.contexts[0].pages if "flow" in page.url][0]

        shot_prompt = "Cinematic epic documentary shot. Mount Vesuvius erupting in background with a colossal 30km black ash plume over ancient Pompeii streets AD 79, photorealistic 8k."

        print("Focusing textbox...")
        textbox = await flow_page.query_selector("div[role='textbox'], [contenteditable='true']")
        if textbox:
            await textbox.click()
            await flow_page.wait_for_timeout(300)
            
            # Select all and delete previous text
            await flow_page.keyboard.press("Control+A")
            await flow_page.keyboard.press("Backspace")
            await flow_page.wait_for_timeout(200)

            # Type text using real keyboard strokes
            print("Typing prompt with keyboard...")
            await flow_page.keyboard.type(shot_prompt, delay=15)
            await flow_page.wait_for_timeout(500)

            # Press Enter
            print("Pressing Enter...")
            await flow_page.keyboard.press("Enter")
            await flow_page.wait_for_timeout(1000)

            # Also click the generate button if Enter doesn't trigger
            submit_btn = await flow_page.query_selector("button:has(i:has-text('arrow_forward')), button[aria-label*='만들기'], button:has-text('arrow_forward')")
            if submit_btn and await submit_btn.is_visible():
                print("Clicking submit button...")
                await submit_btn.click()

            print("Waiting 15 seconds for Google Flow to generate...")
            await flow_page.wait_for_timeout(15000)

            # Take screenshot
            ss_path = Path(r"C:\Users\shs\.gemini\antigravity\brain\a0949ae3-8f9f-4702-af2f-0b95fe1fdedc\flow_debug_screenshot.png")
            await flow_page.screenshot(path=str(ss_path))
            print(f"Screenshot saved to: {ss_path}")


if __name__ == "__main__":
    asyncio.run(debug_flow())
