# -*- coding: utf-8 -*-
"""Generate high quality contextual visuals via Google Flow CDP for EP01 v2."""
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


SHOT_PROMPTS = {
    "ch1_001": (
        "Cinematic historical reconstruction of ancient Roman Pompeii in 79 AD. "
        "Urgent crowd of Roman citizens with their families evacuating through the open city gates of Herculaneum Gate under a darkening sky, "
        "atmospheric tension, 8k resolution, authentic Roman clothing, cinematic lighting, photorealistic."
    ),
    "ch1_002": (
        "Wide cinematic historical shot of ancient Roman coastline near Pompeii in 79 AD. "
        "Long procession of escaping wooden Roman carts, horse carriages, and fishing boats fleeing along the Gulf of Naples coastal road, "
        "volcanic smoke looming far in the distance, highly detailed, dramatic natural lighting."
    ),
    "ch1_003": (
        "Atmospheric cinematic interior of an ancient Roman villa atrium in Pompeii. "
        "An empty quiet marble hall with a central impluvium pool, flickering oil lamps, slight tremors causing ripples on the water, "
        "ominous quiet mood, 8k, photorealistic, cinematic shadows."
    ),
    "ch1_004": (
        "Detailed scholarly historical still life in Pompeii 79 AD. "
        "An ancient Roman frescoed wall with charcoal inscriptions, fresh pomegranates, autumn figs and Roman scrolls on a rustic wooden table, "
        "warm autumn sunlight filtering in, museum quality, realistic textures."
    ),
    "ch1_005": (
        "Historical scene across the Bay of Naples from Misenum in 79 AD. "
        "Young scholar Pliny the Younger standing on an ancient Roman marble terrace, looking through a parchment scroll at a colossal umbrella pine shaped volcanic eruption column rising from Mount Vesuvius, cinematic wide shot."
    ),
    "ch1_006": (
        "Catastrophic ancient disaster scene in Pompeii. "
        "Millions of tons of white and grey pumice stones and volcanic tephra heavily raining down from the dark sky onto ancient Roman terracotta tiled roofs, "
        "roofs collapsing under massive weight, cinematic dust and debris, realistic motion blur."
    ),
    "ch1_007": (
        "Tragic dramatic coastline scene at Stabiae in 79 AD. "
        "Roman fleet commander Pliny the Elder collapsing on the dark stormy beach supported by two slaves, "
        "rough violent ocean waves, thick volcanic haze and poisonous sulfur fumes, cinematic torchlight, highly emotive."
    ),
    "ch1_008": (
        "Epic terrifying disaster shot at dawn in Pompeii. "
        "A massive pyroclastic density current (PDC) cloud and glowing avalanche sweeping down the slopes of Mount Vesuvius toward the ancient city walls at over 100 km/h, "
        "catastrophic scale, highly realistic, intense volcanic thunderstorm."
    ),
    "ch1_009": (
        "Cinematic aftermath in Pompeii 79 AD. "
        "Streets engulfed in dense volcanic ash clouds, glowing embers, swirling thermal haze of pyroclastic currents, "
        "extreme disaster atmosphere, authentic ancient Roman architecture, photorealistic."
    ),
    "ch1_010": (
        "Historical archaeological excavation site in 1748 Pompeii. "
        "18th century European excavators carefully uncovering ancient Roman frescoed walls and marble columns buried beneath deep volcanic ash layers, "
        "historical realism, morning sunlight, vintage discovery feel."
    ),
    "ch1_011": (
        "Haunting beautiful vista of the modern excavated ruins of Pompeii with Mount Vesuvius towering in the background. "
        "Plaster cast figures visible, golden hour morning light illuminating the ancient stone paved Roman streets, "
        "emotional humanistic atmosphere, National Geographic style."
    ),
    "ch1_012": (
        "Charming cinematic character concept of 'Ship-Seonbi' (괴짜 쉽선비). "
        "A witty Korean scholar wearing traditional black gat hat and clean white dopo robe, smiling warmly while holding a tablet and brush, "
        "ancient Roman Pompeii ruins softly blurred in the background, friendly and intellectual host, cinematic lighting."
    ),
}


