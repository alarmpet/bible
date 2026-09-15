# -*- coding: utf-8 -*-
"""Google Flow CDP Automated Image Generation Service.
Connects to Chrome on remote debugging port 9222.
Executes 1-shot-1-completion automated image generation, download, 1080p Lanczos normalization,
and manifest registration per flow-batch-orchestrator skill rules.
Supports:
1. Single scene real-time automated generation & regeneration.
2. Background sequential batch generation with 3s adaptive cooldown.
3. Live status and progress telemetry.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from PIL import Image
from playwright.async_api import Page, async_playwright
from lib.flow_dom_maintenance import (
    clear_first_error_card,
    cleanup_verified_cards as shared_cleanup_verified_cards,
    wait_for_canvas_idle,
)
from lib.flow_generation_state import adaptive_cooldown

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from workspace_manager import workspace_mgr
except Exception:
    workspace_mgr = None

DEFAULT_EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")

def get_current_ep_dir() -> Path:
    if workspace_mgr:
        return workspace_mgr.current_ep_dir
    return DEFAULT_EP_DIR

def get_approved_dir() -> Path:
    d = get_current_ep_dir() / "generation" / "downloads" / "approved"
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_images_dir() -> Path:
    d = get_current_ep_dir() / "images"
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_manifest_path() -> Path:
    p = get_current_ep_dir() / "generation" / "approved_asset_manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

APPROVED_DIR = get_approved_dir()
IMAGES_DIR = get_images_dir()
MANIFEST_PATH = get_manifest_path()
CDP_URL = "http://127.0.0.1:9222"

VALID_IMAGE_DOMAINS = [
    "flow-content.google/image",
    "flow.google.com/asb/",
    "labs.google/fx/api",
    "getMediaUrlRedirect",
    "googleusercontent.com",
]


def is_flow_image_url(src: str) -> bool:
    """Check if URL points to a generated image asset in Google Flow."""
    if not src or len(src) < 20:
        return False
    return any(d in src for d in VALID_IMAGE_DOMAINS)


async def get_flow_page(browser) -> Optional[Page]:
    """Find active Google Flow or Labs tab."""
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if "flow" in pg.url or "labs.google" in pg.url:
                return pg
    return None


async def ensure_image_mode(page: Page) -> None:
    """Ensure Google Flow prompt bar is set to Image mode (16:9), not Video mode."""
    try:
        trigger = await page.query_selector("button[aria-label='설정 트리거']")
        if not trigger:
            return
        text = (await trigger.inner_text()).replace('\n', ' ')
        if "동영상" in text:
            await trigger.click()
            await page.wait_for_timeout(500)
            await page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('.cdk-overlay-pane button, [role="menu"] button'));
                const imgBtn = btns.find(b => (b.innerText || '').includes('이미지'));
                if (imgBtn) imgBtn.click();
            }""")
            await page.wait_for_timeout(400)
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(300)
    except Exception as e:
        print("ensure_image_mode warning:", e)


async def _detect_and_clear_error_card(page: Page) -> Optional[str]:
    """Apply the shared retry/trash error-card policy."""
    return await clear_first_error_card(page)



async def cleanup_verified_cards(page: Page, verified_count: int) -> int:
    """Two-Phase Commit: Trash completed cards from canvas after local disk verification
    to trigger DOM Garbage Collection and prevent memory leaks during large batches (up to 92 shots).
    """
    return await shared_cleanup_verified_cards(page, verified_count)


