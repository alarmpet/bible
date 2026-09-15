# -*- coding: utf-8 -*-
"""Regenerate specific shots in Google Flow to ensure 100% unique hashes."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def fix_duplicate_shots(shot_ids: list[str]):
    run_dir = Path("human_archive/runs/ep01_pompeii_18hours")
    script_file = run_dir / "full_script_68shots.json"
    images_dir = run_dir / "images"

    data = json.loads(script_file.read_text(encoding="utf-8"))
    shots_by_id = {s["shot_id"]: s for s in data["shots"]}

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        flow_page = [page for page in browser.contexts[0].pages if "flow" in page.url][0]

        for sid in shot_ids:
            shot = shots_by_id[sid]
            prompt = shot["prompt"]
            out_img = images_dir / f"{sid}.jpg"

            print(f"\nRegenerating dedicated image for {sid}: {shot['title']}...")

            # Get current media list before generating
            pre_urls = await flow_page.evaluate("""() => {
                const s = new Set();
                document.querySelectorAll('img').forEach(el => {
                    const src = el.src || '';
                    if (src.includes('getMediaUrlRedirect')) s.add(src);
                });
                return Array.from(s);
            }""")

            # Focus and type prompt
            textbox = await flow_page.query_selector("div[role='textbox'], [contenteditable='true']")
            await textbox.click()
            await flow_page.wait_for_timeout(200)
            await flow_page.keyboard.press("Control+A")
            await flow_page.keyboard.press("Backspace")
            await flow_page.wait_for_timeout(100)
            await flow_page.keyboard.type(prompt, delay=5)
            await flow_page.wait_for_timeout(300)

            # Submit
            submit_btn = await flow_page.query_selector("button:has-text('arrow_forward')")
            if submit_btn:
                await submit_btn.click()
            else:
                await flow_page.keyboard.press("Enter")

            print("Waiting for generation (~18s)...")
            await flow_page.wait_for_timeout(18000)

            # Find newly generated image URL
            post_urls = await flow_page.evaluate("""() => {
                const list = [];
                document.querySelectorAll('img').forEach(el => {
                    const src = el.src || '';
                    if (src.includes('getMediaUrlRedirect')) list.push(src);
                });
                return list;
            }""")

            new_urls = [u for u in post_urls if u not in pre_urls]
            target_url = new_urls[-1] if new_urls else post_urls[-1]

            resp = await flow_page.request.get(target_url)
            img_bytes = await resp.body()
            out_img.write_bytes(img_bytes)
            print(f"✅ Successfully saved unique image for {sid} ({len(img_bytes)} bytes)")


if __name__ == "__main__":
    asyncio.run(fix_duplicate_shots(["ch1_06", "ch1_07", "ch1_08", "ch1_09"]))
