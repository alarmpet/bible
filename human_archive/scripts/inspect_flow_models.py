# -*- coding: utf-8 -*-
"""Inspect the live Google Flow model picker over Chrome CDP without changing it."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def inspect_models(cdp_url: str, screenshot: Path | None = None) -> list[dict[str, object]]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(cdp_url)
        pages = [
            page
            for context in browser.contexts
            for page in context.pages
            if "flow" in page.url or "labs.google" in page.url
        ]
        if len(pages) != 1:
            raise RuntimeError(f"expected exactly one Google Flow page, found {len(pages)}")
        page = pages[0]
        picker = page.locator("button").filter(has_text="Nano Banana").last
        await picker.wait_for(state="visible", timeout=10_000)
        await picker.click()
        await page.wait_for_timeout(800)
        model_dropdown = page.locator("button").filter(has_text="arrow_drop_down").last
        await model_dropdown.wait_for(state="visible", timeout=10_000)
        await model_dropdown.click()
        await page.wait_for_timeout(800)
        items = await page.evaluate(
            """() => Array.from(document.querySelectorAll(
              '[role="menuitem"], [role="option"], [data-radix-collection-item], button'
            )).filter((element) => {
              const rect = element.getBoundingClientRect();
              return rect.width > 0 && rect.height > 0;
            }).map((element) => ({
              tag: element.tagName,
              role: element.getAttribute('role') || '',
              text: (element.innerText || element.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 200),
              disabled: Boolean(element.disabled) || element.getAttribute('aria-disabled') === 'true'
            })).filter((item) => item.text.length > 0)"""
        )
        if screenshot:
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(screenshot))
        await page.keyboard.press("Escape")
        return items


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cdp", default="http://127.0.0.1:9222")
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()
    items = asyncio.run(inspect_models(args.cdp, args.screenshot))
    print(json.dumps(items, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
