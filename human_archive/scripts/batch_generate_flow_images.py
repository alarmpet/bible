# -*- coding: utf-8 -*-
"""Batch generate real AI images in Google Flow via Chrome CDP and save to images directory."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def generate_shots_batch(start_idx: int = 1, count: int = 68):
    run_dir = Path("human_archive/runs/ep01_pompeii_18hours")
    script_file = run_dir / "full_script_68shots.json"
    images_dir = run_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(script_file.read_text(encoding="utf-8"))
    shots = data["shots"]

    target_shots = shots[start_idx - 1 : start_idx - 1 + count]
    print(f"=== Starting Google Flow Batch Generation for {len(target_shots)} Shots (from #{start_idx}) ===")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        except Exception as e:
            print(f"Error connecting to Chrome CDP: {e}")
            return

        flow_page = None
        for page in browser.contexts[0].pages:
            if "flow" in page.url:
                flow_page = page
                break

        if not flow_page:
            print("Google Flow tab not found in Chrome.")
            return

        # Track already downloaded media URLs to detect new ones
        seen_media_urls = set()

        for idx, shot in enumerate(target_shots, start_idx):
            shot_id = shot["shot_id"]
            title = shot["title"]
            prompt = shot["prompt"]
            out_img = images_dir / f"{shot_id}.jpg"

            print(f"\n[{idx:02d}/{len(shots)}] Processing {shot_id}: {title}...")
            print(f"  Prompt: {prompt[:80]}...")

            # 1. Dismiss modal if any
            for close_sel in ["button:has-text('Agree')", "button:has-text('닫기')", "button:has-text('close')"]:
                b = await flow_page.query_selector(close_sel)
                if b and await b.is_visible():
                    await b.click()
                    await flow_page.wait_for_timeout(300)

            # 2. Find textbox and input prompt
            textbox = await flow_page.query_selector("div[role='textbox'], [contenteditable='true']")
            if not textbox:
                print("  Textbox not found, retrying...")
                await flow_page.wait_for_timeout(2000)
                textbox = await flow_page.query_selector("div[role='textbox'], [contenteditable='true']")

            if not textbox:
                print(f"  Error: Textbox not found for {shot_id}, skipping.")
                continue

            await textbox.click()
            await flow_page.wait_for_timeout(200)
            await flow_page.keyboard.press("Control+A")
            await flow_page.keyboard.press("Backspace")
            await flow_page.wait_for_timeout(100)
            await flow_page.keyboard.type(prompt, delay=5)
            await flow_page.wait_for_timeout(300)

            # 3. Click generate button
            submit_btn = await flow_page.query_selector("button:has-text('arrow_forward')")
            if submit_btn:
                await submit_btn.click()
                print("  Submitted prompt. Waiting for generation (~15s)...")
            else:
                await flow_page.keyboard.press("Enter")
                print("  Pressed Enter. Waiting for generation (~15s)...")

            # Wait for generation to complete
            await flow_page.wait_for_timeout(16000)

            # 4. Find latest generated image from page
            media_list = await flow_page.evaluate("""() => {
                const list = [];
                document.querySelectorAll('img').forEach(el => {
                    const src = el.src || el.currentSrc || '';
                    if (src.includes('labs.google/fx/api') || src.includes('getMediaUrlRedirect')) {
                        list.push({
                            src: src,
                            w: el.naturalWidth || el.width,
                            h: el.naturalHeight || el.height
                        });
                    }
                });
                return list;
            }""")

            downloaded = False
            for m in reversed(media_list):
                url = m["src"]
                if url not in seen_media_urls:
                    seen_media_urls.add(url)
                    try:
                        resp = await flow_page.request.get(url)
                        img_bytes = await resp.body()
                        if len(img_bytes) > 20000:
                            out_img.write_bytes(img_bytes)
                            print(f"  ✅ Saved Google Flow image to {out_img.name} ({len(img_bytes)} bytes)")
                            downloaded = True
                            break
                    except Exception as e:
                        print(f"  Download error: {e}")

            if not downloaded and media_list:
                # If all were seen, take the latest anyway
                latest_url = media_list[-1]["src"]
                resp = await flow_page.request.get(latest_url)
                img_bytes = await resp.body()
                out_img.write_bytes(img_bytes)
                print(f"  ✅ Saved latest image to {out_img.name} ({len(img_bytes)} bytes)")

        print("\n=== Google Flow Batch Generation Completed! ===")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--count", type=int, default=68)
    args = ap.parse_args()
    asyncio.run(generate_shots_batch(start_idx=args.start, count=args.count))
