# HA002 Narrative-First Sample v4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 현재 지루한 prefix 샘플을 폐기하고, 근거가 허용하는 질문과 사건 spine을 따라가는 독립 3분 HA002 샘플을 `sample-3m-v4-001`로 생성한다.

**Architecture:** 기존 v2/v3 artifact와 실행 경로는 읽기 전용으로 보존한다. 신규 v4는 `narrative_outline_v1` → `verified_script_v3` → fact/persona/narrative report → fact approval → v3 projection → provisional M4 TTS → post-TTS narrative timing report와 audio-first editorial approval → 신규 이미지·자막·모션·렌더의 단방향 DAG를 사용한다.

**Tech Stack:** Python 3.12, pytest, jsonschema, PyYAML, Pillow, ffmpeg/ffprobe, SuperTonic3 HTTP `M4` voice.

**Spec:** [설계 문서](D:/module/bible/docs/superpowers/specs/2026-08-31-ha002-narrative-first-script-design.md)

## Global Constraints

- 기존 `sample-3m-v3-001` MP4와 자산은 변경하지 않는다.
- 신규 출력 루트는 `D:\module\bible\human_archive\runs\ep02_jang_huibin\sample-3m-v4-001`이다.
- `promise_answerability`가 `SUPPORTED`가 아니면 대본 생성과 이미지 생성을 중단한다.
- 현재 `CLM-JH-003`, `CLM-JH-006`, `CLM-JH-007`은 정상 source snapshot과 사람 fact 승인을 얻기 전까지 사용할 수 없다.
- `negative_evidence`는 명시한 공식 기록 corpus에서 장면을 찾지 못했다는 범위만 말하고 비존재 증명으로 확대하지 않는다.

## File Map

- Create: `human_archive/schemas/narrative_outline_v1.schema.json`, `human_archive/schemas/verified_script_v3.schema.json`, `human_archive/schemas/narrative_quality_report_v1.schema.json`, `human_archive/schemas/narrative_editorial_approval_v1.schema.json`, `human_archive/schemas/artifact_envelope_v1.schema.json`, `human_archive/schemas/selection_manifest_v1.schema.json`.
- Create: `human_archive/scripts/lib/artifact_lineage.py`, `narrative_outline.py`, `narrative_quality.py`, `script_projection.py`, `editorial_approval.py`, `supertonic3_runtime.py`.
- Create CLIs: `compile_narrative_outline.py`, `generate_verified_script_v3.py`, `validate_narrative_quality.py`, `compile_context_sample_v4.py`, `build_script_common_projection.py`, `record_narrative_editorial_approval.py`, `build_sample_3m_v4.py`, `verify_sample_v4.py`.
- Modify: `requirements.txt`, `human_archive/scripts/lib/provenance.py`, `fact_review_approval.py`, `build_sentence_audio_master.py`, `tts_provider.py`, `build_subtitles_v2.py`, `build_motion_clips_v3.py`, `render_pilot_v3.py`, `postflight_release.py`, `human_archive/README.md`, `CLAUDE.md`.

## Task 1: Artifact contracts and lineage primitives

**Files:** Create human_archive/schemas/narrative_outline_v1.schema.json, verified_script_v3.schema.json, narrative_quality_report_v1.schema.json, narrative_editorial_approval_v1.schema.json, artifact_envelope_v1.schema.json, selection_manifest_v1.schema.json; create human_archive/scripts/lib/artifact_lineage.py; create human_archive/tests/test_artifact_lineage.py.

**Interfaces:**
- canonical_payload_sha256(payload: Any) -> str
- build_envelope(*, artifact_id: str, artifact_type: str, schema_version: str, scope_kind: str, scope_id: str, run_id: str, payload_sha256: str, parents: list[dict[str, str]], generator: dict[str, str], policy_sha256: str, created_at: str) -> dict[str, Any]
- envelope_core_sha256(envelope: dict[str, Any]) -> str
- write_sidecar(target_path: Path, envelope: dict[str, Any]) -> Path
- validate_parent_matrix(artifact_type: str, parents: list[dict[str, str]], scope: dict[str, str]) -> list[str]
- publish_staged_run(staging_dir: Path, final_dir: Path, inventory: list[dict[str, str]]) -> Path

