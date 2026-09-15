from __future__ import annotations

import asyncio
import hashlib

from PIL import Image

from generate_flow_batch import (
    classify_generation_error_text,
    current_asset_rows,
    merge_asset_rows,
    pending_requests,
    pilot_asset_fingerprint,
    provider_prompt,
    select_pilot_requests,
    select_v5_dual_pilot_requests,
    asset_has_download_evidence,
    archive_stale_asset_rows,
    summarize_batch,
    update_generation_scope,
    validate_pilot_approval,
    prepare_generation_manifest,
    _close_transient_popovers,
    is_flow_media_url,
)
from build_exact_flow_request_manifest import sanitize_flow_prompt
from inspect_live_flow import is_flow_project_url


class _FakeButton:
    def __init__(self, exists: bool):
        self.exists = exists
        self.clicked = False

    async def count(self):
        return 1 if self.exists else 0

    async def click(self):
        self.clicked = True


class _FakeDialog:
    def __init__(self):
        self.buttons = {}
        self.waited_for_hidden = False

    async def count(self):
        return 1

    def get_by_role(self, role, *, name, exact):
        button = _FakeButton(name == "시작하기")
        self.buttons[name] = button
        return button

    async def wait_for(self, *, state, timeout):
        assert state == "hidden"
        assert timeout == 5_000
        self.waited_for_hidden = True


class _FakeKeyboard:
    def __init__(self):
        self.keys = []

    async def press(self, key):
        self.keys.append(key)


class _FakePage:
    def __init__(self):
        self.dialog = _FakeDialog()
        self.keyboard = _FakeKeyboard()

    def get_by_role(self, role):
        assert role == "dialog"
        return self.dialog

    async def wait_for_timeout(self, timeout):
        assert timeout == 250


def test_close_transient_popovers_dismisses_korean_flow_update_dialog():
    page = _FakePage()

    asyncio.run(_close_transient_popovers(page))

    assert page.dialog.buttons["시작하기"].clicked
    assert page.dialog.waited_for_hidden


def test_v5_dual_pilot_selects_12_cold_open_and_8_coverage_without_duplicates():
    requests = [
        {"scene_id": f"S{i:03d}", "order": i, "start_sec": float((i - 1) * 10),
         "visual_mode": ["historical_reconstruction", "place_establishing", "evidence_artifact", "analogy_explainer"][i % 4]}
        for i in range(1, 102)
    ]
    result = select_v5_dual_pilot_requests(requests)
    cold = result["cold_open"]
    coverage = result["coverage"]
    assert len(cold) == 12
    assert len(coverage) == 8
    assert not ({row["scene_id"] for row in cold} & {row["scene_id"] for row in coverage})
    assert max(row["start_sec"] for row in cold) < 120.0


def test_completed_asset_without_download_evidence_is_not_complete():
    assert not asset_has_download_evidence({"status": "COMPLETED", "file_path": "", "sha256": "", "bytes": 0})
    assert asset_has_download_evidence({"status": "COMPLETED", "file_path": "S1.jpg", "sha256": "A" * 64, "bytes": 20000, "width": 1920, "height": 1080, "card_id": "FLOW-S1-A"})


def test_stale_asset_rows_move_to_history_instead_of_remaining_active():
    manifest = {"assets": [
        {"shot_id": "S1", "prompt_sha256": "CURRENT", "status": "COMPLETED"},
        {"shot_id": "S2", "prompt_sha256": "OLD", "status": "COMPLETED"},
    ]}
    updated = archive_stale_asset_rows(manifest, [
        {"scene_id": "S1", "request_sha256": "CURRENT"},
        {"scene_id": "S2", "request_sha256": "NEW"},
    ])
    assert [row["shot_id"] for row in updated["assets"]] == ["S1"]
    assert updated["asset_history"][-1]["shot_id"] == "S2"
    assert updated["asset_history"][-1]["archive_reason"] == "stale_request_hash"


def test_generation_preparation_archives_stale_row_before_replacement_merge():
    old = {"assets": [{
        "shot_id": "S1", "order": 1, "prompt_sha256": "OLD", "sha256": "IMAGE-OLD",
        "status": "COMPLETED",
    }]}
    requests = [{"scene_id": "S1", "request_sha256": "NEW"}]

    prepared = prepare_generation_manifest(old, requests)
    merged = merge_asset_rows(prepared, [{
        "shot_id": "S1", "order": 1, "prompt_sha256": "NEW", "sha256": "IMAGE-NEW",
        "status": "COMPLETED",
    }])

    assert merged["assets"][0]["prompt_sha256"] == "NEW"
    assert merged["asset_history"][0]["prompt_sha256"] == "OLD"
    assert merged["asset_history"][0]["sha256"] == "IMAGE-OLD"


