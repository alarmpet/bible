# Task 1 Implementation Report

## Files Changed

- `human_archive/flow_automation/native_host/__init__.py`
- `human_archive/flow_automation/native_host/job_store.py`
- `human_archive/flow_automation/schemas/automation_job.schema.json`
- `human_archive/flow_automation/schemas/approved_asset_manifest.schema.json`
- `human_archive/flow_automation/tests/conftest.py`
- `human_archive/flow_automation/tests/test_job_store.py`

## Interfaces Implemented

- `compile_job(source_manifest: Path, episode_dir: Path, expected_url: str, job_id: str) -> dict[str, Any]`
- `validate_job(job: Mapping[str, Any], episode_dir: Path) -> None`
- `atomic_write_json(path: Path, value: Mapping[str, Any]) -> None`

## What Changed

- Added a deterministic job compiler that reads `scene_script_manifest_v2.json`, trims the `midjourney_prompt` at `--ar`, hashes the exact submission prompt, and assigns stable output filenames.
- Added schema-backed validation for the generated job envelope.
- Enforced the requested safety checks:
  - unique `shot_id` values
  - unique prompt hashes
  - unique expected filenames
  - positive shot durations
  - exact prompt hash matching
  - `output_dir` confinement to `episode_dir/generation`
  - HTTPS Flow project URL validation
- Added atomic JSON writing with a same-directory temporary file and `os.replace`-style behavior.
- Added fixtures for the real Himalaya manifest and a disposable episode directory.
- Added tests for the exact prompt hash, duplicate shot rejection, output path escape rejection, and atomic JSON round-trip.

## Tests and Commands

- `python -m pytest flow_automation/tests/test_job_store.py -v`
  - Output: `4 passed in 0.64s`
- Real Himalaya compile check:
  - `python -c "from pathlib import Path; from flow_automation.native_host.job_store import compile_job; manifest=Path('runs/nollam_file/2026-09-02/himalaya-glof-water-crisis/source/scene_script_manifest_v2.json'); episode_dir=Path('runs/nollam_file/2026-09-02/himalaya-glof-water-crisis'); job=compile_job(manifest, episode_dir, 'https://labs.google/fx/ko/tools/flow/project/p1', 'HIMALAYA-v1'); print(len(job['shots'])); print(job['shots'][0]['shot_id']); print(job['shots'][-1]['shot_id']); print(len({shot['shot_id'] for shot in job['shots']})); print(len({shot['prompt_sha256'] for shot in job['shots']})); print(len({shot['expected_filename'] for shot in job['shots']}))"`
  - Output:
    - `105`
    - `SHOT_001`
    - `SHOT_105`
    - `105`
    - `105`
    - `105`

## Commit Hash

- Implementation commit: `ba0765c`

## Concerns

- The repository had many unrelated dirty changes already present; I preserved them and only touched the Task 1 subtree.
- I used a local repository git identity because the workspace had no configured author name/email.
- `approved_asset_manifest.schema.json` is defined for the later pipeline contract, but Task 1 only exercises the job compiler/validator path.

## Round 1 Fix

- Tightened `validate_job` so `expected_filename` must exactly equal the canonical `{shot_id}__{prompt_sha256[:8]}.png` value.
- Kept a resolved-path check against `output_dir` so filename traversal cannot escape the generation directory.
- Added a 64-lowercase-hex constraint for `assets[].sha256` in `approved_asset_manifest.schema.json`.
- Expanded Task 1 coverage for duplicate prompt hashes, duplicate filenames, hash mismatches, filename traversal, invalid asset hashes, and nonpositive durations.

## Verification

- `python -m pytest flow_automation/tests/test_job_store.py -v`
  - Output: `10 passed in 0.89s`
- `python -c "from pathlib import Path; from flow_automation.native_host.job_store import compile_job; manifest=Path('runs/nollam_file/2026-09-02/himalaya-glof-water-crisis/source/scene_script_manifest_v2.json'); episode_dir=Path('runs/nollam_file/2026-09-02/himalaya-glof-water-crisis'); job=compile_job(manifest, episode_dir, 'https://labs.google/fx/ko/tools/flow/project/p1', 'HIMALAYA-v1'); print(len(job['shots'])); print(job['shots'][0]['shot_id']); print(job['shots'][-1]['shot_id']); print(len({shot['shot_id'] for shot in job['shots']})); print(len({shot['prompt_sha256'] for shot in job['shots']})); print(len({shot['expected_filename'] for shot in job['shots']}))"`
  - Output:
    - `105`
    - `SHOT_001`
    - `SHOT_105`
    - `105`
    - `105`
    - `105`

## Round 1 Commit

- Fix commit: `16326cb`
