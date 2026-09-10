# EP02 Narration-Aligned Migration and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the completed narration-aligned infrastructure to EP02 in a new `full-v5-001` build, stop at both human visual gates, then produce motion, subtitles, a final candidate and release report without reusing rejected v4 visual assets.

**Architecture:** An episode-neutral orchestrator runs deterministic stages and stops at approval boundaries. EP02 snapshots its approved script and claims into a build-local source directory, creates sentence audio before shots, generates a dual Flow pilot, resumes only after current-hash approval, and renders only from the fully verified v5 lineage.

**Tech Stack:** Python 3.12+, pytest, PowerShell, Codex CLI, Supertonic3, Playwright CDP, Google Flow/Nano Banana 2, Pillow/RapidOCR, FFmpeg/ffprobe

**Spec:** `docs/superpowers/specs/2026-08-27-narration-aligned-visual-workflow-design.md`

## Global Constraints

- Plans `2026-08-27-tts-first-shot-alignment.md` and `2026-08-27-semantic-image-generation-and-qa.md` must pass before EP02 generation begins.
- New build path is exactly `human_archive/runs/ep02_jang_huibin/full-v5-001`.
- `full-v4-001` remains `REJECTED`; no images or prompt hashes are copied from v4.
- Approved v4 script and claim data may be snapshotted only after their current SHA values are recorded.
- Default image model is `Nano Banana 2`; quota or policy failure never triggers automatic account change.
- Expected visual count is 95–120 for the 18-minute approved script; a count outside this range stops for profile/segmentation review.
- The browser must expose exactly one signed-in Flow page over CDP port 9222.
- The cold-open and coverage pilots require explicit current-hash human approval.
- Full visual approval is separate from pilot approval.
- Motion, subtitles, render and postflight run only after full visual PASS.
- Do not commit generated WAV, JPG or MP4 files unless repository policy explicitly tracks that build artifact class.

---

### Task 1: Add an Episode-Neutral Staged Orchestrator

**Files:**
- Create: `human_archive/scripts/lib/narration_pipeline.py`
- Create: `human_archive/scripts/run_narration_aligned_episode.py`
- Create: `human_archive/tests/test_narration_pipeline.py`
- Modify: `human_archive/scripts/lib/build_manifest.py`

**Interfaces:**
- Consumes: episode root, build ID, approved script path, claim inventory path, profile ID and provider choices.
- Produces: `PipelineConfig`; `build_stage_commands(config: PipelineConfig) -> list[PipelineStage]`; `run_until(config: PipelineConfig, stop_after: str, runner: CommandRunner) -> dict`; resumable `config.episode_root / config.build_id / "pipeline_state.json"`.

- [ ] **Step 1: Write failing stage-order and gate tests**

```python
from pathlib import Path
from lib.narration_pipeline import PipelineConfig, build_stage_commands, run_until


def config(tmp_path):
    return PipelineConfig(
        repository_root=tmp_path,
        episode_root=tmp_path / "human_archive/runs/ep02_jang_huibin",
        build_id="full-v5-001",
        script_path=tmp_path / "script_candidate.json",
        claims_path=tmp_path / "claim_inventory_v2.json",
        profile_id="narration_aligned_hybrid_v1",
        brief_provider="codex-cli",
        image_model="Nano Banana 2",
        cdp_url="http://127.0.0.1:9222",
    )


def test_stage_order_puts_audio_before_timing_and_images(tmp_path):
    names = [stage.name for stage in build_stage_commands(config(tmp_path))]
    assert names == [
        "initialize", "sentence_audio", "shot_timing", "visual_briefs",
        "alignment", "prompt_preflight", "pilot_generation",
        "pilot_semantic_review", "pilot_approval", "full_generation",
        "full_semantic_review", "full_approval", "motion", "subtitles",
        "render", "postflight",
    ]


def test_run_stops_before_human_gate_without_executing_next_stage(tmp_path):
    calls = []
    result = run_until(config(tmp_path), stop_after="pilot_semantic_review", runner=lambda stage: calls.append(stage.name) or 0)
    assert calls[-1] == "pilot_semantic_review"
    assert "pilot_approval" not in calls
    assert result["next_required_stage"] == "pilot_approval"
```

- [ ] **Step 2: Run tests and verify RED**

Run: `pytest human_archive/tests/test_narration_pipeline.py -v`

Expected: FAIL with import error.

- [ ] **Step 3: Implement immutable config and stage definitions**

