# Doodle Seonbi Viral Video Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 갓 쓴 스틱맨 쉽선비가 설명하는 낙서풍 애니메이션을 Human Archive의 기본 스타일로 만들고, 주제 선정부터 대본·TTS·자막·비주얼·렌더·YouTube 게시 패키지까지 자동으로 연결한다.

**Architecture:** 기존 fact/approval/hash chain과 `episode_visual_contract`를 유지하면서 `channel_profile_id`를 모든 artifact에 전파한다. 기본 `doodle_seonbi_v1`은 AI keyframe과 deterministic 쉽선비 sprite/label overlay를 합성하고, 기존 사극 K-웹툰 스타일은 `human_archive_cinematic_v1`로 격리한다. `pipeline_state.json`이 단계별 입력·출력 hash와 상태를 기록해 재개·무효화·fail-closed 동작을 담당한다.

**Tech Stack:** Python 3.13, pytest, JSON Schema, PyYAML, Jinja2, Pillow, FFmpeg/ffprobe, SQLite, 기존 OmniRoute/Flow provider adapter.

**Spec:** `docs/superpowers/specs/2026-08-27-doodle-seonbi-channel-pipeline-design.md`

## Global Constraints

- 기본 channel profile은 `doodle_seonbi_v1`, 기존 스타일은 `human_archive_cinematic_v1`이다.
- 기본 장편 profile은 목표 720초, 허용 600~840초, 1920x1080, 16:9, 25 CFR이다.
- production은 `FAIL`과 `REVIEW_REQUIRED`를 통과시키지 않는다.
- 승인 대본, fact report, profile, visual contract, audio, caption, metadata, candidate hash가 모두 연결되어야 한다.
- 이미지 모델에 readable text 생성을 맡기지 않는다. 화면 text는 renderer overlay만 생성한다.
- `doodle_seonbi_v1`은 gradient, shadow, texture, photorealism, 3D, anime, realistic face를 금지한다.
- 기존 EP01~EP03 산출물은 덮어쓰지 않고 새 build ID를 사용한다.
- 이 계획은 `2026-08-26-ep02-ep03-script-repetition-rebuild-plan.md`와 `2026-08-26-human-archive-script-image-motion-upgrade.md`의 gate와 visual lineage 작업을 선행 조건으로 삼는다.

---

## File Map

| 책임 | 파일 |
|---|---|
| 채널·delivery profile 로드 | `human_archive/config/channel_profiles.yaml`, `human_archive/scripts/lib/channel_profiles.py` |
| 주제 후보 생성·선택 | `human_archive/scripts/lib/topic_selection.py`, `human_archive/scripts/generate_topic_candidates.py` |
| 자동 상태 머신 | `human_archive/scripts/lib/pipeline_state.py`, `human_archive/scripts/run_episode_pipeline.py` |
| outline·대본 품질 | `human_archive/schemas/script_outline.schema.json`, `human_archive/scripts/lib/script_quality.py` |
| TTS 정본 caption timing | `human_archive/scripts/compile_caption_timeline.py` |
| 쉽선비 character rig | `human_archive/assets/character_rigs/doodle_seonbi_v1/`, `human_archive/scripts/lib/character_rig.py` |
| visual/overlay contract | `human_archive/schemas/episode_visual_contract_v2.schema.json`, `human_archive/schemas/overlay_event_manifest.schema.json` |
| prompt·asset 요청 | `human_archive/config/image_prompt_profiles.yaml`, `human_archive/scripts/lib/prompt_compiler.py` |
| doodle 합성·render | `human_archive/scripts/lib/doodle_overlay.py`, `human_archive/scripts/render_episode_v2.py` |
| 게시 metadata | `human_archive/schemas/publication_package.schema.json`, `human_archive/scripts/lib/publication_metadata.py` |
| release chain | `human_archive/scripts/lib/build_manifest.py`, `human_archive/scripts/postflight_release.py`, `human_archive/scripts/release_episode.py` |

---

### Task 1: Versioned Channel Profile Contract

**Files:**
- Create: `human_archive/config/channel_profiles.yaml`
- Create: `human_archive/schemas/channel_profile.schema.json`
- Create: `human_archive/scripts/lib/channel_profiles.py`
- Modify: `human_archive/config/delivery_profiles.yaml`
- Modify: `human_archive/schemas/episode_contract_v2.schema.json`
- Modify: `human_archive/templates/documentary_contract.yaml`
- Test: `human_archive/tests/test_channel_profiles.py`

**Interfaces:**
- Produces: `load_channel_profile(path: Path, profile_id: str) -> dict[str, Any]`
- Produces: `resolve_delivery_profile(delivery_config: Path, profile_id: str) -> dict[str, Any]`
- Contract field: `channel_profile_id: "doodle_seonbi_v1" | "human_archive_cinematic_v1"`

- [ ] **Step 1: Write failing profile tests**

```python
def test_doodle_is_default_and_cinematic_is_selectable():
    cfg = load_channel_profile(PROFILES, "doodle_seonbi_v1")
    assert cfg["is_default"] is True
    assert cfg["visual"]["forbidden"] == [
        "gradient", "shadow", "texture", "photorealism", "3d", "anime", "realistic_face"
    ]
    assert load_channel_profile(PROFILES, "human_archive_cinematic_v1")["is_default"] is False

def test_unknown_profile_fails_closed():
    with pytest.raises(ValueError, match="Unknown channel profile"):
        load_channel_profile(PROFILES, "missing")
```

- [ ] **Step 2: Run RED test**

Run: `python -m pytest human_archive/tests/test_channel_profiles.py -q`

