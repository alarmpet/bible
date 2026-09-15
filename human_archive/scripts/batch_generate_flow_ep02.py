# -*- coding: utf-8 -*-
"""Batch generate real AI images in Google Flow via Playwright / Chrome CDP for EP02 (45 shots)."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def generate_flow_ep02(
    contract_path: str = "human_archive/runs/ep02_jang_huibin/source/shot_contract.json",
    output_dir: str = "human_archive/runs/ep02_jang_huibin/full-v2-001/images",
    cdp_url: str = "http://127.0.0.1:9222",
    wait_time_sec: int = 16,
):
    c_path = Path(contract_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    contract_data = json.loads(c_path.read_text(encoding="utf-8"))
    shots = contract_data["shots"]
    print(f"=== Starting Google Flow Batch Generation for EP02 ({len(shots)} Shots) ===")

    async with async_playwright() as p:
        browser_ctx = None
        flow_page = None

        # 1. Try CDP connection first
        try:
            browser = await p.chromium.connect_over_cdp(cdp_url)
            print(f"✅ Connected to Chrome via CDP at {cdp_url}")
            for ctx in browser.contexts:
                for page in ctx.pages:
                    if "flow" in page.url or "labs.google" in page.url:
                        flow_page = page
                        print(f"  Found open Google Flow tab: {page.url}")
                        break
                if flow_page:
                    break
        except Exception as e:
            print(f"⚠️ CDP connection unavailable ({e}). Launching persistent Chrome context...")

        # 2. If CDP not available or no tab found, launch persistent context
        if not flow_page:
            user_dir = Path("C:/Users/shs/.playwright_flow_profile")
            user_dir.mkdir(parents=True, exist_ok=True)
            browser_ctx = await p.chromium.launch_persistent_context(
                user_data_dir=user_dir,
                headless=False,
                channel="chrome",
                viewport={"width": 1920, "height": 1080},
            )
            flow_page = browser_ctx.pages[0] if browser_ctx.pages else await browser_ctx.new_page()
            await flow_page.goto("https://labs.google/fx/editor/flow")
            print(f"  Navigated to Google Flow: {flow_page.url}")
            await flow_page.wait_for_timeout(3000)

        # 3. Check login status
        if "accounts.google.com" in flow_page.url:
            print("⚠️ Google Account Login Required! Please complete login in the opened browser window.")
            print("Waiting for login to complete (checking URL every 3s)...")
            for _ in range(60):
                await flow_page.wait_for_timeout(3000)
                if "accounts.google.com" not in flow_page.url:
                    print(f"✅ Login complete! Current URL: {flow_page.url}")
                    break

        seen_media_urls = set()

        for idx, shot in enumerate(shots, 1):
            shot_id = shot["shot_id"]
            vis = shot.get("visual", {})
            subject = vis.get("subject", "Historical scene")
            place = vis.get("place", "Joseon Palace")
            art_style = vis.get("art_style", "joseon_cinematic_ink_wash_hanji")
            lighting = vis.get("lighting", "dramatic chiaroscuro")

            prompt = (
                f"Historical Korean documentary cinematography: {subject}, located at {place} during 1701 Joseon Dynasty. "
                f"Art style: {art_style}, authentic traditional Hanbok, {lighting}, volumetric dust, 8k resolution, photorealistic matte oil painting texture."
            )

            out_img = out_dir / f"{shot_id}.jpg"
            print(f"\n[{idx:02d}/{len(shots)}] Processing {shot_id} ({subject[:40]})...")
            print(f"  Prompt: {prompt[:90]}...")

            # Dismiss popup if any
            for close_sel in ["button:has-text('Agree')", "button:has-text('닫기')", "button:has-text('close')"]:
                b = await flow_page.query_selector(close_sel)
                if b and await b.is_visible():
                    try:
                        await b.click()
                        await flow_page.wait_for_timeout(300)
                    except Exception:
                        pass

            # Find textbox
            textbox = await flow_page.query_selector("div[role='textbox'], [contenteditable='true'], textarea")
            if not textbox:
                print("  Textbox not found, waiting...")
                await flow_page.wait_for_timeout(2000)
                textbox = await flow_page.query_selector("div[role='textbox'], [contenteditable='true'], textarea")

            if not textbox:
                print(f"  ❌ Error: Textbox not found for {shot_id}, skipping.")
                continue

            await textbox.click()
            await flow_page.wait_for_timeout(200)
            await flow_page.keyboard.press("Control+A")
            await flow_page.keyboard.press("Backspace")
            await flow_page.wait_for_timeout(100)
            await flow_page.keyboard.type(prompt, delay=3)
            await flow_page.wait_for_timeout(300)

            # Submit
            submit_btn = await flow_page.query_selector("button:has-text('arrow_forward')")
            if submit_btn and await submit_btn.is_visible():
                await submit_btn.click()
                print(f"  Submitted prompt. Waiting for generation (~{wait_time_sec}s)...")
            else:
                await flow_page.keyboard.press("Enter")
                print(f"  Pressed Enter. Waiting for generation (~{wait_time_sec}s)...")

            await flow_page.wait_for_timeout(wait_time_sec * 1000)

            # Find generated image
            media_list = await flow_page.evaluate("""() => {
                const list = [];
                document.querySelectorAll('img').forEach(el => {
                    const src = el.src || el.currentSrc || '';
                    if (src.includes('labs.google/fx/api') || src.includes('getMediaUrlRedirect') || src.includes('googleusercontent')) {
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
                latest_url = media_list[-1]["src"]
                resp = await flow_page.request.get(latest_url)
                img_bytes = await resp.body()
                out_img.write_bytes(img_bytes)
                print(f"  ✅ Saved latest image to {out_img.name} ({len(img_bytes)} bytes)")

        print("\n=== Google Flow Batch Generation Completed for EP02! ===")
        if browser_ctx:
            await browser_ctx.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default="human_archive/runs/ep02_jang_huibin/source/shot_contract.json")
    parser.add_argument("--output", default="human_archive/runs/ep02_jang_huibin/full-v2-001/images")
    parser.add_argument("--cdp", default="http://127.0.0.1:9222")
    parser.add_argument("--wait", type=int, default=16)
    args = parser.parse_args()

    asyncio.run(generate_flow_ep02(
        contract_path=args.contract,
        output_dir=args.output,
        cdp_url=args.cdp,
        wait_time_sec=args.wait
    ))