```python
@dataclass(frozen=True)
class PipelineConfig:
    repository_root: Path
    episode_root: Path
    build_id: str
    script_path: Path
    claims_path: Path
    profile_id: str
    brief_provider: str
    image_model: str
    cdp_url: str


@dataclass(frozen=True)
class PipelineStage:
    name: str
    command: tuple[str, ...]
    required_outputs: tuple[Path, ...]
    human_gate: bool = False
```

Every command is an argument tuple executed with `shell=False`. Mark `pilot_approval` and `full_approval` as human gates; `run_until()` must never synthesize approval files.

- [ ] **Step 4: Implement hash-aware resumability**

`pipeline_state.json` stores each stage's command arguments, input SHA values, output SHA values, status and completion time. Reuse a completed stage only when all input and output hashes still match. A human gate is complete only when its approval validator passes.

- [ ] **Step 5: Extend build manifest lineage**

Add optional v5 SHA fields for script snapshot, sentence audio, shot timing, visual briefs, shot alignment, prompt alignment report and semantic review. Existing manifests without these fields remain valid.

- [ ] **Step 6: Run tests and verify GREEN**

Run: `pytest human_archive/tests/test_narration_pipeline.py human_archive/tests/test_build_freshness.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add human_archive/scripts/lib/narration_pipeline.py human_archive/scripts/run_narration_aligned_episode.py human_archive/tests/test_narration_pipeline.py human_archive/scripts/lib/build_manifest.py
git commit -m "feat: orchestrate narration-aligned episode builds"
```

### Task 2: Prepare EP02 v5 Through Prompt Preflight

**Files:**
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/source/script_candidate.json`
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/source/claim_inventory_v2.json`
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/source/source_snapshot_manifest.json`
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/pipeline_state.json`
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/sentence_audio_manifest.json`
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/shot_timing_manifest.json`
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/visual_brief_manifest.json`
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/shot_alignment_manifest.json`
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/image_request_manifest.json`
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/prompt_alignment_report.json`
- Modify: `human_archive/tests/test_ep02_visual_failure_regression.py`

**Interfaces:**
- Consumes: approved `full-v4-001/source/script_candidate.json` and `source/claim_inventory_v2.json`.
- Produces: a fully preflighted v5 source/audio/alignment/request chain with no images generated.

- [ ] **Step 1: Update the EP02 regression test for the approved profile**

```python
V5 = ROOT / "human_archive" / "runs" / "ep02_jang_huibin" / "full-v5-001"


def test_v5_alignment_has_benchmark_density_and_sequence_rules():
    alignment = json.loads((V5 / "shot_alignment_manifest.json").read_text(encoding="utf-8"))
    shots = alignment["shots"]
    assert 95 <= len(shots) <= 120
    assert max(float(shot["duration_sec"]) for shot in shots) <= 15.0
    hosts = [shot for shot in shots if shot["visual_mode"] == "host_chapter_hinge"]
    assert 0.08 <= len(hosts) / len(shots) <= 0.12
    assert all(shots[index]["visual_mode"] != shots[index + 1]["visual_mode"] or shots[index]["visual_mode"] != "evidence_artifact" for index in range(len(shots) - 1))


def test_v5_requests_preserve_anchors_and_do_not_cycle_generic_books():
    requests = json.loads((V5 / "image_request_manifest.json").read_text(encoding="utf-8"))["requests"]
    assert all(request["semantic_anchors"] for request in requests)
    assert sum("blank archive volume" in request["submission_prompt"].lower() for request in requests) <= 2
    assert all("1701" not in request["submission_prompt"] for request in requests)
```

- [ ] **Step 2: Run the regression test and verify RED**

Run: `pytest human_archive/tests/test_ep02_visual_failure_regression.py -v`

Expected: FAIL because `full-v5-001` does not exist.

- [ ] **Step 3: Initialize a build-local immutable source snapshot**

Run:

```powershell
python human_archive/scripts/run_narration_aligned_episode.py --episode-root human_archive/runs/ep02_jang_huibin --build-id full-v5-001 --script human_archive/runs/ep02_jang_huibin/full-v4-001/source/script_candidate.json --claims human_archive/runs/ep02_jang_huibin/source/claim_inventory_v2.json --profile narration_aligned_hybrid_v1 --brief-provider codex-cli --image-model "Nano Banana 2" --cdp http://127.0.0.1:9222 --stop-after initialize
```

Expected: build-local copies exist and `source_snapshot_manifest.json` records their source paths and SHA values. No v4 JPG or Flow prompt is copied.

- [ ] **Step 4: Build sentence audio and measured timing**

