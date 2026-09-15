# -*- coding: utf-8 -*-
"""Generate Google Flow AI Images via Chrome CDP for Himalaya GLOF Episode."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
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


async def generate_flow_shots(start_idx: int = 1, count: int = 4):
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    scenes = manifest["scenes"]
    target_scenes = scenes[start_idx - 1 : start_idx - 1 + count]

    print(f"\n=================================================================")
    print(f"🎬 GOOGLE FLOW BATCH GENERATOR: SHOTS #{start_idx} ~ #{start_idx + len(target_scenes) - 1} (Total: {len(target_scenes)})")
    print(f"=================================================================\n")

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        pages = [pg for ctx in browser.contexts for pg in ctx.pages if "flow" in pg.url or "labs.google" in pg.url]
        if not pages:
            print("❌ Google Flow tab not found in Chrome!")
            return

        page = pages[0]
        print(f"✅ Connected to Google Flow tab: {page.url}\n")
        await page.bring_to_front()

        downloaded_urls = set()
        # Find existing images on canvas
        existing_imgs = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('img')).map(i => i.src || i.currentSrc || '').filter(s => s && (s.includes('labs.google/fx/api') || s.includes('getMediaUrlRedirect') || s.includes('googleusercontent.com')));
        }""")
        downloaded_urls.update(existing_imgs)
        print(f"Already seen {len(existing_imgs)} media URLs on canvas.")

        success_count = 0

        for idx, s in enumerate(target_scenes, start_idx):
            shot_id = s["shot_id"]
            out_img = IMAGES_DIR / f"{shot_id}.jpg"
            part_img = IMAGES_DIR / f"{shot_id}.jpg.part"

            # Clean Google Flow prompt (remove midjourney parameters)
            clean_prompt = s["midjourney_prompt"].split("--ar")[0].strip()
            if "--no" in clean_prompt:
                clean_prompt = clean_prompt.split("--no")[0].strip()

            print(f"\n[{idx:03d}/{len(scenes)}] 🎨 Generating {shot_id} ({s['visual_mode']})...")
            print(f"  Prompt: {clean_prompt[:90]}...")

            # 1. Focus textbox
            textbox = await page.query_selector("div[role='textbox'], [data-slate-editor='true'], [contenteditable='true']")
            if not textbox:
                await page.wait_for_timeout(2000)
                textbox = await page.query_selector("div[role='textbox'], [data-slate-editor='true'], [contenteditable='true']")

            if textbox:
                try:
                    await textbox.click(force=True)
                    await page.wait_for_timeout(200)
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Backspace")
                    await page.wait_for_timeout(100)
                    await page.keyboard.type(clean_prompt, delay=3)
                    await page.wait_for_timeout(300)

                    # 2. Click submit button or press Enter
                    submit_btn = await page.query_selector("button:has-text('arrow_forward')")
                    if submit_btn and await submit_btn.is_visible():
                        await submit_btn.click()
                    else:
                        await page.keyboard.press("Enter")

                    print(f"  ⏳ Prompt submitted. Waiting 18s for Google Flow generation...")
                    await page.wait_for_timeout(18000)
                except Exception as ex:
                    print(f"  ⚠️ Error during submission: {ex}")

            # 3. Download newly generated image
            media_list = await page.evaluate("""() => {
                const list = [];
                document.querySelectorAll('img').forEach(el => {
                    const src = el.src || el.currentSrc || '';
                    if (src && (src.includes('labs.google/fx/api') || src.includes('getMediaUrlRedirect') || src.includes('googleusercontent.com')) && !src.includes('flower-placeholder') && !src.includes('favicon')) {
                        list.push(src);
                    }
                });
                return list;
            }""")

            downloaded = False
            for cand_url in reversed(media_list):
                if cand_url in downloaded_urls:
                    continue
                try:
                    resp = await page.request.get(cand_url)
                    if resp.status == 200:
                        img_bytes = await resp.body()
                        if len(img_bytes) > 20000:
                            part_img.write_bytes(img_bytes)
                            with Image.open(part_img) as im:
                                im_rgb = im.convert("RGB")
                                if im_rgb.size != (1920, 1080):
                                    im_rgb = im_rgb.resize((1920, 1080), Image.Resampling.LANCZOS)
                                im_rgb.save(out_img, format="JPEG", quality=95)

                            if part_img.exists():
                                part_img.unlink()

                            downloaded_urls.add(cand_url)
                            downloaded = True
                            success_count += 1
                            stat = out_img.stat()
                            print(f"  ✅ Saved Google Flow 1080p visual for {shot_id}: {out_img.name} ({stat.st_size // 1024} KB)")
                            break
                except Exception as ex:
                    print(f"  ⚠️ Error downloading {cand_url}: {ex}")

            if not downloaded and out_img.exists():
                print(f"  ℹ️ Using existing image for {shot_id}")
                success_count += 1

            await page.wait_for_timeout(1000)

        print(f"\n=================================================================")
        print(f"🎉 Google Flow Generation Finished: {success_count}/{len(target_scenes)} images saved!")
        print(f"📁 Destination: {IMAGES_DIR}")
        print(f"=================================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--count", type=int, default=4)
    args = parser.parse_args()
    asyncio.run(generate_flow_shots(start_idx=args.start, count=args.count))
