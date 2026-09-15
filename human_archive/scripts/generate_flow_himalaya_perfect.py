# -*- coding: utf-8 -*-
"""Bulletproof Google Flow Batch Image Generator via Chrome CDP."""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import sys
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
MANIFEST_PATH = EP_DIR / "source" / "scene_script_manifest_v2.json"
IMAGES_DIR = EP_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


async def run_batch(start_idx: int = 1, count: int = 4):
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    scenes = manifest["scenes"]
    target_scenes = scenes[start_idx - 1 : start_idx - 1 + count]

    print(f"\n=================================================================")
    print(f"🎬 GOOGLE FLOW AI IMAGE GENERATOR (Himalaya 20m Episode)")
    print(f"   Generating Shots: #{start_idx} ~ #{start_idx + len(target_scenes) - 1} ({len(target_scenes)} shots)")
    print(f"=================================================================\n")

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
            print("❌ Google Flow tab not found in Chrome.")
            return

        print(f"✅ Connected to Google Flow: {flow_page.url}\n")
        await flow_page.bring_to_front()

        # Track existing media URLs so we only save newly generated images
        downloaded_urls = set()
        initial_imgs = await flow_page.evaluate("""() => {
            return Array.from(document.querySelectorAll('img')).map(i => i.src || i.currentSrc || '').filter(s => s && s.includes('getMediaUrlRedirect'));
        }""")
        downloaded_urls.update(initial_imgs)
        print(f"ℹ️ Found {len(initial_imgs)} existing generated images on canvas.")

        success_count = 0

        for idx, s in enumerate(target_scenes, start_idx):
            shot_id = s["shot_id"]
            out_img = IMAGES_DIR / f"{shot_id}.jpg"

            # Clean Google Flow prompt
            clean_prompt = s["midjourney_prompt"].split("--ar")[0].strip()
            if "--no" in clean_prompt:
                clean_prompt = clean_prompt.split("--no")[0].strip()

            print(f"\n[{idx:03d}/{len(scenes)}] 🎨 Processing {shot_id} ({s['visual_mode']})...")
            print(f"   Prompt: {clean_prompt[:85]}...")

            # 1. Wait for any active generation to finish
            for _ in range(30):
                stop_btn = await flow_page.query_selector("button:has-text('stop')")
                if stop_btn and await stop_btn.is_visible():
                    print("   ⏳ Waiting for previous generation to finish...")
                    await flow_page.wait_for_timeout(2000)
                else:
                    break

            # 2. Click & Focus the textbox
            tb = flow_page.locator("div[role='textbox'], [data-slate-editor='true']").first
            if await tb.count() == 0 or not await tb.is_visible():
                # Click on the prompt bar area to wake up textbox
                await flow_page.mouse.click(900, 915)
                await flow_page.wait_for_timeout(500)
                tb = flow_page.locator("div[role='textbox'], [data-slate-editor='true']").first

            if await tb.count() == 0:
                print(f"   ❌ Textbox not available for {shot_id}. Skipping.")
                continue

            await tb.click(force=True)
            await flow_page.wait_for_timeout(200)

            # Clear existing text
            await flow_page.keyboard.press("Control+A")
            await flow_page.keyboard.press("Backspace")
            await flow_page.wait_for_timeout(100)

            # Type the new prompt
            await flow_page.keyboard.type(clean_prompt, delay=3)
            await flow_page.wait_for_timeout(300)

            # 3. Click Submit (arrow_forward)
            arrow_btn = flow_page.locator("button:has-text('arrow_forward')").first
            if await arrow_btn.count() > 0 and await arrow_btn.is_visible():
                await arrow_btn.click()
            else:
                await flow_page.keyboard.press("Enter")

            print("   ⏳ Prompt submitted! Waiting for Google Flow to generate...")

            # 4. Wait for generation to start and complete (wait until stop button appears then disappears)
            await flow_page.wait_for_timeout(3000)
            for wait_sec in range(25): # Wait up to 25s
                stop_btn = await flow_page.query_selector("button:has-text('stop')")
                if stop_btn and await stop_btn.is_visible():
                    await flow_page.wait_for_timeout(1000)
                else:
                    # Generation finished!
                    break

            await flow_page.wait_for_timeout(2000) # Give DOM 2s to settle

            # 5. Extract newly generated image from DOM
            media_list = await flow_page.evaluate("""() => {
                const list = [];
                document.querySelectorAll('img').forEach(el => {
                    const src = el.src || el.currentSrc || '';
                    if (src.includes('getMediaUrlRedirect')) {
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
                cand_url = m["src"]
                if cand_url in downloaded_urls:
                    continue

                try:
                    resp = await flow_page.request.get(cand_url)
                    if resp.status == 200:
                        img_bytes = await resp.body()
                        if len(img_bytes) > 20000:
                            img = Image.open(io.BytesIO(img_bytes))
                            img_rgb = img.convert("RGB")
                            if img_rgb.size != (1920, 1080):
                                img_rgb = img_rgb.resize((1920, 1080), Image.Resampling.LANCZOS)
                            img_rgb.save(out_img, format="JPEG", quality=95)

                            downloaded_urls.add(cand_url)
                            downloaded = True
                            success_count += 1
                            stat = out_img.stat()
                            print(f"   ✅ Saved 1080p Full HD visual for {shot_id}: {out_img.name} ({stat.st_size // 1024} KB)")
                            break
                except Exception as ex:
                    print(f"   ⚠️ Download error for {cand_url}: {ex}")

            if not downloaded and out_img.exists():
                print(f"   ℹ️ Preserved existing visual for {shot_id}")
                success_count += 1

            await flow_page.wait_for_timeout(1000)

        print(f"\n=================================================================")
        print(f"🎉 Batch Finished: {success_count}/{len(target_scenes)} images successfully created!")
        print(f"📁 Destination: {IMAGES_DIR}")
        print(f"=================================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--count", type=int, default=4)
    args = parser.parse_args()
    asyncio.run(run_batch(start_idx=args.start, count=args.count))
