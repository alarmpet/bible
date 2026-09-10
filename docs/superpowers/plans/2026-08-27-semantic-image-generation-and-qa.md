# Semantic Image Generation and QA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compile narration-aligned image prompts without generic object collapse, generate a dual pilot through Flow, preserve semantics during policy retries, and block motion rendering until text, duplication, continuity and narration-image matching all pass.

**Architecture:** Treat `shot_alignment_manifest.json` as immutable input. A mode-aware compiler emits provider requests plus a deterministic alignment report; Flow remains a resumable adapter that cannot run without a current PASS. Post-generation QA combines pixel/OCR/hash checks, sequence-aware duplicate checks, schema-constrained Codex vision review, and current-hash human approval.

**Tech Stack:** Python 3.12+, pytest, Pillow, imagehash, RapidOCR, Playwright CDP, Codex CLI vision, FFmpeg

**Spec:** `docs/superpowers/specs/2026-08-27-narration-aligned-visual-workflow-design.md`

## Global Constraints

- The compiler must preserve every required semantic anchor, focal subject, action, place and era.
- `_HOST_BASE_VIGNETTES` and `_EVIDENCE_OBJECT_VIGNETTES` rotation is not used by the v5 profile.
- Base images contain no readable letters, Hangul, numerals, years, labels, signs, captions, seals, speech bubbles, watermarks or service marks.
- `evidence_artifact` is legal only when a named artifact or evidence method is a required narration anchor.
- Policy retry permits two automatic attempts and may not change claim IDs, required anchor IDs, place or era.
- The pilot is the union of a first-12/first-120-second cold-open set and an eight-shot coverage set.
- `--all` requires both pilot sets to be approved against current asset fingerprints.
- Full generation is resumable per shot and never reuses an older card URL as a new result.
- Motion rendering fails closed unless all current visual gates pass.
- Tests use fake CDP/model/OCR adapters and do not spend provider quota.

---

### Task 1: Replace Role Templates with a Mode-Aware Semantic Prompt Compiler

**Files:**
- Create: `human_archive/scripts/lib/aligned_prompt_compiler.py`
- Modify: `human_archive/config/seonbi_visual_policy.yaml`
- Modify: `human_archive/scripts/lib/prompt_compiler.py`
- Modify: `human_archive/scripts/prepare_narration_aligned_workflow.py`
- Modify: `human_archive/tests/test_prompt_compiler.py`
- Create: `human_archive/tests/test_aligned_prompt_compiler.py`

**Interfaces:**
- Consumes: one validated aligned shot and its `alignment_sha256`.
- Produces: `compile_aligned_scene_request(scene: dict, alignment_sha256: str, provider: str = "flow") -> dict`; updated `image_request_manifest.json`, compatibility `flow_image_prompts.json`, and renderer-only `overlay_event_manifest.json`.

- [ ] **Step 1: Write failing semantic-preservation tests**

```python
from lib.aligned_prompt_compiler import compile_aligned_scene_request


def aligned_scene(mode="event_reconstruction"):
    return {
        "shot_id": "ha002_v5_shot_001",
        "scene_id": "ha002_v5_shot_001",
        "order": 1,
        "visual_mode": mode,
        "visual_role": "historical_reconstruction",
        "host_mode": "absent",
        "semantic_anchors": [
            {"anchor_id": "a-person", "kind": "person", "source_text": "숙종", "visual_token": "King Sukjong", "required": True},
            {"anchor_id": "a-action", "kind": "action", "source_text": "대신들과 논의", "visual_token": "debates with court ministers", "required": True},
        ],
        "focal_subject": "King Sukjong and court ministers",
        "action": "debate a royal decision face to face",
        "place": "late Joseon royal council hall",
        "era": "late Joseon",
        "shot_scale": "wide",
        "camera": "eye-level documentary view",
        "foreground": "one seated minister in profile",
        "midground": "King Sukjong debating with ministers",
        "background": "wooden royal council hall",
        "continuity_group": "sukjong_v1",
        "reference_asset_ids": ["character_sukjong_v1"],
        "prop_motifs": ["council_mat"],
        "text_overlay_policy": "renderer_only",
        "overlay_items": [],
        "motion_profile": "reenactment_push",
        "novelty_signature": "NOVEL-1",
        "source_sentence_spans": [{"sentence_id": "S1", "char_start": 0, "char_end": 17}],
    }


def test_reconstruction_prompt_keeps_person_action_and_place():
    request = compile_aligned_scene_request(aligned_scene(), "ALIGN-1")
    prompt = request["submission_prompt"].lower()
    assert "king sukjong" in prompt
    assert "debate a royal decision" in prompt
    assert "royal council hall" in prompt
    assert "blank archive volume" not in prompt
    assert request["semantic_anchors"][0]["anchor_id"] == "a-person"


def test_evidence_mode_requires_specific_evidence_anchor():
    scene = aligned_scene("evidence_artifact")
    scene["visual_role"] = "evidence_object"
    with pytest.raises(ValueError, match="specific evidence anchor"):
        compile_aligned_scene_request(scene, "ALIGN-1")


def test_host_base_uses_context_but_never_generates_host():
    scene = aligned_scene("host_chapter_hinge")
    scene.update({"visual_role": "host_explainer", "host_mode": "full", "motion_profile": "host_hinge"})
    request = compile_aligned_scene_request(scene, "ALIGN-1")
    assert request["host_overlay"]["asset"] == "human_archive/assets/doodle_seonbi_v1.png"
    assert "no people" in request["submission_prompt"].lower()
    assert "generated presenter" in request["negative"]["items"]
```

