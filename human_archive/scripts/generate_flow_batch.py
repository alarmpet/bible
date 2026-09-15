# -*- coding: utf-8 -*-
"""Pilot-first, resumable Google Flow image generation over Chrome CDP."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image
from playwright.async_api import Page, async_playwright

from build_exact_flow_request_manifest import sanitize_flow_prompt
from lib.host_overlay import composite_canonical_host, render_canonical_host_asset
from lib.flow_dom_maintenance import (
    clear_error_cards,
    cleanup_verified_cards,
    dom_gc_due,
    wait_for_canvas_idle,
)
from lib.flow_generation_state import adaptive_cooldown, validate_download_evidence
from lib.provenance import compute_file_sha256, compute_object_sha256


_PROJECT_ROOT = Path(__file__).resolve().parents[2]

PILOT_ROLE_COUNTS = {
    "host_explainer": 2,
    "historical_reconstruction": 3,
    "evidence_object": 1,
    "diagram_metaphor": 1,
    "atmosphere": 1,
}

FLOW_GENERATION_ERROR_PATTERNS = {
    "provider_policy_rejected": (
        "Google 정책을 위반할 수 있습니다",
        "may violate Google's policies",
        "may violate Google policy",
    ),
    "provider_quota_exhausted": (
        "생성량 한도에 도달",
        "generation limit",
        "quota has been reached",
    ),
    "provider_activity_blocked": (
        "비정상적인 활동이 감지되었습니다",
        "unusual activity was detected",
        "suspicious activity was detected",
    ),
    "provider_generation_failed": (
        "요청을 처리할 수 없습니다",
        "문제가 발생했습니다",
        "something went wrong",
        "generation failed",
    ),
}


class FlowGenerationError(RuntimeError):
    """Flow rendered an explicit provider failure instead of new media."""


def classify_generation_error_text(text: str) -> str | None:
    normalized = str(text).casefold()
    for error_kind, patterns in FLOW_GENERATION_ERROR_PATTERNS.items():
        if any(pattern.casefold() in normalized for pattern in patterns):
            return error_kind
    return None


def provider_prompt(request: dict[str, Any]) -> str:
    prompt = str(request.get("submission_prompt") or request["positive_prompt"])
    if request.get("visual_mode") == "exact_2d_webtoon_plate":
        return sanitize_flow_prompt(prompt)
    return prompt


def asset_has_download_evidence(row: dict[str, Any], file_path: Path | None = None) -> bool:
    metadata_valid = (
        row.get("status") == "COMPLETED"
        and bool(row.get("file_path"))
        and len(str(row.get("sha256", ""))) == 64
        and int(row.get("bytes", 0)) >= 20_000
        and int(row.get("width", 0)) > 0
        and int(row.get("height", 0)) > 0
        and bool(row.get("card_id"))
    )
    if not metadata_valid:
        return False
    if file_path is None:
        # Resume manifests created by older runs may not have been checked
        # against the local disk yet; retain the metadata-only signal here so
        # callers can locate those rows for revalidation.
        return True
    return validate_download_evidence(row, file_path)


def current_asset_rows(requests: list[dict[str, Any]], assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    request_sha_by_id = {
        str(request.get("asset_id") or request.get("scene_id") or request.get("shot_id")): str(request.get("request_sha256", ""))
        for request in requests
    }
    return [
        row
        for row in assets
        if str(row.get("asset_id") or row.get("shot_id", "")) in request_sha_by_id
        and str(row.get("prompt_sha256", "")) == request_sha_by_id[str(row.get("asset_id") or row.get("shot_id", ""))]
    ]


def pilot_asset_fingerprint(manifest: dict[str, Any], shot_ids: list[str]) -> str:
    rows_by_id = {str(row.get("asset_id") or row.get("shot_id", "")): row for row in manifest.get("assets", [])}
    stable_fields = (
        "shot_id", "asset_id", "order", "prompt_sha256", "file_path", "sha256", "bytes", "width", "height", "status"
    )
    projection = []
    for shot_id in shot_ids:
        row = rows_by_id.get(str(shot_id))
        if row is None:
            projection.append({"shot_id": str(shot_id), "status": "MISSING"})
        else:
            projection.append({field: row.get(field) for field in stable_fields if field in row or field == "shot_id"})
    return compute_object_sha256({"shot_ids": [str(shot_id) for shot_id in shot_ids], "assets": projection})


def pending_requests(
    requests: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    *,
    asset_root: Path | None = None,
) -> list[dict[str, Any]]:
    root = asset_root.resolve() if asset_root is not None else None

    def has_evidence(row: dict[str, Any]) -> bool:
        if root is None:
            return asset_has_download_evidence(row)
        raw_path = Path(str(row.get("file_path", "")))
        candidate = raw_path if raw_path.is_absolute() else root / raw_path
        try:
            candidate.resolve().relative_to(root)
        except ValueError:
            return False
        return asset_has_download_evidence(row, candidate)

    completed_ids = {
        str(row.get("asset_id") or row.get("shot_id", ""))
        for row in current_asset_rows(requests, assets)
        if has_evidence(row)
    }
    return [
        request
        for request in requests
        if str(request.get("asset_id") or request.get("scene_id") or request.get("shot_id")) not in completed_ids
    ]


def update_generation_scope(manifest: dict[str, Any], selected_ids: list[str], scope: str) -> dict[str, Any]:
    updated = dict(manifest)
    existing_scope = str(updated.get("generation_scope", ""))
    existing_ids = [str(scene_id) for scene_id in updated.get("expected_ids", [])]
    if scope == "selected" and existing_scope in {"pilot", "all"} and set(selected_ids) <= set(existing_ids):
        return updated
    updated["generation_scope"] = scope
    updated["expected_ids"] = list(selected_ids)
    return updated


def merge_asset_rows(existing: dict[str, Any] | None, updates: list[dict[str, Any]]) -> dict[str, Any]:
    base = dict(existing or {})
    by_id = {str(row.get("asset_id") or row.get("shot_id", "")): dict(row) for row in base.get("assets", [])}
    for row in updates:
        by_id[str(row.get("asset_id") or row.get("shot_id", ""))] = dict(row)
    base["assets"] = sorted(
        by_id.values(),
        key=lambda row: (int(row.get("order", 0)), str(row.get("asset_id") or row.get("shot_id", "")))
    )
    base.setdefault("schema_version", 2)
    base["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    return base


def archive_stale_asset_rows(manifest: dict[str, Any], requests: list[dict[str, Any]]) -> dict[str, Any]:
    updated = dict(manifest)
    current_sha = {
        str(request.get("asset_id") or request.get("scene_id") or request.get("shot_id")): str(request.get("request_sha256", ""))
        for request in requests
    }
    active: list[dict[str, Any]] = []
    history = [dict(row) for row in updated.get("asset_history", [])]
    history_keys = {
        (str(row.get("asset_id") or row.get("shot_id", "")), str(row.get("prompt_sha256", "")), str(row.get("sha256", "")))
        for row in history
    }
    for source_row in updated.get("assets", []):
        row = dict(source_row)
        key_id = str(row.get("asset_id") or row.get("shot_id", ""))
        if key_id in current_sha and str(row.get("prompt_sha256", "")) == current_sha[key_id]:
            active.append(row)
            continue
        row["archive_reason"] = "stale_request_hash" if key_id in current_sha else "unknown_request_id"
        row["archived_at_utc"] = datetime.now(timezone.utc).isoformat()
        key = (key_id, str(row.get("prompt_sha256", "")), str(row.get("sha256", "")))
        if key not in history_keys:
            history.append(row)
            history_keys.add(key)
    updated["assets"] = active
    if history:
        updated["asset_history"] = history
    return updated


def prepare_generation_manifest(
    manifest: dict[str, Any], requests: list[dict[str, Any]]
) -> dict[str, Any]:
    """Archive stale rows before a replacement can overwrite them by shot ID."""
    return archive_stale_asset_rows(manifest, requests)


def summarize_batch(
    expected_ids: list[str],
    downloaded_ids: list[str],
    *,
    failed_ids: list[str] | None = None,
    review_required_ids: list[str] | None = None,
) -> dict[str, Any]:
    expected = list(dict.fromkeys(expected_ids))
    downloaded = set(downloaded_ids)
    failed = sorted(set(failed_ids or []))
    review_required = sorted(set(review_required_ids or []))
    missing = [shot_id for shot_id in expected if shot_id not in downloaded]
    duplicates = sorted({shot_id for shot_id in downloaded_ids if downloaded_ids.count(shot_id) > 1})
    status = "PASS" if not missing and not duplicates and not failed and not review_required else "FAIL"
    return {
        "status": status,
        "expected_count": len(expected),
        "downloaded_count": len(downloaded & set(expected)),
        "missing": missing,
        "duplicates": duplicates,
        "failed": failed,
        "review_required": review_required,
    }


def select_pilot_requests(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for role, count in PILOT_ROLE_COUNTS.items():
        candidates = [request for request in requests if request.get("visual_role") == role]
        if len(candidates) < count:
            raise ValueError(f"pilot requires {count} {role} request(s), found {len(candidates)}")
        if count == 1:
            picks = [candidates[len(candidates) // 2]]
        elif count == len(candidates):
            picks = candidates
        else:
            picks = [candidates[round(index * (len(candidates) - 1) / (count - 1))] for index in range(count)]
        for request in picks:
            scene_id = str(request["scene_id"])
            if scene_id not in selected_ids:
                selected.append(request)
                selected_ids.add(scene_id)
    return sorted(selected, key=lambda request: int(request.get("order", requests.index(request) + 1)))


def select_v5_dual_pilot_requests(requests: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    ordered = sorted(requests, key=lambda request: (int(request.get("order", 0)), str(request["scene_id"])))
    cold_open = [request for request in ordered if float(request.get("start_sec", 10**9)) < 120.0][:12]
    if len(cold_open) < 12:
        cold_open = ordered[:12]
    cold_ids = {str(request["scene_id"]) for request in cold_open}
    remaining = [request for request in ordered if str(request["scene_id"]) not in cold_ids]
    if len(remaining) < 8:
        raise ValueError(f"v5 dual pilot requires at least 20 requests, found {len(ordered)}")
    coverage = [remaining[round(index * (len(remaining) - 1) / 7)] for index in range(8)]
    return {"cold_open": cold_open, "coverage": coverage}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def validate_pilot_approval(
    approval: dict[str, Any],
    *,
    contract_sha256: str,
    manifest_sha256: str,
    pilot_asset_fingerprint_sha256: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if approval.get("decision") != "approved":
        errors.append("Pilot approval decision is not approved")
    if approval.get("contract_sha256") != contract_sha256:
        errors.append("Pilot approval is stale for the current visual contract")
    if approval.get("manifest_sha256") != manifest_sha256:
        approved_fingerprint = approval.get("pilot_asset_fingerprint_sha256")
        if not approved_fingerprint or approved_fingerprint != pilot_asset_fingerprint_sha256:
            errors.append("Pilot approval is stale for the current asset manifest")
    return errors


def _require_current_pilot_approval(
    build_dir: Path,
    contract_sha256: str,
    manifest: dict[str, Any],
) -> None:
    approval_path = build_dir / "approvals" / "visual_pilot_review.json"
    if not approval_path.exists():
        raise SystemExit(f"Current pilot approval required before --all: {approval_path}")
    approval = _read_json(approval_path)
    pilot_ids = [str(item.get("shot_id", "")) for item in approval.get("shot_evaluations", [])]
    errors = validate_pilot_approval(
        approval,
        contract_sha256=contract_sha256,
        manifest_sha256=compute_object_sha256(manifest),
        pilot_asset_fingerprint_sha256=pilot_asset_fingerprint(manifest, pilot_ids),
    )
    if errors:
        raise SystemExit("; ".join(errors))


def is_flow_media_url(url: str) -> bool:
    return bool(url) and not any(token in url for token in ("flower-placeholder", "favicon")) and any(
        token in url
        for token in (
            "flow-content.google/",
            "labs.google/fx/api",
            "getMediaUrlRedirect",
            "googleusercontent.com",
        )
    )


async def _media_urls(page: Page) -> list[str]:
    return await page.evaluate("""() => Array.from(document.querySelectorAll('img'))
      .map((element) => element.currentSrc || element.src || '')
      .filter((url) => url && !url.includes('flower-placeholder') && !url.includes('favicon') &&
        (url.includes('flow-content.google/') || url.includes('labs.google/fx/api') ||
         url.includes('getMediaUrlRedirect') || url.includes('googleusercontent.com')))""")


async def _generation_error_counts(page: Page) -> dict[str, int]:
    body_text = await page.locator("body").inner_text()
    normalized = body_text.casefold()
    return {
        error_kind: sum(normalized.count(pattern.casefold()) for pattern in patterns)
        for error_kind, patterns in FLOW_GENERATION_ERROR_PATTERNS.items()
    }


async def _close_transient_popovers(page: Page) -> None:
    dialog = page.get_by_role("dialog")
    if await dialog.count():
        for button_name in ("시작하기", "Get started", "Start"):
            dismiss = dialog.get_by_role("button", name=button_name, exact=True)
            if await dismiss.count():
                await dismiss.click()
                await dialog.wait_for(state="hidden", timeout=5_000)
                break
    await page.keyboard.press("Escape")
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(250)


async def _select_flow_model(page: Page, target_model: str) -> None:
    await _close_transient_popovers(page)
    picker = page.locator("button").filter(has_text="Nano Banana").last
    await picker.wait_for(state="visible", timeout=10_000)
    current_text = await picker.inner_text()
    if any(line.strip().endswith(target_model) for line in current_text.splitlines()):
        return
    await picker.click()
    model_dropdown = page.locator("button").filter(has_text="arrow_drop_down").last
    await model_dropdown.wait_for(state="visible", timeout=10_000)
    await model_dropdown.click()
    option = page.get_by_role("menuitem").filter(has_text=target_model).last
    await option.wait_for(state="visible", timeout=10_000)
    await option.click()
    await _close_transient_popovers(page)
    selected_text = await page.locator("button").filter(has_text="Nano Banana").last.inner_text()
    if not any(line.strip().endswith(target_model) for line in selected_text.splitlines()):
        raise RuntimeError(f"Flow model selection did not stick: requested {target_model!r}, got {selected_text!r}")


async def _submit_prompt(page: Page, prompt: str) -> None:
    textbox = page.locator("div[role='textbox'], [contenteditable='true']").last
    await textbox.wait_for(state="visible", timeout=15_000)
    await textbox.click()
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Backspace")
    await textbox.fill(prompt)
    submit = page.locator("button").filter(has_text="arrow_forward").last
    if await submit.count():
        await submit.wait_for(state="visible", timeout=5_000)
        await submit.click(timeout=3_000)
    else:
        await page.keyboard.press("Enter")


async def _wait_for_stable_new_url(
    page: Page,
    before: set[str],
    before_errors: dict[str, int],
    timeout_sec: int = 150,
) -> str:
    deadline = asyncio.get_running_loop().time() + timeout_sec
    candidate = ""
    stable_count = 0
    while asyncio.get_running_loop().time() < deadline:
        current_errors = await _generation_error_counts(page)
        for error_kind, count in current_errors.items():
            if count > before_errors.get(error_kind, 0):
                raise FlowGenerationError(f"{error_kind}: Flow rendered an explicit generation error card")
        urls = await _media_urls(page)
        new_urls = [url for url in urls if url not in before]
        newest = new_urls[-1] if new_urls else ""
        if newest and newest == candidate:
            stable_count += 1
        elif newest:
            candidate = newest
            stable_count = 1
        if stable_count >= 2:
            return candidate
        await page.wait_for_timeout(2_000)
    raise TimeoutError("no stable new Flow media URL appeared before timeout")


async def _download_asset(page: Page, url: str, target: Path) -> tuple[str, int]:
    response = await page.request.get(url)
    if response.status != 200:
        raise RuntimeError(f"Flow media download returned HTTP {response.status}")
    body = await response.body()
    if len(body) < 20_000:
        raise RuntimeError("Flow media response is too small to be a generated image")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    temporary.write_bytes(body)
    with Image.open(temporary) as image:
        rgb = image.convert("RGB")
        if rgb.size != (1920, 1080):
            rgb = rgb.resize((1920, 1080), Image.Resampling.LANCZOS)
        rgb.save(target, format="JPEG", quality=95)
    temporary.unlink(missing_ok=True)
    return compute_file_sha256(target), target.stat().st_size


async def generate_flow_batch(
    build_dir: Path,
    requests: list[dict[str, Any]],
    *,
    cdp_url: str,
    model: str | None = None,
) -> dict[str, Any]:
    build_dir = Path(build_dir)
    images_dir = build_dir / "images"
    manifest_path = build_dir / "asset_manifest.json"
    existing = _read_json(manifest_path) if manifest_path.exists() else {
        "schema_version": 2,
        "build_id": build_dir.name,
        "provider": "google_flow_cdp",
        "assets": [],
    }
    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.connect_over_cdp(cdp_url)
        except Exception as cdp_err:
            print(f"[*] Chrome CDP 연결 실패 ({cdp_err}). Chrome 자동 기동을 시도합니다...")
            try:
                from lib.external_service_manager import ensure_flow_cdp_chrome_running
            except ImportError:
                try:
                    from external_service_manager import ensure_flow_cdp_chrome_running
                except ImportError:
                    ensure_flow_cdp_chrome_running = None
            if ensure_flow_cdp_chrome_running:
                ensure_flow_cdp_chrome_running()
                browser = await playwright.chromium.connect_over_cdp(cdp_url)
            else:
                raise
        pages = [page for context in browser.contexts for page in context.pages if "labs.google" in page.url or "flow" in page.url]
        if len(pages) != 1:
            raise RuntimeError(f"expected exactly one Google Flow page, found {len(pages)}")
        page = pages[0]
        if model:
            await _select_flow_model(page, model)
            existing["model"] = model
        seen = set(await _media_urls(page))
        verified_count = 0
        consecutive_success = 0
        for index, request in enumerate(requests, 1):
            shot_id = str(request["scene_id"])
            prompt = provider_prompt(request)
            row = {
                "shot_id": shot_id,
                "order": int(request.get("order", index)),
                "asset_type": "FLOW_IMAGE",
                "card_id": "",
                "prompt_sha256": request.get("request_sha256") or hashlib.sha256(prompt.encode("utf-8")).hexdigest().upper(),
                "file_path": "",
                "sha256": "",
                "bytes": 0,
                "width": 0,
                "height": 0,
                "status": "SUBMITTED",
            }
            existing = merge_asset_rows(existing, [row])
            _write_json_atomic(manifest_path, existing)
            stop_after_row = False
            try:
                before = set(await _media_urls(page)) | seen
                before_errors = await _generation_error_counts(page)
                if not await wait_for_canvas_idle(page, timeout_sec=90.0):
                    raise FlowGenerationError("Flow canvas did not become idle before submission")
                await clear_error_cards(page)
                await _submit_prompt(page, prompt)
                media_url = await _wait_for_stable_new_url(page, before, before_errors)
                image_path = images_dir / f"{shot_id}.jpg"
                host_overlay = request.get("host_overlay")
                if host_overlay:
                    raw_path = images_dir / "raw" / f"{shot_id}.jpg"
                    await _download_asset(page, media_url, raw_path)
                    overlay_path = Path(str(host_overlay["asset"]))
                    if not overlay_path.is_absolute():
                        overlay_path = _PROJECT_ROOT / overlay_path
                    if not overlay_path.exists():
                        render_canonical_host_asset(overlay_path)
                    postprocess = composite_canonical_host(
                        raw_path,
                        overlay_path,
                        image_path,
                        width_ratio=float(host_overlay.get("width_ratio", 0.38)),
                    )
                    postprocess["raw_file"] = str(raw_path.relative_to(images_dir)).replace("\\", "/")
                    overlay_path = Path(str(host_overlay["asset"]))
                    if not overlay_path.is_absolute():
                        overlay_path = _PROJECT_ROOT / overlay_path
                    if not overlay_path.exists():
                        render_canonical_host_asset(overlay_path)
                    postprocess = composite_canonical_host(
                        raw_path,
                        overlay_path,
                        image_path,
                        width_ratio=float(host_overlay.get("width_ratio", 0.38)),
                    )
                    postprocess["raw_file"] = str(raw_path.relative_to(images_dir)).replace("\\", "/")
                    row["postprocess"] = postprocess
                    digest = str(postprocess["output_sha256"])
                    byte_count = image_path.stat().st_size
                else:
                    digest, byte_count = await _download_asset(page, media_url, image_path)
                seen.add(media_url)
                row.update({
                    "card_id": f"FLOW-{shot_id}-{digest[:8]}",
                    "file_path": image_path.name,
                    "sha256": digest,
                    "bytes": byte_count,
                    "width": 1920,
                    "height": 1080,
                    "status": "COMPLETED",
                })
                if not validate_download_evidence(row, image_path):
                    raise FlowGenerationError("downloaded asset failed physical file/hash validation")
                verified_count += 1
                if dom_gc_due(verified_count):
                    await cleanup_verified_cards(page, 25)
            except FlowGenerationError as error:
                row["status"] = "FAILED"
                row["error"] = str(error)
                stop_after_row = True
                try:
                    await clear_error_cards(page)
                except Exception:
                    pass
            except Exception as error:
                row["status"] = "FAILED"
                row["error"] = str(error)
                try:
                    await clear_error_cards(page)
                except Exception:
                    pass
            existing = merge_asset_rows(existing, [row])
            _write_json_atomic(manifest_path, existing)
            print(f"[{index}/{len(requests)}] {shot_id}: {row['status']}")
            if row["status"] == "COMPLETED":
                consecutive_success += 1
            else:
                consecutive_success = 0
            if index < len(requests):
                cooldown = adaptive_cooldown(consecutive_success, had_error=row["status"] != "COMPLETED")
                await page.wait_for_timeout(int(cooldown * 1000))
            if stop_after_row:
                break
        await browser.close()
    return existing


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pilot", action="store_true")
    mode.add_argument("--all", action="store_true")
    mode.add_argument("--only", nargs="+")
    parser.add_argument("--cdp", default="http://127.0.0.1:9222")
    parser.add_argument("--model", choices=["Nano Banana Pro", "Nano Banana 2", "Nano Banana 2 Lite"])
    args = parser.parse_args()

    request_manifest = _read_json(args.build / "image_request_manifest.json")
    requests = list(request_manifest.get("requests", []))
    contract_sha256 = str(request_manifest.get("contract_sha256", ""))
    existing_manifest_path = args.build / "asset_manifest.json"
    existing_manifest = _read_json(existing_manifest_path) if existing_manifest_path.exists() else {"assets": []}
    existing_manifest = prepare_generation_manifest(existing_manifest, requests)
    _write_json_atomic(existing_manifest_path, existing_manifest)
    if args.pilot:
        pilot_sets = select_v5_dual_pilot_requests(requests) if any(request.get("visual_mode") for request in requests) else None
        expected_requests = (
            [*pilot_sets["cold_open"], *pilot_sets["coverage"]]
            if pilot_sets else select_pilot_requests(requests)
        )
        selected = pending_requests(
            expected_requests,
            existing_manifest.get("assets", []),
            asset_root=args.build / "images",
        )
    elif args.only:
        wanted = set(args.only)
        selected = [request for request in requests if request["scene_id"] in wanted]
        missing = sorted(wanted - {request["scene_id"] for request in selected})
        if missing:
            raise SystemExit(f"Unknown requested scene IDs: {missing}")
        expected_requests = selected
    else:
        _require_current_pilot_approval(
            args.build,
            contract_sha256,
            existing_manifest,
        )
        selected = pending_requests(
            requests,
            existing_manifest.get("assets", []),
            asset_root=args.build / "images",
        )
        expected_requests = requests

    manifest = (
        asyncio.run(generate_flow_batch(args.build, selected, cdp_url=args.cdp, model=args.model))
        if selected
        else existing_manifest
    )
    manifest = archive_stale_asset_rows(manifest, requests)
    selected_ids = [request["scene_id"] for request in selected]
    scope = "pilot" if args.pilot else ("selected" if args.only else "all")
    expected_ids = [request["scene_id"] for request in expected_requests]
    manifest = update_generation_scope(manifest, expected_ids, scope)
    if args.pilot and pilot_sets:
        manifest["pilot_sets"] = {
            "cold_open": [request["scene_id"] for request in pilot_sets["cold_open"]],
            "coverage": [request["scene_id"] for request in pilot_sets["coverage"]],
        }
    _write_json_atomic(args.build / "asset_manifest.json", manifest)
    selected_rows = current_asset_rows(expected_requests, manifest.get("assets", []))
    report = summarize_batch(
        expected_ids,
        [row["shot_id"] for row in selected_rows if row.get("status") == "COMPLETED"],
        failed_ids=[row["shot_id"] for row in selected_rows if row.get("status") == "FAILED"],
        review_required_ids=[row["shot_id"] for row in selected_rows if row.get("status") == "REVIEW_REQUIRED"],
    )
    _write_json_atomic(args.build / "flow_batch_report.json", report)
    if report["status"] != "PASS":
        raise SystemExit(f"Flow batch failed closed: {report}")
    print(f"Flow batch PASS: {report['downloaded_count']}/{report['expected_count']}")


if __name__ == "__main__":
    main()
