# -*- coding: utf-8 -*-
"""Interact with NotebookLM to fetch source bodies and research reports."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = next((pg for pg in context.pages if "722a35c7-7da8-43d4-b941-a93c898cff60" in pg.url or "notebook" in pg.url), None)
        if not page:
            print("Notebook page not found")
            return

        out_dir = Path("human_archive/sources/notebooklm_extract/sources_detail")
        out_dir.mkdir(parents=True, exist_ok=True)

        # Let's ask NotebookLM via its chat interface to summarize all core historical topics and narrative scripts
        chat_input = await page.query_selector("textarea, input[placeholder*='질문'], div[contenteditable='true']")
        if chat_input:
            print("Submitting comprehensive synthesis request to NotebookLM chat...")
            prompt = (
                "이 노트북에 포함된 모든 역사 자료와 Deep Research 보고서들을 종합하여, "
                "'쉽선비' 유튜브 채널(역사 미스터리, 상식 파괴, 1차 사료, 역사적 아이러니)에서 다룰 수 있는 "
                "가장 매력적인 에피소드 소재 10가지와 각 소재별 핵심 반전 팩트, 1차 사료, 3초 직관 비유 아이디어를 아주 상세하게 정리해줘."
            )
            await chat_input.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await page.keyboard.type(prompt, delay=5)
            await page.wait_for_timeout(300)
            await page.keyboard.press("Enter")
            print("Prompt sent. Waiting for NotebookLM response (~20s)...")
            await page.wait_for_timeout(20000)

            # Extract latest chat response
            responses = await page.evaluate("""() => {
                const res = [];
                document.querySelectorAll('[role="article"], .chat-message-response, .response-content, div[class*="response"]').forEach(el => {
                    res.push(el.innerText);
                });
                return res;
            }""")

            if responses:
                full_chat = "\n\n=== CHAT RESPONSE ===\n\n".join(responses)
                (out_dir / "notebooklm_synthesis_report.txt").write_text(full_chat, encoding="utf-8")
                print(f"✅ Saved NotebookLM synthesis response ({len(full_chat)} chars)")

        # Inspect all source titles and metadata
        source_items = await page.evaluate("""() => {
            const list = [];
            document.querySelectorAll('button, div[role="button"], div[role="checkbox"]').forEach(el => {
                const t = el.innerText ? el.innerText.trim() : '';
                if (t.length > 5 && !t.includes('add') && !t.includes('설정')) {
                    list.push(t);
                }
            });
            return list;
        }""")

        (out_dir / "all_source_titles.json").write_text(json.dumps(source_items, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✅ Saved all source titles ({len(source_items)} items)")


if __name__ == "__main__":
    asyncio.run(main())