Expected: FAIL because `channel_profiles.py` does not exist.

- [ ] **Step 3: Add exact profile configuration**

```yaml
schema_version: 1
default_profile_id: doodle_seonbi_v1
profiles:
  doodle_seonbi_v1:
    is_default: true
    delivery_profile_id: doodle_docu_12m
    renderer_mode: hybrid_doodle
    prompt_profile_id: doodle_flat_v1
    character_rig_id: doodle_seonbi_v1
    visual:
      aspect_ratio: "16:9"
      line_style: bold_black_imperfect_marker
      forbidden: [gradient, shadow, texture, photorealism, 3d, anime, realistic_face]
  human_archive_cinematic_v1:
    is_default: false
    delivery_profile_id: standard_docu
    renderer_mode: cinematic_keyframe
    prompt_profile_id: cinematic_seonbi_v1
    character_rig_id: null
```

Add `doodle_docu_12m` to `delivery_profiles.yaml` with `target_duration_sec: 720`, `min_duration_sec: 600`, `max_duration_sec: 840`, `fps: 25`, `width: 1920`, and `height: 1080`.

- [ ] **Step 4: Implement strict loader and schema validation**

```python
def load_channel_profile(path: Path, profile_id: str) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    validate_json(data, load_schema(SCHEMA_PATH))
    profile = data["profiles"].get(profile_id)
    if profile is None:
        raise ValueError(f"Unknown channel profile: {profile_id}")
    return {"profile_id": profile_id, **profile}
```

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest human_archive/tests/test_channel_profiles.py human_archive/tests/test_delivery_profiles.py -q`

Expected: PASS.

```bash
git add human_archive/config/channel_profiles.yaml human_archive/config/delivery_profiles.yaml human_archive/schemas/channel_profile.schema.json human_archive/schemas/episode_contract_v2.schema.json human_archive/templates/documentary_contract.yaml human_archive/scripts/lib/channel_profiles.py human_archive/tests/test_channel_profiles.py
git commit -m "feat: add versioned doodle and cinematic channel profiles"
```

---

### Task 2: Existing Episode Profile Migration Without Rewriting Artifacts

**Files:**
- Create: `human_archive/scripts/migrate_episode_profiles.py`
- Modify: `human_archive/scripts/capture_run_baseline.py`
- Test: `human_archive/tests/test_episode_profile_migration.py`

**Interfaces:**
- Consumes: episode contract JSON/YAML and baseline manifest.
- Produces: `migrate_contract_profile(contract: dict, profile_id: str) -> dict`
- Rule: existing EP01~EP03 maps to `human_archive_cinematic_v1`; new contracts default to `doodle_seonbi_v1`.

- [ ] **Step 1: Write migration tests**

```python
def test_legacy_contract_is_labeled_cinematic_without_content_changes():
    migrated = migrate_contract_profile({"schema_version": 2, "episode_id": "HA002"}, "human_archive_cinematic_v1")
    assert migrated["channel_profile_id"] == "human_archive_cinematic_v1"
    assert migrated["episode_id"] == "HA002"

def test_migration_refuses_to_overwrite_existing_different_profile():
    with pytest.raises(ValueError, match="already declares"):
        migrate_contract_profile({"channel_profile_id": "doodle_seonbi_v1"}, "human_archive_cinematic_v1")
```

- [ ] **Step 2: Run RED test**

Run: `python -m pytest human_archive/tests/test_episode_profile_migration.py -q`

Expected: FAIL because migration module is absent.

- [ ] **Step 3: Implement dry-run-first migration**

CLI:

```powershell
python human_archive/scripts/migrate_episode_profiles.py --runs human_archive/runs --legacy-profile human_archive_cinematic_v1 --dry-run
```

The CLI prints exact target files and before/after SHA-256. Without `--apply`, it writes nothing. `--apply` modifies only source contracts and writes `profile_migration_report.json`; it never touches media.

- [ ] **Step 4: Verify baselines remain byte-identical**

Run: `python human_archive/scripts/capture_run_baseline.py verify --run human_archive/runs/ep02_jang_huibin/full-v2-001 --baseline human_archive/reports/baselines/HA002-full-v2-001.json`

Expected: media hashes unchanged; only the migration report and explicitly targeted contract may differ.

- [ ] **Step 5: Run tests and commit**

```bash
git add human_archive/scripts/migrate_episode_profiles.py human_archive/scripts/capture_run_baseline.py human_archive/tests/test_episode_profile_migration.py
git commit -m "feat: label legacy Human Archive episodes with cinematic profile"
```

---

### Task 3: Five-Candidate Topic Generation and Automatic Selection

**Files:**
- Create: `human_archive/schemas/topic_candidates.schema.json`
- Create: `human_archive/scripts/lib/topic_selection.py`
- Create: `human_archive/scripts/generate_topic_candidates.py`
- Modify: `human_archive/scripts/lib/topics_inventory.py`
- Modify: `human_archive/db/seeds/topics_seed.json`
- Test: `human_archive/tests/test_topic_selection.py`

**Interfaces:**
- Produces: `score_candidate(candidate: dict, used_topics: list[dict], kpi_rows: list[dict]) -> dict`
- Produces: `select_candidate(candidates: list[dict]) -> dict`
- Output: `topic_candidates.json` with exactly five candidates and one `selected_topic_id` or `status: REVIEW_REQUIRED`.

- [ ] **Step 1: Write deterministic scoring tests**

```python
def test_selects_highest_safe_source_ready_topic():
    result = select_candidate([
        candidate("A", source=26, novelty=18, fit=18, hook=12, visual=8, risk=-2),
        candidate("B", source=10, novelty=20, fit=20, hook=15, visual=10, risk=0),
    ])
    assert result["selected_topic_id"] == "A"

