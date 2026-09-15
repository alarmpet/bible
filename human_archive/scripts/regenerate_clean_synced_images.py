# -*- coding: utf-8 -*-
"""Regenerate clean, watermark-free, perfectly synced images in Google Flow."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def generate_clean_synced_shots(shot_ids: list[str] | None = None):
    run_dir = Path("human_archive/runs/ep01_pompeii_18hours")
    script_file = run_dir / "full_script_68shots.json"
    images_dir = run_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(script_file.read_text(encoding="utf-8"))
    shots = data["shots"]

    if shot_ids:
        target_shots = [s for s in shots if s["shot_id"] in shot_ids]
    else:
        target_shots = shots

    print(f"=== Generating {len(target_shots)} Clean, Synced Images in Google Flow ===")

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        flow_page = [page for page in browser.contexts[0].pages if "flow" in page.url][0]

        for s_idx, shot in enumerate(target_shots, 1):
            shot_id = shot["shot_id"]
            title = shot["title"]
            prompt = shot["prompt"]
            out_img = images_dir / f"{shot_id}.jpg"

            print(f"\n[{s_idx:02d}/{len(target_shots)}] Generating {shot_id}: {title}...")
            print(f"  Prompt: {prompt[:80]}...")

            # Get current media list before generating
            pre_urls = await flow_page.evaluate("""() => {
                const s = new Set();
                document.querySelectorAll('img').forEach(el => {
                    const src = el.src || '';
                    if (src.includes('getMediaUrlRedirect')) s.add(src);
                });
                return Array.from(s);
            }""")

            # Focus and type clean prompt
            textbox = await flow_page.query_selector("div[role='textbox'], [contenteditable='true']")
            await textbox.click()
            await flow_page.wait_for_timeout(200)
            await flow_page.keyboard.press("Control+A")
            await flow_page.keyboard.press("Backspace")
            await flow_page.wait_for_timeout(100)
            await flow_page.keyboard.type(prompt, delay=4)
            await flow_page.wait_for_timeout(300)

            # Submit
            submit_btn = await flow_page.query_selector("button:has-text('arrow_forward')")
            if submit_btn:
                await submit_btn.click()
            else:
                await flow_page.keyboard.press("Enter")

            print("  Submitted. Waiting for generation (~18s)...")
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
            print(f"  ✅ Saved clean image for {shot_id} to {out_img.name} ({len(img_bytes)} bytes)")

    print("\n=== Clean Synced Image Generation Completed! ===")


if __name__ == "__main__":
    # Regenerate Chapter 1 (shots 1 to 10) first to guarantee 100% clean sync and no logo
    ch1_shot_ids = [f"ch1_{i:02d}" for i in range(1, 11)]
    asyncio.run(generate_clean_synced_shots(ch1_shot_ids))