- [ ] **Step 2: Run tests and verify RED**

Run: `pytest human_archive/tests/test_aligned_prompt_compiler.py -v`

Expected: FAIL because the aligned compiler does not exist.

- [ ] **Step 3: Implement mode-specific composition functions**

Create these exact functions, each returning only a composition phrase and never replacing content anchors:

```python
def event_reconstruction_composition(scene: dict) -> str
def place_establishing_composition(scene: dict) -> str
def route_map_composition(scene: dict) -> str
def mechanism_diagram_composition(scene: dict) -> str
def evidence_artifact_composition(scene: dict) -> str
def modern_analogy_composition(scene: dict) -> str
def atmosphere_transition_composition(scene: dict) -> str
def host_chapter_hinge_composition(scene: dict) -> str
```

The final prompt order must be `style → era/place → required anchors → focal action → depth layers → camera/scale → mode composition → no-text rule`. For host mode, retain context as an object/place base, remove people only from the generated base, and add canonical overlay metadata.

Add `doodle_seonbi_narrative_v2` to `seonbi_visual_policy.yaml` with hand-drawn black ink contours, restrained warm pastel fills, subtle off-white paper, and filled foreground/midground/background. Its negative style list must include photograph, 3D render, anime, realistic face, poster layout, collage, catalogue sheet, split panel and broad empty space; permit broad empty space only in the host composition function.

- [ ] **Step 4: Route v5 scenes through the new compiler**

Modify `compile_scene_request()` to call `compile_aligned_scene_request()` when `visual_mode` is present. Keep the existing role-aware path for v4 fixtures. Ensure the v5 request stores `visual_mode`, `semantic_anchors`, `continuity_group`, `reference_asset_ids`, `motion_profile`, `novelty_signature`, `source_sentence_spans`, and `alignment_sha256` before calculating `request_sha256`. Do not append `overlay_items[].text` to either prompt; `prepare_narration_aligned_workflow.py` writes those rows to `overlay_event_manifest.json` with the same alignment SHA.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `pytest human_archive/tests/test_aligned_prompt_compiler.py human_archive/tests/test_prompt_compiler.py human_archive/tests/test_prompt_lint.py -v`

Expected: PASS; legacy prompt tests remain green.

- [ ] **Step 6: Commit**

```bash
git add human_archive/config/seonbi_visual_policy.yaml human_archive/scripts/lib/aligned_prompt_compiler.py human_archive/scripts/lib/prompt_compiler.py human_archive/scripts/prepare_narration_aligned_workflow.py human_archive/tests/test_aligned_prompt_compiler.py human_archive/tests/test_prompt_compiler.py
git commit -m "feat: compile narration-aligned image requests"
```

### Task 2: Add a Fail-Closed Prompt Alignment and Diversity Preflight

**Files:**
- Create: `human_archive/scripts/lib/prompt_alignment_qa.py`
- Create: `human_archive/scripts/validate_image_requests.py`
- Create: `human_archive/tests/test_prompt_alignment_qa.py`
- Modify: `human_archive/scripts/generate_flow_batch.py`
- Modify: `human_archive/tests/test_flow_batch_state.py`