def test_low_source_readiness_requires_review():
    result = select_candidate([candidate("B", source=10, novelty=20, fit=20, hook=15, visual=10, risk=0)])
    assert result["status"] == "REVIEW_REQUIRED"
    assert "SOURCE_READINESS_LOW" in result["error_codes"]
```

- [ ] **Step 2: Run RED test**

Run: `python -m pytest human_archive/tests/test_topic_selection.py -q`

Expected: FAIL because selection functions are absent.

- [ ] **Step 3: Implement scoring weights and safety thresholds**

```python
WEIGHTS = {
    "source_readiness": 30,
    "novelty": 20,
    "channel_fit": 20,
    "hook_strength": 15,
    "visualizability": 10,
    "kpi_prior": 5,
}
MIN_TOTAL = 65
MIN_SOURCE = 20
```

Reject a candidate that duplicates a `RESERVED` or `USED` topic, lacks a source acquisition plan, or has unresolved high-risk claims.

- [ ] **Step 4: Add CLI and five-candidate schema enforcement**

Run:

```powershell
python human_archive/scripts/generate_topic_candidates.py --db human_archive/db/topics_inventory.sqlite3 --profile doodle_seonbi_v1 --count 5 --output human_archive/runs/HA004/source/topic_candidates.json
```

Expected: schema-valid file with five candidates; selected topic is atomically RESERVED.

- [ ] **Step 5: Run tests and commit**

```bash
git add human_archive/schemas/topic_candidates.schema.json human_archive/scripts/lib/topic_selection.py human_archive/scripts/generate_topic_candidates.py human_archive/scripts/lib/topics_inventory.py human_archive/db/seeds/topics_seed.json human_archive/tests/test_topic_selection.py
git commit -m "feat: automate evidence-aware topic selection"
```

---

### Task 4: Resumable Automatic Pipeline State Machine

**Files:**
- Create: `human_archive/schemas/pipeline_state.schema.json`
- Create: `human_archive/scripts/lib/pipeline_state.py`
- Create: `human_archive/scripts/run_episode_pipeline.py`
- Modify: `human_archive/scripts/build_episode_v2.py`
- Test: `human_archive/tests/test_pipeline_state.py`
- Test: `human_archive/tests/test_run_episode_pipeline.py`

**Interfaces:**
- Produces: `StageResult(status: Literal["PASS", "FAIL", "REVIEW_REQUIRED"], outputs: dict[str, Path], errors: list[str])`
- Produces: `run_pipeline(contract_path: Path, build_id: str, mode: str) -> Path`
- State stages: `topic`, `research`, `outline`, `script`, `audio_caption`, `visual_plan`, `assets`, `render`, `metadata`, `release`.

- [ ] **Step 1: Write state invalidation tests**

```python
def test_changed_script_invalidates_every_downstream_stage(tmp_path):
    state = completed_state(script_hash="A" * 64)
    updated = reconcile_state(state, {"script": "B" * 64})
    assert updated["stages"]["script"]["status"] == "PENDING"
    for name in ["audio_caption", "visual_plan", "assets", "render", "metadata", "release"]:
        assert updated["stages"][name]["status"] == "INVALIDATED"

def test_review_required_stops_production():
    with pytest.raises(PipelineBlocked, match="REVIEW_REQUIRED"):
        assert_stage_can_continue("production", StageResult("REVIEW_REQUIRED", {}, ["SEMANTIC_PROVIDER_UNAVAILABLE"]))
```

- [ ] **Step 2: Run RED tests**

Run: `python -m pytest human_archive/tests/test_pipeline_state.py human_archive/tests/test_run_episode_pipeline.py -q`

Expected: FAIL because state machine modules are absent.

- [ ] **Step 3: Implement atomic state writes**

Write to `pipeline_state.json.tmp`, flush and `os.replace` to `pipeline_state.json`. Store each stage's `input_hashes`, `output_hashes`, `started_at_utc`, `finished_at_utc`, `status`, and `error_codes`.

- [ ] **Step 4: Wire existing commands through adapters**

```python
STAGES = [
    TopicStage(), ResearchStage(), OutlineStage(), ScriptStage(),
    AudioCaptionStage(), VisualPlanStage(), AssetStage(),
    RenderStage(), MetadataStage(), ReleaseStage(),
]
```

Do not shell-build command strings. Each adapter imports and calls existing Python functions. External provider processes use argument arrays.

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest human_archive/tests/test_pipeline_state.py human_archive/tests/test_run_episode_pipeline.py human_archive/tests/test_build_freshness.py -q`

```bash
git add human_archive/schemas/pipeline_state.schema.json human_archive/scripts/lib/pipeline_state.py human_archive/scripts/run_episode_pipeline.py human_archive/scripts/build_episode_v2.py human_archive/tests/test_pipeline_state.py human_archive/tests/test_run_episode_pipeline.py
git commit -m "feat: add resumable fail-closed episode orchestrator"
```

---

### Task 5: Outline-First Viral Narrative Contract Without Template Loops

**Files:**
- Create: `human_archive/schemas/script_outline.schema.json`
- Create: `human_archive/schemas/verified_script_v3.schema.json`
- Create: `human_archive/scripts/plan_script_outline.py`
- Create: `human_archive/scripts/lib/script_quality.py`
- Modify: `human_archive/scripts/lib/script_generation.py`
- Modify: `human_archive/templates/seonbi_script_prompt.j2`
- Modify: `human_archive/config/seonbi_narration_policy.yaml`
- Test: `human_archive/tests/test_script_outline.py`
- Test: `human_archive/tests/test_script_quality_v3.py`

