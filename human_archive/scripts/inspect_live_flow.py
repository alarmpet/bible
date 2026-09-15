# -*- coding: utf-8 -*-
"""Inspect live Google Flow UI using Playwright persistent Chrome context."""
import asyncio
import argparse
import json
import sys
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def is_flow_project_url(url: str) -> bool:
    return str(url).startswith("https://flow.google.com/project/")


async def main(cdp_url: str = "http://127.0.0.1:9222", project_url: str | None = None):
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        pages = [
            page
            for context in browser.contexts
            for page in context.pages
            if is_flow_project_url(page.url)
            and (project_url is None or page.url.startswith(project_url))
        ]
        if len(pages) != 1:
            raise SystemExit(f"expected exactly one Flow project page, found {len(pages)}")
        page = pages[0]
        await page.bring_to_front()

        print(f"Current URL: {page.url}")
        print(f"Title: {await page.title()}")

        # Check if sign in button or prompt box is present
        elements = await page.evaluate("""() => {
            const list = [];
            document.querySelectorAll('button, a, textarea, input, [role="button"], [contenteditable="true"]').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    list.push({
                        tag: el.tagName,
                        text: (el.innerText || el.value || el.getAttribute('placeholder') || el.getAttribute('aria-label') || '').trim().substring(0, 80),
                        role: el.getAttribute('role') || '',
                        aria: el.getAttribute('aria-label') || '',
                        href: el.getAttribute('href') || ''
                    });
                }
            });
            return list;
        }""")

        print(f"\n--- Found {len(elements)} Interactive Elements ---")
        for i, el in enumerate(elements[:25]):
            print(f"[{i:02d}] {el['tag']} | Role: {el['role']} | Text: {el['text']} | Href: {el['href']}")

        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cdp", default="http://127.0.0.1:9222")
    parser.add_argument("--project-url")
    args = parser.parse_args()
    asyncio.run(main(args.cdp, args.project_url))
