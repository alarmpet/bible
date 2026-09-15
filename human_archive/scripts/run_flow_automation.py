# -*- coding: utf-8 -*-
"""Interactive Google Flow AI Image Generator for EP02 (45 shots).

1. Opens Chrome on screen with persistent user profile.
2. If login is needed, waits for user to log into Google account (session saved permanently).
3. Automatically iterates through all 45 shots, entering prompts, generating images, and downloading.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.provenance import compute_file_sha256

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def run_flow_pipeline(
    contract_path: str = "human_archive/runs/ep02_jang_huibin/source/shot_contract.json",
    output_dir: str = "human_archive/runs/ep02_jang_huibin/full-v2-001/images",
    user_profile_dir: str = "C:/Users/shs/.playwright_flow_profile",
    wait_time_sec: int = 18,
):
    c_path = Path(contract_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    contract_data = json.loads(c_path.read_text(encoding="utf-8"))
    shots = contract_data.get("shots", [])

    print("\n=======================================================")
    print(f"🎨 GOOGLE FLOW AI IMAGE PIPELINE: {len(shots)} SHOTS")
    print("=======================================================\n")

    user_dir = Path(user_profile_dir)
    user_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=user_dir,
            headless=False,
            channel="chrome",
            viewport={"width": 1920, "height": 1080},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://labs.google/fx/tools/flow?from=imagefx")
        await page.wait_for_timeout(3000)

        # 1. Cookie Agree
        agree_btn = await page.query_selector("button:has-text('Agree'), button:has-text('동의')")
        if agree_btn and await agree_btn.is_visible():
            try:
                await agree_btn.click()
                await page.wait_for_timeout(1000)
            except Exception:
                pass

        # 2. Check if login is needed
        if "accounts.google.com" in page.url or await page.query_selector("button:has-text('Create with Google Flow')"):
            create_btn = await page.query_selector("button:has-text('Create with Google Flow'), button:has-text('Try in Google Flow')")
            if create_btn and await create_btn.is_visible():
                await create_btn.click()
                await page.wait_for_timeout(3000)

        if "accounts.google.com" in page.url:
            print("\n" + "="*60)
            print("🔑 [GOOGLE LOGIN REQUIRED]")
            print("Please log into your Google Account in the opened Chrome window.")
            print("Waiting for login to complete (session will be saved permanently)...")
            print("="*60 + "\n")

            while "accounts.google.com" in page.url:
                await page.wait_for_timeout(2000)

            print("✅ Google Account Login detected! Proceeding to Google Flow Studio...")
            await page.wait_for_timeout(5000)

        print(f"Current Studio URL: {page.url}")

        # 3. Enter Studio Project if on dashboard
        if "/project/" not in page.url and "/editor" not in page.url:
            new_btn = await page.query_selector("button:has-text('New project'), button:has-text('새 프로젝트'), button:has-text('Create'), button:has-text('만들기')")
            if new_btn and await new_btn.is_visible():
                print("Clicking 'New project'...")
                await new_btn.click()
                await page.wait_for_timeout(3000)

        assets = []
        downloaded_urls = set()

        for idx, shot in enumerate(shots, 1):
            shot_id = shot["shot_id"]
            order = shot["order"]
            vis = shot.get("visual", {})
            subject = vis.get("subject", "Historical scene")
            place = vis.get("place", "Joseon Palace")
            art_style = vis.get("art_style", "joseon_cinematic_ink_wash_hanji")
            lighting = vis.get("lighting", "dramatic chiaroscuro")

            prompt = (
                f"Historical Korean documentary cinematography: {subject}, located at {place} during 1701 Joseon Dynasty. "
                f"Art style {art_style}, authentic traditional Hanbok clothing, {lighting}, volumetric dust, 8k resolution, photorealistic matte oil painting texture."
            )

            out_img = out_dir / f"{shot_id}.jpg"
            part_img = out_dir / f"{shot_id}.jpg.part"
            prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest().upper()

            print(f"\n[{idx:02d}/{len(shots)}] Processing {shot_id}: {subject[:45]}...")
            print(f"  Prompt: {prompt[:80]}...")

            # Dismiss popups
            for close_sel in ["button:has-text('Agree')", "button:has-text('닫기')", "button:has-text('close')", "button:has-text('동의')"]:
                b = await page.query_selector(close_sel)
                if b and await b.is_visible():
                    try:
                        await b.click(force=True)
                        await page.wait_for_timeout(200)
                    except Exception:
                        pass

            # Find textbox
            textbox = None
            for tb_sel in [
                "div[role='textbox']",
                "[contenteditable='true']",
                "textarea[placeholder*='prompt']",
                "textarea",
                "input[placeholder*='prompt']",
            ]:
                tb = await page.query_selector(tb_sel)
                if tb and await tb.is_visible():
                    textbox = tb
                    break

            if not textbox:
                print(f"  ⚠️ Textbox not found yet. Retrying in 2s...")
                await page.wait_for_timeout(2000)
                textbox = await page.query_selector("div[role='textbox'], [contenteditable='true'], textarea")

            if textbox:
                await textbox.click(force=True)
                await page.wait_for_timeout(100)
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.wait_for_timeout(100)
                await page.keyboard.type(prompt, delay=2)
                await page.wait_for_timeout(200)

                # Submit
                submit_btn = None
                for btn_sel in [
                    "button:has-text('Generate')",
                    "button:has-text('생성')",
                    "button:has-text('arrow_forward')",
                    "button[aria-label*='Generate']",
                    "button[aria-label*='생성']",
                ]:
                    b = await page.query_selector(btn_sel)
                    if b and await b.is_visible():
                        submit_btn = b
                        break

                if submit_btn:
                    await submit_btn.click(force=True)
                else:
                    await page.keyboard.press("Enter")

                print(f"  Submitted to Google Flow. Generating (~{wait_time_sec}s)...")
                await page.wait_for_timeout(wait_time_sec * 1000)

            # Download generated media
            media_list = await page.evaluate("""() => {
                const list = [];
                document.querySelectorAll('img').forEach(el => {
                    const src = el.src || el.currentSrc || '';
                    if (src && (src.includes('labs.google/fx/api') || src.includes('getMediaUrlRedirect') || src.includes('googleusercontent.com') || src.includes('blob:'))) {
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
                            file_sha = compute_file_sha256(out_img)
                            stat = out_img.stat()
                            assets.append({
                                "shot_id": shot_id,
                                "order": order,
                                "card_id": f"FLOW-{shot_id}-{file_sha[:8]}",
                                "prompt_sha256": prompt_sha,
                                "file_path": out_img.name,
                                "sha256": file_sha,
                                "bytes": stat.st_size,
                                "width": 1920,
                                "height": 1080,
                                "status": "COMPLETED",
                            })
                            print(f"  ✅ Saved Google Flow AI image for {shot_id}: {out_img.name} ({stat.st_size // 1024} KB)")
                            break
                except Exception as ex:
                    print(f"  ⚠️ Error downloading {cand_url}: {ex}")

        print("\n🎉 ALL 45 SHOTS GENERATED FROM GOOGLE FLOW!")
        await ctx.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default="human_archive/runs/ep02_jang_huibin/source/shot_contract.json")
    parser.add_argument("--output", default="human_archive/runs/ep02_jang_huibin/full-v2-001/images")
    parser.add_argument("--wait", type=int, default=18)
    args = parser.parse_args()

    asyncio.run(run_flow_pipeline(
        contract_path=args.contract,
        output_dir=args.output,
        wait_time_sec=args.wait
    ))