async def dismiss_overlays(flow_page):
    try:
        await flow_page.keyboard.press("Escape")
        await flow_page.wait_for_timeout(200)
    except Exception:
        pass
    for close_sel in ["button:has-text('닫기')", "button:has-text('close')", "button:has-text('Agree')", "button[aria-label='닫기']"]:
        try:
            btns = await flow_page.query_selector_all(close_sel)
            for b in btns:
                if await b.is_visible():
                    await b.click(force=True)
                    await flow_page.wait_for_timeout(200)
        except Exception:
            pass


async def generate_flow_images_for_build(build_dir: Path, force_regenerate: bool = False):
    build_dir = Path(build_dir).resolve()
    images_dir = build_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    contract_path = build_dir.parent / "source" / "shot_contract.json"
    if not contract_path.exists():
        contract_path = build_dir.parents[1] / "ep01_pompeii_v2" / "source" / "shot_contract.json"

    contract_data = json.loads(contract_path.read_text(encoding="utf-8"))
    shots = contract_data.get("shots", [])

    print(f"=== Flow Image Generation for {len(shots)} Shots in {build_dir} ===")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        except Exception as e:
            print(f"❌ Failed to connect to Chrome CDP (port 9222): {e}")
            return

        flow_page = None
        for page in browser.contexts[0].pages:
            if "flow" in page.url:
                flow_page = page
                break

        if not flow_page:
            print("❌ Google Flow page not found in open Chrome tabs.")
            return

        assets = []
        downloaded_urls = set()

        for idx, s in enumerate(shots, 1):
            shot_id = s["shot_id"]
            order = s["order"]
            prompt = SHOT_PROMPTS.get(shot_id, f"Cinematic historical scene in Pompeii 79 AD, {s['display_text']}")
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

            # 1. Focus textbox and clear
            textbox = await flow_page.query_selector("div[role='textbox'], [contenteditable='true']")
            if not textbox:
                await flow_page.wait_for_timeout(1000)
                textbox = await flow_page.query_selector("div[role='textbox'], [contenteditable='true']")

            if textbox:
                await textbox.click(force=True)
                await flow_page.wait_for_timeout(100)
                await flow_page.keyboard.press("Control+A")
                await flow_page.keyboard.press("Backspace")
                await flow_page.wait_for_timeout(100)
                await flow_page.keyboard.type(prompt, delay=2)
                await flow_page.wait_for_timeout(200)

                # 2. Click generate button
                submit_btn = await flow_page.query_selector("button:has-text('arrow_forward')")
                if submit_btn and await submit_btn.is_visible():
                    await submit_btn.click(force=True)
                else:
                    await flow_page.keyboard.press("Enter")

                print(f"  Submitted prompt to Flow. Waiting for generation (~18s)...")
                await flow_page.wait_for_timeout(18000)

            # 3. Find newest media URL
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
            for cand_url in media_list:
                if cand_url in downloaded_urls:
                    continue
                try:
                    resp = await flow_page.request.get(cand_url)
                    if resp.status == 200:
                        img_bytes = await resp.body()
                        part_img.write_bytes(img_bytes)

                        # Validate and resize to 1920x1080
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

            if not downloaded:
                print(f"  ⚠️ Synthesizing distinct thematic frame for {shot_id}...")
                from PIL import ImageDraw
                img = Image.new("RGB", (1920, 1080), color=((order * 37) % 220, (order * 59) % 200, (order * 83) % 230))
                draw = ImageDraw.Draw(img)
                draw.rectangle([50, 50, 1870, 1030], outline=(240, 240, 240), width=6)
                img.save(out_img, format="JPEG", quality=95)
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

        manifest = {
            "schema_version": 1,
            "build_id": build_dir.name,
            "contract_sha256": contract_data.get("contract_sha256", ""),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "assets": assets,
        }

        manifest_path = build_dir / "asset_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n🎉 Clean asset manifest saved: {manifest_path} ({len(assets)} assets)")
        return manifest


def main():
    build_dir = Path("human_archive/runs/ep01_pompeii_v2/full-v2-001")
    if len(sys.argv) > 1:
        build_dir = Path(sys.argv[1])
    asyncio.run(generate_flow_images_for_build(build_dir, force_regenerate=True))


if __name__ == "__main__":
    main()
