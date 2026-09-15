# -*- coding: utf-8 -*-
"""Test visual QA integrity, dimension checks, near-duplicates, and approvals."""
from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest
from PIL import Image

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.visual_content_qa import inspect_generated_text, rapidocr_result_to_findings
from lib.visual_qa import check_near_duplicates, validate_visual_evaluation, verify_image_pixel_integrity
from verify_visual_assets import verify_visual_build
from lib.provenance import compute_object_sha256


def test_detects_invalid_image_dimensions(tmp_path: Path):
    bad_img = tmp_path / "bad.jpg"
    img = Image.new("RGB", (800, 600), color=(100, 100, 100))
    img.save(bad_img)

    ok, issues = verify_image_pixel_integrity(bad_img)
    assert ok is False
    assert any("Invalid dimensions 800x600" in iss for iss in issues)


def test_detects_near_duplicate_images(tmp_path: Path):
    img1_path = tmp_path / "img1.jpg"
    img2_path = tmp_path / "img2.jpg"

    base_img = Image.new("RGB", (1920, 1080), color=(120, 50, 80))
    base_img.save(img1_path)

    # Slight pixel tweak still detected as duplicate by pHash
    tweaked = base_img.copy()
    tweaked.putpixel((10, 10), (121, 51, 81))
    tweaked.save(img2_path)

    duplicates = check_near_duplicates([img1_path, img2_path])
    assert len(duplicates) >= 1
    assert duplicates[0][0] == "img1.jpg"
    assert duplicates[0][1] == "img2.jpg"


def test_requires_human_visual_approval(tmp_path: Path):
    build = tmp_path / "build"
    (build / "images").mkdir(parents=True)
    image = build / "images" / "shot.jpg"
    Image.new("RGB", (1920, 1080), color=(10, 20, 30)).save(image)
    import hashlib
    sha = hashlib.sha256(image.read_bytes()).hexdigest().upper()
    (build / "asset_manifest.json").write_text(json.dumps({"assets": [{
        "shot_id": "shot", "status": "COMPLETED", "file_path": "shot.jpg", "sha256": sha
    }]}), encoding="utf-8")

    ok, errors = verify_visual_build(build_dir=build)

    assert ok is False
    assert any("approval" in error.lower() for error in errors)


class _FakeOCR:
    def __init__(self, findings):
        self.findings = findings

    def __call__(self, _path):
        return self.findings


def test_base_image_fails_when_ocr_detects_year(tmp_path: Path):
    image = tmp_path / "shot.jpg"
    Image.new("RGB", (1920, 1080), color=(255, 255, 255)).save(image)
    result = inspect_generated_text(
        image,
        _FakeOCR([{"text": "1701", "confidence": 0.97, "bbox": [1, 2, 30, 20]}]),
    )
    assert result.status == "FAIL"
    assert result.findings[0]["text"] == "1701"


def test_ocr_unavailable_is_review_required(tmp_path: Path):
    image = tmp_path / "shot.jpg"
    Image.new("RGB", (1920, 1080), color=(255, 255, 255)).save(image)
    result = inspect_generated_text(image, None)
    assert result.status == "REVIEW_REQUIRED"


def test_rapidocr_numpy_output_is_normalized_without_truth_value_error():
    import numpy as np

    class Result:
        txts = ("1701",)
        scores = np.array([0.98])
        boxes = np.array([[[1, 2], [30, 2], [30, 20], [1, 20]]])

    findings = rapidocr_result_to_findings(Result())
    assert findings == [{
        "text": "1701",
        "confidence": 0.98,
        "bbox": [[1, 2], [30, 2], [30, 20], [1, 20]],
    }]


def test_reconstruction_requires_host_absence_review_axis():
    errors = validate_visual_evaluation(
        scene={"visual_role": "historical_reconstruction"},
        evaluation={
            "decision": "approved",
            "axes": {
                "semantic_match": "PASS",
                "historical_subject": "PASS",
                "host_presence": "FAIL",
                "embedded_text": "PASS",
                "composition_density": "PASS",
                "style_profile": "PASS",
                "dignity": "PASS",
                "service_mark": "PASS",
            },
        },
    )
    assert any("host_presence" in error for error in errors)


