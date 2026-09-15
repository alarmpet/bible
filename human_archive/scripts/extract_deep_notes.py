# -*- coding: utf-8 -*-
"""Extract full deep research notes from NotebookLM via Chrome CDP."""
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
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = next((pg for pg in context.pages if "722a35c7-7da8-43d4-b941-a93c898cff60" in pg.url or "notebook" in pg.url), None)
        if not page:
            page = await context.new_page()
            await page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)

        out_dir = Path("human_archive/sources/notebooklm_extract/notes")
        out_dir.mkdir(parents=True, exist_ok=True)

        # Find all source/note cards on the page and click to extract full body
        sources = await page.query_selector_all("div[role='listitem'], div[role='button'], .source-item, .note-item")
        print(f"Found {len(sources)} clickable items on page.")

        # Extract all notes/markdown content in notebook guide panel or note editor
        notes_text = await page.evaluate("""() => {
            const data = [];
            // Look for all text containers
            document.querySelectorAll('[role="main"], [role="region"], .note-content, .markdown-content, [contenteditable="true"]').forEach((el, idx) => {
                data.push({
                    index: idx,
                    html: el.innerHTML,
                    text: el.innerText
                });
            });
            return data;
        }""")

        for i, note in enumerate(notes_text):
            if len(note["text"]) > 200:
                p_out = out_dir / f"note_section_{i:02d}.txt"
                p_out.write_text(note["text"], encoding="utf-8")
                print(f"Saved {p_out} ({len(note['text'])} chars)")

        # Query chat or notebook summary if available
        summary = await page.evaluate("""() => {
            const el = document.querySelector('.notebook-guide, .chat-response, .study-guide');
            return el ? el.innerText : '';
        }""")
        if summary:
            (out_dir / "notebook_guide_summary.txt").write_text(summary, encoding="utf-8")
            print("Saved notebook_guide_summary.txt")


if __name__ == "__main__":
    asyncio.run(main())
