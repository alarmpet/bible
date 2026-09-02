# Task 4 Report

Date: 2026-09-03
Base HEAD consumed: `20689826873abf87c4f69eec7ca8626237bf3f7b` (`2068982`)
Task scope: Implement Task 4 only in `human_archive/flow_automation/native_host/asset_validator.py` and `human_archive/flow_automation/tests/test_asset_validator.py`.

## Files Changed

- `D:\module\bible\human_archive\flow_automation\native_host\asset_validator.py`
- `D:\module\bible\human_archive\flow_automation\tests\test_asset_validator.py`

## Implementation Summary

- Added `validate_asset(job, shot_id, chrome_path, downloads_root, prior_assets)`.
- Added `AssetValidationResult(status, code, sha256, width, height, mime_type, approved_path, rejected_path)`.
- Implemented fail-closed checks for:
  - download path outside configured root
  - partial downloads via `.crdownload` and `.partial`
  - non-regular or empty files
  - Pillow decode failures
  - unsupported MIME/type
  - non-16:9 assets
  - duplicate accepted SHA-256 reuse across shots
- Implemented 16:9 normalization to `1920x1080` using `ImageOps.fit(..., (1920, 1080))` and deterministic approved filenames from the job contract.
- Implemented approved/rejected moves plus JSON sidecars.
- Implemented atomic manifest updates for `approved_asset_manifest.json` using the existing atomic JSON writer.
- Added TDD coverage for acceptance, rejection, duplicate hash rejection, deterministic filename/provenance, and path rejection.

## Commands Run

1. Red test run:

```powershell
cd D:\module\bible\human_archive
python -m pytest flow_automation/tests/test_asset_validator.py -v
```

Observed output:
- `ModuleNotFoundError: No module named 'flow_automation.native_host.asset_validator'`
- Result: expected red failure before implementation.

2. Validator-only green verification:

```powershell
cd D:\module\bible\human_archive
python -m pytest flow_automation/tests/test_asset_validator.py -v
```

Observed output:
- `7 passed in 1.36s`

3. Exact brief verification:

```powershell
cd D:\module\bible\human_archive
python -m pytest flow_automation/tests/test_asset_validator.py tests/test_semantic_image_reuse.py -v
```

Observed output:
- `11 passed in 1.40s`

4. Scoped commit:

```powershell
cd D:\module\bible
git add -- human_archive/flow_automation/native_host/asset_validator.py human_archive/flow_automation/tests/test_asset_validator.py
git commit -m "feat(flow-automation): validate and bind downloaded assets"
```

Observed output:
- Commit created successfully on branch `feat/full-media-pipeline-freeze`
- Commit: `db09cc8`

## Commit

- `db09cc8` `feat(flow-automation): validate and bind downloaded assets`

## Concerns

- `approved_asset_manifest.schema.json` currently describes a narrower asset entry than the richer provenance written by Task 4. The validator writes the requested fields, but schema validation for this richer manifest shape is not part of this task and would need a follow-up if strict manifest-schema enforcement is added.
- The validator currently records SHA-256 from the downloaded source file before normalization. That matches duplicate-download detection, but if downstream consumers expect the checksum of the normalized approved PNG bytes instead, they will need a follow-up contract clarification.
- The Codex `apply_patch` update path was intermittently failing in this environment with a Windows sandbox helper refresh error, so the final validator rewrite was completed via a scoped PowerShell file replacement to keep the task moving.

## Task 4 fix round 1 (2026-09-03)

Review findings addressed:

- Normalization now happens before hashing; `AssetValidationResult.sha256` and manifest `sha256` are the SHA-256 of the bytes written to `approved_path`. The source download digest is retained separately as `source_sha256`.
- Duplicate detection uses accepted approved-file hashes.
- `approved_asset_manifest.schema.json` now describes every emitted manifest and asset field with closed properties, exact types, SHA-256 patterns, dimensions, MIME, status, and UTC timestamp patterns.
- `validate_asset` now requires keyword-only `binding` containing `job_id`, `shot_id`, `prompt_sha256`, `attempt`, `card_id`, `media_identity`, `download_id`, and `original_filename`; missing, mismatched, and filename-binding cases are rejected.

Exact verification command and output:

