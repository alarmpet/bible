# Media Rules Lock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make voice, subtitle, background, storage, and final-render rules single-source and mechanically enforced.

**Architecture:** A canonical JSON lock is the only runtime source of truth. Preflight validates job metadata, media inputs, subtitle layout/timing, and output storage before rendering; postflight validates the finished MP4 before release.

**Tech Stack:** Python, JSON, PowerShell, FFmpeg/ffprobe, Markdown.

## Global Constraints

- Male scripture voice: M4, speed 0.72, pitch -8%, silence 0.65s.
- Speakers: narrator and scripture only; no source-stage voice substitution.
- Captions: maximum 2 lines, 14–18 Korean characters per line target, never split inside a word/particle/ending, sentence-aware segmentation.
- Background: all 12 one-minute pingpong MP4 samples, 0.333 playback speed; still images forbidden.
- Final outputs: `D:\bible_healing_ep01\final`; work files: `D:\bible_healing_ep01\work`.
- Any mismatch blocks render and release.

### Task 1: Canonical lock and documentation

**Files:** Create `bible_healing/config/media_rules_lock.json`; update `manual.md`, `CLAUDE.md`, `D_DRIVE_OUTPUT_POLICY.md`.

- [ ] Add exact canonical values and forbidden fallbacks.
- [ ] Document that existing stale `voice_map.json`/`render-options.json` cannot be used.
- [ ] Document sentence-aware caption rules and mandatory pre/postflight.

### Task 2: Runtime preflight

**Files:** Create `bible_healing/scripts/media_rules_preflight.py`.

- [ ] Validate canonical voice settings, job metadata, scene count, background samples, D output path, and subtitle constraints.
- [ ] Exit nonzero on any stale F3/M5/0.78 configuration or wrong output root.

### Task 3: Runtime postflight

**Files:** Create `bible_healing/scripts/media_rules_postflight.py`.

- [ ] Validate MP4 metadata, audio/video duration, output path, subtitle final timestamp, and source audio identity.
- [ ] Emit a JSON report and nonzero exit on mismatch.

### Task 4: Verification

- [ ] Run preflight against the current job and record every blocking mismatch.
- [ ] Do not regenerate a final video until preflight passes.
- [ ] Run postflight only on a newly rendered D output.
