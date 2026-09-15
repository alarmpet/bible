# -*- coding: utf-8 -*-
"""Test clicking the generate button using mouse click on exact coordinates."""
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

        # Find button with 'arrow_forward'
        btns = await page.query_selector_all("button")
        target_btn = None
        for b in btns:
            txt = await b.inner_text()
            if "arrow_forward" in txt or "만들기" in txt:
                box = await b.bounding_box()
                if box and box["y"] > 700:
                    target_btn = b
                    btn_box = box
                    break

        if target_btn:
            cx = btn_box["x"] + btn_box["width"] / 2
            cy = btn_box["y"] + btn_box["height"] / 2
            print(f"Found generate button at ({cx}, {cy}). Clicking via page.mouse.click...")
            await page.mouse.click(cx, cy)
            await page.wait_for_timeout(1000)
            print("Also triggering target_btn.click()...")
            try:
                await target_btn.click(force=True)
            except Exception:
                pass
            print("Waiting for generation to start...")
            await page.wait_for_timeout(5000)
        else:
            print("Target button not found, pressing Enter...")
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(5000)

        print("Checked after click.")


if __name__ == "__main__":
    asyncio.run(main())
