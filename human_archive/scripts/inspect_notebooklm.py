# -*- coding: utf-8 -*-
"""Inspect and extract content from Google NotebookLM via Chrome CDP."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


TARGET_URL = "https://notebook.google.com/notebook/722a35c7-7da8-43d4-b941-a93c898cff60"


async def main():
    print(f"Connecting to Chrome CDP on http://127.0.0.1:9222 to access NotebookLM: {TARGET_URL}")
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        except Exception as e:
            print(f"❌ Could not connect to Chrome CDP: {e}")
            return

        context = browser.contexts[0]
        target_page = None
        for page in context.pages:
            if "722a35c7-7da8-43d4-b941-a93c898cff60" in page.url or "notebook" in page.url:
                target_page = page
                break

        if not target_page:
            print("Notebook tab not found, creating or navigating in new page...")
            target_page = await context.new_page()
            await target_page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)
        else:
            print(f"Found existing NotebookLM page: {target_page.url}")
            if TARGET_URL not in target_page.url:
                await target_page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)

        await target_page.wait_for_timeout(5000)

        # Extract title and visible text/elements
        title = await target_page.title()
        print(f"\nPage Title: {title}")

        # Extract text content from the notebook
        body_text = await target_page.evaluate("() => document.body.innerText")
        print("\n--- Extracted Text Preview (First 1500 chars) ---")
        print(body_text[:1500])

        # Save complete text content
        out_dir = Path("human_archive/sources/notebooklm_extract")
        out_dir.mkdir(parents=True, exist_ok=True)
        raw_text_file = out_dir / "notebook_raw_text.txt"
        raw_text_file.write_text(body_text, encoding="utf-8")
        print(f"\n✅ Full extracted text saved to {raw_text_file} ({len(body_text)} chars)")

        # Try to extract specific notes / source panels
        notes_data = await target_page.evaluate("""() => {
            const results = [];
            // Look for cards, note elements, chat responses, source titles
            document.querySelectorAll('[role="article"], .mat-mdc-card, [data-test-id], div[class*="note"], div[class*="source"], div[class*="card"]').forEach(el => {
                const txt = el.innerText ? el.innerText.trim() : '';
                if (txt.length > 30) {
                    results.push({
                        tag: el.tagName,
                        className: el.className,
                        text: txt
                    });
                }
            });
            return results;
        }""")

        json_file = out_dir / "notebook_elements.json"
        json_file.write_text(json.dumps(notes_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✅ Extracted elements saved to {json_file} ({len(notes_data)} elements)")


if __name__ == "__main__":
    asyncio.run(main())