async def check_cdp_status(auto_start: bool = True) -> Dict[str, Any]:
    """Check if Chrome CDP port 9222 is open and Flow tab is ready. Auto-starts if offline and auto_start=True."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
            page = await get_flow_page(browser)
            if not page:
                return {
                    "connected": True,
                    "flow_ready": False,
                    "message": "Chrome 9222 포트 연결됨. 단, Google Flow 탭이 열려있지 않습니다.",
                    "page_url": None,
                }

            title = await page.title()
            url = page.url

            # Check if prompt box exists
            has_box = await page.evaluate("""() => {
                const el = document.querySelector("div[contenteditable='true']") || document.querySelector("div[role='textbox']");
                return el !== null;
            }""")

            # Check account
            account_text = await page.evaluate("""() => {
                const acc = document.querySelector("a[href*='accounts.google.com/SignOutOptions']");
                if (!acc) return 'Google Flow 로그인됨 (PRO)';
                return (acc.innerText || '').slice(0, 40);
            }""")

            trigger = await page.query_selector("button[aria-label='설정 트리거']")
            mode_text = (await trigger.inner_text()).replace('\n', ' ') if trigger else '이미지 (기본)'

            return {
                "connected": True,
                "flow_ready": has_box,
                "page_url": url,
                "project_title": title.replace("Google Flow - ", "").strip(),
                "user_account": account_text,
                "mode": mode_text,
                "message": "Google Flow CDP 정상 연결 및 생성 준비 완료",
            }
    except Exception as e:
        if auto_start:
            print("[*] Chrome CDP 미연결 감지. Chrome 자동 기동을 시도합니다...")
            try:
                from lib.external_service_manager import ensure_flow_cdp_chrome_running
                ensure_flow_cdp_chrome_running()
                return await check_cdp_status(auto_start=False)
            except Exception as auto_err:
                return {
                    "connected": False,
                    "flow_ready": False,
                    "message": f"Chrome 디버그 포트 9222 미연결 및 자동 기동 실패: {auto_err}",
                    "page_url": None,
                }
        return {
            "connected": False,
            "flow_ready": False,
            "message": f"Chrome 디버그 포트 9222 미연결: {e}",
            "page_url": None,
        }


async def _generate_scene_with_page(
    page: Page,
    scene_id: str,
    prompt: str,
    output_dir: Optional[Path] = None,
    timeout_sec: int = 45,
) -> Dict[str, Any]:
    """Core 1-shot-1-completion image generation engine using an active page."""
    target_dir = output_dir or get_approved_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / f"{scene_id}.jpg"
    images_copy = get_images_dir() / f"{scene_id}.jpg"

    # 0. 멱등성 검사 (Idempotent Skip): 이미 유효한 파일이 존재하면 0초 만에 스킵
    if out_file.exists() and out_file.stat().st_size > 50000:
        if not images_copy.exists() or images_copy.stat().st_size != out_file.stat().st_size:
            try:
                shutil.copy2(out_file, images_copy)
            except Exception:
                pass
        return {
            "status": "SUCCESS",
            "scene_id": scene_id,
            "asset_type": "FLOW_IMAGE",
            "file_path": str(out_file),
            "bytes": out_file.stat().st_size,
            "skipped": True,
            "message": f"{scene_id} 이미 생성 완료됨 (멱등적 스킵)"
        }

    # Scroll Anchor Lock: 가상 스크롤 누락 방지를 위해 최상단(Index 0) 강제 앵커링
    try:
        await page.evaluate("window.scrollTo(0, 0)")
    except Exception:
        pass

    # 1. Dismiss cookie agree if present
    agree_btn = await page.query_selector("button:has-text('동의'), button:has-text('Agree')")
    if agree_btn and await agree_btn.is_visible():
        try:
            await agree_btn.click()
            await page.wait_for_timeout(300)
        except Exception:
            pass

    # 2. Ensure Image Mode
    await ensure_image_mode(page)
    if not await wait_for_canvas_idle(page, timeout_sec=min(90.0, float(timeout_sec))):
        return {"status": "ERROR", "scene_id": scene_id, "error": "Flow 캔버스가 idle 상태가 되지 않았습니다."}

    # 3. Capture baseline image URLs
    all_imgs = await page.evaluate("""() => {
        return Array.from(document.querySelectorAll('img'))
            .map(i => i.src || i.currentSrc || '');
    }""")
    baseline_set = set(u for u in all_imgs if is_flow_image_url(u))

    # 4. Focus textbox and clear
    textbox = await page.query_selector("div[contenteditable='true'], div[role='textbox']")
    if not textbox:
        return {"status": "ERROR", "scene_id": scene_id, "error": "프롬프트 입력창을 찾을 수 없습니다."}

    await textbox.click(force=True)
    await page.wait_for_timeout(200)

    # 5. Insert sanitized prompt
    clean_prompt = prompt.strip()
    await page.evaluate("""(p) => {
        const el = document.querySelector("div[contenteditable='true']") || document.querySelector("div[role='textbox']");
        if (el) {
            el.focus();
            document.execCommand('selectAll', false, null);
            document.execCommand('insertText', false, p);
        }
    }""", clean_prompt)
    await page.wait_for_timeout(300)

    # 6. Click submit button
    submit_btn = await page.query_selector("button:has-text('arrow_forward'), button:has-text('만들기')")
    if submit_btn and await submit_btn.is_visible():
        await submit_btn.click(force=True)
    else:
        await page.keyboard.press("Enter")

    # 7. Poll for new image card (up to timeout_sec)
    start_time = time.time()
    new_url = None
    while time.time() - start_time < timeout_sec:
        await page.wait_for_timeout(2000)

        # Early check for error or safety filter card on canvas
        err_card = await _detect_and_clear_error_card(page)
        if err_card:
            return {"status": "ERROR", "scene_id": scene_id, "error": f"Google Flow 에러 카드 감지 (자동 소거 조치): {err_card}"}

        cur_imgs = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('img'))
                .map(i => i.src || i.currentSrc || '');
        }""")
        new_candidates = [u for u in cur_imgs if is_flow_image_url(u) and u not in baseline_set]
        if new_candidates:
            new_url = new_candidates[0]
            break

    if not new_url:
        return {"status": "ERROR", "scene_id": scene_id, "error": f"이미지 생성 대기 시간 초과 ({timeout_sec}초)"}

    # 8. Download and Lanczos normalize to 1920x1080 JPEG
    resp = await page.request.get(new_url)
    if resp.status != 200:
        return {"status": "ERROR", "scene_id": scene_id, "error": f"이미지 다운로드 HTTP {resp.status}"}

    raw_bytes = await resp.body()
    part_file = out_file.with_suffix(".jpg.part")
    part_file.write_bytes(raw_bytes)

    with Image.open(part_file) as im:
        im_rgb = im.convert("RGB")
        if im_rgb.size != (1920, 1080):
            im_rgb = im_rgb.resize((1920, 1080), Image.Resampling.LANCZOS)
        im_rgb.save(out_file, format="JPEG", quality=95)

    if part_file.exists():
        part_file.unlink()

    # Synchronize to images/
    images_copy = get_images_dir() / f"{scene_id}.jpg"
    try:
        shutil.copy2(out_file, images_copy)
    except Exception:
        pass

    # Gate 8 Visibility Gate Evaluation
    gate8_eval = None
    try:
        from lib.asset_contract import evaluate_frame_visibility_from_file
        role = "opening_group" if ("SHOT_001" in scene_id or "cut" in scene_id) else "body"
        gate8_eval = evaluate_frame_visibility_from_file(out_file, scene_role=role)
    except Exception as e:
        print("Gate 8 evaluation note:", e)

    # Update manifest
    sha256 = hashlib.sha256(out_file.read_bytes()).hexdigest()
    logical_shot_id = scene_id.split("_cut")[0] if "_cut" in scene_id else scene_id
    try:
        manifest_data = {"assets": []}
        cur_manifest = get_manifest_path()
        if cur_manifest.exists():
            manifest_data = json.loads(cur_manifest.read_text(encoding="utf-8"))
        
        updated = False
        for a in manifest_data.get("assets", []):
            if a.get("asset_id") == scene_id or a.get("shot_id") == scene_id or a.get("scene_id") == scene_id:
                a["file_path"] = str(out_file)
                a["asset_type"] = "FLOW_IMAGE"
                a["asset_id"] = scene_id
                a["shot_id"] = logical_shot_id
                a["sha256"] = sha256
                a["bytes"] = out_file.stat().st_size
                a["width"] = 1920
                a["height"] = 1080
                a["status"] = "COMPLETED"
                if gate8_eval:
                    a["gate8_visibility"] = gate8_eval
                a["updated_at"] = datetime.now(timezone.utc).isoformat()
                updated = True
                break
        if not updated:
            entry = {
                "scene_id": scene_id,
                "asset_id": scene_id,
                "shot_id": logical_shot_id,
                "asset_type": "FLOW_IMAGE",
                "file_path": str(out_file),
                "sha256": sha256,
                "bytes": out_file.stat().st_size,
                "width": 1920,
                "height": 1080,
                "status": "COMPLETED",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            if gate8_eval:
                entry["gate8_visibility"] = gate8_eval
            manifest_data["assets"].append(entry)
        cur_manifest.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as err:
        print("Manifest update error:", err)

    elapsed = round(time.time() - start_time, 1)
    return {
        "status": "SUCCESS",
        "scene_id": scene_id,
        "asset_type": "FLOW_IMAGE",
        "file_path": str(out_file),
        "filename": out_file.name,
        "bytes": out_file.stat().st_size,
        "width": 1920,
        "height": 1080,
        "elapsed_sec": elapsed,
        "media_url": new_url,
    }


async def generate_single_scene_cdp(
    scene_id: str,
    prompt: str,
    output_dir: Optional[Path] = None,
    timeout_sec: int = 45,
    auto_start: bool = True,
) -> Dict[str, Any]:
    """Automate generating 1 shot image in Google Flow via CDP. Auto-starts Chrome if offline and auto_start=True."""
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            if auto_start:
                try:
                    from lib.external_service_manager import ensure_flow_cdp_chrome_running
                    ensure_flow_cdp_chrome_running()
                    browser = await p.chromium.connect_over_cdp(CDP_URL)
                except Exception as auto_err:
                    return {"status": "ERROR", "scene_id": scene_id, "error": f"CDP 연결 및 자동기동 실패 (포트 9222): {auto_err}"}
            else:
                return {"status": "ERROR", "scene_id": scene_id, "error": f"CDP 연결 실패 (포트 9222): {e}"}

        page = await get_flow_page(browser)
        if not page:
            return {"status": "ERROR", "scene_id": scene_id, "error": "Google Flow 탭을 찾을 수 없습니다."}

        return await _generate_scene_with_page(page, scene_id, prompt, output_dir, timeout_sec)


class FlowBatchManager:
    """Manages sequential batch image generation with 3s adaptive cooldown."""

    def __init__(self):
        self.is_running = False
        self.stop_requested = False
        self.total = 0
        self.current_index = 0
        self.current_scene = ""
        self.completed: List[Dict[str, Any]] = []
        self.failed: List[Dict[str, Any]] = []
        self.logs: List[str] = []
        self.start_time: Optional[float] = None
        self._task: Optional[asyncio.Task] = None

    def log(self, msg: str):
        now_str = datetime.now().strftime("%H:%M:%S")
        entry = f"[{now_str}] {msg}"
        self.logs.append(entry)
        if len(self.logs) > 200:
            self.logs = self.logs[-200:]
        print(entry)

    def get_status(self) -> Dict[str, Any]:
        elapsed = round(time.time() - self.start_time, 1) if self.start_time and self.is_running else 0
        progress_pct = round((self.current_index / max(1, self.total)) * 100, 1) if self.total else 0
        return {
            "is_running": self.is_running,
            "stop_requested": self.stop_requested,
            "total": self.total,
            "current_index": self.current_index,
            "current_scene": self.current_scene,
            "progress_percent": progress_pct,
            "completed_count": len(self.completed),
            "failed_count": len(self.failed),
            "completed_recent": self.completed[-5:],
            "failed_recent": self.failed[-5:],
            "logs": self.logs[-25:],
            "elapsed_sec": elapsed,
        }

    def stop(self) -> Dict[str, str]:
        if self.is_running:
            self.stop_requested = True
            self.log("사용자에 의해 일괄 생성 중지 요청됨. 현재 진행 중인 씬 완료 후 안전하게 종료됩니다.")
            return {"status": "STOP_REQUESTED", "message": "중지 요청이 접수되었습니다."}
        return {"status": "IDLE", "message": "현재 실행 중인 일괄 생성 작업이 없습니다."}

    async def _run_batch_internal(self, items: List[Dict[str, Any]], overwrite: bool = False):
        self.is_running = True
        self.stop_requested = False
        self.total = len(items)
        self.current_index = 0
        self.current_scene = ""
        self.completed = []
        self.failed = []
        self.logs = []
        self.start_time = time.time()
        consecutive_success = 0

        self.log(f"🚀 총 {self.total}개 씬 Google Flow CDP 순차 일괄 자동 생성 가동 (규격: 1920x1080 Lanczos, 적응형 쿨다운)")

        try:
            async with async_playwright() as p:
                try:
                    browser = await p.chromium.connect_over_cdp(CDP_URL)
                except Exception as e:
                    self.log(f"[*] CDP 연결 실패 (포트 9222). Chrome 자동 기동을 시도합니다...")
                    try:
                        from lib.external_service_manager import ensure_flow_cdp_chrome_running
                        ensure_flow_cdp_chrome_running()
                        browser = await p.chromium.connect_over_cdp(CDP_URL)
                    except Exception as auto_err:
                        self.log(f"❌ CDP 자동 기동 및 연결 실패 (포트 9222): {auto_err}")
                        self.is_running = False
                        return

                page = await get_flow_page(browser)
                if not page:
                    self.log("❌ Google Flow 활성 탭을 찾을 수 없습니다.")
                    self.is_running = False
                    return

                for idx, item in enumerate(items, 1):
                    if self.stop_requested:
                        self.log(f"⏹ 중지 요청에 따라 {idx-1}/{self.total}번째 씬에서 배치가 중단되었습니다.")
                        break

                    sid = item.get("scene_id") or item.get("shot_id")
                    prompt = item.get("compiled_prompt") or item.get("prompt") or ""
                    self.current_index = idx
                    self.current_scene = sid

                    # Check if already exists and valid
                    out_file = get_approved_dir() / f"{sid}.jpg"
                    if out_file.exists() and out_file.stat().st_size > 20000 and not overwrite:
                        self.log(f"[{idx}/{self.total}] {sid} 기존 고품질 이미지 존재 ({out_file.stat().st_size:,} bytes) -> 건너뜁니다.")
                        self.completed.append({"scene_id": sid, "status": "SKIPPED_EXISTING", "bytes": out_file.stat().st_size})
                        continue

                    self.log(f"[{idx}/{self.total}] {sid} 생성 착수 -> Google Flow 프롬프트 전송...")
                    res = await _generate_scene_with_page(page, sid, prompt, output_dir=get_approved_dir())

                    if res.get("status") == "SUCCESS":
                        consecutive_success += 1
                        self.log(f"[{idx}/{self.total}] {sid} 완료 ({res.get('bytes', 0):,} bytes, 소요 {res.get('elapsed_sec')}초)")
                        self.completed.append(res)
                    else:
                        consecutive_success = 0
                        err_msg = res.get("error", "미확인 오류")
                        self.log(f"[{idx}/{self.total}] {sid} 실패: {err_msg}")
                        self.failed.append({"scene_id": sid, "error": err_msg})

                    # Shared adaptive cooldown prevents provider/card race conditions.
                    if idx < self.total and not self.stop_requested:
                        cooldown = adaptive_cooldown(consecutive_success, had_error=res.get("status") != "SUCCESS")
                        self.log(f"쿨다운 대기 ({cooldown:.1f}초)...")
                        await page.wait_for_timeout(int(cooldown * 1000))

        except Exception as e:
            self.log(f"❌ 일괄 생성 치명적 예외: {e}")
        finally:
            self.is_running = False
            self.current_scene = ""
            total_time = round(time.time() - (self.start_time or time.time()), 1)
            self.log(f"🏁 일괄 생성 완료. 성공: {len(self.completed)}건, 실패: {len(self.failed)}건 (총 {total_time}초 소요)")

    def start_batch(self, items: List[Dict[str, Any]], overwrite: bool = False) -> Dict[str, Any]:
        if self.is_running:
            return {"status": "ALREADY_RUNNING", "message": f"현재 {self.current_scene} 생성이 진행 중입니다."}
        
        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._run_batch_internal(items, overwrite))
        return {
            "status": "STARTED",
            "message": f"총 {len(items)}개 씬 Google Flow CDP 일괄 생성이 백그라운드에서 시작되었습니다.",
            "total_items": len(items)
        }

    def start_batch_for_active_episode(self, start_idx: int = 0, max_count: Optional[int] = None, overwrite: bool = False) -> Dict[str, Any]:
        """Load shot items dynamically from the current active episode manifest and start batch."""
        ep_dir = get_current_ep_dir()
        manifest_p = ep_dir / "generation" / "master_1200s_manifest.json"
        if not manifest_p.exists():
            manifest_p = ep_dir / "source" / "scene_script_manifest_v2.json"
        if not manifest_p.exists():
            manifest_p = DEFAULT_EP_DIR / "generation" / "master_1200s_manifest.json"
        
        items = []
        if manifest_p.exists():
            try:
                data = json.loads(manifest_p.read_text(encoding="utf-8"))
                raw_shots = data.get("shots") or data.get("scenes") or []
                for s in raw_shots:
                    sid = s.get("shot_id") or s.get("scene_id")
                    prompt = s.get("visual_prompt") or s.get("compiled_prompt") or s.get("t2v_prompt") or s.get("prompt") or s.get("display_text") or s.get("narration") or ""
                    if sid:
                        items.append({"scene_id": sid, "shot_id": sid, "prompt": prompt, "compiled_prompt": prompt})
            except Exception as e:
                self.log(f"Manifest load warning: {e}")
        
        if not items:
            # Fallback to default prompts
            try:
                from workspace_manager import get_prompts_file_path
                p_file = get_prompts_file_path()
                if p_file.exists():
                    p_data = json.loads(p_file.read_text(encoding="utf-8"))
                    items = p_data.get("prompts", [])
            except Exception:
                pass

        if start_idx > 0:
            items = items[start_idx:]
        if max_count is not None and max_count > 0:
            items = items[:max_count]

        return self.start_batch(items, overwrite=overwrite)

    def start(self, start_idx: int = 0, max_count: Optional[int] = None, overwrite: bool = False) -> Dict[str, Any]:
        """Convenience alias for start_batch_for_active_episode to prevent legacy AttributeError."""
        return self.start_batch_for_active_episode(start_idx=start_idx, max_count=max_count, overwrite=overwrite)


# Singleton batch manager
batch_manager = FlowBatchManager()


def check_cdp_status_sync(auto_start: bool = True) -> Dict[str, Any]:
    return asyncio.run(check_cdp_status(auto_start=auto_start))


def generate_single_scene_cdp_sync(scene_id: str, prompt: str) -> Dict[str, Any]:
    return asyncio.run(generate_single_scene_cdp(scene_id, prompt))
