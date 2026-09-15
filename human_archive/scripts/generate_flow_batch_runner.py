# -*- coding: utf-8 -*-
"""Robust Google Flow Batch Image Generator via Chrome CDP."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from PIL import Image
import io
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
MANIFEST_PATH = EP_DIR / "source" / "scene_script_manifest_v2.json"
IMAGES_DIR = EP_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


async def run_flow_batch(start_idx: int = 1, count: int = 4):
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    scenes = manifest["scenes"]
    target_scenes = scenes[start_idx - 1 : start_idx - 1 + count]

    print(f"\n=======================================================")
    print(f"🚀 Google Flow Batch Generator (Himalaya 20m Episode)")
    print(f"   Target: Shots #{start_idx} ~ #{start_idx + len(target_scenes) - 1} ({len(target_scenes)} shots)")
    print(f"=======================================================\n")

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        flow_page = None
        for ctx in browser.contexts:
            for page in ctx.pages:
                if "flow" in page.url:
                    flow_page = page
                    break
            if flow_page:
                break

        if not flow_page:
            print("❌ Google Flow tab not found.")
            return

        print(f"✅ Connected to Google Flow: {flow_page.url}\n")
        await flow_page.bring_to_front()

        # Track already known media URLs
        seen_media_urls = set()
        initial_media = await flow_page.evaluate("""() => {
            const list = [];
            document.querySelectorAll('img').forEach(el => {
                const src = el.src || el.currentSrc || '';
                if (src) list.push(src);
            });
            return list;
        }""")
        seen_media_urls.update(initial_media)

        successful_shots = 0

        for idx, s in enumerate(target_scenes, start_idx):
            shot_id = s["shot_id"]
            out_img = IMAGES_DIR / f"{shot_id}.jpg"

            # Prepare clean prompt
            clean_prompt = s["midjourney_prompt"].split("--ar")[0].strip()
            if "--no" in clean_prompt:
                clean_prompt = clean_prompt.split("--no")[0].strip()

            print(f"[{idx:03d}/{len(scenes)}] 🎨 Processing {shot_id} ({s['visual_mode']})...")
            print(f"     Prompt: {clean_prompt[:85]}...")

            # 1. Dismiss any overlay dialogs
            for close_sel in ["button:has-text('닫기')", "button:has-text('Agree')", "button[aria-label='닫기']"]:
                b = flow_page.locator(close_sel).first
                if await b.count() > 0 and await b.is_visible():
                    try:
                        await b.click()
                        await flow_page.wait_for_timeout(300)
                    except Exception:
                        pass

            # 2. Locate and focus the textbox
            tb = flow_page.locator("div[role='textbox'], [data-slate-editor='true']").first
            if await tb.count() == 0 or not await tb.is_visible():
                print("   ⚠️ Textbox not visible, waiting 2s...")
                await flow_page.wait_for_timeout(2000)
                tb = flow_page.locator("div[role='textbox'], [data-slate-editor='true']").first

            if await tb.count() == 0:
                print(f"   ❌ Textbox not found for {shot_id}, skipping.")
                continue

            await tb.click()
            await flow_page.wait_for_timeout(200)

            # Clear existing text
            await flow_page.keyboard.press("Control+A")
            await flow_page.keyboard.press("Backspace")
            await flow_page.wait_for_timeout(100)

            # Type the new prompt
            await flow_page.keyboard.type(clean_prompt, delay=3)
            await flow_page.wait_for_timeout(300)

            # 3. Click submit button
            submit_btn = flow_page.locator("button:has-text('arrow_forward')").first
            if await submit_btn.count() > 0 and await submit_btn.is_visible():
                await submit_btn.click()
            else:
                await flow_page.keyboard.press("Enter")

            print("   ⏳ Prompt submitted. Waiting for image generation (~18s)...")
            
            # Wait for generation and poll for newly added media
            downloaded = False
            for wait_cycle in range(9): # Wait up to 18 seconds (9 * 2s)
                await flow_page.wait_for_timeout(2000)

                media_list = await flow_page.evaluate("""() => {
                    const list = [];
                    document.querySelectorAll('img').forEach(el => {
                        const src = el.src || el.currentSrc || '';
                        if (src.includes('getMediaUrlRedirect') || src.includes('googleusercontent.com') || src.includes('labs.google/fx/api')) {
                            list.push({
                                src: src,
                                w: el.naturalWidth || el.width,
                                h: el.naturalHeight || el.height
                            });
                        }
                    });
                    return list;
                }""")

                # Look for new images
                for m in reversed(media_list):
                    url = m["src"]
                    if url not in seen_media_urls:
                        seen_media_urls.add(url)
                        try:
                            resp = await flow_page.request.get(url)
                            if resp.status == 200:
                                img_bytes = await resp.body()
                                if len(img_bytes) > 20000:
                                    img = Image.open(io.BytesIO(img_bytes))
                                    img.convert("RGB").save(out_img, quality=95)
                                    print(f"   ✅ Saved {out_img.name} ({out_img.stat().st_size:,} bytes | {img.size[0]}x{img.size[1]})")
                                    downloaded = True
                                    successful_shots += 1
                                    break
                        except Exception as e:
                            print(f"   ⚠️ Download error: {e}")

                if downloaded:
                    break

            if not downloaded:
                print(f"   ⚠️ Generation timed out or image not intercepted for {shot_id}")

            await flow_page.wait_for_timeout(1000)

        print(f"\n🎉 Batch Finished: {successful_shots}/{len(target_scenes)} images successfully generated and saved!")
        print(f"📁 Output Directory: {IMAGES_DIR}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--count", type=int, default=4)
    args = parser.parse_args()
    asyncio.run(run_flow_batch(start_idx=args.start, count=args.count))
