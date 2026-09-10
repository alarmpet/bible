# Nepal Tunnel Rescue Episode Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a release-ready Nollam File episode package and final 8-minute MP4 explaining the post-flood hydropower tunnel rescue effort in Nepal.

**Architecture:** Build a one-episode adapter under the existing `human_archive` conventions. Keep research claims, verified Korean narration, sentence-level visual alignment, overlays, and render metadata as separate manifests so every visual and number remains auditable. Reuse existing audio, subtitle, motion, and render components where available; do not reuse reference-video copy or footage.

**Tech Stack:** Existing Human Archive/Nollam File manifests, SuperTonic3 M2_WARM, original no-glyph AI visuals, ASS subtitles, existing video renderer, JSON postflight validation.

**Spec:** `docs/superpowers/specs/2026-09-01-nollam-file-trend-explainer-design.md`

## Global Constraints

- Format: `nollam_file_long`; delivery: `trend_explainer_8m`; target duration: 480 seconds.
- Render: 1920×1080, 16:9, 25fps; audio: M2_WARM, speed 0.95, total_step 10.
- All claims require source IDs; disputed or changing numbers use explicit status overlays.
- Base images contain no glyphs; text, dates, sources, and status labels are separate overlays.
- QA requires semantic coverage ≥0.90, zero claim/visual mismatches, zero unsupported visuals, and no more than two consecutive uses of one asset.
- Reference assets under `audits/nollam_reference_KWL8_AnSp2g/` are analysis-only and must not be republished.

---

### Task 1: Create the episode contract and research packet

**Files:**
- Create: `human_archive/runs/nollam_file/2026-09-01/nepal-tunnel-rescue/<run_id>/trend_job_contract_v1.json`
- Create: `human_archive/runs/nollam_file/2026-09-01/nepal-tunnel-rescue/<run_id>/trend_research_packet_v1.json`

**Interfaces:**
- Consumes: Approved `nollam_file_v1` profile and dated source URLs.
- Produces: Immutable cutoff timestamp, topic slug, source registry, claim IDs, confidence/status labels, and correction-monitoring schedule.
- [ ] Record the 26 August 2026 Bhote Koshi–Trishuli flash flood as the event date and 1 September 2026 Asia/Seoul as the editorial cutoff.
- [ ] Register AP, Kathmandu Post, OnlineKhabar, and Nepal Ministry of Foreign Affairs sources with exact URLs and publication dates.
- [ ] Separate confirmed site facts from estimates: Upper Trishuli-3A has 40–42 engineers reported inside; the access route is water- and mud-blocked; Upper Trishuli-3B tunnel occupants were reported safe; Rasuwagadhi tunnel search reported no people found.
- [ ] Mark all casualty and missing-person totals as rapidly changing and exclude them from the hook unless source-bound at render time.

### Task 2: Write and verify the Korean narration

**Files:**
- Create: `human_archive/runs/nollam_file/2026-09-01/nepal-tunnel-rescue/<run_id>/trend_verified_script_v1.json`
- Create: `human_archive/runs/nollam_file/2026-09-01/nepal-tunnel-rescue/<run_id>/studio_disclosure_manifest_v1.json`

**Interfaces:**
- Consumes: Claim registry from Task 1.
- Produces: 6–10 minute Korean narration with sentence IDs, claim IDs, uncertainty labels, and AI-reconstruction disclosure text.
- [ ] Structure the script into six beats: flash-flood scale; why workers were underground; buried entrance; vertical access/oxygen/dewatering; site-by-site correction; what remains unknown.
- [ ] Use “추정”, “확인”, and “미확인” explicitly; never convert “believed trapped” into “confirmed trapped.”
- [ ] Add a disclosure that reconstructed visuals are illustrative and not eyewitness footage.
- [ ] Run a manual claim audit: every number, place name, and rescue-method statement maps to at least one registered source.

### Task 3: Produce timed audio and subtitles

**Files:**
- Create: `audio/sentences/<sentence_id>.wav`
- Create: `master_audio_48k.wav`
- Create: `sentence_audio_manifest.json`
- Create: `subtitles.ass`

**Interfaces:**
- Consumes: `trend_verified_script_v1.json`.
- Produces: Measured sentence start/end times and synchronized subtitle events.
- [ ] Synthesize each sentence with M2_WARM at speed 0.95 and total_step 10.
- [ ] Concatenate and loudness-check the master at 48 kHz.
- [ ] Measure actual timings from generated audio; do not infer durations from character counts.
- [ ] Keep subtitle lines within the profile limit of two lines and 14 characters per line.

### Task 4: Build sentence-level visual alignment and overlay events

**Files:**
- Create: `visual_brief_manifest.json`
- Create: `flow_image_prompts.json`
- Create: `sentence_visual_alignment_v1.json`
- Create: `overlay_event_manifest_v1.json`

**Interfaces:**
- Consumes: Script claims and measured audio timings.
- Produces: One semantic visual role per sentence and source-bound text overlays.
- [ ] Assign roles in order: satellite/map context, flood reconstruction, tunnel cross-section, vertical shaft, oxygen/dewatering diagram, rescue-team logistics, site-status correction, family uncertainty.
- [ ] Use original no-glyph visuals only; attach `why_this_visual` and `source_basis` to every alignment row.
- [ ] Add status overlays for `공식 발표`, `추정`, `미확인`, and `정정됨` where appropriate.
- [ ] Verify coverage ≥0.90 and reject unsupported or semantically mismatched rows before rendering.

### Task 5: Generate assets, motion clips, and final render

**Files:**
- Create: `assets/` and `motion_clips/` under the run root
- Create: `candidate/nepal-tunnel-rescue-<run_id>.mp4`
- Create: `build_manifest.json`

**Interfaces:**
- Consumes: Visual alignment, prompts, audio, and overlays.
- Produces: Preview render followed by 1080p final MP4 and complete asset provenance.
- [ ] Generate each visual with no embedded text and retain prompt/model metadata.
- [ ] Build the sentence-to-shot timeline from measured timings.
- [ ] Render a low-resolution preview, inspect for visual meaning mismatch, subtitle overflow, and unsafe imagery, then render final 1080p.
- [ ] Record every asset, transition, overlay, and source in `build_manifest.json`.

### Task 6: Run postflight and package delivery

**Files:**
- Create: `correction_action_manifest_v1.json`
- Create: `postflight_report.json`

**Interfaces:**
- Consumes: Final MP4 and all manifests.
- Produces: Pass/fail report and correction-monitoring actions for 6/24/72 hours.
- [ ] Confirm duration, resolution, frame rate, audio presence, subtitle presence, and manifest completeness.
- [ ] Confirm mismatch count = 0, unsupported visual count = 0, and repeated-asset constraint.
- [ ] Schedule correction checks at 6, 24, and 72 hours after publication; keep release manual and do not auto-post.
- [ ] Deliver the MP4 plus the complete auditable run directory.