**Interfaces:**
- Consumes: shot alignment manifest and image request manifest.
- Produces: `validate_image_request_alignment(alignment: dict, requests: dict, profile: dict) -> dict`; `build_dir / "prompt_alignment_report.json"`; `require_current_prompt_preflight(build_dir: Path) -> None`; testable `generate_flow_batch.main(argv: list[str] | None = None) -> None`.

- [ ] **Step 1: Write failing preflight tests**

```python
import generate_flow_batch
import pytest

from lib.prompt_alignment_qa import validate_image_request_alignment


def profile_fixture():
    return {
        "host_ratio_min": 0.08, "host_ratio_max": 0.12,
        "host_min_non_host_gap": 7, "max_same_mode_streak": 2,
        "max_evidence_streak": 1, "motif_window_shots": 10,
        "max_motif_occurrences_per_window": 2,
    }


def test_preflight_rejects_dropped_anchor_and_duplicate_novelty():
    alignment = {"alignment_sha256": "ALIGN", "shots": [
        {"shot_id": "S1", "semantic_anchors": [{"anchor_id": "A1", "required": True}], "novelty_signature": "N1", "visual_mode": "event_reconstruction", "prop_motifs": []},
        {"shot_id": "S2", "semantic_anchors": [{"anchor_id": "A2", "required": True}], "novelty_signature": "N1", "visual_mode": "place_establishing", "prop_motifs": []},
    ]}
    requests = {"alignment_sha256": "ALIGN", "requests": [
        {"scene_id": "S1", "semantic_anchors": [], "novelty_signature": "N1", "request_sha256": "R1"},
        {"scene_id": "S2", "semantic_anchors": [{"anchor_id": "A2", "required": True}], "novelty_signature": "N1", "request_sha256": "R2"},
    ]}
    report = validate_image_request_alignment(alignment, requests, profile_fixture())
    assert report["status"] == "FAIL"
    assert "A1" in report["shots"][0]["missing_required_anchor_ids"]
    assert report["sequence"]["duplicate_novelty_signatures"] == ["N1"]


def test_flow_refuses_to_connect_before_current_preflight_passes(tmp_path, monkeypatch):
    monkeypatch.setattr(generate_flow_batch, "require_current_prompt_preflight", lambda path: (_ for _ in ()).throw(SystemExit("preflight stale")))
    with pytest.raises(SystemExit, match="preflight stale"):
        generate_flow_batch.main(["--build", str(tmp_path), "--pilot"])
```

- [ ] **Step 2: Run tests and verify RED**

Run: `pytest human_archive/tests/test_prompt_alignment_qa.py human_archive/tests/test_flow_batch_state.py -v`

Expected: FAIL because the preflight module and entry hook are missing.

- [ ] **Step 3: Implement one-pass report generation**

The report must contain:

```json
{
  "schema_version": 1,
  "alignment_sha256": "ALIGNMENT_SHA256",
  "request_manifest_sha256": "REQUEST_MANIFEST_SHA256",
  "status": "PASS",
  "shots": [],
  "sequence": {
    "duplicate_request_sha256": [],
    "duplicate_novelty_signatures": [],
    "mode_streak_violations": [],
    "evidence_streak_violations": [],
    "host_spacing_violations": [],
    "motif_window_violations": []
  }
}
```

Every request must preserve the exact set of required anchor IDs from its shot. Compare current hashes and reject extra, missing, duplicate, or reordered scene IDs.

- [ ] **Step 4: Gate browser generation on the report**

At the start of `generate_flow_batch.py` main processing, load the report and require `status == "PASS"`, current `alignment_sha256`, and current request manifest SHA. Perform this before `async_playwright()` or CDP connection.
Refactor the entry point to `main(argv: list[str] | None = None) -> None` and call `parser.parse_args(argv)` so the preflight ordering can be tested without a subprocess.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `pytest human_archive/tests/test_prompt_alignment_qa.py human_archive/tests/test_flow_batch_state.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add human_archive/scripts/lib/prompt_alignment_qa.py human_archive/scripts/validate_image_requests.py human_archive/scripts/generate_flow_batch.py human_archive/tests/test_prompt_alignment_qa.py human_archive/tests/test_flow_batch_state.py
git commit -m "feat: gate Flow on semantic prompt preflight"
```