**TDD and implementation:**
1. Add failing tests for key-order-independent canonical hashes, uppercase SHA-256, missing parent/envelope-core digests, and self-referential COMPLETE rejection. Run python -m pytest human_archive/tests/test_artifact_lineage.py -q; the new tests must fail before implementation.
2. Implement deterministic canonical JSON (RFC 8785-compatible), exact-byte hashing for legacy JSON sidecars, and envelope-core hashing that excludes created_at and the envelope's own digest.
3. Implement the artifact parent matrix and sidecars containing target path, file SHA-256, scope, run ID, schema/version, parents, generator, and policy digest.
4. Implement staging plus content-addressed storage (CAS), reject path escapes/reparse-point escapes, raise CONCURRENT_PUBLISH when the final run already exists, and write COMPLETE last.
5. Re-run the focused test and require PASS. Commit as feat: add v4 artifact lineage contracts.

Schemas must set additionalProperties: false where the contract is closed; every parent must carry both payload_sha256 and envelope_core_sha256; COMPLETE is not included in its own inventory.

## Task 2: Fact-scoped story packet and narrative outline

**Files:** Create human_archive/scripts/lib/narrative_outline.py, human_archive/scripts/compile_narrative_outline.py, human_archive/templates/ha002_power_mystery_outline_prompt.j2, human_archive/tests/test_narrative_outline.py, and deterministic fixtures under human_archive/tests/fixtures/ha002_v4/.

**Interfaces:**
- build_story_evidence_packet(source_snapshot_path: Path, claim_inventory_path: Path, policy_path: Path) -> dict[str, Any]
- validate_promise_answerability(packet: dict[str, Any], outline: dict[str, Any]) -> list[str]
- validate_narrative_outline(outline: dict[str, Any], packet: dict[str, Any]) -> list[str]
- compile_narrative_outline(packet: dict[str, Any], output_path: Path) -> Path

**TDD and implementation:**
1. Add a fixture with blocked claims and a test proving a blocked claim cannot be used as a factual promise or generate an image. Add a second test proving an outline with no supported claim cannot pass its hook.
2. Run python -m pytest human_archive/tests/test_narrative_outline.py -q; it must fail before implementation.
3. Normalize the packet into timeline, entities, documented events, allegations, negative evidence, interpretations, attribution, and allowed visual modes. Mark CLM-JH-003, CLM-JH-006, and CLM-JH-007 as BLOCKED until a valid source snapshot and human fact approval exist.
4. Compile exactly four core slots: TRIGGER, DECISION_CHANGE, RECORDED_JUSTIFICATION, and FINAL_ORDER, with typed causal/contrast/uncertainty edges. Keep LOOP_HOOK separate from LOOP_CORE; include target-specific question, promise, answer, reveal, and recall fields. Reject source-commentary filler and unsupported universal claims.
5. Require promise_answerability=SUPPORTED before script or visual generation. Re-run the focused tests and commit as feat: add fact-scoped narrative outline compiler.

Example test shape:
```python
def test_blocked_claim_cannot_be_promised(packet_with_blocked_claim):
    outline = outline_using(packet_with_blocked_claim, claim_id="CLM-JH-003")
    assert "promise_answerability" in validate_narrative_outline(outline, packet_with_blocked_claim)
```

## Task 3: Verified script v3 and legacy projection

**Files:** Create human_archive/scripts/generate_verified_script_v3.py, human_archive/scripts/build_script_common_projection.py, human_archive/scripts/lib/script_projection.py, human_archive/tests/test_verified_script_v3.py, human_archive/tests/test_script_projection_v3.py; use the schema from Task 1.

