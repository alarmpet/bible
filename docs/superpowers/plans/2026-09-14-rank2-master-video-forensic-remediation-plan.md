# Rank 2 Exact Master Forensic Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the current Rank 2 output into a clean-scope, independently verified master without treating container-level PASS as proof of visual 1:1 replication.

**Architecture:** Freeze the original source/timeline as the only timing authority, derive clean plate candidates without overwriting provider outputs, render a candidate master through an atomic `.part.mp4` path, and promote only after encoded-frame, subtitle, audio, and integrity gates independently pass. Channel logo, HUD, BGM, sidechain, SFX, and sub-bass remain out of scope.

**Tech Stack:** Python 3.13, pytest, FFmpeg/ffprobe/libass, OpenCV/Pillow, SHA-256 manifests, Google Flow through the existing CDP/Playwright adapter only when a new plate is required.

**Spec:** [Rank 2 forensic review](../reviews/2026-09-14-rank2-master-video-forensic-review.md), [Rank 2 release manifest](../../../human_archive/runs/human_library_replica/rank2_forgotten_civilization/metadata/rank2_exact_release_manifest.json), and the source file `D:\module\scratch\human_library_top3\original_rank2.mp4`.

## Global Constraints

- Never overwrite the current output; render to a candidate `.part.mp4` and promote only after all gates pass.
- Resolve the timing SSOT conflict first: source probe is 1,439.800s while the current canonical target is 1,440.000s.
- Preserve 30.00fps CFR and the selected target frame count; validate both first and last frame timestamps.
- Preserve 48,000Hz stereo voice-only audio and validate sample count, decoded duration, and AV parity independently.
- Keep 128 A/B plate identity, 2304×1296 target dimensions, unique content, prompt lineage, and provider provenance.
- Do not erase or inpaint a Flow provider watermark until the export/license terms explicitly permit it; otherwise rerender from an allowed clean export or mark the plate ineligible.
- Subtitle contract is one line, zero overlap, zero zero-start events, zero multiline events, `BorderStyle=3`, and semantic yellow highlighting only.
- Channel logo, HUD, laurel, BGM, sidechain, SFX, and sub-bass are excluded from this release profile.
- Existing output and manifests are evidence, not trusted declarations; every release metric must be recomputed from physical files.

### Task 1: Freeze forensic evidence and correct the release status

