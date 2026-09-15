# -*- coding: utf-8 -*-
"""Inspect Google Flow editor UI state and take screenshot."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def take_ss():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        flow_page = [page for page in browser.contexts[0].pages if "flow" in page.url][0]

        ss_path = Path(r"C:\Users\shs\.gemini\antigravity\brain\a0949ae3-8f9f-4702-af2f-0b95fe1fdedc\flow_editor_state.png")
        await flow_page.screenshot(path=str(ss_path))
        print(f"Screenshot captured: {ss_path}")

        # Check prompt box and buttons
        info = await flow_page.evaluate("""() => {
            const tb = document.querySelector('div[role="textbox"], [contenteditable="true"]');
            const btns = Array.from(document.querySelectorAll('button')).map(b => ({
                text: b.innerText,
                disabled: b.disabled,
                aria: b.getAttribute('aria-label'),
                classes: b.className
            }));
            return {
                textbox_text: tb ? tb.innerText : 'not found',
                textbox_html: tb ? tb.innerHTML : 'not found',
                buttons: btns
            };
        }""")
        print("\nTextbox text:", info['textbox_text'])
        print("\nButtons count:", len(info['buttons']))
        for i, b in enumerate(info['buttons']):
            print(f"[{i:02d}] disabled={b['disabled']} | aria={b['aria']} | text={b['text'][:40]}")


if __name__ == "__main__":
    asyncio.run(take_ss())