### Task 3: Replace Object-Only Policy Collapse with a Semantic Retry Ladder

**Files:**
- Modify: `human_archive/scripts/lib/prompt_compiler.py`
- Modify: `human_archive/scripts/rewrite_policy_rejected_prompt.py`
- Modify: `human_archive/tests/test_prompt_compiler.py`
- Modify: `human_archive/tests/test_policy_retry_archive.py`

**Interfaces:**
- Consumes: aligned scene, failed request, provider error kind, previous retry audit.
- Produces: `compile_policy_safe_retry(scene: dict, attempt: int, provider: str = "flow", reason: str = "provider_policy_rejected") -> dict`; append-only `policy_retry_manifest.json`.

- [ ] **Step 1: Write failing semantic retry tests**

```python
import pytest

from lib.prompt_compiler import compile_policy_safe_retry


def aligned_reconstruction_scene():
    return {
        "shot_id": "ha002_v5_shot_014", "scene_id": "ha002_v5_shot_014", "order": 14,
        "visual_mode": "event_reconstruction", "visual_role": "historical_reconstruction",
        "host_mode": "absent", "claim_ids": ["C14"],
        "semantic_anchors": [
            {"anchor_id": "a-person", "kind": "person", "source_text": "숙종", "visual_token": "King Sukjong", "required": True},
            {"anchor_id": "a-action", "kind": "action", "source_text": "대신들과 논의", "visual_token": "debates with court ministers", "required": True},
        ],
        "focal_subject": "King Sukjong and court ministers",
        "action": "debate a royal decision face to face",
        "place": "late Joseon royal council hall", "era": "late Joseon",
        "shot_scale": "wide", "camera": "eye-level documentary view",
        "foreground": "one minister", "midground": "the council debate", "background": "royal council hall",
        "continuity_group": "sukjong_v1", "prop_motifs": ["council_mat"],
        "reference_asset_ids": ["character_sukjong_v1"],
        "text_overlay_policy": "renderer_only", "overlay_items": [],
        "motion_profile": "reenactment_push",
        "novelty_signature": "NOVEL-14", "source_sentence_spans": [{"sentence_id": "S14", "char_start": 0, "char_end": 18}],
    }


def test_first_retry_preserves_event_anchors_and_changes_safety_treatment():
    scene = aligned_reconstruction_scene()
    request = compile_policy_safe_retry(scene, attempt=1)
    assert request["policy_retry_transform"] == "safe_rephrase"
    assert [a["anchor_id"] for a in request["semantic_anchors"]] == ["a-person", "a-action"]
    assert "royal council hall" in request["submission_prompt"].lower()
    assert "blank documents in a peaceful palace workroom" not in request["submission_prompt"].lower()


def test_second_retry_uses_mode_compatible_abstraction_not_generic_table():
    scene = aligned_reconstruction_scene()
    request = compile_policy_safe_retry(scene, attempt=2)
    assert request["policy_retry_transform"] == "safe_abstraction"
    assert "distant silhouettes" in request["submission_prompt"].lower()
    assert "wooden table" not in request["submission_prompt"].lower()


def test_third_automatic_retry_is_rejected():
    with pytest.raises(ValueError, match="maximum.*two"):
        compile_policy_safe_retry(aligned_reconstruction_scene(), attempt=3)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `pytest human_archive/tests/test_prompt_compiler.py human_archive/tests/test_policy_retry_archive.py -v`

Expected: FAIL because current retries erase subjects and accept object-only variants.

- [ ] **Step 3: Implement exact retry transforms**

Use this mode-aware transform table:

```python
SAFE_ABSTRACTION_BY_MODE = {
    "event_reconstruction": "same named actors as distant non-graphic silhouettes performing the same action in the same place",
    "place_establishing": "the same place after the event, with environmental traces but no harmed person",
    "route_map": "the same unlabeled route map with a single highlighted path",
    "mechanism_diagram": "the same causal relationship as neutral unlabeled shapes and arrows",
    "evidence_artifact": "the same named evidence object in its real archive or excavation context",
    "modern_analogy": "the same single analogy using neutral everyday objects",
    "atmosphere_transition": "the same place and time as an unoccupied atmospheric view",
    "host_chapter_hinge": "the same contextual base with no generated person and canonical host overlay metadata",
}
```

Attempt 1 adds non-graphic educational wording without changing the mode. Attempt 2 may apply the table but must keep required anchor IDs, claim IDs, place and era. Recompute the request hash after adding `policy_retry_attempt`, `policy_retry_transform`, `policy_retry_reason`, and `previous_request_sha256`.

- [ ] **Step 4: Update archive and audit behavior**

`rewrite_policy_rejected_prompt.py` must infer the next attempt from prior audit rows, archive the current image/request, append one audit row, and set the shot `REVIEW_REQUIRED` instead of compiling attempt 3. Remove CLI choices `object_only`, `minimal_objects`, `ultra_minimal`; replace them with `--attempt 1|2` and default to the inferred next attempt.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `pytest human_archive/tests/test_prompt_compiler.py human_archive/tests/test_policy_retry_archive.py human_archive/tests/test_flow_batch_state.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add human_archive/scripts/lib/prompt_compiler.py human_archive/scripts/rewrite_policy_rejected_prompt.py human_archive/tests/test_prompt_compiler.py human_archive/tests/test_policy_retry_archive.py
git commit -m "fix: preserve scene semantics during policy retry"
```

### Task 4: Implement the Cold-Open Plus Coverage Dual Pilot

**Files:**
- Modify: `human_archive/scripts/generate_flow_batch.py`
- Modify: `human_archive/scripts/build_contact_sheet.py`
- Create: `human_archive/schemas/visual_pilot_approval_v2.schema.json`
- Modify: `human_archive/tests/test_flow_batch_state.py`
- Modify: `human_archive/tests/test_visual_pilot_approval.py`
- Create: `human_archive/tests/test_contact_sheet_metadata.py`

**Interfaces:**
- Consumes: ordered aligned requests with `start_sec`, `end_sec`, `visual_mode`, narration digest and anchors.
- Produces: `select_cold_open_requests(requests, shot_limit=12, max_end_sec=120.0)`, `select_coverage_requests(requests, count=8)`, `select_dual_pilot_requests(requests) -> dict[str, list[dict]]`; `pilot_cold_open_contact_sheet.jpg`; `pilot_coverage_contact_sheet.jpg`; v2 approval with `pilot_sets` and fingerprints.

- [ ] **Step 1: Write failing selection tests**

```python
from generate_flow_batch import select_cold_open_requests, select_dual_pilot_requests