**Interfaces:**
- validate_verified_script(script: dict[str, Any], outline: dict[str, Any], packet: dict[str, Any]) -> list[str]
- project_script_common(script: dict[str, Any], output_path: Path) -> Path
- load_projected_script(path: Path) -> dict[str, Any]

**TDD and implementation:**
1. Add failing tests for absent content_mode, unknown entity references, duplicate order, and a projection whose parent digest differs from the verified script.
2. Run python -m pytest human_archive/tests/test_verified_script_v3.py human_archive/tests/test_script_projection_v3.py -q; expect FAIL.
3. Require the common fields used by existing consumers plus narrative fields (narrative_role, content_mode, target_question, target_promise, target_answer, reveal, recall, entity_ids, claim_ids, and source_refs). Keep additionalProperties: false; unknown semantic findings become REVIEW_REQUIRED, never silent PASS.
4. Emit a legacy-consumer-compatible common projection with an adapter version and v3 payload/envelope digests. Do not allow direct v3-to-TTS bypass; all downstream consumers read the projection and its sidecar.
5. Run focused tests and commit as feat: add verified script v3 projection.

## Task 4: Preflight and post-TTS narrative quality gates

**Files:** Create human_archive/scripts/lib/narrative_quality.py, human_archive/scripts/validate_narrative_quality.py, human_archive/tests/test_narrative_quality.py.

**Interfaces:**
- run_structure_preflight(script_path: Path, outline_path: Path) -> dict[str, Any]
- build_post_tts_quality_report(script_path: Path, outline_path: Path, tts_manifest_path: Path) -> dict[str, Any]
- write_narrative_quality_report(report: dict[str, Any], output_path: Path) -> Path

**TDD and implementation:**
1. Add failing tests proving the hook deadline is the end time of the final required hook proposition (a proposition ending at 15.9 seconds fails a 15-second deadline), and that metadata laundering is REVIEW_REQUIRED.
2. Run python -m pytest human_archive/tests/test_narrative_quality.py -q; expect FAIL.
3. Keep pre-TTS checks deterministic and structural; do not claim speech-time compliance before TTS. After TTS, measure each sentence's start, end, and duration from the authoritative manifest.
4. Enforce hook/core deadlines, information gaps of 10–12 seconds with a 15-second maximum, methodology/reflection limits, story/evidence ratio of at least 85%, total duration 170–190 seconds, and sentence rhythm. Use the last required proposition end for deadline calculations.
5. Preserve semantic findings as REVIEW_REQUIRED; only deterministic failures become FAIL. Run the focused tests and commit as feat: add post-tts narrative quality gates.

## Task 5: Independent v4 sample compiler

Files: Create human_archive/scripts/compile_context_sample_v4.py, human_archive/schemas/context_sample_build_v2.schema.json, human_archive/tests/test_context_sample_v4_compiler.py. Keep existing compiler and schema unchanged for legacy runs.

Interfaces:
- compile_context_sample_v4(*, outline_path: Path, script_path: Path, source_snapshot_path: Path, claim_inventory_path: Path, output_build: Path) -> Path
- validate_sample_v4_manifest(manifest_path: Path, run_root: Path) -> list[str]
- assert_no_legacy_asset_parent(manifest: dict[str, Any], legacy_roots: list[Path]) -> None

TDD and implementation:
1. Add a failing test proving shot order follows the outline typed spine rather than prefix slicing, and a test rejecting a full-v6 report, old selected_from_full field, or asset path from v2/v3/context-final.
2. Run python -m pytest human_archive/tests/test_context_sample_v4_compiler.py -q; expect FAIL.
3. Emit IDs such as HA002-V4-S001, scope_kind quick_3m, exact scope_id and run_id, and a manifest that records every source digest and adapter version. Do not copy reports, images, audio, or motion assets from earlier runs.
4. Write only to a staging directory under sample-3m-v4-001; validate the manifest and parent matrix before publication. Run focused tests and commit as feat: add independent v4 sample compiler.

