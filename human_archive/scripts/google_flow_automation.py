# -*- coding: utf-8 -*-
"""Full Google Flow Image Generation Automation via Chrome CDP."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def open_project_and_inspect(flow_page):
    print("\n--- Inspecting Google Flow Workspace ---")
    
    # 1. Close popups if any
    for close_sel in ["button:has-text('닫기')", "button[aria-label='닫기']", "button:has-text('close')"]:
        btns = await flow_page.query_selector_all(close_sel)
        for b in btns:
            if await b.is_visible():
                try:
                    await b.click()
                    await flow_page.wait_for_timeout(300)
                except Exception:
                    pass

    # 2. Check if we are in project dashboard or inside a project editor
    cur_url = flow_page.url
    print(f"Current URL: {cur_url}")

    if "/project/" not in cur_url:
        new_proj_btn = await flow_page.query_selector("button:has-text('새 프로젝트')")
        if new_proj_btn:
            print("Clicking '새 프로젝트' (New Project)...")
            await new_proj_btn.click()
            await flow_page.wait_for_timeout(3000)
            print(f"Opened Project Editor: {flow_page.url}")

    # 3. Inspect editor UI elements
    elements = await flow_page.evaluate("""() => {
        const res = [];
        document.querySelectorAll('button, textarea, input, [role="button"], [contenteditable="true"]').forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
                res.push({
                    tag: el.tagName,
                    text: (el.innerText || el.value || el.getAttribute('placeholder') || el.getAttribute('aria-label') || '').trim().substring(0, 60),
                    role: el.getAttribute('role') || '',
                    aria: el.getAttribute('aria-label') || '',
                    id: el.id || '',
                    placeholder: el.getAttribute('placeholder') || '',
                    type: el.getAttribute('type') || ''
                });
            }
        });
        return res;
    }""")

    print(f"\nVisible Editor Elements ({len(elements)} items):")
    for i, el in enumerate(elements):
        print(f"[{i:02d}] {el['tag']} | Role: {el['role']} | Aria: {el['aria']} | Text/Placeholder: {el['text']}")

    return flow_page


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        flow_page = None
        for page in browser.contexts[0].pages:
            if "flow" in page.url:
                flow_page = page
                break

        if not flow_page:
            print("Google Flow page not found in open Chrome tabs.")
            return

        await open_project_and_inspect(flow_page)


if __name__ == "__main__":
    asyncio.run(main())
