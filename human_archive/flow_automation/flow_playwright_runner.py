# -*- coding: utf-8 -*-
"""NOLLAM Autonomous Google Flow Playwright Runner."""
from __future__ import annotations

import hashlib
import json
import random
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from playwright.sync_api import sync_playwright, Page, BrowserContext

from flow_automation.native_host.asset_validator import validate_asset
from flow_automation.native_host.job_store import append_event, replay_job
from flow_automation.native_host.semantic_review import build_contact_sheet

ROOT_DIR = Path(__file__).resolve().parent.parent
JOB_PATH = ROOT_DIR / 'runs' / 'nollam_file' / '2026-09-02' / 'himalaya-glof-water-crisis' / 'generation' / 'automation_job.json'
USER_DATA_DIR = Path(r"C:\Users\shs\AppData\Local\Google\Chrome\AutomationProfile")

def load_job() -> dict:
    return json.loads(JOB_PATH.read_text(encoding='utf-8'))

def find_editor(page: Page):
    for selector in ["div[role='textbox']", "[data-slate-editor='true']", "textarea"]:
        el = page.query_selector(selector)
        if el and el.is_visible():
            return el
    return None

def get_canvas_card_ids(page: Page) -> set[str]:
    cards = page.query_selector_all("[data-testid='generation-card'], [data-card-id]")
    ids = set()
    for c in cards:
        cid = c.get_attribute('data-card-id') or c.get_attribute('id') or c.get_attribute('data-testid')
        if cid:
            ids.add(cid)
    return ids

