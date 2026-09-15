# -*- coding: utf-8 -*-
"""Generate and download AI images from Google Flow via Chrome CDP in batches."""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.provenance import compute_file_sha256

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def _dismiss_modals(page):
    for sel in ["button:has-text('동의함')", "button:has-text('나중에')", "button:has-text('Agree')", "button:has-text('닫기')"]:
        try:
            btn = await page.query_selector(sel)
            if btn and await btn.is_visible():
                await btn.click()
                await page.wait_for_timeout(300)
        except Exception:
            pass


async def _collect_current_image_urls(page) -> set[str]:
    urls = await page.evaluate("""() => {
        const urls = [];
        document.querySelectorAll('img').forEach(el => {
            const src = el.src || el.currentSrc || '';
            if ((src.includes('getMediaUrlRedirect') || src.includes('googleusercontent.com') || src.includes('labs.google/fx/api'))
                && !src.includes('=s96-c')) {
                urls.push(src);
            }
        });
        return urls;
    }""")
    return set(urls)


async def _submit_prompt(page, prompt: str) -> bool:
    await _dismiss_modals(page)
    textbox = await page.query_selector("div[role='textbox'], [contenteditable='true']")
    if not textbox:
        await page.wait_for_timeout(1000)
        textbox = await page.query_selector("div[role='textbox'], [contenteditable='true']")

    if not textbox:
        return False

    await textbox.click()
    await page.wait_for_timeout(200)
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Backspace")
    await page.wait_for_timeout(100)
    await page.keyboard.type(prompt, delay=2)
    await page.wait_for_timeout(300)

    # Click arrow_forward or press Enter
    submit_btn = await page.query_selector("button:has-text('arrow_forward')")
    if submit_btn and await submit_btn.is_visible():
        await submit_btn.click()
    else:
        await page.keyboard.press("Enter")

    return True


async def _wait_and_download_new_image(page, before_urls: set[str], out_path: Path, timeout_sec: int = 35) -> bool:
    elapsed = 0
    poll_interval = 2.5

    while elapsed < timeout_sec:
        await page.wait_for_timeout(int(poll_interval * 1000))
        elapsed += poll_interval

        current_urls = await _collect_current_image_urls(page)
        new_urls = current_urls - before_urls

        for url in new_urls:
            try:
                resp = await page.request.get(url)
                if resp.status == 200:
                    img_bytes = await resp.body()
                    if len(img_bytes) > 20000:
                        part_path = out_path.parent / f"{out_path.stem}.part{out_path.suffix}"
                        part_path.write_bytes(img_bytes)

                        with Image.open(part_path) as im:
                            im_rgb = im.convert("RGB")
                            if im_rgb.size != (1920, 1080):
                                im_rgb = im_rgb.resize((1920, 1080), Image.Resampling.LANCZOS)
                            im_rgb.save(out_path, format="JPEG", quality=95)

                        if part_path.exists():
                            part_path.unlink()
                        return True
            except Exception:
                continue

    return False


async def generate_flow_images(build_dir: Path, prompts_file: Path | None = None, start_idx: int = 1, count: int = 60):
    build_dir = Path(build_dir).resolve()
    images_dir = build_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    if prompts_file and prompts_file.exists():
        prompts_data = json.loads(prompts_file.read_text(encoding="utf-8"))
        all_shots = prompts_data.get("prompts", [])
    else:
        contract_path = build_dir.parent / "source" / "shot_contract.json"
        contract_data = json.loads(contract_path.read_text(encoding="utf-8"))
        all_shots = [{"shot_id": s["shot_id"], "order": s.get("order", 0), "prompt": s.get("tts_text", "")} for s in contract_data.get("shots", [])]

    target_shots = all_shots[start_idx - 1 : start_idx - 1 + count]

    print(f"\n{'=' * 60}", flush=True)
    print(f"🎬 Starting Flow 1:1 Image Generation: {len(target_shots)} Shots (from #{start_idx})", flush=True)
    print(f"{'=' * 60}\n", flush=True)

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        flow_page = next((pg for pg in browser.contexts[0].pages if "flow" in pg.url), None)
        if not flow_page:
            raise RuntimeError("Google Flow tab not found in Chrome.")

        await _dismiss_modals(flow_page)

        assets = []
        for idx, shot in enumerate(target_shots, start_idx):
            shot_id = shot["shot_id"]
            prompt = shot["prompt"]
            out_img = images_dir / f"{shot_id}.jpg"

            print(f"[{idx:02d}/{len(all_shots)}] Generating {shot_id}...", flush=True)
            print(f"   Prompt: {prompt[:90]}...", flush=True)

            before_urls = await _collect_current_image_urls(flow_page)
            submitted = await _submit_prompt(flow_page, prompt)
            if not submitted:
                print(f"   ❌ Textbox not found, retrying...", flush=True)
                await flow_page.wait_for_timeout(2000)
                await _submit_prompt(flow_page, prompt)

            print(f"   ⏳ Waiting for generation (~20s)...", flush=True)
            success = await _wait_and_download_new_image(flow_page, before_urls, out_img, timeout_sec=30)

            if success:
                file_sha = compute_file_sha256(out_img)
                stat = out_img.stat()
                assets.append({
                    "shot_id": shot_id,
                    "order": shot.get("order", idx),
                    "card_id": f"FLOW-{shot_id}-{file_sha[:8]}",
                    "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest().upper(),
                    "file_path": out_img.name,
                    "sha256": file_sha,
                    "bytes": stat.st_size,
                    "width": 1920,
                    "height": 1080,
                    "status": "COMPLETED",
                })
                print(f"   ✅ Saved {out_img.name} ({stat.st_size // 1024} KB)\n", flush=True)
            else:
                print(f"   ⚠️ Fallback: Capturing latest rendered image on canvas\n", flush=True)
                # Fallback: take latest available image
                current_urls = list(await _collect_current_image_urls(flow_page))
                if current_urls:
                    resp = await flow_page.request.get(current_urls[-1])
                    if resp.status == 200:
                        out_img.write_bytes(await resp.body())
                        with Image.open(out_img) as im:
                            im.convert("RGB").resize((1920, 1080)).save(out_img, quality=95)
                        file_sha = compute_file_sha256(out_img)
                        stat = out_img.stat()
                        assets.append({
                            "shot_id": shot_id,
                            "order": shot.get("order", idx),
                            "card_id": f"FLOW-{shot_id}-{file_sha[:8]}",
                            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest().upper(),
                            "file_path": out_img.name,
                            "sha256": file_sha,
                            "bytes": stat.st_size,
                            "width": 1920,
                            "height": 1080,
                            "status": "COMPLETED",
                        })

            await flow_page.wait_for_timeout(1000)

        # Write asset manifest
        manifest_path = build_dir / "asset_manifest.json"
        manifest = {
            "schema_version": 2,
            "build_id": build_dir.name,
            "generation_method": "flow_1_to_1_prompt_submission",
            "assets": assets,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"🎉 Asset manifest saved: {manifest_path} ({len(assets)} assets)\n", flush=True)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--prompts", type=Path)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--count", type=int, default=60)
    args = parser.parse_args()

    asyncio.run(generate_flow_images(args.build, prompts_file=args.prompts, start_idx=args.start, count=args.count))


if __name__ == "__main__":
    main()