**Interfaces:**
- Produces: `build_outline(contract, claims, sources, profile) -> dict`
- Produces: `evaluate_script_quality(script, outline, policy) -> ScriptQualityReport`
- Report error codes: `DUPLICATE_TEXT`, `NORMALIZED_DUPLICATE`, `TEMPLATE_LOOP`, `NO_INFORMATION_GAIN`, `HOOK_CONTRACT_MISSING`, `OPENING_ECHO_MISSING`, `TERM_NOT_EXPLAINED`, `DURATION_OUT_OF_RANGE`.

- [ ] **Step 1: Add failing narrative contract tests**

```python
def test_requires_modern_moment_reframe_and_echo():
    report = evaluate_script_quality(script_without_echo(), outline(), policy())
    assert report["status"] == "FAIL"
    assert "OPENING_ECHO_MISSING" in report["error_codes"]

def test_question_rhythm_is_soft_not_a_generation_loop():
    report = evaluate_script_quality(valid_script(question_gap=7), outline(), policy())
    assert report["status"] == "PASS"
    assert report["soft_scores"]["question_rhythm"] < 1.0
```

- [ ] **Step 2: Run RED tests**

Run: `python -m pytest human_archive/tests/test_script_outline.py human_archive/tests/test_script_quality_v3.py -q`

- [ ] **Step 3: Define outline and script v3 fields**

```json
{
  "hook_contract": {
    "modern_moment": "string",
    "reframe": "string",
    "core_promise": "string"
  },
  "opening_echo": {
    "opening_sentence_id": "s-001",
    "closing_sentence_id": "s-120",
    "reframe_explanation": "string"
  }
}
```

Every chapter requires `chapter_question`, `new_claim_ids`, `evidence_span_ids`, `counterpoint`, `chapter_takeaway`, and `new_information_summary`.

- [ ] **Step 4: Make duration and evidence diversity profile-aware**

Historical topics require a primary source when available plus an independent secondary analysis. Scientific/psychology topics require methods/sample/population metadata for named studies. Never force exactly three researchers when the evidence inventory does not support it.

- [ ] **Step 5: Run regression tests and commit**

Run: `python -m pytest human_archive/tests/test_script_outline.py human_archive/tests/test_script_quality_v3.py human_archive/tests/test_script_quality.py human_archive/tests/test_fact_verification_v2.py human_archive/tests/test_persona_validation.py -q`

```bash
git add human_archive/schemas/script_outline.schema.json human_archive/schemas/verified_script_v3.schema.json human_archive/scripts/plan_script_outline.py human_archive/scripts/lib/script_quality.py human_archive/scripts/lib/script_generation.py human_archive/templates/seonbi_script_prompt.j2 human_archive/config/seonbi_narration_policy.yaml human_archive/tests/test_script_outline.py human_archive/tests/test_script_quality_v3.py
git commit -m "feat: add outline-first viral narrative contract"
```

---

### Task 6: Authoritative TTS-to-Caption Timeline

**Files:**
- Create: `human_archive/schemas/caption_timeline.schema.json`
- Create: `human_archive/scripts/compile_caption_timeline.py`
- Modify: `human_archive/scripts/lib/audio_timeline.py`
- Modify: `human_archive/scripts/build_audio_master_v2.py`
- Modify: `human_archive/scripts/build_subtitles_v2.py`
- Test: `human_archive/tests/test_caption_timeline.py`

**Interfaces:**
- Consumes: approved script and `scene_audio_manifest.json` phrase timings.
- Produces: `compile_caption_timeline(script, audio_manifest) -> dict`
- Output caption: `caption_id`, `sentence_id`, `text_span`, `text_sha256`, `start_ms`, `end_ms`, `phrase_index`.

- [ ] **Step 1: Write coverage and mismatch tests**

```python
def test_caption_timeline_covers_approved_text_exactly():
    result = compile_caption_timeline(script_fixture(), audio_fixture())
    assert result["coverage"] == 1.0
    assert result["orphan_sentence_ids"] == []

def test_rejects_audio_text_not_bound_to_script():
    with pytest.raises(ValueError, match="AUDIO_SCRIPT_TEXT_MISMATCH"):
        compile_caption_timeline(script_fixture(), audio_fixture(text="변조된 문장"))
```

- [ ] **Step 2: Run RED test**

Run: `python -m pytest human_archive/tests/test_caption_timeline.py -q`

- [ ] **Step 3: Emit phrase timing from TTS provider output**

Preserve provider phrase timing when available. Otherwise use measured per-sentence WAV durations; never use character-ratio timing for production.

- [ ] **Step 4: Make ASS consume caption timeline only**