def test_role_aware_build_fails_closed_on_embedded_text(tmp_path: Path):
    build = tmp_path / "build"
    (build / "images").mkdir(parents=True)
    (build / "approvals").mkdir()
    image = build / "images" / "scene-1.jpg"
    Image.new("RGB", (1920, 1080), color=(255, 255, 255)).save(image)
    import hashlib
    image_sha = hashlib.sha256(image.read_bytes()).hexdigest().upper()
    contract = {
        "scenes": [{"scene_id": "scene-1", "visual_role": "historical_reconstruction", "host_mode": "absent"}]
    }
    manifest = {"assets": [{
        "shot_id": "scene-1", "status": "COMPLETED", "file_path": "scene-1.jpg", "sha256": image_sha
    }]}
    (build / "episode_visual_contract_v2.json").write_text(json.dumps(contract), encoding="utf-8")
    (build / "asset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    axes = {
        "semantic_match": "PASS", "historical_subject": "PASS", "host_presence": "PASS",
        "embedded_text": "PASS", "composition_density": "PASS", "style_profile": "PASS",
        "dignity": "PASS", "service_mark": "PASS",
    }
    approval = {
        "decision": "approved",
        "contract_sha256": compute_object_sha256(contract),
        "manifest_sha256": compute_object_sha256(manifest),
        "shot_evaluations": [{"shot_id": "scene-1", "decision": "approved", "axes": axes}],
    }
    (build / "approvals" / "visual_approval.json").write_text(json.dumps(approval), encoding="utf-8")
    ok, errors = verify_visual_build(
        build_dir=build,
        ocr=_FakeOCR([{"text": "1701", "confidence": 0.99, "bbox": []}]),
    )
    assert ok is False
    assert any("embedded text" in error.lower() for error in errors)
    report = json.loads((build / "visual_content_report.json").read_text(encoding="utf-8"))
    assert report["shots"][0]["status"] == "FAIL"


