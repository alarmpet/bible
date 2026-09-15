# -*- coding: utf-8 -*-
"""Generate Google Flow AI Images via Chrome CDP for Himalaya GLOF Episode."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
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

    print(f"\n=======================================================")
    print(f"🚀 Google Flow CDP Image Generator (Nollam Himalaya EP)")
    print(f"   Target Shots: #{start_idx} ~ #{start_idx + len(target_scenes) - 1} (Total: {len(target_scenes)})")
    print(f"=======================================================\n")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            print(" Connected to Chrome CDP (port 9222).")
        except Exception as e:
            print(f"❌ Error connecting to Chrome CDP: {e}")
            return

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

        print(f" Active Flow Tab: {flow_page.url}\n")
        await flow_page.bring_to_front()

        # Track existing media URLs so we capture only new generations
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

        for i, s in enumerate(target_scenes, start_idx):
            shot_id = s["shot_id"]
            out_img = IMAGES_DIR / f"{shot_id}.jpg"

            # Clean Google Flow prompt (without Midjourney specific parameters like --ar 16:9 --style raw --v 6.0)
            clean_prompt = s["midjourney_prompt"].split("--ar")[0].strip()
            # Remove negative prompt if present
            if "--no" in clean_prompt:
                clean_prompt = clean_prompt.split("--no")[0].strip()

            print(f"[{i:03d}/{len(scenes)}] 🎨 Generating {shot_id} ({s['visual_mode']})...")
            print(f"     Prompt: {clean_prompt[:90]}...")

            # 1. Check & close popups
            for close_sel in ["button:has-text('닫기')", "button:has-text('Agree')", "button[aria-label='닫기']"]:
                b = await flow_page.query_selector(close_sel)
                if b and await b.is_visible():
                    await b.click()
                    await flow_page.wait_for_timeout(300)

            # 2. Find textbox
            textbox = await flow_page.query_selector("div[role='textbox'], [contenteditable='true'], textarea")
            if not textbox:
                print("   ⚠️ Textbox not found, waiting 2s...")
                await flow_page.wait_for_timeout(2000)
                textbox = await flow_page.query_selector("div[role='textbox'], [contenteditable='true'], textarea")

            if not textbox:
                print(f"   ❌ Failed to locate textbox for {shot_id}. Skipping.")
                continue

            await textbox.click()
            await flow_page.wait_for_timeout(200)
            await flow_page.keyboard.press("Control+A")
            await flow_page.keyboard.press("Backspace")
            await flow_page.wait_for_timeout(100)
            await flow_page.keyboard.type(clean_prompt, delay=3)
            await flow_page.wait_for_timeout(300)

            # 3. Submit generation
            submit_btn = await flow_page.query_selector("button:has-text('arrow_forward'), button[aria-label='만들기'], button[aria-label='생성']")
            if submit_btn and await submit_btn.is_visible():
                await submit_btn.click()
            else:
                await flow_page.keyboard.press("Enter")

            print("   ⏳ Prompt submitted. Waiting for generation (~15s)...")
            await flow_page.wait_for_timeout(15000)

            # 4. Detect newly generated image
            downloaded = False
            for retry in range(5):
                media_list = await flow_page.evaluate("""() => {
                    const list = [];
                    document.querySelectorAll('img').forEach(el => {
                        const src = el.src || el.currentSrc || '';
                        if (src.includes('labs.google/fx/api') || src.includes('getMediaUrlRedirect') || src.includes('googleusercontent.com')) {
                            list.push({
                                src: src,
                                w: el.naturalWidth || el.width,
                                h: el.naturalHeight || el.height
                            });
                        }
                    });
                    return list;
                }""")

                for m in reversed(media_list):
                    url = m["src"]
                    if url not in seen_media_urls:
                        seen_media_urls.add(url)
                        try:
                            resp = await flow_page.request.get(url)
                            img_bytes = await resp.body()
                            if len(img_bytes) > 20000:
                                out_img.write_bytes(img_bytes)
                                print(f"   ✅ Saved {out_img.name} ({len(img_bytes):,} bytes | {m['w']}x{m['h']})")
                                downloaded = True
                                break
                        except Exception as e:
                            print(f"   ⚠️ Download error: {e}")

                if downloaded:
                    break
                await flow_page.wait_for_timeout(3000)

            if not downloaded:
                print(f"   ⚠️ Could not automatically extract new image for {shot_id}")

        print("\n✨ Google Flow generation batch finished!\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--count", type=int, default=4)
    args = parser.parse_args()
    asyncio.run(generate_flow_shots(start_idx=args.start, count=args.count))