## Task 6: Fact approval, editorial approval, and M4 TTS

Files: Create human_archive/scripts/lib/editorial_approval.py, human_archive/scripts/record_narrative_editorial_approval.py, human_archive/scripts/lib/supertonic3_runtime.py, and tests; modify human_archive/scripts/fact_review_approval.py, build_sentence_audio_master.py, and tts_provider.py.

Interfaces:
- validate_fact_review_v2_scope(approval_path: Path, *, source_snapshot_path: Path, claim_inventory_path: Path) -> dict[str, Any]
- record_narrative_editorial_approval(report_path: Path, approval_input: dict[str, Any], output_path: Path) -> Path
- ensure_server(base_url: str, launcher_path: Path, startup_timeout_sec: float = 60.0) -> dict[str, Any]
- build_sentence_audio_master_v4(projection_path: Path, fact_approval_path: Path, build_dir: Path, voice: str = "M4", auto_start_server: bool = True) -> Path

TDD and implementation:
1. Add failing tests proving audio-first approval is mandatory, unsupported fact scope blocks TTS, and runtime startup is attempted only after a health check fails.
2. Run the focused tests; expect FAIL.
3. Keep fact approval separate from narrative/editorial approval. Require seven narrative scores, audio_first=true, exposure and recall assessments, and mandatory recall checks for beats 2 and 3. Do not treat a numeric score as clearance when its rubric status is REVIEW_REQUIRED.
4. Check GET /health first; if unhealthy, launch D:\module\bible\bible_healing\scripts\start_supertonic3_server.ps1 hidden, poll for up to 60 seconds, and record the launcher path and health evidence. Use only SuperTonic3 voice M4 and never fall back to another tone or prior WAV.
5. Produce provisional sentence audio only from the v3 projection, valid fact approval, and M4 voice. Run focused tests and commit as feat: gate v4 TTS on approvals and M4 runtime.

## Task 7: New images, captions, motion, and render

Files: Create human_archive/scripts/verify_sample_zero_image_reuse.py and human_archive/tests/test_v4_visual_isolation.py; modify build_subtitles_v2.py, build_motion_clips_v3.py, and render_pilot_v3.py.

Interfaces:
- build_v4_visual_requests(script_path: Path, tts_manifest_path: Path, outline_path: Path, output_dir: Path) -> Path
- build_ass_subtitles(build_dir: Path, output_file: Path | None = None, *, font_size: int = 108, max_chars_per_line: int = 22) -> Path
- verify_sample_zero_reuse(run_dir: Path, legacy_roots: list[Path]) -> dict[str, Any]
- render_v4_candidate(run_dir: Path) -> Path

TDD and implementation:
1. Add failing tests for the 108-point subtitle contract and a legacy image SHA appearing in the v4 manifest.
2. Run python -m pytest human_archive/tests/test_v4_visual_isolation.py -q; expect FAIL.
3. Create one visual request per beat/shot with scene semantics, entity/claim refs, negative prompts, and authoritative TTS start/end times. Require newly generated assets, unique SHA-256 within v4, and no legacy ID/path or legacy SHA.
4. Render with authoritative sentence times, at most two subtitle lines, 108-point text, and no bind_existing_assets or first-image fallback. Run focused tests and commit as feat: isolate v4 visuals and caption scale.

## Task 8: Staged orchestrator and final gates

Files: Create human_archive/scripts/build_sample_3m_v4.py, human_archive/scripts/verify_sample_v4.py, human_archive/tests/test_sample_v4_integration.py; modify postflight_release.py, human_archive/README.md, and CLAUDE.md.

Interfaces:
- build_sample_v4(*, run_root: Path, outline: Path, script: Path, source_snapshot: Path, claim_inventory: Path, launcher: Path, auto_start_tts: bool = True) -> Path
- verify_sample_v4(run_root: Path) -> tuple[bool, dict[str, Any]]
- Preserve existing verify_postflight(...) behavior for legacy consumers.

