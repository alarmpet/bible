# -*- coding: utf-8 -*-
"""Extract generated image URLs or download images from Google Flow canvas."""
from __future__ import annotations

import asyncio
import base64
import sys
import urllib.request
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def extract_and_save_generated_images():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        flow_page = [page for page in browser.contexts[0].pages if "flow" in page.url][0]

        print("Searching for generated images on Google Flow canvas...")

        # Find all images on the page
        media_list = await flow_page.evaluate("""() => {
            const list = [];
            document.querySelectorAll('img, video, canvas').forEach(el => {
                const rect = el.getBoundingClientRect();
                const src = el.src || el.currentSrc || el.getAttribute('data-src') || '';
                if (src && !src.includes('avatar') && !src.includes('favicon') && !src.includes('icon') && !src.includes('placeholder')) {
                    list.push({
                        tag: el.tagName,
                        src: src,
                        w: Math.round(rect.width),
                        h: Math.round(rect.height),
                        natW: el.naturalWidth || 0,
                        natH: el.naturalHeight || 0
                    });
                }
            });
            return list;
        }""")

        print(f"Found {len(media_list)} generated media items:")
        out_dir = Path("human_archive/runs/ep01_pompeii_18hours/flow_downloads")
        out_dir.mkdir(parents=True, exist_ok=True)

        for i, m in enumerate(media_list):
            print(f"[{i:02d}] <{m['tag']}> {m['w']}x{m['h']} (nat: {m['natW']}x{m['natH']}) | {m['src'][:80]}")
            if m['src'].startswith('http'):
                try:
                    save_path = out_dir / f"flow_img_{i:02d}.jpg"
                    # Download via playwright request context to keep cookies/auth
                    resp = await flow_page.request.get(m['src'])
                    save_path.write_bytes(await resp.body())
                    print(f"  -> Saved to {save_path} ({save_path.stat().st_size} bytes)")
                except Exception as e:
                    print(f"  -> Download error: {e}")


if __name__ == "__main__":
    asyncio.run(extract_and_save_generated_images())