**Files:**
- Create: `D:\module\bible\docs\superpowers\reviews\2026-09-14-rank2-master-video-forensic-review.md`
- Modify: `D:\module\PROGRESS.md`, `D:\module\ERRORS.md`, `D:\module\TASK.md`, `D:\module\PROJECT_MEMORY.md`, `D:\module\DECISIONS.md`
- Test: `D:\module\scratch\rank2_forensic_20260914\` read-only probes and hash checks

**Steps:**

- [ ] Record the current output SHA-256, bytes, ffprobe streams, and production/output mirror parity.
- [ ] Record source-vs-result duration difference as an unresolved SSOT decision, not as parity PASS.
- [ ] Mark old Rank 2 entries claiming 958 subtitles, 485,532,409 bytes, or unconditional Gate 0–5 PASS as historical/superseded where they conflict with recomputed values.
- [ ] Keep the current MP4 physically preserved and quarantine it from “exact release approved” selection until later tasks pass.
- [ ] Record the observed provider watermark and baked-in lower band as P0 evidence.

### Task 2: Lock the Rank 2 timing SSOT

**Files:**
- Inspect/Modify: `D:\module\bible\human_archive\runs\human_library_replica\rank2_forgotten_civilization\metadata\canonical_timeline_manifest.json`
- Inspect/Modify: `D:\module\bible\human_archive\runs\human_library_replica\rank2_forgotten_civilization\script\master_script_clean.json`
- Inspect: source cues and `original_rank2.mp4`
- Test: `D:\module\bible\human_archive\tests\test_human_library_rank2_exact_physical_release.py`

**Steps:**

- [ ] Compare source media duration, cue end time, canonical target duration, and audio sample boundary.
- [ ] Choose one authoritative target and document why; do not silently round 1,439.800s to 1,440.000s.
- [ ] Derive the exact frame count and audio sample count from the chosen target.
- [ ] Add a regression test rejecting a manifest whose source duration and target duration differ without an explicit `timing_policy`.
- [ ] Recompute all downstream start/end/frame fields from the locked SSOT.

### Task 3: Repair plate provenance and visual cleanliness

**Files:**
- Inspect/Modify: `D:\module\bible\human_archive\runs\human_library_replica\rank2_forgotten_civilization\metadata\master_plates_composition_plan.json`
- Inspect/Modify: `D:\module\bible\human_archive\runs\human_library_replica\rank2_forgotten_civilization\images_2d_master\`
- Modify: `D:\module\bible\human_archive\scripts\finalize_exact_flow_plates.py`
- Test: `D:\module\bible\human_archive\tests\test_finalize_exact_flow_plates.py`

**Steps:**

- [ ] Add a physical provider-overlay detector for the lower band and lower-right Flow mark; report coordinates and confidence per plate.
- [ ] Preserve the raw Flow files and provenance hashes; never mutate them in place.
- [ ] Determine whether the provider supplies an allowed watermark-free export. If not, stop promotion of affected plates instead of masking them silently.
- [ ] If clean exports are available, create a separate derived plate directory and bind its hashes in the manifest.
- [ ] Add OCR/text-artifact review for generated labels such as `LOWER EGYPT`; `no text` in a prompt is not a visual PASS.
- [ ] Require human/automated semantic approval for the opening sequence so the first frame is checked against the source brief rather than only against image dimensions.

### Task 4: Rebuild subtitle and safe-area composition

**Files:**
- Modify: `D:\module\bible\human_archive\runs\human_library_replica\rank2_forgotten_civilization\subtitles\rank2_exact_master_subtitles.ass`
- Modify: `D:\module\bible\human_archive\scripts\build_rank2_exact_subtitles.py` or the actual Rank 2 subtitle compiler discovered during baseline scan
- Modify: `D:\module\bible\human_archive\scripts\run_human_library_rank2_exact_clone_pipeline.py`
- Test: Rank 2 subtitle and physical release tests

**Steps:**

- [ ] Change the exact style contract to `BorderStyle=3` with a bounded semi-transparent rounded box; do not use a full-width baked band.
- [ ] Keep the actual event count derived from SSOT and correct documentation to the recomputed count (currently 542 in the inspected ASS).
- [ ] Verify one-line, zero overlap, zero zero-start, and yellow keyword tags from the physical ASS and from burned frames.
- [ ] Render subtitles only after the visual plate layer is clean; ensure the lower 18% safe zone is empty before the subtitle box is added.
- [ ] Add a frame-level test that distinguishes a per-event rounded box from a persistent full-width bottom bar.

### Task 5: Bind encoded motion to the 837-cut plan and eliminate A/B toggle loops

**Files:**
- Inspect/Modify: `D:\module\bible\human_archive\runs\human_library_replica\rank2_forgotten_civilization\metadata\subcut_montage_plan.json`
- Modify: Rank 2 montage/renderer discovered by baseline scan
- Test: `D:\module\bible\human_archive\tests\test_human_library_rank2_exact_physical_release.py`

**Steps:**

- [ ] Generate expected frame-boundary indices from the locked SSOT and subcut plan.
- [ ] Measure frame differences at every expected boundary and at control points inside each cut.
- [ ] Report actual boundary count separately from scene-detector “scene-like” count; do not use 1,670 as the cut count.
- [ ] Reject freeze frames or repeated plate spans outside the declared motion profile.
- [ ] Compute `same_parent_adjacent_transition_count` and `aba_repeat_count` from the ordered `plate_id` sequence before rendering. The current baseline is 773 same-parent transitions and 709 `plate[i] == plate[i-2]` A/B repetitions across 837 planned cuts.
- [ ] Assign explicit complementary roles to each A/B pair (for example, A=wide/context and B=evidence/detail) and prohibit unconditional alternation. `A-B-A` and `B-A-B` are rejected unless an explicit script beat records why the reversal is intentional.
- [ ] Require semantic progression for adjacent cuts within one parent shot; a Ken Burns pixel difference alone cannot satisfy this requirement. Add a no-loop window and a per-parent role-order test so the same two plates cannot masquerade as montage diversity.
- [ ] Verify the first 300 seconds against the declared pacing budget and preserve subtitle-safe crop behavior.

**Task 5 acceptance:** the encoded boundary map matches the plan; every same-parent transition has a declared role progression; `aba_repeat_count=0` by default (or each exception is explicitly justified and independently reviewed); and the first 300 seconds passes both cut pacing and semantic non-loop checks. A zero exact-pixel-repeat result is recorded only as a secondary metric, never as an A/B-loop waiver.

### Task 6: Audit voice-only audio and semantic pauses

**Files:**
- Inspect/Modify: Rank 2 audio builder and release verifier
- Test: `D:\module\bible\human_archive\tests\test_human_library_rank2_exact_physical_release.py`

**Steps:**

- [ ] Recompute 48kHz stereo sample count and decoded duration from the candidate WAV and final MP4.
- [ ] Align every `silencedetect` interval with cue/sentence boundaries; classify natural pause versus unbound dead air.
- [ ] Set an explicit allowed pause policy instead of reporting “dead-air 0” from a boolean placeholder.
- [ ] Run loudness and true-peak checks on the voice-only profile; keep BGM/SFX/sidechain/sub-bass excluded.
- [ ] Fail closed when video and audio differ beyond the selected threshold or when the final frame is lost at mux.

### Task 7: Candidate render, independent gates, and atomic promotion

**Files:**
- Modify: `D:\module\bible\human_archive\scripts\run_human_library_rank2_exact_clone_pipeline.py`
- Modify: `D:\module\bible\human_archive\scripts\rank2_exact_release_verifier.py` or the actual verifier discovered during baseline scan
- Test: `D:\module\bible\human_archive\tests\test_human_library_rank2_exact_physical_release.py`

**Steps:**

- [ ] Render to `rank2_exact_master_documentary.part.mp4` with explicit MP4 format and stream maps.
- [ ] Recompute physical metrics from the candidate rather than copying predicted manifest values.
- [ ] Run Gate 0 duration/frame boundary, Gate 1 subtitle, Gate 2 clean plate/style, Gate 3 encoded pacing, Gate 4 voice-only audio, and Gate 5 full decode/integrity.
- [ ] Generate an ordered source-to-release SHA-256 chain only after all gates pass.
- [ ] Atomically replace the output mirror only after the candidate and production master hashes match.
- [ ] Leave the current output untouched and status `CONDITIONAL_REVIEW` if any P0/P1 remains.

### Task 8: Regression, documentation, and final handoff

**Files:**
- Modify: `D:\module\PROGRESS.md`, `D:\module\ERRORS.md`, `D:\module\TASK.md`, `D:\module\PROJECT_MEMORY.md`, `D:\module\DECISIONS.md`
- Modify: relevant Flow and exact-render skills under `D:\module\.agents\skills\`
- Test: `pytest tests/` plus targeted Rank 2 physical release suite and `python -m py_compile`

**Steps:**

- [ ] Add permanent error records for baked provider overlays, BorderStyle mismatch, source/target duration drift, and unclassified pauses.
- [ ] Update the reusable skills with the same fail-closed rules; no skill may claim generation or release before physical evidence exists.
- [ ] Run the targeted and full relevant tests; record Exit Code 0 and exact counts.
- [ ] Record final artifact sizes and SHA-256 values in the progress and release manifest.
- [ ] Mark the task complete only when the physical candidate, manifest chain, and all gates agree.

## Definition of Done

- [ ] Timing SSOT is explicitly chosen and source/target discrepancy is resolved.
- [ ] No unapproved provider watermark or baked lower band remains in promoted plates.
- [ ] Subtitle style is physically `BorderStyle=3`; no persistent full-width bar is present.
- [ ] Actual encoded cut boundaries are reconciled with the montage plan.
- [ ] Natural pauses and dead air are separately classified; voice-only audio parity passes.
- [ ] Candidate and output mirror are byte-identical and manifest SHA-256 chain matches physical files.
- [ ] Targeted tests, relevant full tests, and `py_compile` all exit 0.