TDD and implementation:
1. Add an integration test proving missing narrative approval blocks image requests and proving COMPLETE is not counted in its own inventory.
2. Run python -m pytest human_archive/tests/test_sample_v4_integration.py -q; expect FAIL.
3. Orchestrate in this exact order: resolve and validate paths; build evidence packet and outline; generate v3 script; run structural preflight; verify fact approval; project common script; health-check/start SuperTonic3; generate provisional M4 TTS; build post-TTS report; obtain audio-first/text editorial approval; generate new visual requests and images; build subtitles and motion; render; verify zero reuse, synchronization, postflight, and lineage; publish CAS and write COMPLETE last.
4. The final verifier must check parent/envelope digests, ordered IDs, hook/core deadlines, 170–190 second total duration, 1920x1080, CFR 25, yuv420p/bt709/tv, audio stream, subtitles, M4 provenance, image uniqueness, absence of legacy SHA, and nonzero candidate size. Use a generic synchronization adapter and do not reuse the Pompeii-specific table.
5. Document exact absolute commands and paths in README and CLAUDE.md, including the known launcher path and output root. Run the integration test plus legacy regression set:
   python -m pytest human_archive/tests/test_sample_v4_integration.py human_archive/tests/test_context_sample_script_projection.py human_archive/tests/test_context_sample_contract.py human_archive/tests/test_sentence_audio_timeline.py human_archive/tests/test_tts_provenance.py -q
6. Require PASS and commit as feat: orchestrate and verify narrative-first sample v4.

## Task 9: Controlled production run

Files: Only write under human_archive/runs/ep02_jang_huibin/sample-3m-v4-001/; do not modify sample-3m-v3-001 or context-final. Versioned run metadata may be committed only after verification.

Execution contract:
1. Verify all input roots and files exist using absolute PowerShell paths; fail closed on any missing or escaping path.
2. Run the v4 orchestrator with explicit absolute paths and the SuperTonic3 launcher. If the server is unhealthy, let the runtime helper start it and record health evidence. Stop at any missing fact or narrative approval; never fabricate approval.
3. Run verify_sample_v4.py against the final run root. Expected results are PASS, zero legacy image reuse, valid narrative approval, 170–190 seconds, M4 provenance, and a COMPLETE marker whose inventory excludes itself.
4. Perform the audio-first human checkpoint before requesting final images/render. If it is rejected, revise the script/projection and repeat the affected gates rather than patching the MP4.
5. Check the exact candidate path human_archive/runs/ep02_jang_huibin/sample-3m-v4-001/candidate/HA002-sample-3m-v4-001.mp4 and its nonzero byte size. Do not report success unless the verifier and path check both pass.

## Self-review checklist

- Every requirement in the approved design spec has a corresponding task, file, interface, test, and commit boundary.
- No task contains an unresolved placeholder or vague implementation instruction; every failure mode has a concrete status or exception.
- New artifacts carry scope, run ID, parent payload digest, parent envelope-core digest, generator, policy digest, and target file hash.
- Existing v2/v3/context-final consumers remain backward compatible and are not modified by the controlled run.
- TTS timing is measured after provisional M4 synthesis; deadlines use proposition end times and are not inferred from sentence starts.
- Fact approval and narrative/editorial approval are separate gates; semantic uncertainty remains REVIEW_REQUIRED.
- Visual generation is downstream of approvals and uses no legacy image/audio/motion asset.
- Publication is staged and atomic with COMPLETE written last.
- Before declaring the implementation plan ready, run the plan lint, focused document checks, and staged diff check; confirm only the plan file is staged.



Example test shape:
```python
def test_hook_uses_last_required_proposition_end(script, outline, tts_manifest):
    report = build_post_tts_quality_report(script, outline, tts_manifest)
    assert report["checks"]["hook_deadline"]["status"] == "FAIL"
```