Ensure Supertonic3 is responding, then run:

```powershell
python human_archive/scripts/run_narration_aligned_episode.py --episode-root human_archive/runs/ep02_jang_huibin --build-id full-v5-001 --script human_archive/runs/ep02_jang_huibin/full-v4-001/source/script_candidate.json --claims human_archive/runs/ep02_jang_huibin/source/claim_inventory_v2.json --profile narration_aligned_hybrid_v1 --brief-provider codex-cli --image-model "Nano Banana 2" --cdp http://127.0.0.1:9222 --stop-after shot_timing
```

Expected: `sentence_audio_manifest.json` has 126 ordered sentences, the master is approximately 18 minutes, and timing has no missing or overlapping span.

- [ ] **Step 5: Generate visual briefs, alignment and prompts**

Run the same command with `--stop-after prompt_preflight`.

Expected:

- 95–120 aligned shots;
- required anchor coverage 100%;
- host 8–12%, minimum seven-shot gap;
- evidence streak maximum one;
- prompt and novelty duplicate count zero;
- `prompt_alignment_report.json.status == "PASS"`;
- no browser or Flow generation yet.

- [ ] **Step 6: Review the alignment contact report before spending quota**

Run:

```powershell
python human_archive/scripts/validate_image_requests.py --build human_archive/runs/ep02_jang_huibin/full-v5-001
pytest human_archive/tests/test_ep02_visual_failure_regression.py human_archive/tests/test_shot_alignment.py human_archive/tests/test_prompt_alignment_qa.py -v
```

Expected: PASS. Inspect the mode distribution and narration digest list; if generic books/tables exceed the acceptance limits, stop and correct briefs rather than generating images.

- [ ] **Step 7: Commit only code/tests, not generated media**

```bash
git add human_archive/tests/test_ep02_visual_failure_regression.py
git commit -m "test: bind EP02 to narration-aligned visual density"
```

### Task 3: Generate and Approve the Dual EP02 Pilot

**Files:**
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/asset_manifest.json`
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/pilot_cold_open_contact_sheet.jpg`
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/pilot_coverage_contact_sheet.jpg`
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/visual_semantic_review.json`
- Create after explicit user approval: `human_archive/runs/ep02_jang_huibin/full-v5-001/approvals/visual_pilot_review.json`

**Interfaces:**
- Consumes: current prompt preflight, one signed-in Google Flow page, explicit human review.
- Produces: current-hash approved dual pilot; no full-batch images.

- [ ] **Step 1: Start Chrome with a clean CDP profile and verify the port**

```powershell
Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue
Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" -WindowStyle Hidden -ArgumentList '--remote-debugging-port=9222','--remote-allow-origins=*','--user-data-dir=C:\Users\shs\.chrome_debug_ep02_v5','https://labs.google/fx/tools/image-fx'
curl.exe http://127.0.0.1:9222/json/version
```

Expected: curl prints JSON containing `webSocketDebuggerUrl`. If the new profile requires login, complete it in that Chrome window and leave exactly one Flow/ImageFX page open.

- [ ] **Step 2: Generate only the dual pilot**

```powershell
python human_archive/scripts/generate_flow_batch.py --build human_archive/runs/ep02_jang_huibin/full-v5-001 --pilot --model "Nano Banana 2" --cdp http://127.0.0.1:9222
```

Expected: `asset_manifest.json.pilot_sets` contains 12 cold-open IDs and 8 coverage IDs; the union has no duplicates; generation stops after that union.

- [ ] **Step 3: Build both contact sheets and run automatic review**

```powershell
python human_archive/scripts/build_contact_sheet.py --build human_archive/runs/ep02_jang_huibin/full-v5-001 --pilot-set cold_open --output human_archive/runs/ep02_jang_huibin/full-v5-001/pilot_cold_open_contact_sheet.jpg
python human_archive/scripts/build_contact_sheet.py --build human_archive/runs/ep02_jang_huibin/full-v5-001 --pilot-set coverage --output human_archive/runs/ep02_jang_huibin/full-v5-001/pilot_coverage_contact_sheet.jpg
python human_archive/scripts/review_visual_semantics.py --build human_archive/runs/ep02_jang_huibin/full-v5-001 --scope pilot --provider codex-cli
python human_archive/scripts/verify_visual_assets.py --build human_archive/runs/ep02_jang_huibin/full-v5-001
```

Expected before human approval: all pixel, OCR, hash, duplicate and semantic checks pass; verifier fails only because current pilot approval is missing.

- [ ] **Step 4: Handle a policy failure per scene only**