`build_subtitles_v2.py` must reject a missing/stale caption timeline in production. It must not repartition shot duration by character count.

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest human_archive/tests/test_caption_timeline.py human_archive/tests/test_audio_timeline_v2.py human_archive/tests/test_subtitles_v2.py -q`

```bash
git add human_archive/schemas/caption_timeline.schema.json human_archive/scripts/compile_caption_timeline.py human_archive/scripts/lib/audio_timeline.py human_archive/scripts/build_audio_master_v2.py human_archive/scripts/build_subtitles_v2.py human_archive/tests/test_caption_timeline.py
git commit -m "feat: derive captions from authoritative TTS timing"
```

---

### Task 7: Approved Doodle Seonbi Character Rig

**Files:**
- Create: `human_archive/schemas/character_rig_manifest.schema.json`
- Create: `human_archive/assets/character_rigs/doodle_seonbi_v1/rig_manifest.json`
- Create: `human_archive/assets/character_rigs/doodle_seonbi_v1/reference.png`
- Create: `human_archive/assets/character_rigs/doodle_seonbi_v1/layers/*.png`
- Create: `human_archive/scripts/lib/character_rig.py`
- Create: `human_archive/scripts/verify_character_rig.py`
- Test: `human_archive/tests/test_character_rig.py`

**Interfaces:**
- Produces: `load_rig(rig_dir: Path) -> CharacterRig`
- Produces: `resolve_pose(rig: CharacterRig, pose: str, expression: str) -> list[RigLayer]`
- Required poses: `neutral`, `point`, `write`, `walk`, `think`, `react`.
- Required expressions: `neutral`, `confused`, `surprised`, `serious`, `warm`.

- [ ] **Step 1: Write rig integrity tests**

```python
def test_rig_has_required_pose_expression_matrix():
    rig = load_rig(FIXTURE_RIG)
    for pose in REQUIRED_POSES:
        for expression in REQUIRED_EXPRESSIONS:
            assert resolve_pose(rig, pose, expression)

def test_rig_rejects_hash_mismatch(tmp_path):
    rig_dir = copy_fixture_rig(tmp_path)
    (rig_dir / "layers" / "hat.png").write_bytes(b"changed")
    with pytest.raises(ValueError, match="RIG_LAYER_HASH_MISMATCH"):
        load_rig(rig_dir)
```

- [ ] **Step 2: Run RED test**

Run: `python -m pytest human_archive/tests/test_character_rig.py -q`

- [ ] **Step 3: Create and approve the minimum rig pack**

Use transparent 1920x1080-aligned PNG layers with fixed anchors for head, gat, body, arms, brows, eyes, mouth, brush/tablet, and motion accents. `reference.png` shows neutral front, 3/4, and side poses on white. Record every layer SHA-256 in `rig_manifest.json`.

- [ ] **Step 4: Implement deterministic composition validation**

Reject layers with non-transparent background, dimensions outside manifest, missing anchor, or colors outside the profile palette beyond a configured antialias tolerance.

- [ ] **Step 5: Run visual verification and commit**

Run: `python human_archive/scripts/verify_character_rig.py --rig human_archive/assets/character_rigs/doodle_seonbi_v1`

Expected: `PASS`, zero missing layers, zero hash mismatches, zero opaque-background violations.

```bash
git add human_archive/schemas/character_rig_manifest.schema.json human_archive/assets/character_rigs/doodle_seonbi_v1 human_archive/scripts/lib/character_rig.py human_archive/scripts/verify_character_rig.py human_archive/tests/test_character_rig.py
git commit -m "feat: add approved doodle Seonbi character rig"
```

---

### Task 8: Caption-to-Scene Continuity and Overlay Event Contract

**Files:**
- Create: `human_archive/schemas/episode_visual_contract_v2.schema.json`
- Create: `human_archive/schemas/overlay_event_manifest.schema.json`
- Create: `human_archive/templates/seonbi_visual_planner_prompt.j2`
- Modify: `human_archive/scripts/lib/visual_planning.py`
- Modify: `human_archive/scripts/plan_episode_visuals.py`
- Modify: `human_archive/scripts/validate_visual_contract.py`
- Test: `human_archive/tests/test_doodle_visual_contract.py`
- Test: `human_archive/tests/test_scene_continuity.py`

**Interfaces:**
- Produces: `build_visual_contract_v2(script, captions, scene_specs, profile, rig) -> dict`
- Scene strategy enum: `new_keyframe`, `hold`, `overlay_only`, `detail_crop`, `approved_reuse`.
- Overlay types: `character_pose`, `expression`, `arrow`, `label`, `thought_bubble`, `object_reveal`, `progression`.

- [ ] **Step 1: Write continuity tests**

```python
def test_three_related_captions_can_hold_one_scene():
    contract = build_visual_contract_v2(script(), captions(3), [held_scene(3)], profile(), rig())
    assert len(contract["scenes"]) == 1
    assert len(contract["overlay_events"]) == 3

def test_one_prompt_per_caption_is_not_required():
    errors = validate_visual_contract(contract_with_100_captions_30_scenes())
    assert "CAPTION_SCENE_COUNT_MISMATCH" not in errors
```

- [ ] **Step 2: Run RED tests**

Run: `python -m pytest human_archive/tests/test_doodle_visual_contract.py human_archive/tests/test_scene_continuity.py -q`

- [ ] **Step 3: Add doodle visual beat taxonomy**

Support `concept_text_frame`, `evolution_sequence`, `labeled_diagram`, `stick_figure_reaction`, `villain_personified`, `globe_creatures`, `historical_reconstruction`, `source_card`, and `modern_mirror`. The planner chooses background palette by beat/tone and never embeds final readable text in the AI prompt.

- [ ] **Step 4: Bind profile and rig hashes**

Every scene stores `channel_profile_sha256`; every character overlay stores `rig_id`, `rig_sha256`, `pose`, `expression`, `anchor`, `scale`, and `z_index`.

- [ ] **Step 5: Run tests and commit**

```bash
git add human_archive/schemas/episode_visual_contract_v2.schema.json human_archive/schemas/overlay_event_manifest.schema.json human_archive/templates/seonbi_visual_planner_prompt.j2 human_archive/scripts/lib/visual_planning.py human_archive/scripts/plan_episode_visuals.py human_archive/scripts/validate_visual_contract.py human_archive/tests/test_doodle_visual_contract.py human_archive/tests/test_scene_continuity.py
git commit -m "feat: add continuity-aware doodle visual contracts"
```

---

### Task 9: Single Profile-Aware Prompt Compiler

**Files:**
- Create: `human_archive/config/image_prompt_profiles.yaml`
- Modify: `human_archive/scripts/lib/prompt_compiler.py`
- Modify: `human_archive/scripts/compile_image_requests.py`
- Modify: `human_archive/schemas/image_request_manifest.schema.json`
- Modify: `human_archive/scripts/generate_flow_assets_v2.py`
- Test: `human_archive/tests/test_doodle_prompt_compiler.py`

**Interfaces:**
- Produces: `compile_scene_request(scene, profile, provider_capabilities) -> dict`
- Doodle request excludes renderer-owned `overlay_events` and text.
- Request records: `profile_id`, `profile_sha256`, `compiler_version`, `positive_prompt`, `negative`, `reference_assets`, `request_sha256`.

- [ ] **Step 1: Write prompt lock tests**

```python
def test_doodle_prompt_has_style_anchor_and_lock():
    request = compile_scene_request(scene(), doodle_profile(), flow_caps())
    assert request["positive_prompt"].startswith("Hand-drawn 2D doodle cartoon animation")
    for banned in ["no gradients", "no shadows", "no textures", "no photorealism", "no 3D"]:
        assert banned in request["negative"]["items"]

def test_doodle_prompt_does_not_ask_model_to_draw_labels():
    request = compile_scene_request(scene(label="왕권"), doodle_profile(), flow_caps())
    assert "왕권" not in request["positive_prompt"]
```

- [ ] **Step 2: Run RED test**

Run: `python -m pytest human_archive/tests/test_doodle_prompt_compiler.py -q`

- [ ] **Step 3: Define separate prompt profiles**

`doodle_flat_v1` contains the flat palette/style lock. `cinematic_seonbi_v1` imports the existing historical webtoon rules. Mixing forbidden constraints across profiles raises `PROFILE_CONSTRAINT_CONFLICT`.

- [ ] **Step 4: Remove production string assembly from episode scripts**

Route `build_ep02_flow_prompts.py`, `build_ep03_flow_prompts.py`, `batch_flow_all_ep02.py`, `batch_flow_all_ep03.py`, `generate_flow_ep02_v2.py`, and `run_flow_automation.py` through the canonical manifest or mark their direct builders `legacy_only` and `release_eligible: false`.

- [ ] **Step 5: Run regression tests and commit**

Run: `python -m pytest human_archive/tests/test_doodle_prompt_compiler.py human_archive/tests/test_prompt_compiler.py human_archive/tests/test_image_request_manifest.py human_archive/tests/test_generation_lineage.py -q`

```bash
git add human_archive/config/image_prompt_profiles.yaml human_archive/scripts/lib/prompt_compiler.py human_archive/scripts/compile_image_requests.py human_archive/schemas/image_request_manifest.schema.json human_archive/scripts/generate_flow_assets_v2.py human_archive/scripts/build_ep02_flow_prompts.py human_archive/scripts/build_ep03_flow_prompts.py human_archive/scripts/batch_flow_all_ep02.py human_archive/scripts/batch_flow_all_ep03.py human_archive/scripts/generate_flow_ep02_v2.py human_archive/scripts/run_flow_automation.py human_archive/tests/test_doodle_prompt_compiler.py
git commit -m "feat: compile profile-locked doodle image requests"
```

---

### Task 10: Deterministic Doodle Overlay Renderer

**Files:**
- Create: `human_archive/scripts/lib/doodle_overlay.py`
- Create: `human_archive/scripts/build_doodle_overlay_track.py`
- Modify: `human_archive/scripts/lib/motion_engine_v3.py`
- Modify: `human_archive/scripts/build_motion_clips_v3.py`
- Modify: `human_archive/scripts/render_episode_v2.py`
- Test: `human_archive/tests/test_doodle_overlay.py`
- Test: `human_archive/tests/test_doodle_render_smoke.py`

**Interfaces:**
- Produces: `render_overlay_frame(event, rig, canvas_size, frame_index) -> PIL.Image.Image`
- Produces: `build_overlay_track(contract_path: Path, output_path: Path) -> Path`
- Animation curves are deterministic functions of frame index at 25fps.

- [ ] **Step 1: Write pixel and timing tests**

```python
def test_label_is_renderer_owned_and_inside_safe_area():
    frame = render_overlay_frame(label_event("왕권"), rig(), (1920, 1080), 0)
    assert frame.getbbox() is not None
    assert alpha_bbox(frame).right <= 1760

def test_same_event_and_frame_are_byte_deterministic():
    a = render_overlay_frame(point_event(), rig(), (1920, 1080), 37)
    b = render_overlay_frame(point_event(), rig(), (1920, 1080), 37)
    assert a.tobytes() == b.tobytes()
```

- [ ] **Step 2: Run RED tests**

Run: `python -m pytest human_archive/tests/test_doodle_overlay.py human_archive/tests/test_doodle_render_smoke.py -q`

- [ ] **Step 3: Implement limited animation vocabulary**

Implement eyebrow/mouth swap, 4~8px breathing bob, arm pose crossfade, arrow draw-on, label pop, thought bubble scale-in, and object reveal. Avoid continuous full-body interpolation in v1.

- [ ] **Step 4: Compose keyframe, motion, overlay, subtitles in one frame clock**

The render plan uses integer `start_frame`/`end_frame`. Generate lossless or direct filtergraph intermediates; do not concatenate VFR clips. Verify decoded `r_frame_rate == avg_frame_rate == 25/1`.

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest human_archive/tests/test_doodle_overlay.py human_archive/tests/test_doodle_render_smoke.py human_archive/tests/test_motion_engine_v3.py human_archive/tests/test_render_episode_v2.py -q`

```bash
git add human_archive/scripts/lib/doodle_overlay.py human_archive/scripts/build_doodle_overlay_track.py human_archive/scripts/lib/motion_engine_v3.py human_archive/scripts/build_motion_clips_v3.py human_archive/scripts/render_episode_v2.py human_archive/tests/test_doodle_overlay.py human_archive/tests/test_doodle_render_smoke.py
git commit -m "feat: render deterministic doodle character overlays"
```

---

### Task 11: Claim-Safe YouTube Publication Package

**Files:**
- Create: `human_archive/schemas/publication_package.schema.json`
- Create: `human_archive/config/publication_policy.yaml`
- Create: `human_archive/templates/publication_metadata_prompt.j2`
- Create: `human_archive/scripts/lib/publication_metadata.py`
- Create: `human_archive/scripts/generate_publication_package.py`
- Test: `human_archive/tests/test_publication_metadata.py`

**Interfaces:**
- Produces: `generate_publication_package(script, claims, fact_report, candidate, policy, provider) -> dict`
- Produces: `validate_publication_claims(package, script, claims) -> list[str]`
- Hard limits: title 100 chars, description 5000 chars, hashtags <= 8, tags canonical string <= 500 chars.
- Internal target: selected title <= 70 chars.

- [ ] **Step 1: Write metadata safety tests**

```python
def test_rejects_title_stronger_than_approved_claim():
    errors = validate_publication_claims(
        package(title="실록이 숨긴 확정적 살인 증거"), script(), claims_without_murder()
    )
    assert "UNSUPPORTED_PUBLICATION_CLAIM" in errors

def test_tags_focus_on_names_and_misspellings():
    result = normalize_tags(["황현", "매천 황현", "매천야록", "매천 야록", "viral history"])
    assert "viral history" not in result
    assert len(",".join(result)) <= 500
```

- [ ] **Step 2: Run RED test**

Run: `python -m pytest human_archive/tests/test_publication_metadata.py -q`

- [ ] **Step 3: Generate three titles and score them**

Scores: accuracy 40, clarity 20, curiosity 20, mobile readability 10, topic keyword 10. Any title with an unsupported claim is excluded before scoring.

- [ ] **Step 4: Bind publication package to current artifacts**

Store SHA-256 for approved script, claim inventory, fact report, channel profile, thumbnail brief, candidate video, and metadata prompt policy. A changed candidate or script invalidates the package.

- [ ] **Step 5: Run tests and commit**

```bash
git add human_archive/schemas/publication_package.schema.json human_archive/config/publication_policy.yaml human_archive/templates/publication_metadata_prompt.j2 human_archive/scripts/lib/publication_metadata.py human_archive/scripts/generate_publication_package.py human_archive/tests/test_publication_metadata.py
git commit -m "feat: generate claim-safe YouTube publication packages"
```

---

### Task 12: Profile, Content, and Metadata Release Gates

**Files:**
- Modify: `human_archive/schemas/build_manifest.schema.json`
- Modify: `human_archive/schemas/release_report.schema.json`
- Modify: `human_archive/scripts/lib/build_manifest.py`
- Modify: `human_archive/scripts/postflight_release.py`
- Modify: `human_archive/scripts/release_episode.py`
- Create: `human_archive/scripts/qa_doodle_style.py`
- Test: `human_archive/tests/test_doodle_style_gate.py`
- Test: `human_archive/tests/test_publication_release_binding.py`

**Interfaces:**
- Produces: `verify_doodle_style(frames, profile, rig) -> DoodleStyleReport`
- Release requires checks: `profile_binding`, `script_repetition`, `caption_coverage`, `doodle_style`, `character_rig`, `publication_claims`, `candidate_hash`.

- [ ] **Step 1: Add negative-control tests**

```python
@pytest.mark.parametrize("violation", ["gradient", "shadow", "photorealism", "model_text"])
def test_doodle_release_rejects_style_violation(violation):
    ok, report = verify_fixture_with_violation(violation)
    assert ok is False
    assert report["checks"]["doodle_style"]["status"] == "FAIL"

def test_release_rejects_stale_publication_package():
    with pytest.raises(ValueError, match="PUBLICATION_PACKAGE_STALE"):
        promote_release(candidate_hash="B" * 64, package_hash_binding="A" * 64)
```

- [ ] **Step 2: Run RED tests**

Run: `python -m pytest human_archive/tests/test_doodle_style_gate.py human_archive/tests/test_publication_release_binding.py -q`

- [ ] **Step 3: Implement sampled and exhaustive QA split**

Run deterministic checks on every frame event and asset. Run semantic/visual model checks on opening, every chapter boundary, random body samples with a recorded seed, and outro. Model unavailable returns `REVIEW_REQUIRED`.

- [ ] **Step 4: Extend hash chain and approval schemas**

The release approval must sign `candidate_video_sha256`, `release_report_sha256`, `publication_package_sha256`, and `channel_profile_sha256`. Missing or non-hex placeholders fail.

- [ ] **Step 5: Run regression tests and commit**

Run: `python -m pytest human_archive/tests/test_doodle_style_gate.py human_archive/tests/test_publication_release_binding.py human_archive/tests/test_atomic_release_gate.py human_archive/tests/test_postflight_release.py human_archive/tests/test_release_gate_v2.py -q`

```bash
git add human_archive/schemas/build_manifest.schema.json human_archive/schemas/release_report.schema.json human_archive/scripts/lib/build_manifest.py human_archive/scripts/postflight_release.py human_archive/scripts/release_episode.py human_archive/scripts/qa_doodle_style.py human_archive/tests/test_doodle_style_gate.py human_archive/tests/test_publication_release_binding.py
git commit -m "feat: gate doodle style and publication metadata at release"
```

---

### Task 13: HA002 Doodle Pilot, Then EP02/EP03 Full Rebuild

**Files:**
- Create: `human_archive/runs/ep02_jang_huibin/doodle-pilot-v1/source/episode_contract.yaml`
- Create: `human_archive/runs/ep02_jang_huibin/doodle-pilot-v1/approvals/visual_pilot_review.json`
- Create: `human_archive/reports/doodle-pilot/HA002-doodle-pilot-v1-report.json`
- Create after pilot approval: `human_archive/runs/ep02_jang_huibin/full-v4-001/`
- Create after HA002 full approval: `human_archive/runs/ep03_maecheon/full-v4-001/`
- Modify: `human_archive/README.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: newly approved, repetition-free EP02/EP03 scripts from the existing rebuild plan.
- Produces: 60~90 second HA002 pilot spanning hook, body/source explanation, and modern-mirror outro.
- Produces after approval: new `full-v4-*` builds; old v2/v3 remains read-only baseline.

- [ ] **Step 1: Confirm upstream script gates before media generation**

Run:

```powershell
python -m pytest human_archive/tests/test_script_repetition_gate.py human_archive/tests/test_script_quality_v3.py human_archive/tests/test_script_approval_binding.py -q
```

Expected: PASS. Do not generate pilot media if EP02's current 33/180 legacy script is still the approved input.

- [ ] **Step 2: Run automatic HA002 pilot through candidate**

```powershell
python human_archive/scripts/run_episode_pipeline.py --contract human_archive/runs/ep02_jang_huibin/doodle-pilot-v1/source/episode_contract.yaml --build-id doodle-pilot-v1 --mode production --stop-after candidate
```

Expected: candidate, contact sheet, style report, content report, publication-package draft, and `pipeline_state.json` are generated; release remains pending.

- [ ] **Step 3: Approve the pilot against exact hashes**

Reviewer checks character identity, text legibility, scene continuity, historical depiction, victim dignity, motion comfort, and opening/body/outro rhythm. Store exact candidate, profile, rig, visual-contract and contact-sheet hashes.

- [ ] **Step 4: Build HA002 full-v4 and calibrate**

Run full production pipeline. Compare against cinematic baseline for first 15s/30s clarity, number of unique AI assets, overlay reuse, render time, and reviewer issue count. Do not claim higher CTR before publication data exists.

- [ ] **Step 5: Build HA003 only after HA002 checkpoint passes**

Use the same profile and rig version. Any profile/rig changes learned from HA002 require a new version and invalidate HA003 downstream artifacts.

- [ ] **Step 6: Run full regression suite and commit documentation**

Run:

```powershell
python -m pytest human_archive/tests -q
python human_archive/scripts/run_episode_pipeline.py --contract human_archive/runs/ep02_jang_huibin/full-v4-001/source/episode_contract.yaml --build-id full-v4-001 --mode production --resume
```

```bash
git add human_archive/README.md CLAUDE.md human_archive/reports/doodle-pilot/HA002-doodle-pilot-v1-report.json
git commit -m "docs: record Doodle Seonbi pilot and rollout procedure"
```

---

## Rollout Checkpoints

### Checkpoint 1 - Contracts and fail-closed automation

Tasks 1~6 complete. New contracts carry profile IDs, five topic candidates are scored, pipeline resume/invalidation works, repetition-free script and authoritative captions pass. No images are generated before this checkpoint.

### Checkpoint 2 - Doodle identity and scene continuity

Tasks 7~9 complete. Rig reference, visual contract, overlay events, canonical prompts, and request hashes are reviewed on a dry-run manifest. No full render before this checkpoint.

### Checkpoint 3 - 60~90 second HA002 pilot

Tasks 10~12 complete. Opening, body, source card, and modern mirror are included. Doodle style and release negative controls all fail correctly; pilot candidate receives exact-hash visual approval.

### Checkpoint 4 - Full production rollout

Task 13 completes HA002 `full-v4-001`, then HA003 `full-v4-001`. Existing cinematic finals remain comparison artifacts and are never overwritten.

## Final Verification Commands

```powershell
python -m pytest human_archive/tests/test_channel_profiles.py human_archive/tests/test_topic_selection.py human_archive/tests/test_pipeline_state.py -q
python -m pytest human_archive/tests/test_script_outline.py human_archive/tests/test_script_quality_v3.py human_archive/tests/test_caption_timeline.py -q
python -m pytest human_archive/tests/test_character_rig.py human_archive/tests/test_doodle_visual_contract.py human_archive/tests/test_scene_continuity.py -q
python -m pytest human_archive/tests/test_doodle_prompt_compiler.py human_archive/tests/test_doodle_overlay.py human_archive/tests/test_doodle_render_smoke.py -q
python -m pytest human_archive/tests/test_publication_metadata.py human_archive/tests/test_doodle_style_gate.py human_archive/tests/test_publication_release_binding.py -q
python -m pytest human_archive/tests -q
```

## Explicit Non-Goals

- YouTube 계정 로그인·업로드·예약 공개 자동화.
- 댓글·커뮤니티·광고·수익화 자동 운영.
- frame-by-frame 캐릭터 애니메이션 또는 물리 기반 관절 리깅.
- Doodle 실패 시 cinematic으로 조용히 대체하는 fallback.
- 충분한 publishable 표본 전에 “viral 성과 향상”을 확정하는 것.
