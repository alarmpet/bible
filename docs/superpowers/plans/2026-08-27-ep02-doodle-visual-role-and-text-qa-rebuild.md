# EP02 Doodle Visual Role and Text QA Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild EP02 visuals so 쉽선비 appears only in intentional presenter beats, AI-generated base images contain no readable dates or labels, and the pipeline blocks full generation and motion rendering when visual-role or text QA fails.

**Architecture:** Replace the EP02 cyclic template prompt builder with a role-aware visual planner that classifies each narration group as `host_explainer`, `historical_reconstruction`, `evidence_object`, `diagram_metaphor`, or `atmosphere`. Keep dates and captions as metadata rendered by deterministic overlays, never as AI prompt content. Generate and approve a representative pilot before full Flow generation, then enforce prompt lint, OCR, asset completeness, and signed visual approval before motion rendering.

**Tech Stack:** Python 3.13, pytest, Pydantic/JSON Schema, Playwright CDP, Pillow/imagehash, RapidOCR ONNX Runtime, FFmpeg.

**Spec:** `docs/superpowers/specs/2026-08-27-doodle-seonbi-channel-pipeline-design.md`

## Global Constraints

- `channel_profile_id` remains `doodle_seonbi_v1`; do not silently fall back to cinematic K-webtoon style.
- Preserve `human_archive/runs/ep02_jang_huibin/full-v4-001` as rejected evidence; regenerate into `full-v4-002`.
- The AI base image must contain zero readable letters, words, dates, numerals, captions, seals, or watermarks.
- Dates such as `1701` may appear only through `overlay_event_manifest.json` and only on editorially selected timeline/source-card scenes.
- 쉽선비 is allowed only in `host_explainer` scenes and deterministic host overlays; historical reconstructions must not contain him.
- Flow must generate presenter-free host bases. Every accepted host scene composites the same canonical transparent host asset with a complete white dopo torso, sleeves, collar, and waist tie; partial stick bodies or per-scene regenerated hosts fail QA.
- Host bases contain no people, hands, or body parts; evidence scenes contain one coherent focal object and never use catalogue, collage, split-panel, or disembodied-hand compositions.
- Target host presence is 15–25% of shots, with no more than two consecutive host shots.
- Historical reconstruction plus evidence/object shots must comprise at least 60% of shots.
- Every Flow result must have a one-to-one `shot_id` → request hash → downloaded asset hash lineage.
- Full generation and motion rendering are blocked until the representative pilot and the full contact sheet receive current-hash visual approval.
- Never report attempted prompts as completed assets; counts must come from verified files and manifest rows.

---

## Confirmed Failure Analysis

The current generator hardcodes both defects into every prompt:

```python
f"..., at {place}, 1701 Joseon Dynasty. "
"The main character is a friendly Korean Joseon seonbi stickman ..."
```

Consequently, all 63 prompts request 쉽선비 and expose the literal token `1701` to the image model. The builder also cycles 15 generic templates without reading the narration meaning, so the same host-led compositions repeat regardless of claim, actor, or visual beat. The contact sheet therefore shows omnipresent 쉽선비, repeated `1701`/pseudo-label text, large empty infographic layouts, and weak correspondence with the historical narration. This violates `brand_layer_separation: true` and the existing design requirement that AI images contain no readable text.

---

### Task 1: Lock the Failure as Regression Evidence

**Files:**
- Create: `human_archive/runs/ep02_jang_huibin/full-v4-001/visual_failure_report.json`
- Create: `human_archive/tests/fixtures/ep02_visual_failure_prompts.json`
- Create: `human_archive/tests/test_ep02_visual_failure_regression.py`

**Interfaces:**
- Consumes: current `flow_image_prompts.json`, `shot_contract_v4.json`, and 63 generated images.
- Produces: immutable failure categories and tests that prevent every-shot host/date regressions.

- [ ] **Step 1: Write the failing regression test**

```python
def test_ep02_prompts_do_not_force_host_or_literal_year_everywhere():
    prompts = json.loads(FIXTURE.read_text(encoding="utf-8"))
    host_count = sum("main character is" in p["prompt"].lower() for p in prompts)
    year_count = sum("1701" in p["prompt"] for p in prompts)
    assert host_count / len(prompts) <= 0.25
    assert year_count == 0
```

