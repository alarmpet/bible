# -*- coding: utf-8 -*-
"""Batch generate all 45 K-Webtoon shots of EP03 Maecheon Yarok on Google Flow CDP."""
from __future__ import annotations

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


async def generate_all_shots():
    contract_path = Path("human_archive/runs/ep03_maecheon/source/shot_contract.json")
    build_dir = Path("human_archive/runs/ep03_maecheon/full-v3-001")
    images_dir = build_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    contract_data = json.loads(contract_path.read_text(encoding="utf-8"))
    shots = contract_data.get("shots", [])

    print(f"\n=================================================================")
    print(f"🎬 GOOGLE FLOW BATCH GENERATOR (K-WEBTOON): {len(shots)} SHOTS FOR EP03")
    print(f"=================================================================\n")

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        pages = [pg for ctx in browser.contexts for pg in ctx.pages if "flow" in pg.url or "labs.google" in pg.url]
        if not pages:
            print("❌ Google Flow tab not found in Chrome!")
            return

        page = pages[0]
        print(f"✅ Connected to Google Flow tab: {page.url}")

        downloaded_urls = set()
        assets = []

        # Find existing images
        existing_imgs = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('img')).map(i => i.src || i.currentSrc || '').filter(s => s && (s.includes('labs.google/fx/api') || s.includes('getMediaUrlRedirect') || s.includes('googleusercontent.com')));
        }""")
        downloaded_urls.update(existing_imgs)
        print(f"Already seen {len(existing_imgs)} media URLs on canvas.")

        for idx, shot in enumerate(shots, 1):
            shot_id = shot["shot_id"]
            order = shot["order"]
            vis = shot.get("visual", {})
            subject = vis.get("subject", "Historical scene")
            place = vis.get("place", "Gurye Seojae Study")

            prompt = (
                f"Masterpiece Korean historical webtoon style manhwa illustration: {subject}, located at {place} during 1864-1910 Late Joseon Dynasty. "
                f"Fine delicate ink contour line work, rich Hanji color wash, dramatic chiaroscuro candle lighting with deep obsidian shadows and warm amber rim light, "
                f"volumetric dust particles, 8k resolution, cinematic anime keyframe, trending on Webtoon, highly detailed"
            )

            out_img = images_dir / f"{shot_id}.jpg"
            part_img = images_dir / f"{shot_id}.jpg.part"
            prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest().upper()

            print(f"\n[{idx:02d}/{len(shots)}] 🎨 Generating {shot_id}: {subject[:45]}...")

            # 1. Focus textbox and type prompt
            textbox = await page.query_selector("div[role='textbox'], [contenteditable='true']")
            if not textbox:
                await page.wait_for_timeout(2000)
                textbox = await page.query_selector("div[role='textbox'], [contenteditable='true']")

            if textbox:
                await textbox.click(force=True)
                await page.wait_for_timeout(150)
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.wait_for_timeout(100)
                await page.keyboard.type(prompt, delay=2)
                await page.wait_for_timeout(250)

                # 2. Click right arrow submit button at (1236, 854)
                await page.mouse.click(1236, 854)
                await page.wait_for_timeout(200)
                await page.keyboard.press("Enter")

                print(f"  ⏳ Prompt submitted. Waiting ~18s for Google Flow generation...")
                await page.wait_for_timeout(18000)

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
                            print(f"  ✅ Saved Google Flow K-Webtoon visual for {shot_id}: {out_img.name} ({stat.st_size // 1024} KB)")
                            break
                except Exception as ex:
                    print(f"  ⚠️ Error downloading {cand_url}: {ex}")

            if not downloaded and out_img.exists():
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

        # 4. Save manifest and contact sheet
        manifest_path = build_dir / "asset_manifest.json"
        manifest_data = {
            "schema_version": 2,
            "build_id": build_dir.name,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "provider": "google_flow_cdp",
            "assets": assets,
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n✅ EP03 Flow Asset Manifest saved: {manifest_path} ({len(assets)} assets)")

        # Contact sheet
        img_files = sorted(images_dir.glob("*.jpg"))
        if img_files:
            cols = 5
            rows = (len(img_files) + cols - 1) // cols
            thumb_w, thumb_h = 384, 216
            sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (15, 20, 25))
            for i, im_p in enumerate(img_files):
                with Image.open(im_p) as im:
                    im_thumb = im.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                    r_i = i // cols
                    c_i = i % cols
                    sheet.paste(im_thumb, (c_i * thumb_w, r_i * thumb_h))
            sheet_path = build_dir / "contact_sheet.jpg"
            sheet.save(sheet_path, format="JPEG", quality=90)
            print(f"✅ Contact sheet created: {sheet_path}")

        print("\n🎉 ALL 45 K-WEBTOON SHOTS SUCCESSFULLY GENERATED ON GOOGLE FLOW!")


if __name__ == "__main__":
    asyncio.run(generate_all_shots())