ALLOWED_VISUAL_MODES = (
    "event_reconstruction", "place_establishing", "route_map", "mechanism_diagram",
    "evidence_artifact", "modern_analogy", "atmosphere_transition", "host_chapter_hinge",
)


def request(index, *, start, end, mode):
    return {
        "scene_id": f"S{index:03d}", "order": index,
        "start_sec": start, "end_sec": end, "visual_mode": mode,
        "chapter": 1 + (index - 1) // 6, "shot_scale": "wide",
        "continuity_group": "" if mode != "event_reconstruction" else "history_group",
        "narration_digest": f"narration {index}",
        "semantic_anchors": [{"anchor_id": f"A{index}", "visual_token": f"anchor {index}", "required": True}],
    }


def representative_requests_for_eight_modes(total):
    return [
        request(
            index,
            start=(index - 1) * 10.0,
            end=index * 10.0,
            mode=ALLOWED_VISUAL_MODES[(index - 1) % len(ALLOWED_VISUAL_MODES)],
        )
        for index in range(1, total + 1)
    ]


def test_cold_open_is_contiguous_and_stops_at_twelve():
    requests = [request(i, start=(i - 1) * 10.0, end=i * 10.0, mode="event_reconstruction") for i in range(1, 21)]
    selected = select_cold_open_requests(requests)
    assert [item["order"] for item in selected] == list(range(1, 13))


def test_dual_pilot_keeps_named_sets_and_deduplicates_union():
    requests = representative_requests_for_eight_modes(total=24)
    pilot = select_dual_pilot_requests(requests)
    assert len(pilot["cold_open"]) == 12
    assert len(pilot["coverage"]) == 8
    assert len(pilot["all"]) == len({item["scene_id"] for item in pilot["cold_open"] + pilot["coverage"]})
    assert {item["visual_mode"] for item in pilot["coverage"]} == set(ALLOWED_VISUAL_MODES)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `pytest human_archive/tests/test_flow_batch_state.py human_archive/tests/test_contact_sheet_metadata.py -v`