- [ ] **Step 2: Run the regression test and confirm current failure**

Run: `pytest human_archive/tests/test_ep02_visual_failure_regression.py -v`

Expected: FAIL with host and year counts equal to all 63 prompts.

- [ ] **Step 3: Record the rejected build without deleting it**

Write `visual_failure_report.json` with status `REJECTED`, current contact-sheet hash, affected shot count `63`, observed defects `host_omnipresence`, `embedded_year_text`, `pseudo_labels`, `template_repetition`, and `semantic_mismatch`. Record that the stopped motion clips are non-release artifacts.

- [ ] **Step 4: Commit the regression evidence**

```bash
git add human_archive/runs/ep02_jang_huibin/full-v4-001/visual_failure_report.json human_archive/tests/fixtures/ep02_visual_failure_prompts.json human_archive/tests/test_ep02_visual_failure_regression.py
git commit -m "test: lock EP02 visual prompt regression"
```

### Task 2: Add Explicit Visual Roles and Host Quotas

**Files:**
- Create: `human_archive/schemas/doodle_scene_contract.schema.json`
- Create: `human_archive/scripts/lib/doodle_visual_roles.py`
- Modify: `human_archive/config/channel_profiles.yaml`
- Modify: `human_archive/config/seonbi_visual_policy.yaml`
- Create: `human_archive/tests/test_doodle_visual_roles.py`

**Interfaces:**
- Consumes: sentence `beat`, `chapter`, `claim_id`, evidence IDs, and narration text.
- Produces: `VisualRoleDecision(role, host_mode, overlay_text, era_context, rationale)` and episode-level quota validation.

- [ ] **Step 1: Write failing role and quota tests**

```python
def test_fact_body_maps_to_reconstruction_without_host():
    result = classify_visual_role({"beat": "body", "claim_ids": ["CLM-JH-002"]})
    assert result.role == "historical_reconstruction"
    assert result.host_mode == "absent"

def test_host_quota_rejects_omnipresent_presenter():
    scenes = [{"role": "host_explainer", "host_mode": "full"}] * 20
    with pytest.raises(ValueError, match="host presence"):
        validate_role_mix(scenes)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest human_archive/tests/test_doodle_visual_roles.py -v`

Expected: FAIL because the role classifier and quota validator do not exist.

- [ ] **Step 3: Define the scene contract**

Require these fields:

```json
{
  "visual_role": "historical_reconstruction",
  "host_mode": "absent",
  "historical_subjects": ["장희빈", "숙종"],
  "era_context": "late Joseon royal court",
  "overlay_text": [],
  "must_not": ["host character", "letters", "numerals", "signage", "speech bubbles"]
}
```

Allowed roles are `host_explainer`, `historical_reconstruction`, `evidence_object`, `diagram_metaphor`, and `atmosphere`.

- [ ] **Step 4: Implement classification and episode quotas**

Map `hook`, `roadmap`, `analogy`, `insight`, and `outro` to host-eligible roles. Map evidence-bearing `body` and `source_commentary` to reconstruction/evidence roles. Enforce host ratio `0.15..0.25`, maximum consecutive host scenes `2`, and reconstruction/evidence ratio `>=0.60`.

- [ ] **Step 5: Make visual policy profile-aware**

Remove the unconditional cinematic K-webtoon style from the doodle path. Keep it only under `human_archive_cinematic_v1`, and add explicit doodle exclusions for poster layouts, empty infographic panels, generated captions, seals, and speech bubbles.

- [ ] **Step 6: Run focused tests and commit**

Run: `pytest human_archive/tests/test_doodle_visual_roles.py -v`

Expected: PASS.

```bash
git add human_archive/schemas/doodle_scene_contract.schema.json human_archive/scripts/lib/doodle_visual_roles.py human_archive/config/channel_profiles.yaml human_archive/config/seonbi_visual_policy.yaml human_archive/tests/test_doodle_visual_roles.py
git commit -m "feat: add role-aware doodle scene policy"
```

### Task 3: Replace Cyclic Templates with Narration-Aware Scene Planning