```text
python -m pytest flow_automation/tests/test_asset_validator.py tests/test_semantic_image_reuse.py -v
============================= test session starts =============================
flow_automation\\tests\\test_asset_validator.py::test_valid_png_moves_to_approved_and_records_provenance PASSED [  7%]
flow_automation\\tests\\test_asset_validator.py::test_invalid_asset_is_rejected[corrupt-IMAGE_DECODE_FAILED] PASSED [ 15%]
flow_automation\\tests\\test_asset_validator.py::test_invalid_asset_is_rejected[zero-EMPTY_FILE] PASSED [ 23%]
flow_automation\\tests\\test_asset_validator.py::test_invalid_asset_is_rejected[partial-PARTIAL_DOWNLOAD] PASSED [ 30%]
flow_automation\\tests\\test_asset_validator.py::test_invalid_asset_is_rejected[wrong_ratio-INVALID_ASPECT_RATIO] PASSED [ 38%]
flow_automation\\tests\\test_asset_validator.py::test_duplicate_file_hash_cannot_serve_two_shots PASSED [ 46%]
flow_automation\\tests\\test_asset_validator.py::test_asset_outside_download_root_is_rejected PASSED [ 53%]
flow_automation\\tests\\test_asset_validator.py::test_manifest_matches_schema PASSED [ 61%]
flow_automation\\tests\\test_asset_validator.py::test_binding_is_required_and_filename_bound PASSED [ 69%]
tests\\test_semantic_image_reuse.py::test_reuse_planner_auto_reuses_only_exact_sentence_groups PASSED [ 76%]
tests\\test_semantic_image_reuse.py::test_reuse_planner_rejects_exact_match_without_completed_asset PASSED [ 84%]
tests\\test_semantic_image_reuse.py::test_reuse_planner_rejects_exact_match_when_host_mode_changes PASSED [ 92%]
tests\\test_semantic_image_reuse.py::test_reuse_planner_demotes_request_mode_or_role_mismatches PASSED [100%]
============================== 13 passed in 1.90s ==============================
```

Scoped focused run:

```text
python -m pytest flow_automation/tests/test_asset_validator.py -q
============================== 8 passed in 1.54s ==============================
```

Commit for this fix round: fdd6303 (amended below for final whitespace/report metadata).


## Remaining binding finding (2026-09-03)

The public contract is now `binding={"expected": {...}, "observed": {...}}`. Each subobject must contain `job_id`, `shot_id`, `prompt_sha256`, `attempt`, `card_id`, `media_identity`, `download_id`, and `original_filename`. Every expected/observed field must match exactly; expected job/shot fields must match the active job/shot; and observed `original_filename` must equal the actual source basename. Mismatched `download_id` and `media_identity` are explicitly tested.

Exact command and output:

```text
python -m pytest flow_automation/tests/test_asset_validator.py tests/test_semantic_image_reuse.py -v
============================= test session starts =============================
flow_automation\\tests\\test_asset_validator.py::test_valid_png_moves_to_approved_and_records_provenance PASSED [  7%]
flow_automation\\tests\\test_asset_validator.py::test_invalid_asset_is_rejected[corrupt-IMAGE_DECODE_FAILED] PASSED [ 14%]
flow_automation\\tests\\test_asset_validator.py::test_invalid_asset_is_rejected[zero-EMPTY_FILE] PASSED [ 21%]
flow_automation\\tests\\test_asset_validator.py::test_invalid_asset_is_rejected[partial-PARTIAL_DOWNLOAD] PASSED [ 28%]
flow_automation\\tests\\test_asset_validator.py::test_invalid_asset_is_rejected[wrong_ratio-INVALID_ASPECT_RATIO] PASSED [ 35%]
flow_automation\\tests\\test_asset_validator.py::test_duplicate_file_hash_cannot_serve_two_shots PASSED [ 42%]
flow_automation\\tests\\test_asset_validator.py::test_asset_outside_download_root_is_rejected PASSED [ 50%]
flow_automation\\tests\\test_asset_validator.py::test_manifest_matches_schema PASSED [ 57%]
flow_automation\\tests\\test_asset_validator.py::test_binding_is_required_and_filename_bound PASSED [ 64%]
flow_automation\\tests\\test_asset_validator.py::test_binding_rejects_download_and_media_identity_mismatch PASSED [ 71%]
tests\\test_semantic_image_reuse.py::test_reuse_planner_auto_reuses_only_exact_sentence_groups PASSED [ 78%]
tests\\test_semantic_image_reuse.py::test_reuse_planner_rejects_exact_match_without_completed_asset PASSED [ 85%]
tests\\test_semantic_image_reuse.py::test_reuse_planner_rejects_exact_match_when_host_mode_changes PASSED [ 92%]
tests\\test_semantic_image_reuse.py::test_reuse_planner_demotes_request_mode_or_role_mismatches PASSED [100%]
============================== 14 passed in 1.82s ==============================
```