Expected: FAIL because only the legacy role-stratified eight-shot selector exists.

- [ ] **Step 3: Implement deterministic pilot selection**

Coverage selection must score candidates by uncovered visual mode, chapter, continuity group and shot scale, then choose the lowest-order highest-score candidate until eight are selected. It must fail with a list of uncovered required categories when the episode cannot provide a valid coverage set.

Store these fields in `asset_manifest.json`:

```json
{
  "generation_scope": "pilot",
  "pilot_sets": {
    "cold_open": ["ha002_v5_shot_001"],
    "coverage": ["ha002_v5_shot_001"],
    "all": ["ha002_v5_shot_001"]
  },
  "expected_ids": ["ha002_v5_shot_001"]
}
```

- [ ] **Step 4: Add metadata contact sheets**

Make `create_contact_sheet()` accept `shot_ids` and `output_file`. Read alignment metadata and reserve a 110-pixel caption band below each 480x270 thumbnail. Render shot ID, `mm:ss.s-mm:ss.s`, visual mode, narration digest truncated to 42 Korean characters, and required anchor visual tokens. Use a Korean-capable local font with a deterministic fallback; test the generated sheet dimensions and that both requested files exist.

- [ ] **Step 5: Bind both sets to approval**

The v2 approval schema must require `decision`, `contract_sha256`, `request_manifest_sha256`, `pilot_sets`, `pilot_asset_fingerprints`, and one `shot_evaluation` per union ID. `_require_current_pilot_approval()` must verify each named set independently before `--all`.

- [ ] **Step 6: Run tests and verify GREEN**

Run: `pytest human_archive/tests/test_flow_batch_state.py human_archive/tests/test_visual_pilot_approval.py human_archive/tests/test_contact_sheet_metadata.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add human_archive/scripts/generate_flow_batch.py human_archive/scripts/build_contact_sheet.py human_archive/schemas/visual_pilot_approval_v2.schema.json human_archive/tests/test_flow_batch_state.py human_archive/tests/test_visual_pilot_approval.py human_archive/tests/test_contact_sheet_metadata.py
git commit -m "feat: require dual visual pilot approval"
```

### Task 5: Add Codex Vision Semantic Review and Sequence-Aware Visual QA

**Files:**
- Create: `human_archive/schemas/visual_semantic_review.schema.json`
- Create: `human_archive/scripts/lib/visual_semantic_qa.py`
- Create: `human_archive/scripts/review_visual_semantics.py`
- Modify: `human_archive/scripts/lib/visual_qa.py`
- Modify: `human_archive/scripts/verify_visual_assets.py`
- Modify: `human_archive/tests/test_visual_qa.py`
- Create: `human_archive/tests/test_visual_semantic_qa.py`

**Interfaces:**
- Consumes: generated images, aligned shots, current request hashes, a vision review provider.
- Produces: `build_semantic_review_prompt(scene: dict) -> str`; `review_shot(image_path: Path, scene: dict, provider: VisionReviewProvider) -> dict`; `validate_semantic_review_bindings(review: dict, alignment_sha256: str, request_manifest_sha256: str, asset_manifest_sha256: str) -> list[str]`; `build_dir / "visual_semantic_review.json"`; enhanced `verify_visual_build()`.

- [ ] **Step 1: Write failing semantic QA tests**