**Files:**
- Create: `human_archive/scripts/lib/doodle_scene_planner.py`
- Create: `human_archive/scripts/plan_doodle_episode_visuals.py`
- Modify: `human_archive/scripts/prepare_ep02_v4_workflow.py`
- Create: `human_archive/tests/test_doodle_scene_planner.py`

**Interfaces:**
- Consumes: `script_candidate.json`, claim inventory, source ledger, and role policy.
- Produces: `episode_visual_contract_v2.json` whose scenes cover every sentence exactly once and carry semantic subjects/actions.

- [ ] **Step 1: Write failing semantic-planning tests**

```python
def test_planner_uses_narrated_actor_instead_of_template_rotation():
    sentences = [{"sentence_id": "S1", "beat": "body", "tts_text": "숙종은 대신들의 간언을 물리쳤습니다."}]
    scene = plan_scenes(sentences, claims={})[0]
    assert "숙종" in scene["historical_subjects"]
    assert scene["visual_role"] == "historical_reconstruction"
    assert scene["host_mode"] == "absent"
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `pytest human_archive/tests/test_doodle_scene_planner.py -v`

Expected: FAIL because `plan_scenes` does not exist.

- [ ] **Step 3: Implement narration grouping and subject extraction**

Group adjacent sentences by chapter, claim/evidence continuity, and visual action rather than fixed character count alone. Use the current length-derived count as a ceiling, not a command to manufacture repetitive scenes. Preserve sentence coverage and order.

- [ ] **Step 4: Implement visual-beat diversity**

Select among character action, place establishing, evidence close-up, object detail, diagram/metaphor, and host explanation. Reject repeating the same role + subject + camera combination within the previous three scenes.

- [ ] **Step 5: Retire the 15-item `TEMPLATES` loop**

Make `prepare_ep02_v4_workflow.py` call the generic planner and emit `episode_visual_contract_v2.json`, `image_request_manifest.json`, and `overlay_event_manifest.json`. Keep a compatibility `shot_contract_v4.json` derived from the visual contract until downstream renderers migrate.

- [ ] **Step 6: Run planner and coverage tests**

Run: `pytest human_archive/tests/test_doodle_scene_planner.py human_archive/tests/test_visual_contract.py -v`

Expected: PASS with 100% sentence coverage and valid role mix.

- [ ] **Step 7: Commit**

```bash
git add human_archive/scripts/lib/doodle_scene_planner.py human_archive/scripts/plan_doodle_episode_visuals.py human_archive/scripts/prepare_ep02_v4_workflow.py human_archive/tests/test_doodle_scene_planner.py
git commit -m "feat: plan doodle scenes from narration semantics"
```

### Task 4: Compile Text-Safe, Role-Aware Flow Prompts

**Files:**
- Modify: `human_archive/scripts/lib/prompt_compiler.py`
- Create: `human_archive/scripts/lib/prompt_lint.py`
- Modify: `human_archive/tests/test_prompt_compiler.py`
- Create: `human_archive/tests/test_prompt_lint.py`

**Interfaces:**
- Consumes: role-aware scene contracts.
- Produces: Flow requests with `positive_prompt`, `negative.items`, `host_reference_assets`, and deterministic request SHA.

- [ ] **Step 1: Write failing prompt safety tests**

```python
def test_reconstruction_prompt_has_no_host_or_digits():
    request = compile_scene_request(RECONSTRUCTION_SCENE)
    prompt = request["positive_prompt"].lower()
    assert "seonbi" not in prompt
    assert not re.search(r"\d", prompt)
    assert {"letters", "numerals", "captions", "signage"} <= set(request["negative"]["items"])

def test_host_prompt_is_allowed_only_for_host_role():
    with pytest.raises(ValueError, match="host reference"):
        compile_scene_request({**RECONSTRUCTION_SCENE, "host_reference_assets": ["seonbi.png"]})
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `pytest human_archive/tests/test_prompt_compiler.py human_archive/tests/test_prompt_lint.py -v`

Expected: FAIL because current compiler copies literal era text and has no role checks.

- [ ] **Step 3: Separate metadata from generative prose**

Keep `era_context` and dates in the contract, but compile `1701 (조선 숙종 27년)` to non-numeric visual wording such as `late Joseon royal court clothing and architecture`. Do not include overlay strings in the base-image prompt.

