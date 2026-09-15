# -*- coding: utf-8 -*-
"""Test generating 1 shot in Google Flow via CDP."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def generate_single_test():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        flow_page = None
        for page in browser.contexts[0].pages:
            if "flow" in page.url:
                flow_page = page
                break

        if not flow_page:
            print("Flow page not found.")
            return

        print("Testing single prompt generation in Google Flow...")

        # 1. Find the prompt textbox
        textbox = await flow_page.query_selector("div[role='textbox'], [contenteditable='true']")
        if not textbox:
            print("Textbox not found.")
            return

        test_prompt = "Cinematic epic wide shot, National Geographic documentary. Mount Vesuvius violently erupting in background with a colossal 30km black ash plume rising into clear blue sky over ancient Roman Pompeii AD 79, photorealistic 8k."
        
        await textbox.click()
        await flow_page.wait_for_timeout(300)
        await textbox.fill(test_prompt)
        await flow_page.wait_for_timeout(500)
        print("Filled prompt into textbox.")

        # 2. Click 만들기 (Generate) button
        gen_btn = await flow_page.query_selector("button:has-text('arrow_forward'), button:has-text('만들기')")
        if gen_btn:
            print("Clicking '만들기' (Generate)...")
            await gen_btn.click()
            print("Waiting for generation...")
            await flow_page.wait_for_timeout(10000)

        # 3. Check for generated media cards / images on canvas
        images = await flow_page.evaluate("""() => {
            const imgs = [];
            document.querySelectorAll('img').forEach(img => {
                if (img.src && !img.src.includes('avatar') && !img.src.includes('icon') && !img.src.includes('favicon')) {
                    imgs.push({
                        src: img.src.substring(0, 100),
                        width: img.naturalWidth || img.width,
                        height: img.naturalHeight || img.height,
                        alt: img.alt || ''
                    });
                }
            });
            return imgs;
        }""")

        print(f"\nFound {len(images)} images on page:")
        for i, img in enumerate(images):
            print(f"[{i:02d}] {img['width']}x{img['height']} | {img['src'][:60]}")


if __name__ == "__main__":
    asyncio.run(generate_single_test())
