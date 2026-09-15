# -*- coding: utf-8 -*-
"""Generate high quality contextual AI visuals via Google Flow CDP for EP02 (Jang Huibin)."""
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


async def dismiss_overlays(flow_page):
    try:
        await flow_page.keyboard.press("Escape")
        await flow_page.wait_for_timeout(200)
    except Exception:
        pass
    for close_sel in [
        "button:has-text('닫기')",
        "button:has-text('close')",
        "button:has-text('Agree')",
        "button[aria-label='닫기']",
        "button:has-text('동의')",
    ]:
        try:
            btns = await flow_page.query_selector_all(close_sel)
            for b in btns:
                if await b.is_visible():
                    await b.click(force=True)
                    await flow_page.wait_for_timeout(200)
        except Exception:
            pass


async def generate_ep02_flow_images(
    build_dir: Path = Path("human_archive/runs/ep02_jang_huibin/full-v2-001"),
    force_regenerate: bool = False,
):
    build_dir = Path(build_dir).resolve()
    images_dir = build_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    contract_path = build_dir.parent / "source" / "shot_contract.json"
    contract_data = json.loads(contract_path.read_text(encoding="utf-8"))
    shots = contract_data.get("shots", [])

    print(f"=== Google Flow Image Generator for EP02: {len(shots)} Shots in {build_dir} ===")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            print("✅ Successfully connected to Chrome CDP at http://127.0.0.1:9222")
        except Exception as e:
            print(f"❌ Failed to connect to Chrome CDP (port 9222): {e}")
            print("💡 Tip: Launch Chrome with: chrome.exe --remote-debugging-port=9222 https://labs.google/fx/editor/flow")
            return

        flow_page = None
        for ctx in browser.contexts:
            for page in ctx.pages:
                url_low = page.url.lower()
                if "image-fx" in url_low or "flow" in url_low or "labs.google" in url_low or "aitestkitchen" in url_low:
                    flow_page = page
                    break
            if flow_page:
                break

        if not flow_page:
            print("❌ Google ImageFX / Flow page not found in open Chrome tabs.")
            print("💡 Tip: Open https://labs.google/fx/tools/image-fx in the launched Chrome window.")
            return

        print(f"✅ Found Google Creative Studio page: {flow_page.url}")

        assets = []
        downloaded_urls = set()

        for idx, s in enumerate(shots, 1):
            shot_id = s["shot_id"]
            order = s["order"]
            vis = s.get("visual", {})
            subject = vis.get("subject", "Historical scene")
            place = vis.get("place", "Changgyeonggung Palace")
            art_style = vis.get("art_style", "joseon_cinematic_ink_wash_hanji")
            lighting = vis.get("lighting", "dramatic chiaroscuro")

            prompt = (
                f"Cinematic historical Korean docudrama: {subject} at {place}, 1701 Joseon dynasty. "
                f"Art style {art_style}, authentic traditional Hanbok garments, {lighting}, volumetric dust, 8k resolution, photorealistic matte oil painting texture."
            )

            out_img = images_dir / f"{shot_id}.jpg"
            part_img = images_dir / f"{shot_id}.jpg.part"
            prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest().upper()

            if out_img.exists() and not force_regenerate:
                stat = out_img.stat()
                file_sha = compute_file_sha256(out_img)
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
                print(f"[{idx:02d}/{len(shots)}] Existing valid image for {shot_id}: {out_img.name}")
                continue

            print(f"\n[{idx:02d}/{len(shots)}] Processing {shot_id} on Google Flow...")
            print(f"  Prompt: {prompt[:80]}...")

            await dismiss_overlays(flow_page)

            # Focus textbox and clear
            textbox = await flow_page.query_selector("div[role='textbox'], [contenteditable='true'], textarea")
            if not textbox:
                await flow_page.wait_for_timeout(1000)
                textbox = await flow_page.query_selector("div[role='textbox'], [contenteditable='true'], textarea")

            if textbox:
                await textbox.click(force=True)
                await flow_page.wait_for_timeout(100)
                await flow_page.keyboard.press("Control+A")
                await flow_page.keyboard.press("Backspace")
                await flow_page.wait_for_timeout(100)
                await flow_page.keyboard.type(prompt, delay=2)
                await flow_page.wait_for_timeout(200)

                # Submit button
                submit_btn = None
                for sel in [
                    "button:has-text('Generate')",
                    "button:has-text('생성')",
                    "button:has-text('arrow_forward')",
                    "button[aria-label*='Generate']",
                    "button[aria-label*='생성']",
                ]:
                    b = await flow_page.query_selector(sel)
                    if b and await b.is_visible():
                        submit_btn = b
                        break

                if submit_btn:
                    await submit_btn.click(force=True)
                else:
                    await flow_page.keyboard.press("Enter")

                print(f"  Submitted prompt. Waiting for generation (~18s)...")
                await flow_page.wait_for_timeout(18000)

            # Find media URL
            media_list = await flow_page.evaluate("""() => {
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
                    resp = await flow_page.request.get(cand_url)
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
                            print(f"  ✅ Saved visual from Flow for {shot_id}: {out_img.name} ({stat.st_size // 1024} KB)")
                            break
                except Exception as ex:
                    print(f"  ⚠️ Could not download {cand_url}: {ex}")

        # Update asset manifest
        manifest_path = build_dir / "asset_manifest.json"
        manifest_data = {
            "schema_version": 2,
            "build_id": build_dir.name,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "provider": "google_flow_cdp",
            "assets": assets,
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n✅ EP02 Flow Asset Manifest updated: {manifest_path} ({len(assets)} assets)")

        # Create contact sheet
        try:
            from PIL import ImageDraw
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
        except Exception as cs_err:
            print(f"⚠️ Contact sheet build notice: {cs_err}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", default="human_archive/runs/ep02_jang_huibin/full-v2-001")
    parser.add_argument("--force", action="store_true", default=True)
    args = parser.parse_args()

    asyncio.run(generate_ep02_flow_images(
        build_dir=Path(args.build_dir),
        force_regenerate=args.force
    ))