- [ ] **Step 4: Compile role-specific character instructions**

For `host_explainer`, use the approved 쉽선비 reference asset and one pose. For all other roles, inject `no presenter, no black-gat host character` and describe only historical actors, evidence, objects, or atmosphere.

- [ ] **Step 5: Add prompt lint**

Fail a request containing digits, quotation marks intended as labels, `text`, `caption`, `sign`, `written`, or a host reference in a non-host role. Allow those concepts only in structured overlay metadata.

- [ ] **Step 6: Run tests and commit**

Run: `pytest human_archive/tests/test_prompt_compiler.py human_archive/tests/test_prompt_lint.py -v`

Expected: PASS.

```bash
git add human_archive/scripts/lib/prompt_compiler.py human_archive/scripts/lib/prompt_lint.py human_archive/tests/test_prompt_compiler.py human_archive/tests/test_prompt_lint.py
git commit -m "feat: compile text-safe role-aware Flow prompts"
```

### Task 5: Make Flow Generation Pilot-First and Fail-Closed

**Files:**
- Create: `human_archive/scripts/generate_flow_batch.py`
- Modify: `human_archive/scripts/batch_flow_all_ep02.py`
- Modify: `human_archive/scripts/rebuild_flow_manifest.py`
- Create: `human_archive/tests/test_flow_batch_state.py`
- Modify: `human_archive/tests/test_provider_flow.py`

**Interfaces:**
- Consumes: `image_request_manifest.json`, build directory, CDP URL, optional shot IDs.
- Produces: merge-safe `asset_manifest.json` and exact statuses `PENDING`, `SUBMITTED`, `DOWNLOADED`, `FAILED`, `REVIEW_REQUIRED`.

- [ ] **Step 1: Write failing completeness and merge tests**

```python
def test_selected_retry_merges_existing_manifest(tmp_path):
    existing = manifest_with_assets("S1", "S2")
    merged = merge_asset_rows(existing, [asset("S3")])
    assert [a["shot_id"] for a in merged["assets"]] == ["S1", "S2", "S3"]

def test_batch_never_reports_success_when_asset_is_missing():
    report = summarize_batch(expected_ids=["S1", "S2"], downloaded_ids=["S1"])
    assert report["status"] == "FAIL"
    assert report["missing"] == ["S2"]
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `pytest human_archive/tests/test_flow_batch_state.py human_archive/tests/test_provider_flow.py -v`

Expected: FAIL because selected retries overwrite the manifest and attempted rows are treated as success.

- [ ] **Step 3: Implement stable result detection**

Replace fixed waits with polling for a new provider media ID/URL that was absent before submission. Require the new result to stabilize before download. On timeout, mark only that shot `FAILED`; never reuse the newest old URL.

- [ ] **Step 4: Implement pilot selection**

Select 8 representative scenes: two host, three historical reconstruction, one evidence object, one diagram/metaphor, and one atmosphere. Stop after the pilot and require a current-hash `visual_pilot_review.json` before accepting `--all`.

- [ ] **Step 5: Implement resumable manifest merge**

Retrying one shot must update only that shot row. Final success requires expected count, unique IDs, all files present, correct hashes, and zero failed/review-required rows.

- [ ] **Step 6: Keep EP02 wrapper thin**

Make `batch_flow_all_ep02.py` pass EP02 paths to `generate_flow_batch.py`; remove provider logic duplication from the wrapper.

- [ ] **Step 7: Run tests and commit**

Run: `pytest human_archive/tests/test_flow_batch_state.py human_archive/tests/test_provider_flow.py -v`

Expected: PASS.

```bash
git add human_archive/scripts/generate_flow_batch.py human_archive/scripts/batch_flow_all_ep02.py human_archive/scripts/rebuild_flow_manifest.py human_archive/tests/test_flow_batch_state.py human_archive/tests/test_provider_flow.py
git commit -m "fix: make Flow generation resumable and fail closed"
```

### Task 6: Add Embedded-Text and Role-Compliance QA Gates

**Files:**
- Modify: `human_archive/requirements.lock.txt`
- Create: `human_archive/scripts/lib/visual_content_qa.py`
- Modify: `human_archive/scripts/lib/visual_qa.py`
- Modify: `human_archive/scripts/verify_visual_assets.py`
- Modify: `human_archive/tests/test_visual_qa.py`
- Modify: `human_archive/tests/test_visual_pilot_approval.py`

**Interfaces:**
- Consumes: image files, scene role contract, manifest hashes, and human visual evaluations.
- Produces: per-shot OCR findings, role-compliance status, and a fail-closed visual report.

- [ ] **Step 1: Add failing OCR and approval-axis tests**

```python
def test_base_image_fails_when_ocr_detects_year(fake_ocr):
    fake_ocr.returns([{"text": "1701", "confidence": 0.97}])
    result = inspect_generated_text(Path("shot.jpg"), fake_ocr)
    assert result.status == "FAIL"