```python
from PIL import Image

from lib.visual_semantic_qa import review_shot, validate_semantic_review_bindings


def complete_scene_fixture():
    return {
        "shot_id": "S1", "narration_digest": "숙종이 대신들과 왕실 결정을 논의한다",
        "visual_mode": "event_reconstruction",
        "semantic_anchors": [
            {"anchor_id": "a-person", "visual_token": "King Sukjong", "required": True},
            {"anchor_id": "a-action", "visual_token": "council debate", "required": True},
        ],
        "focal_subject": "King Sukjong and court ministers",
        "action": "debate a royal decision", "place": "royal council hall",
        "era": "late Joseon", "continuity_group": "sukjong_v1",
    }


class FakeVisionProvider:
    def __init__(self, result):
        self.result = result
        self.calls = []
    def review(self, image_path, prompt, schema_path):
        self.calls.append((image_path, prompt, schema_path))
        return self.result


def test_semantic_review_requires_every_anchor_and_correct_mode(tmp_path):
    image_path = tmp_path / "S1.jpg"
    Image.new("RGB", (1920, 1080), "white").save(image_path)
    provider = FakeVisionProvider({
        "shot_id": "S1",
        "decision": "rejected",
        "axes": {
            "semantic_match": "FAIL",
            "required_anchor_presence": "FAIL",
            "visual_mode_match": "PASS",
            "character_continuity": "NOT_APPLICABLE",
            "composition_density": "PASS",
            "embedded_text": "PASS",
            "style_profile": "PASS",
            "dignity": "PASS",
            "service_mark": "PASS"
        },
        "missing_anchor_ids": ["a-action"],
        "notes": "The council action is absent."
    })
    result = review_shot(image_path, complete_scene_fixture(), provider)
    assert result["decision"] == "rejected"
    assert result["missing_anchor_ids"] == ["a-action"]


def test_semantic_review_rejects_stale_hash_binding():
    review = {
        "alignment_sha256": "OLD-ALIGN",
        "request_manifest_sha256": "CURRENT-REQUEST",
        "asset_manifest_sha256": "CURRENT-ASSET",
        "shots": [],
    }
    errors = validate_semantic_review_bindings(
        review,
        alignment_sha256="CURRENT-ALIGN",
        request_manifest_sha256="CURRENT-REQUEST",
        asset_manifest_sha256="CURRENT-ASSET",
    )
    assert errors == ["Semantic review is stale for the current shot alignment"]
```

- [ ] **Step 2: Run tests and verify RED**

Run: `pytest human_archive/tests/test_visual_semantic_qa.py human_archive/tests/test_visual_qa.py -v`

Expected: FAIL because semantic review is not implemented.

- [ ] **Step 3: Implement a schema-constrained vision provider**

Reuse the safe subprocess rules from `CodexCliVisualBriefProvider`, append `["--image", str(image_path.resolve())]`, keep `--ephemeral --sandbox read-only --output-schema`, and pass narration digest, required anchors, mode, focal action, place, era and continuity reference hashes in the prompt. Tests inject a fake provider and never launch Codex.

- [ ] **Step 4: Extend visual QA axes and reports**

Add `required_anchor_presence`, `visual_mode_match`, and `character_continuity` to required axes. `NOT_APPLICABLE` is valid for continuity only when `continuity_group` is empty. Bind `visual_semantic_review.json` to current alignment, request manifest and asset manifest SHA values.

Near-duplicate reporting must include order distance. A pHash distance at or below 6 is always a failure unless both shots share an explicit `continuity_exception_id` and human approval records the same exception.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `pytest human_archive/tests/test_visual_semantic_qa.py human_archive/tests/test_visual_qa.py human_archive/tests/test_visual_pilot_approval.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add human_archive/schemas/visual_semantic_review.schema.json human_archive/scripts/lib/visual_semantic_qa.py human_archive/scripts/review_visual_semantics.py human_archive/scripts/lib/visual_qa.py human_archive/scripts/verify_visual_assets.py human_archive/tests/test_visual_qa.py human_archive/tests/test_visual_semantic_qa.py
git commit -m "feat: verify narration-image semantic alignment"
```

### Task 6: Drive Motion and Render Order from the Aligned Contract

**Files:**
- Modify: `human_archive/scripts/lib/motion_plan.py`
- Modify: `human_archive/scripts/build_motion_clips_v2.py`
- Modify: `human_archive/scripts/render_episode_v2.py`
- Modify: `human_archive/scripts/build_subtitles_v2.py`
- Modify: `human_archive/tests/test_motion_clips_v2.py`
- Modify: `human_archive/tests/test_render_episode_v2.py`
- Modify: `human_archive/tests/test_subtitles_v2.py`

**Interfaces:**
- Consumes: current PASS visual verification, `shot_alignment_manifest.json`, projected `scene_audio_manifest.json`, sentence audio manifest.
- Produces: `motion_type_for_profile(profile: str) -> str`; frame-exact motion clips; sentence-time subtitles; rendered candidate with v5 lineage hashes.

- [ ] **Step 1: Write failing motion mapping tests**