For the first `provider_policy_rejected` scene recorded in the manifest, run:

```powershell
$failedSceneId = (Get-Content human_archive/runs/ep02_jang_huibin/full-v5-001/asset_manifest.json -Raw | ConvertFrom-Json).assets | Where-Object { $_.status -eq 'FAILED' -and $_.error -match 'provider_policy_rejected' } | Select-Object -First 1 -ExpandProperty shot_id
if (-not $failedSceneId) { throw 'No provider_policy_rejected scene is recorded in asset_manifest.json' }
python human_archive/scripts/rewrite_policy_rejected_prompt.py --build human_archive/runs/ep02_jang_huibin/full-v5-001 --scene-id $failedSceneId --reason provider_policy_rejected
python human_archive/scripts/validate_image_requests.py --build human_archive/runs/ep02_jang_huibin/full-v5-001
python human_archive/scripts/generate_flow_batch.py --build human_archive/runs/ep02_jang_huibin/full-v5-001 --only $failedSceneId --model "Nano Banana 2" --cdp http://127.0.0.1:9222
```

Repeat the same manifest-derived command for each recorded policy failure; never infer an ID from browser card order. After two failed attempts, keep `REVIEW_REQUIRED` and ask for a new scene treatment.

- [ ] **Step 5: Perform explicit visual review**

Approve only when both sheets satisfy all of these:

- each image depicts the adjacent narration digest and required anchors;
- no long sequence collapses into books, tables, paper or empty rooms;
- historical characters have stable clothing, age and role;
- 쉽선비 appears only in declared host scenes with the canonical full torso/costume;
- no generated letters, digits, year, seal, watermark or service mark;
- composition is full-frame and the visual mode is correct.

- [ ] **Step 6: Record current-hash pilot approval only after the user approves**

Write `approvals/visual_pilot_review.json` conforming to `visual_pilot_approval_v2.schema.json`, copying current hashes and both pilot fingerprints from generated reports. Include one complete human `shot_evaluation` for every union ID. Re-run:

```powershell
python human_archive/scripts/verify_visual_assets.py --build human_archive/runs/ep02_jang_huibin/full-v5-001
```

Expected: PASS for pilot scope.

### Task 4: Generate and Approve the Full EP02 Image Set

**Files:**
- Modify through resumable generation: `human_archive/runs/ep02_jang_huibin/full-v5-001/asset_manifest.json`
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/contact_sheet.jpg`
- Update: `human_archive/runs/ep02_jang_huibin/full-v5-001/visual_semantic_review.json`
- Create after explicit user approval: `human_archive/runs/ep02_jang_huibin/full-v5-001/approvals/visual_approval.json`

**Interfaces:**
- Consumes: approved pilot and current prompt requests.
- Produces: one verified current asset per aligned shot and full human approval.

- [ ] **Step 1: Resume the remaining full set**

```powershell
python human_archive/scripts/generate_flow_batch.py --build human_archive/runs/ep02_jang_huibin/full-v5-001 --all --model "Nano Banana 2" --cdp http://127.0.0.1:9222
```

Expected: already approved current pilot assets are skipped; every other request is generated once; explicit Flow failure stops at that shot and leaves all prior rows intact.

- [ ] **Step 2: Re-run preflight after every rewritten request**

If any scene is rewritten, rerun `validate_image_requests.py`, regenerate only that scene, rerun semantic review for that scene, and invalidate any approval whose request or asset fingerprint changed.

- [ ] **Step 3: Build and inspect the full contact sheet**

```powershell
python human_archive/scripts/build_contact_sheet.py --build human_archive/runs/ep02_jang_huibin/full-v5-001 --output human_archive/runs/ep02_jang_huibin/full-v5-001/contact_sheet.jpg
python human_archive/scripts/review_visual_semantics.py --build human_archive/runs/ep02_jang_huibin/full-v5-001 --scope all --provider codex-cli
python human_archive/scripts/verify_visual_assets.py --build human_archive/runs/ep02_jang_huibin/full-v5-001
```

Expected before human approval: verifier fails only for missing full approval. Any OCR, pHash, missing anchor, wrong mode, character drift or stale hash is corrected per scene.

- [ ] **Step 4: Record full current-hash approval after explicit review**

Create `approvals/visual_approval.json` with one evaluation per aligned shot and current alignment/request/asset/semantic-review hashes. Re-run verification and require PASS.

- [ ] **Step 5: Run the visual regression suite**

```powershell
pytest human_archive/tests/test_ep02_visual_failure_regression.py human_archive/tests/test_prompt_alignment_qa.py human_archive/tests/test_flow_batch_state.py human_archive/tests/test_visual_qa.py human_archive/tests/test_visual_semantic_qa.py human_archive/tests/test_visual_pilot_approval.py -v
```

Expected: PASS.

### Task 5: Build Motion, Subtitles, Candidate and Release Report

**Files:**
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/motion_clips/`
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/subtitles.ass`
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/candidate/HA002-full-v5-001.mp4`
- Create: `human_archive/runs/ep02_jang_huibin/full-v5-001/release_report.json`
- Modify: `CLAUDE.md`
- Modify: `manual.md`
- Modify: `human_archive/README.md`