def test_reconstruction_requires_host_absence_review():
    errors = validate_visual_evaluation(
        scene={"visual_role": "historical_reconstruction"},
        evaluation={"axes": {"host_presence": "FAIL"}},
    )
    assert "host_presence" in errors[0]
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `pytest human_archive/tests/test_visual_qa.py human_archive/tests/test_visual_pilot_approval.py -v`

Expected: FAIL because OCR and host-presence axes are absent.

- [ ] **Step 3: Add local OCR adapter**

Add a pinned RapidOCR ONNX Runtime dependency. Store detected text, confidence, and bounding boxes in `visual_content_report.json`. Any non-empty OCR result with confidence `>=0.70` fails a base image; unavailable OCR returns `REVIEW_REQUIRED`, never PASS.

- [ ] **Step 4: Extend human visual axes**

Require `semantic_match`, `historical_subject`, `host_presence`, `embedded_text`, `composition_density`, `style_profile`, `dignity`, and `service_mark`. A reconstruction with visible 쉽선비 or any scene with generated text cannot be approved.

- [ ] **Step 5: Gate motion rendering**

At the start of `build_motion_clips_v2.py`, call `verify_visual_build(build_dir=...)`. Abort before reading images unless the current contract hash, manifest hash, OCR report, and visual approval all pass.

- [ ] **Step 6: Run tests and commit**

Run: `pytest human_archive/tests/test_visual_qa.py human_archive/tests/test_visual_pilot_approval.py human_archive/tests/test_motion_clips_v2.py -v`

Expected: PASS.

```bash
git add human_archive/requirements.lock.txt human_archive/scripts/lib/visual_content_qa.py human_archive/scripts/lib/visual_qa.py human_archive/scripts/verify_visual_assets.py human_archive/scripts/build_motion_clips_v2.py human_archive/tests/test_visual_qa.py human_archive/tests/test_visual_pilot_approval.py human_archive/tests/test_motion_clips_v2.py
git commit -m "feat: gate visuals on OCR and role compliance"
```

### Task 7: Regenerate EP02 Through Pilot Approval and Full Release Gates

**Files:**
- Create: `human_archive/runs/ep02_jang_huibin/full-v4-002/`
- Create: `human_archive/runs/ep02_jang_huibin/full-v4-002/approvals/visual_pilot_review.json`
- Create: `human_archive/runs/ep02_jang_huibin/full-v4-002/approvals/visual_approval.json`
- Modify: `CLAUDE.md`
- Modify: `manual.md`
- Modify: `human_archive/README.md`

**Interfaces:**
- Consumes: corrected planner, prompt compiler, Flow generator, approved script/audio/subtitles.
- Produces: a new approved build and final candidate without reusing rejected `full-v4-001` visual hashes.

- [ ] **Step 1: Generate and lint the new visual contract**

Run:

```powershell
python human_archive/scripts/plan_doodle_episode_visuals.py --script human_archive/runs/ep02_jang_huibin/full-v4-001/source/script_candidate.json --claims human_archive/runs/ep02_jang_huibin/source/claim_inventory_v2.json --output human_archive/runs/ep02_jang_huibin/full-v4-002/episode_visual_contract_v2.json
```

Expected: role-mix PASS, no literal digits in image prompts, and host ratio between 15% and 25%.

- [ ] **Step 2: Generate the representative 8-shot pilot**

Run:

```powershell
python human_archive/scripts/generate_flow_batch.py --build human_archive/runs/ep02_jang_huibin/full-v4-002 --pilot --model "Nano Banana 2" --cdp http://127.0.0.1:9222
```

Expected: exactly 8 verified assets; no full-batch submission.

- [ ] **Step 3: Run pilot OCR and contact-sheet review**

Run:

```powershell
python human_archive/scripts/verify_visual_assets.py --build human_archive/runs/ep02_jang_huibin/full-v4-002
```

Expected before approval: FAIL only for missing signed pilot approval, with OCR/text and pixel checks otherwise clean.

- [ ] **Step 4: Record human pilot approval only after visual inspection**

Approve only if host scenes contain the canonical 쉽선비, reconstruction scenes omit him, no generated text/date is visible, compositions are sufficiently filled, and all eight scenes match narration.

- [ ] **Step 5: Generate the remaining full set and run full QA**

Run:

```powershell
python human_archive/scripts/generate_flow_batch.py --build human_archive/runs/ep02_jang_huibin/full-v4-002 --all --model "Nano Banana 2" --cdp http://127.0.0.1:9222
python human_archive/scripts/verify_visual_assets.py --build human_archive/runs/ep02_jang_huibin/full-v4-002
```

Expected: all planned shots present once, OCR zero, no near duplicates, role-compliance approval complete.

- [ ] **Step 6: Reuse approved audio/subtitles only after hash check**

Copy or rebuild audio/subtitles into `full-v4-002` only if their script hash matches the approved `script_candidate.json`. Record provenance in the new build manifest.

- [ ] **Step 7: Render motion and candidate only after visual PASS**

Run:

```powershell
python human_archive/scripts/build_motion_clips_v2.py --build human_archive/runs/ep02_jang_huibin/full-v4-002
python human_archive/scripts/render_episode_v2.py --build human_archive/runs/ep02_jang_huibin/full-v4-002
python human_archive/scripts/postflight_release.py --input human_archive/runs/ep02_jang_huibin/full-v4-002/candidate/HA002-full-v4-002.mp4 --report human_archive/runs/ep02_jang_huibin/full-v4-002/release_report.json --duration-mode full
```

- [x] **Step 8: Update runbooks with the role/text/pilot rules**

Document the five roles, 15–25% host quota, digit-free AI prompts, renderer-only dates/labels, pilot-before-full rule, and mandatory OCR/full visual approval in all three runbooks.

- [ ] **Step 9: Run the focused suite and commit**

Run:

```powershell
pytest human_archive/tests/test_doodle_visual_roles.py human_archive/tests/test_doodle_scene_planner.py human_archive/tests/test_prompt_compiler.py human_archive/tests/test_prompt_lint.py human_archive/tests/test_flow_batch_state.py human_archive/tests/test_visual_qa.py human_archive/tests/test_visual_pilot_approval.py human_archive/tests/test_motion_clips_v2.py -v
```

Expected: PASS.

```bash
git add CLAUDE.md manual.md human_archive/README.md human_archive/runs/ep02_jang_huibin/full-v4-002
git commit -m "feat: rebuild EP02 with role-safe doodle visuals"
```

---

## Acceptance Checklist

- [ ] `full-v4-001` is marked rejected and is never released.
- [ ] AI prompts contain no `1701`, other digits, caption text, or renderer overlay strings.
- [ ] 쉽선비 appears in 15–25% of scenes and only where `visual_role == host_explainer`.
- [ ] No more than two host scenes appear consecutively.
- [ ] Historical reconstructions contain the narrated historical actors, not the presenter.
- [ ] Base-image OCR detects zero readable text across the full set.
- [ ] Provider policy cards are classified as `provider_policy_rejected`; failed variants are preserved and only the affected scene is rewritten and regenerated.
- [ ] Every host asset records and verifies the canonical overlay SHA; partial or regenerated host bodies are rejected.
- [ ] Host bases contain no second presenter or body parts, and evidence shots contain no collage/catalogue composition.
- [ ] The representative pilot is approved before full Flow generation.
- [ ] Full contact-sheet approval is tied to current contract and manifest hashes.
- [ ] Missing or stale assets make the batch and motion renderer fail closed.
- [ ] Final candidate is rendered only from `full-v4-002` after all visual gates pass.