```python
import json

import pytest
from PIL import Image

import build_motion_clips_v2
from lib.motion_plan import motion_type_for_profile


def complete_visual_build(tmp_path, motion_profile):
    build = tmp_path / "build"
    images = build / "images"
    images.mkdir(parents=True)
    Image.new("RGB", (1920, 1080), "white").save(images / "S1.jpg")
    (build / "asset_manifest.json").write_text(json.dumps({
        "assets": [{"shot_id": "S1", "order": 1, "file_path": "S1.jpg", "status": "COMPLETED"}]
    }), encoding="utf-8")
    (build / "scene_audio_manifest.json").write_text(json.dumps({
        "total_duration_sec": 10.0,
        "shots": [{"shot_id": "S1", "duration": 10.0, "startSeconds": 0.0, "endSeconds": 10.0}],
    }), encoding="utf-8")
    (build / "shot_alignment_manifest.json").write_text(json.dumps({
        "shots": [{"shot_id": "S1", "order": 1, "motion_profile": motion_profile}]
    }), encoding="utf-8")
    return build


@pytest.mark.parametrize((profile, expected), [
    ("reenactment_push", "push_in"),
    ("place_sweep", "pan_right"),
    ("route_pan", "pan_right"),
    ("diagram_reveal", "static"),
    ("artifact_close_push", "push_in"),
    ("analogy_pan", "pan_left"),
    ("atmosphere_drift", "pan_right"),
    ("host_hinge", "static"),
])
def test_motion_profile_mapping(profile, expected):
    assert motion_type_for_profile(profile) == expected


def test_motion_builder_uses_alignment_profile_not_order_cycle(tmp_path, monkeypatch):
    build = complete_visual_build(tmp_path, motion_profile="artifact_close_push")
    calls = []
    monkeypatch.setattr(build_motion_clips_v2, "verify_visual_build", lambda **kwargs: (True, []))
    monkeypatch.setattr(build_motion_clips_v2, "render_subpixel_clip", lambda **kwargs: calls.append(kwargs))
    build_motion_clips_v2.build_motion_clips(build)
    assert calls[0]["motion_type"] == "push_in"
```

- [ ] **Step 2: Run tests and verify RED**

Run: `pytest human_archive/tests/test_motion_clips_v2.py human_archive/tests/test_render_episode_v2.py human_archive/tests/test_subtitles_v2.py -v`

Expected: FAIL because v2 motion cycles by order and render does not prefer the build-local v5 contract.

- [ ] **Step 3: Implement profile mapping and long-shot two-state motion**

Read motion profile by shot ID from alignment. For a duration over 12 seconds, divide the frame range at 50% and use two continuous crop trajectories from the same image; do not create another semantic shot or alter audio timing.

- [ ] **Step 4: Prefer build-local v5 lineage**

In motion, subtitle and render scripts, resolve contracts in this exact order:

```text
build_dir / "source" / "shot_contract_v5.json"
build_dir / "shot_alignment_manifest.json"
build_dir.parent / "source" / "shot_contract_v4.json"
build_dir.parent / "source" / "shot_contract.json"
```

Subtitles read sentence timing when present; they must not infer caption timing from image count. The final render manifest records SHA values for alignment, sentence audio, scene audio, image assets, motion clips and subtitles.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `pytest human_archive/tests/test_motion_clips_v2.py human_archive/tests/test_render_episode_v2.py human_archive/tests/test_subtitles_v2.py human_archive/tests/test_build_freshness.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add human_archive/scripts/lib/motion_plan.py human_archive/scripts/build_motion_clips_v2.py human_archive/scripts/render_episode_v2.py human_archive/scripts/build_subtitles_v2.py human_archive/tests/test_motion_clips_v2.py human_archive/tests/test_render_episode_v2.py human_archive/tests/test_subtitles_v2.py
git commit -m "feat: render motion from narration-aligned profiles"
```

## Plan Acceptance

- [ ] A v5 prompt cannot replace required people, action or place with a generic archive table.
- [ ] Flow cannot connect until the current prompt alignment report passes.
- [ ] Policy retry preserves required anchors and stops after two attempts.
- [ ] The dual pilot detects both contiguous collapse and cross-episode coverage gaps.
- [ ] OCR, pHash, semantic match, visual mode and continuity all fail closed.
- [ ] Motion profile comes from the aligned scene and subtitle time comes from sentence audio.
- [ ] Legacy v4 fixtures and render fallback tests remain green.