def _asset(shot_id: str, *, status: str = "COMPLETED"):
    return {"shot_id": shot_id, "order": int(shot_id[1:]), "status": status, "file_path": f"{shot_id}.jpg"}


def test_selected_retry_merges_existing_manifest_without_losing_rows():
    existing = {"assets": [_asset("S1"), _asset("S2")]}
    merged = merge_asset_rows(existing, [_asset("S3")])
    assert [asset["shot_id"] for asset in merged["assets"]] == ["S1", "S2", "S3"]


def test_retry_replaces_only_matching_shot_row():
    existing = {"assets": [_asset("S1", status="FAILED"), _asset("S2")]}
    merged = merge_asset_rows(existing, [_asset("S1")])
    assert [asset["shot_id"] for asset in merged["assets"]] == ["S1", "S2"]
    assert merged["assets"][0]["status"] == "COMPLETED"


def test_batch_never_reports_success_when_asset_is_missing():
    report = summarize_batch(expected_ids=["S1", "S2"], downloaded_ids=["S1"])
    assert report["status"] == "FAIL"
    assert report["missing"] == ["S2"]


def test_pilot_selection_covers_representative_roles():
    roles = [
        "host_explainer", "historical_reconstruction", "evidence_object", "diagram_metaphor",
        "atmosphere", "historical_reconstruction", "host_explainer", "historical_reconstruction",
    ]
    requests = [{"scene_id": f"S{i + 1}", "visual_role": role} for i, role in enumerate(roles)]
    selected = select_pilot_requests(requests)
    assert len(selected) == 8
    selected_roles = [request["visual_role"] for request in selected]
    assert selected_roles.count("host_explainer") == 2
    assert selected_roles.count("historical_reconstruction") == 3
    assert {"evidence_object", "diagram_metaphor", "atmosphere"} <= set(selected_roles)


def test_provider_uses_submission_prompt_with_inline_exclusions():
    request = {"positive_prompt": "clean scene", "submission_prompt": "clean scene. all surfaces blank"}
    assert provider_prompt(request) == "clean scene. all surfaces blank"


def test_exact_flow_provider_sanitizes_raw_prompt_at_submission_boundary():
    request = {
        "visual_mode": "exact_2d_webtoon_plate",
        "submission_prompt": "disintegrating under intense UV rays next to healthy cellular membrane",
    }
    prompt = provider_prompt(request)
    assert len(prompt) <= 441
    assert "disintegrat" not in prompt.casefold()
    assert "uv rays" not in prompt.casefold()
    assert "cellular membrane" not in prompt.casefold()


def test_flow_content_media_url_is_a_candidate_result():
    assert is_flow_media_url("https://flow-content.google/image/result-123?Expires=1")


def test_live_flow_inspector_accepts_only_project_pages():
    assert is_flow_project_url("https://flow.google.com/project/8550306b-a63c-450f-beda-5ed1d72a760e")
    assert not is_flow_project_url("https://accounts.google.com/v3/signin/rejected?app_domain=https%3A%2F%2Flabs.google")


def test_flow_prompt_sanitizer_removes_sensitive_terms_and_bounds_length():
    prompt = (
        "2D graphic novel illustration, bold black ink contour outlines, "
        "2D graphic novel illustration style, bold clean black ink contour outlines, "
        "disintegrating under intense UV rays next to healthy cellular membrane, "
        "folate vitamin B9, sickle cell, detailed medical photorealistic scene, "
        "keep the bottom 18% visually clear for subtitles"
    )
    sanitized = sanitize_flow_prompt(prompt)

    assert len(sanitized) <= 441
    assert sanitized.lower().count("2d graphic novel") == 1
    assert not any(
        term in sanitized.casefold()
        for term in (
            "disintegrat",
            "uv ray",
            "cellular membrane",
            "folate",
            "vitamin b9",
            "sickle cell",
            "photorealistic",
        )
    )


def test_stale_completed_row_is_not_counted_for_current_request():
    requests = [{"scene_id": "S1", "request_sha256": "NEW"}, {"scene_id": "S2", "request_sha256": "SAME"}]
    assets = [
        {"shot_id": "S1", "status": "COMPLETED", "prompt_sha256": "OLD"},
        {"shot_id": "S2", "status": "COMPLETED", "prompt_sha256": "SAME"},
    ]
    assert [row["shot_id"] for row in current_asset_rows(requests, assets)] == ["S2"]