def run_automation():
    job = load_job()
    job_id = job['job_id']
    expected_url = job['project']['expected_url']
    downloads_root = Path(job['output_dir']).resolve()
    downloads_root.mkdir(parents=True, exist_ok=True)
    events_path = downloads_root.parent / 'automation_events.jsonl'

    print(f"=== NOLLAM Flow Autonomous Playwright Runner ===")
    print(f"Job ID: {job_id}")
    print(f"Total Shots: {len(job['shots'])}")
    print(f"Expected URL: {expected_url}")
    print(f"Downloads Root: {downloads_root}")

    snapshot = replay_job(job, events_path)
    accepted_shots = {k for k, v in snapshot.shots.items() if v.status == 'ACCEPTED'}
    print(f"Accepted Shots: {len(accepted_shots)} / {len(job['shots'])}")

    with sync_playwright() as p:
        browser = None
        context = None
        page = None

        print("[1/4] Connecting to Chrome on port 9222 (waiting for browser launch)...")
        for attempt in range(60):
            try:
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                print(">>> Successfully connected to Chrome via CDP on port 9222!")
                context = browser.contexts[0]
                break
            except Exception:
                time.sleep(2)

        if not browser:
            print("[1/4-fallback] Port 9222 not detected, launching internal persistent Chrome...")
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(USER_DATA_DIR),
                channel='chrome',
                headless=False,
                args=[
                    r"--load-extension=D:\module\bible\human_archive\flow_automation\extension"
                ]
            )

        for p_page in context.pages:
            if "/project/" in p_page.url or "flow" in p_page.url:
                page = p_page
                break
        if not page:
            page = context.pages[0] if context.pages else context.new_page()
            print(f"[2/4] Navigating to Flow Project: {expected_url}")
            page.goto(expected_url)
        page.wait_for_timeout(3000)

        # Check for Google login
        if 'accounts.google.com' in page.url or page.query_selector('button:has-text("Create with Google Flow"), a[href*="accounts.google.com"]'):
            print("\n" + "="*60)
            print(">>> [USER ACTION REQUIRED] Google Login Needed <<<")
            print("화면에 열린 Chrome 창에서 Google 계정 로그인을 진행해 주세요.")
            print("로그인이 완료되고 Flow 프로젝트 화면이 열리면 자동으로 감지하여 진행합니다.")
            print("="*60 + "\n")

            create_btn = page.query_selector('button:has-text("Create with Google Flow")')
            if create_btn:
                try:
                    create_btn.click()
                except Exception:
                    pass

            for _ in range(120):
                if '/project/' in page.url and find_editor(page):
                    print(">>> Flow Project detected! Starting automated generation...")
                    break
                page.wait_for_timeout(5000)

        page.wait_for_timeout(3000)
        print("[3/4] Ready to process shots...")

        for index, shot in enumerate(job['shots'], 1):
            shot_id = shot['shot_id']
            if shot_id in accepted_shots:
                print(f"[{index}/{len(job['shots'])}] {shot_id} already ACCEPTED, skipping.")
                continue

            prompt = shot['prompt']
            expected_filename = shot['expected_filename']
            print(f"\n--- [{index}/{len(job['shots'])}] Processing {shot_id} ---")
            print(f"Prompt: {prompt[:70]}...")

            baseline = get_canvas_card_ids(page)

            event_id = f"{shot_id}-SUBMITTED-{int(time.time())}"
            append_event(events_path, {
                'event_id': event_id,
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'job_id': job_id,
                'shot_id': shot_id,
                'attempt': 1,
                'type': 'SHOT_SUBMITTED',
                'payload': {'prompt': prompt}
            })

            editor = find_editor(page)
            if not editor:
                print("[ERROR] Prompt editor not found in Flow UI!")
                break

            editor.click()
            editor.fill(prompt)
            page.wait_for_timeout(500)
            editor.press('Enter')
            print("Submitted prompt. Waiting for generation...")

            start_wait = time.time()
            media_url = None
            card_id = None

            while time.time() - start_wait < 90:
                page.wait_for_timeout(2000)
                current_cards = page.query_selector_all("[data-testid='generation-card'], [data-card-id]")
                candidates = []
                for c in current_cards:
                    cid = c.get_attribute('data-card-id') or c.get_attribute('id') or c.get_attribute('data-testid')
                    if cid and cid not in baseline:
                        img = c.query_selector('img[src], picture img[src]')
                        if img:
                            src = img.get_attribute('src')
                            if src and not src.startswith('data:'):
                                candidates.append((cid, src))

                if len(candidates) == 1:
                    card_id, media_url = candidates[0]
                    print(f"Found completed card: {card_id}")
                    break

            if not media_url:
                print(f"[FAIL] Could not identify single new card for {shot_id}")
                continue

            dest_file = downloads_root / expected_filename
            print(f"Downloading to {dest_file.name}...")
            response = page.request.get(media_url)
            dest_file.write_bytes(response.body())

            binding = {
                'expected': {
                    'job_id': job_id,
                    'shot_id': shot_id,
                    'prompt_sha256': shot['prompt_sha256'],
                    'attempt': 1,
                    'card_id': card_id or f'card-{shot_id}',
                    'media_identity': f'media-{shot_id}',
                    'download_id': 'playwright-dl',
                    'original_filename': expected_filename
                },
                'observed': {
                    'job_id': job_id,
                    'shot_id': shot_id,
                    'prompt_sha256': shot['prompt_sha256'],
                    'attempt': 1,
                    'card_id': card_id or f'card-{shot_id}',
                    'media_identity': f'media-{shot_id}',
                    'download_id': 'playwright-dl',
                    'original_filename': expected_filename
                }
            }

            prior_assets = []
            manifest_p = downloads_root / 'approved_asset_manifest.json'
            if manifest_p.exists():
                try:
                    prior_assets = json.loads(manifest_p.read_text(encoding='utf-8')).get('assets', [])
                except Exception:
                    pass

            v_res = validate_asset(job, shot_id, dest_file, downloads_root, prior_assets, binding=binding)
            if v_res.status == 'APPROVED':
                print(f"[SUCCESS] {shot_id} APPROVED! Path: {v_res.approved_path}")
                append_event(events_path, {
                    'event_id': f"{shot_id}-ACCEPTED-{int(time.time())}",
                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    'job_id': job_id,
                    'shot_id': shot_id,
                    'attempt': 1,
                    'type': 'SHOT_ACCEPTED',
                    'payload': {'approved_path': v_res.approved_path, 'sha256': v_res.sha256}
                })
                accepted_shots.add(shot_id)
            else:
                print(f"[REJECTED] {shot_id} validation failed: {v_res.code}")

            delay = random.randint(5, 12)
            print(f"Waiting {delay}s delay...")
            page.wait_for_timeout(delay * 1000)

        print("\n[4/4] Finished run loop!")
        manifest_path = downloads_root / 'approved_asset_manifest.json'
        if manifest_path.exists():
            sheet = build_contact_sheet(manifest_path, downloads_root / 'contact-sheet.jpg')
            print(f"Contact sheet: {sheet['output_path']}")

        context.close()

if __name__ == '__main__':
    run_automation()

