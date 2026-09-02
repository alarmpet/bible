# Task 2 Report — Event-sourced durable state and recovery

Date: 2026-09-03
Repository: `D:\module\bible`
Task brief: `D:\module\bible\.superpowers\sdd\2026-09-03-nollam-flow-automation-implementation\task-2-brief.md`
Base HEAD confirmed: `9cfdb5b09250f14561c08eb2850b2ea0275cebcc`

## Scope completed

Implemented Task 2 in:
- `bible/human_archive/flow_automation/native_host/job_store.py`
- `bible/human_archive/flow_automation/tests/test_job_store.py`

Added:
- `ShotState` and `JobSnapshot` durable replay models
- `append_event(events_path, event)` with append + flush + fsync persistence
- `replay_job(job, events_path)` with event-id deduplication, restart recovery, mismatched-job rejection, malformed-complete-line rejection, and truncated-final-line tolerance
- `next_runnable_shot(snapshot, mode)` with missing-shot selection, waiting-state blocking, pause/stop blocking, retry exhaustion handling, and `Generate All` fresh-job enforcement
- targeted tests for append persistence, replay recovery, idempotency, waiting/pause/stop, retry exhaustion, and mode selection

## Helper failure and fallback

The normal local exec/apply helper failed repeatedly before command launch. Exact error observed:

```text
Rejected("Failed to create unified exec process: helper_unknown_error: setup refresh had errors")
```

Per instruction, work continued using explicit Windows PowerShell commands only. No external mirror or alternate environment was used.

## Commands and outputs

### 1. Initial red test after adding Task 2 interfaces to the test file

Command:

```powershell
cd D:\module\bible\human_archive
python -m pytest flow_automation/tests/test_job_store.py -k "replay or runnable" -v
```

Output:

```text
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\shs\AppData\Local\Programs\Python\Python313\python.exe
cachedir: .pytest_cache
rootdir: D:\module\bible
configfile: pytest.ini
plugins: anyio-4.11.0
collecting ... collected 0 items / 1 error

=================================== ERRORS ====================================
___ ERROR collecting human_archive/flow_automation/tests/test_job_store.py ____
ImportError while importing test module 'D:\module\bible\human_archive\flow_automation\tests\test_job_store.py'.
...
E   ImportError: cannot import name 'JobSnapshot' from 'flow_automation.native_host.job_store' (D:\module\bible\human_archive\flow_automation\native_host\job_store.py)
=========================== short test summary info ===========================
ERROR flow_automation\tests\test_job_store.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
============================== 1 error in 0.67s ===============================
```

Result: expected red failure confirming the missing Task 2 interfaces.

### 2. Green verification for replay/runnable subset after implementing `job_store.py`

Command:

```powershell
cd D:\module\bible\human_archive
python -m pytest flow_automation/tests/test_job_store.py -k "replay or runnable" -v
```

Output:

```text
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\shs\AppData\Local\Programs\Python\Python313\python.exe
cachedir: .pytest_cache
rootdir: D:\module\bible
configfile: pytest.ini
plugins: anyio-4.11.0
collecting ... collected 21 items / 13 deselected / 8 selected

flow_automation\tests\test_job_store.py::test_replay_ignores_duplicate_event_id PASSED [ 12%]
flow_automation\tests\test_job_store.py::test_replay_truncated_last_line_preserves_prior_events PASSED [ 25%]
flow_automation\tests\test_job_store.py::test_replay_waiting_for_result_blocks_next_runnable PASSED [ 37%]
flow_automation\tests\test_job_store.py::test_replay_pause_blocks_runnable_shot PASSED [ 50%]
flow_automation\tests\test_job_store.py::test_replay_stop_blocks_runnable_shot PASSED [ 62%]
flow_automation\tests\test_job_store.py::test_replay_failed_shot_exhaustion_skips_to_next_shot PASSED [ 75%]
flow_automation\tests\test_job_store.py::test_replay_rejects_mismatched_job_id PASSED [ 87%]
flow_automation\tests\test_job_store.py::test_replay_rejects_malformed_complete_line PASSED [100%]

====================== 8 passed, 13 deselected in 0.85s =======================
```

Result: targeted replay/runnable coverage passed.

### 3. Full Task 2 file verification

Command:

```powershell
cd D:\module\bible\human_archive
python -m pytest flow_automation/tests/test_job_store.py -v
```

Output:

```text
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\shs\AppData\Local\Programs\Python\Python313\python.exe
cachedir: .pytest_cache
rootdir: D:\module\bible
configfile: pytest.ini
plugins: anyio-4.11.0
collecting ... collected 21 items

flow_automation\tests\test_job_store.py::test_compile_job_hashes_exact_submission_prompt PASSED [  4%]
flow_automation\tests\test_job_store.py::test_validate_job_rejects_duplicate_shot_id PASSED [  9%]
flow_automation\tests\test_job_store.py::test_validate_job_rejects_duplicate_prompt_sha256 PASSED [ 14%]
flow_automation\tests\test_job_store.py::test_validate_job_rejects_duplicate_expected_filename PASSED [ 19%]
flow_automation\tests\test_job_store.py::test_validate_job_rejects_hash_mismatched_expected_filename PASSED [ 23%]
flow_automation\tests\test_job_store.py::test_validate_job_rejects_filename_traversal PASSED [ 28%]
flow_automation\tests\test_job_store.py::test_validate_job_rejects_nonpositive_duration PASSED [ 33%]
flow_automation\tests\test_job_store.py::test_approved_asset_manifest_schema_rejects_invalid_sha256 PASSED [ 38%]
flow_automation\tests\test_job_store.py::test_validate_job_rejects_output_escape PASSED [ 42%]
flow_automation\tests\test_job_store.py::test_atomic_write_json_round_trips_payload PASSED [ 47%]
flow_automation\tests\test_job_store.py::test_append_event_appends_json_line PASSED [ 52%]
flow_automation\tests\test_job_store.py::test_replay_ignores_duplicate_event_id PASSED [ 57%]
flow_automation\tests\test_job_store.py::test_generate_missing_never_returns_accepted_shot PASSED [ 61%]
flow_automation\tests\test_job_store.py::test_replay_truncated_last_line_preserves_prior_events PASSED [ 66%]
flow_automation\tests\test_job_store.py::test_replay_waiting_for_result_blocks_next_runnable PASSED [ 71%]
flow_automation\tests\test_job_store.py::test_replay_pause_blocks_runnable_shot PASSED [ 76%]
flow_automation\tests\test_job_store.py::test_replay_stop_blocks_runnable_shot PASSED [ 80%]
flow_automation\tests\test_job_store.py::test_replay_failed_shot_exhaustion_skips_to_next_shot PASSED [ 85%]
flow_automation\tests\test_job_store.py::test_generate_all_requires_new_job_id_after_progress PASSED [ 90%]
flow_automation\tests\test_job_store.py::test_replay_rejects_mismatched_job_id PASSED [ 95%]
flow_automation\tests\test_job_store.py::test_replay_rejects_malformed_complete_line PASSED [100%]

============================= 21 passed in 1.56s ==============================
```

Result: full specified Task 2 test file passed.

## Implementation notes

- Replay starts from the validated job shot order and reconstructs state exclusively from JSONL events.
- Duplicate `event_id` entries are ignored after the first application.
- Only a truncated final line is tolerated during recovery; malformed complete lines raise `ValueError`.
- A mismatched event `job_id` raises `ValueError` immediately.
- `WAITING_FOR_RESULT` blocks new runnable shots after restart recovery.
- `missing` mode skips accepted shots.
- `all` mode raises once any durable progress exists, requiring a new job ID.
- Failure events transition a shot to `FAILED` until the retry limit is reached, then to `EXHAUSTED`.
- Job pause/stop events block runnable-shot selection until resumed.

## Files changed

- `D:\module\bible\human_archive\flow_automation\native_host\job_store.py`
- `D:\module\bible\human_archive\flow_automation\tests\test_job_store.py`
- `D:\module\bible\.superpowers\sdd\2026-09-03-nollam-flow-automation-implementation\task-2-report.md`

## Commit

Pending at report-write time. The next step is to stage only the Task 2 files and attempt:

```powershell
git add bible/human_archive/flow_automation/native_host/job_store.py bible/human_archive/flow_automation/tests/test_job_store.py bible/.superpowers/sdd/2026-09-03-nollam-flow-automation-implementation/task-2-report.md
git commit -m "feat(flow-automation): persist and replay generation state"
```