def test_selected_retry_preserves_existing_pilot_scope():
    manifest = {"generation_scope": "pilot", "expected_ids": ["S1", "S2", "S3"]}
    updated = update_generation_scope(manifest, ["S2"], "selected")
    assert updated["generation_scope"] == "pilot"
    assert updated["expected_ids"] == ["S1", "S2", "S3"]


def test_full_generation_skips_current_completed_pilot_assets():
    requests = [
        {"scene_id": "S1", "request_sha256": "A"},
        {"scene_id": "S2", "request_sha256": "B"},
        {"scene_id": "S3", "request_sha256": "C"},
    ]
    assets = [
        {"shot_id": "S1", "prompt_sha256": "A", "status": "COMPLETED", "file_path": "S1.jpg",
         "sha256": "A" * 64, "bytes": 20000, "width": 1920, "height": 1080, "card_id": "FLOW-S1-A"},
        {"shot_id": "S2", "prompt_sha256": "OLD", "status": "COMPLETED"},
    ]
    assert [request["scene_id"] for request in pending_requests(requests, assets)] == ["S2", "S3"]


def test_pending_requests_revalidates_existing_file_when_asset_root_is_provided(tmp_path):
    path = tmp_path / "S1.jpg"
    Image.effect_noise((1920, 1080), 64).convert("RGB").save(path, quality=92)
    row = {
        "shot_id": "S1",
        "prompt_sha256": "A",
        "status": "COMPLETED",
        "file_path": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "width": 1920,
        "height": 1080,
        "card_id": "FLOW-S1",
    }
    requests = [{"scene_id": "S1", "request_sha256": "A"}]
    assert pending_requests(requests, [row], asset_root=tmp_path) == []

    path.write_bytes(b"corrupt" * 5_000)
    assert pending_requests(requests, [row], asset_root=tmp_path) == [requests[0]]


def test_pilot_approval_rejects_stale_manifest_hash():
    errors = validate_pilot_approval(
        {"decision": "approved", "contract_sha256": "CONTRACT", "manifest_sha256": "OLD"},
        contract_sha256="CONTRACT",
        manifest_sha256="CURRENT",
    )
    assert errors == ["Pilot approval is stale for the current asset manifest"]


def test_korean_flow_quota_error_is_classified_before_url_timeout():
    text = "Nano Banana Pro 생성량 한도에 도달했습니다. 다른 모델을 사용해 보세요."
    assert classify_generation_error_text(text) == "provider_quota_exhausted"


def test_flow_activity_block_is_classified_before_url_timeout():
    text = "비정상적인 활동이 감지되었습니다. 자세한 내용은 고객센터를 참고하세요."
    assert classify_generation_error_text(text) == "provider_activity_blocked"


def test_korean_flow_policy_rejection_is_classified_before_url_timeout():
    text = "이 콘텐츠는 Google 정책을 위반할 수 있습니다. 다른 프롬프트를 사용해 보세요."
    assert classify_generation_error_text(text) == "provider_policy_rejected"


def test_pilot_asset_fingerprint_ignores_non_pilot_rows_but_detects_pilot_change():
    pilot_ids = ["S1", "S2"]
    base = {
        "assets": [
            {"shot_id": "S1", "prompt_sha256": "P1", "sha256": "A1", "status": "COMPLETED"},
            {"shot_id": "S2", "prompt_sha256": "P2", "sha256": "A2", "status": "COMPLETED"},
        ]
    }
    grown = {"assets": [*base["assets"], {"shot_id": "S3", "prompt_sha256": "P3", "sha256": "A3", "status": "COMPLETED"}]}
    changed = {"assets": [{**base["assets"][0], "sha256": "CHANGED"}, base["assets"][1]]}
    assert pilot_asset_fingerprint(base, pilot_ids) == pilot_asset_fingerprint(grown, pilot_ids)
    assert pilot_asset_fingerprint(base, pilot_ids) != pilot_asset_fingerprint(changed, pilot_ids)


def test_pilot_approval_accepts_manifest_growth_when_approved_asset_fingerprint_matches():
    approval = {
        "decision": "approved",
        "contract_sha256": "CONTRACT",
        "manifest_sha256": "OLD",
        "pilot_asset_fingerprint_sha256": "PILOT",
    }
    errors = validate_pilot_approval(
        approval,
        contract_sha256="CONTRACT",
        manifest_sha256="CURRENT",
        pilot_asset_fingerprint_sha256="PILOT",
    )
    assert errors == []