def test_pilot_scope_checks_only_declared_representative_ids(tmp_path: Path):
    build = tmp_path / "pilot"
    (build / "images").mkdir(parents=True)
    image = build / "images" / "scene-1.jpg"
    Image.new("RGB", (1920, 1080), color=(10, 20, 30)).save(image)
    import hashlib
    image_sha = hashlib.sha256(image.read_bytes()).hexdigest().upper()
    contract = {"scenes": [
        {"scene_id": "scene-1", "visual_role": "historical_reconstruction", "host_mode": "absent"},
        {"scene_id": "scene-2", "visual_role": "historical_reconstruction", "host_mode": "absent"},
    ]}
    manifest = {
        "generation_scope": "pilot",
        "expected_ids": ["scene-1"],
        "assets": [
            {"shot_id": "scene-1", "status": "COMPLETED", "file_path": "scene-1.jpg", "sha256": image_sha},
            {"shot_id": "scene-2", "status": "FAILED", "file_path": "missing.jpg", "sha256": ""},
        ],
    }
    (build / "episode_visual_contract_v2.json").write_text(json.dumps(contract), encoding="utf-8")
    (build / "asset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    ok, errors = verify_visual_build(build_dir=build, ocr=_FakeOCR([]))
    assert ok is False
    assert any("approval" in error.lower() for error in errors)
    assert not any("missing visual assets" in error.lower() for error in errors)
    assert not any("scene-2" in error for error in errors)


def test_visual_gate_rejects_asset_from_stale_request_hash(tmp_path: Path):
    build = tmp_path / "build"
    (build / "images").mkdir(parents=True)
    image = build / "images" / "scene-1.jpg"
    Image.new("RGB", (1920, 1080), color=(10, 20, 30)).save(image)
    import hashlib
    image_sha = hashlib.sha256(image.read_bytes()).hexdigest().upper()
    contract = {"scenes": [{"scene_id": "scene-1", "visual_role": "historical_reconstruction", "host_mode": "absent"}]}
    manifest = {"assets": [{
        "shot_id": "scene-1", "status": "COMPLETED", "file_path": "scene-1.jpg",
        "sha256": image_sha, "prompt_sha256": "OLD",
    }]}
    requests = {"requests": [{"scene_id": "scene-1", "request_sha256": "CURRENT"}]}
    (build / "episode_visual_contract_v2.json").write_text(json.dumps(contract), encoding="utf-8")
    (build / "image_request_manifest.json").write_text(json.dumps(requests), encoding="utf-8")
    (build / "asset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    ok, errors = verify_visual_build(build_dir=build, ocr=_FakeOCR([]))
    assert ok is False
    assert any("stale request hash" in error.lower() for error in errors)


def test_visual_gate_rejects_host_without_canonical_overlay_record(tmp_path: Path):
    build = tmp_path / "build"
    (build / "images").mkdir(parents=True)
    image = build / "images" / "host.jpg"
    Image.new("RGB", (1920, 1080), color=(10, 20, 30)).save(image)
    import hashlib
    image_sha = hashlib.sha256(image.read_bytes()).hexdigest().upper()
    contract = {"scenes": [{"scene_id": "host", "visual_role": "host_explainer", "host_mode": "full"}]}
    manifest = {"assets": [{
        "shot_id": "host", "status": "COMPLETED", "file_path": "host.jpg",
        "sha256": image_sha, "prompt_sha256": "CURRENT",
    }]}
    requests = {"requests": [{"scene_id": "host", "request_sha256": "CURRENT", "host_overlay": {"asset": "x"}}]}
    (build / "episode_visual_contract_v2.json").write_text(json.dumps(contract), encoding="utf-8")
    (build / "image_request_manifest.json").write_text(json.dumps(requests), encoding="utf-8")
    (build / "asset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    ok, errors = verify_visual_build(build_dir=build, ocr=_FakeOCR([]))
    assert ok is False
    assert any("canonical host overlay" in error.lower() for error in errors)


def test_v5_request_manifest_enables_role_aware_ocr_without_legacy_contract(tmp_path: Path):
    build = tmp_path / "build"
    (build / "images").mkdir(parents=True)
    (build / "approvals").mkdir()
    image = build / "images" / "scene-1.jpg"
    Image.new("RGB", (1920, 1080), color=(255, 255, 255)).save(image)
    import hashlib
    image_sha = hashlib.sha256(image.read_bytes()).hexdigest().upper()
    request_manifest = {
        "schema_version": 2,
        "contract_sha256": "V5-CONTRACT",
        "requests": [{
            "scene_id": "scene-1",
            "visual_role": "historical_reconstruction",
            "request_sha256": "CURRENT",
        }],
    }
    manifest = {"generation_scope": "all", "assets": [{
        "shot_id": "scene-1",
        "status": "COMPLETED",
        "file_path": "scene-1.jpg",
        "sha256": image_sha,
        "prompt_sha256": "CURRENT",
    }]}
    axes = {
        "semantic_match": "PASS", "historical_subject": "PASS", "host_presence": "PASS",
        "embedded_text": "PASS", "composition_density": "PASS", "style_profile": "PASS",
        "dignity": "PASS", "service_mark": "PASS",
    }
    approval = {
        "decision": "approved",
        "contract_sha256": "V5-CONTRACT",
        "manifest_sha256": compute_object_sha256(manifest),
        "shot_evaluations": [{"shot_id": "scene-1", "decision": "approved", "axes": axes}],
    }
    (build / "image_request_manifest.json").write_text(json.dumps(request_manifest), encoding="utf-8")
    (build / "asset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (build / "approvals" / "visual_approval.json").write_text(json.dumps(approval), encoding="utf-8")

    ok, errors = verify_visual_build(
        build_dir=build,
        ocr=_FakeOCR([{"text": "1701", "confidence": 0.99, "bbox": []}]),
    )

    assert ok is False
    assert any("embedded text" in error.lower() for error in errors)
    report = json.loads((build / "visual_content_report.json").read_text(encoding="utf-8"))
    assert report["contract_sha256"] == "V5-CONTRACT"


def test_v5_host_request_requires_canonical_overlay_without_legacy_contract(tmp_path: Path):
    build = tmp_path / "build"
    (build / "images").mkdir(parents=True)
    image = build / "images" / "host.jpg"
    Image.new("RGB", (1920, 1080), color=(10, 20, 30)).save(image)
    import hashlib
    image_sha = hashlib.sha256(image.read_bytes()).hexdigest().upper()
    request_manifest = {
        "schema_version": 2,
        "contract_sha256": "V5-CONTRACT",
        "requests": [{
            "scene_id": "host",
            "visual_role": "host_explainer",
            "request_sha256": "CURRENT",
            "host_overlay": {"asset": "canonical.png"},
        }],
    }
    manifest = {"assets": [{
        "shot_id": "host",
        "status": "COMPLETED",
        "file_path": "host.jpg",
        "sha256": image_sha,
        "prompt_sha256": "CURRENT",
    }]}
    (build / "image_request_manifest.json").write_text(json.dumps(request_manifest), encoding="utf-8")
    (build / "asset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    ok, errors = verify_visual_build(build_dir=build, ocr=_FakeOCR([]))

    assert ok is False
    assert any("canonical host overlay" in error.lower() for error in errors)


def test_v5_gate_accepts_hash_bound_visually_confirmed_ocr_false_positive(tmp_path: Path):
    build = tmp_path / "build"
    (build / "images").mkdir(parents=True)
    (build / "approvals").mkdir()
    image = build / "images" / "scene-1.jpg"
    Image.new("RGB", (1920, 1080), color=(255, 255, 255)).save(image)
    import hashlib
    image_sha = hashlib.sha256(image.read_bytes()).hexdigest().upper()
    findings = [{"text": "U", "confidence": 0.81, "bbox": [[1, 1], [10, 1], [10, 10], [1, 10]]}]
    request_manifest = {
        "schema_version": 2,
        "contract_sha256": "V5-CONTRACT",
        "requests": [{
            "scene_id": "scene-1", "visual_role": "evidence_object", "request_sha256": "CURRENT",
        }],
    }
    manifest = {"generation_scope": "all", "assets": [{
        "shot_id": "scene-1", "status": "COMPLETED", "file_path": "scene-1.jpg",
        "sha256": image_sha, "prompt_sha256": "CURRENT",
    }]}
    axes = {
        "semantic_match": "PASS", "historical_subject": "PASS", "host_presence": "PASS",
        "embedded_text": "PASS", "composition_density": "PASS", "style_profile": "PASS",
        "dignity": "PASS", "service_mark": "PASS",
    }
    approval = {
        "decision": "approved", "contract_sha256": "V5-CONTRACT",
        "manifest_sha256": compute_object_sha256(manifest),
        "shot_evaluations": [{"shot_id": "scene-1", "decision": "approved", "axes": axes}],
    }
    overrides = {"schema_version": 1, "reviews": [{
        "shot_id": "scene-1", "decision": "false_positive", "image_sha256": image_sha,
        "findings_sha256": compute_object_sha256(findings),
        "reason": "visually confirmed curved object handle, not text",
    }]}
    (build / "image_request_manifest.json").write_text(json.dumps(request_manifest), encoding="utf-8")
    (build / "asset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (build / "approvals" / "visual_approval.json").write_text(json.dumps(approval), encoding="utf-8")
    (build / "visual_ocr_overrides.json").write_text(json.dumps(overrides), encoding="utf-8")

    ok, errors = verify_visual_build(build_dir=build, ocr=_FakeOCR(findings))

    assert ok is True, errors
    report = json.loads((build / "visual_content_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["shots"][0]["raw_status"] == "FAIL"
    assert report["shots"][0]["status"] == "PASS"
    assert report["shots"][0]["ocr_override"]["decision"] == "false_positive"