**Interfaces:**
- Consumes: full visual PASS, sentence/scene audio, aligned motion profiles.
- Produces: frame-exact final candidate, postflight report and updated episode-neutral runbooks.

- [ ] **Step 1: Build motion only after the visual gate passes**

```powershell
python human_archive/scripts/verify_visual_assets.py --build human_archive/runs/ep02_jang_huibin/full-v5-001
python human_archive/scripts/build_motion_clips_v2.py --build human_archive/runs/ep02_jang_huibin/full-v5-001
```

Expected: one motion clip per aligned shot, exact 25 CFR duration, mode-derived motion profile.

- [ ] **Step 2: Build sentence-time subtitles**

```powershell
python human_archive/scripts/build_subtitles_v2.py --build human_archive/runs/ep02_jang_huibin/full-v5-001
```

Expected: subtitle cues derive from sentence audio timing, preserve one-to-two-line limits and end at master audio duration.

- [ ] **Step 3: Render and postflight**

```powershell
python human_archive/scripts/render_episode_v2.py --build human_archive/runs/ep02_jang_huibin/full-v5-001 --output human_archive/runs/ep02_jang_huibin/full-v5-001/candidate/HA002-full-v5-001.mp4
python human_archive/scripts/postflight_release.py --input human_archive/runs/ep02_jang_huibin/full-v5-001/candidate/HA002-full-v5-001.mp4 --report human_archive/runs/ep02_jang_huibin/full-v5-001/release_report.json --duration-mode full
```

Expected: release report PASS for duration, streams, frame rate, audio and subtitles.

- [ ] **Step 4: Update all three runbooks**

Replace the v4 character-count workflow as the default with the episode-neutral v5 order:

```text
approved script → sentence TTS → shot timing → Codex visual briefs
→ alignment/prompt preflight → dual pilot → full images
→ semantic/OCR/duplicate/continuity QA → motion → subtitles → render → postflight
```

Document the exact Chrome `Start-Process` and `curl.exe` commands, 9–12-second profile, 8–12% host rule, policy retry limit, no account auto-switch, build-local contract precedence and resumable `--only` behavior. Keep legacy v4 commands under an explicitly labeled legacy section.

- [ ] **Step 5: Run the full focused suite**

```powershell
pytest human_archive/tests/test_narration_alignment_contracts.py human_archive/tests/test_sentence_audio_timeline.py human_archive/tests/test_shot_timing.py human_archive/tests/test_visual_brief_provider.py human_archive/tests/test_shot_alignment.py human_archive/tests/test_aligned_prompt_compiler.py human_archive/tests/test_prompt_alignment_qa.py human_archive/tests/test_policy_retry_archive.py human_archive/tests/test_flow_batch_state.py human_archive/tests/test_visual_semantic_qa.py human_archive/tests/test_visual_qa.py human_archive/tests/test_motion_clips_v2.py human_archive/tests/test_subtitles_v2.py human_archive/tests/test_render_episode_v2.py human_archive/tests/test_ep02_visual_failure_regression.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit code and runbooks without generated media**

```bash
git add CLAUDE.md manual.md human_archive/README.md human_archive/scripts human_archive/tests human_archive/config human_archive/schemas human_archive/templates
git commit -m "docs: adopt narration-aligned episode workflow"
```

## Plan Acceptance

- [ ] EP02 v5 contains 95–120 semantically aligned shots based on measured TTS.
- [ ] Rejected v4 images and hashes are absent from v5.
- [ ] Both pilot sets and the full set have explicit current-hash human approval.
- [ ] Policy and quota errors remain per-scene failures with no automatic account change.
- [ ] All automatic and human visual gates pass before motion.
- [ ] Candidate duration, audio, subtitles and 25 CFR video pass postflight.
- [ ] `CLAUDE.md`, `manual.md` and `human_archive/README.md` describe the reusable v5 workflow for every episode.
