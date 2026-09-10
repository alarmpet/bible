# 놀람파일 트렌드 해설 프로필 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 리뷰에서 실제 코드·런타임과 대조해 타당하다고 판정된 설계만 구현하여, 기존 Human Archive/HA002 결과를 건드리지 않는 opt-in `nollam_file_v1` 트렌드 해설 파이프라인을 만든다.

**Architecture:** offline fixture·Google Trends 공식 입력·사람이 보존한 Google News 원문을 필수 discovery로 수집하고, 선택 provider는 capability가 있을 때만 보조 신호로 사용한다. event fingerprint 기반 후보화 → source/claim 분리 검증 → 한국어 서사 대본 → 명시적 SuperTonic3 M2 warm TTS → 실제 오디오 기반 shot timing → 신규 시각 자산과 overlay manifest → 전용 16:9 postflight 순서로 실행한다. trend envelope에만 profile bundle lineage를 묶고 기존 HA v5/v6 artifact lineage는 변경하지 않는다.

**Tech Stack:** Python 3.12, PyYAML, jsonschema, SQLite, FFmpeg, SuperTonic3 HTTP provider, 기존 `build_sentence_audio_master.py`와 `plan_narration_shots.py`의 호환 인터페이스.

**Spec:** `D:\module\bible\docs\superpowers\specs\2026-09-01-nollam-file-trend-explainer-design.md`

## Global Constraints

- v1 활성 포맷은 `nollam_file_long`(16:9, 1920x1080, 25fps) 하나다. 숏폼·반응지도·팩트체크·REALTIME/FAST·무인 게시·상주 모니터는 v1.1 이후다.
- 최종 실제 영상의 목표 길이는 20분이며 허용 오차는 +/-30%다. 허용 범위는 14~26분(840~1560초)이고, 대본 글자 수나 예상 TTS 길이가 아니라 완료된 TTS/렌더 산출물에서 실측한다. 최종 렌더가 이 범위를 벗어나면 delivery를 차단한다.
- `nollam_file_v1`은 opt-in이며 `doodle_seonbi_v1` 기본값과 HA002의 `standard_docu`/`quick_3m` 결정을 바꾸지 않는다.
- 현재 SuperTonic3 provider 기본 M4/0.94와 기존 EP02 산출물은 보존한다. Nollam job만 `voice_lock_id=M2_WARM`, voice=M2, speed=0.95, total_step=10을 명시한다. 서버 health 실패 시 FAIL이며 다른 음성·fallback으로 우회하지 않는다.
- 기존 `artifact_lineage.py`, `generate_verified_script.py`, `persona_validation.py`, `compile_shot_contract.py`, `postflight_release.py`는 수정하지 않는다.
- AI base image에는 글자·숫자·로고를 생성하지 않고, 상태 라벨·날짜·출처는 `overlay_event_manifest_v1`에서 렌더한다.
- 필수 provider 부재는 `SOURCE_UNAVAILABLE` FAIL, 선택 provider 부재는 기록 후 계속한다. scraper fallback, 비공개 계정 수집, Reddit Pro 화면 재배포는 금지한다.
- source state(`active|edited|deleted|private|unavailable`)와 claim status를 분리한다. 단일 소셜 신호만으로 core claim을 확정하지 않는다.
- 모든 단계는 입력 manifest SHA-256을 기록하며 변경 시 downstream 승인을 stale 처리한다. 외부 게시·플랫폼 수정은 v1에서 하지 않는다.

---

## Phase 0 — 기존 계약 복구 확인(별도 릴리스)

- [ ] **읽기 전용 사전 게이트를 먼저 실행한다.**
  - Files: `human_archive/config/channel_profiles.yaml`, `human_archive/config/delivery_profiles.yaml`, `human_archive/tests/test_channel_profiles.py`, HA002 plan 문서.
  - Verify: 기본 프로필이 `doodle_seonbi_v1`, host ratio 정본이 8–12%, `doodle_docu_12m` 누락 및 12개 forbidden 테스트 불일치가 재현되는지 기록한다.
  - Boundary: 이 복구 작업은 별도 커밋/릴리스로 처리하며, Nollam 구현에서 HA002 산출물을 migration하지 않는다.

## Phase 1 — 프로필·정책 계약

- [ ] **strict profile schema v2와 legacy v1 oneOf를 추가한다.**
  - Files: `human_archive/config/channel_profiles.yaml`, `human_archive/schemas/channel_profile.schema.json`.
  - Interface: `load_channel_profile(profile_id, config_path=None) -> dict`; canonical key는 `delivery_profile_id`, legacy `delivery_profile`은 입력에서만 정규화하며 동시 존재는 FAIL.
  - Tests first: `human_archive/tests/test_channel_profiles.py`, 신규 `human_archive/tests/test_nollam_profile_contract.py`에 unknown reference, duplicate default, v1 compatibility, v2 strict nested validation을 고정한다.
  - Implement: `nollam_file_v1`을 기본값 false로 추가하고 delivery profile은 v1에서 long 하나만 활성화한다.

- [ ] **정책 파일과 schema를 생성한다.**
  - Files: `human_archive/config/nollam_file_editorial_policy.yaml`, `nollam_file_narration_policy.yaml`, `nollam_file_visual_policy.yaml`, `trend_research_policy.yaml`, `trend_publication_policy.yaml`, `trend_source_providers.yaml` 및 대응 `*_v1.schema.json`.
  - Required contract: persona, source roles, freshness DAILY/STABLE, M2 lock reference, rights/AI disclosure, provider capability, retention, correction SLA, overlay accessibility.
  - Tests: `test_policy_schema_validation.py`에서 모든 reference ID와 enum을 검증한다.

- [ ] **trend 전용 profile bundle resolver를 구현한다.**
  - Files: `human_archive/scripts/lib/channel_profiles.py`.
  - Interface: `resolve_nollam_profile(profile_id) -> ResolvedProfileBundle`, `canonicalize_profile_bundle(bundle) -> (canonical_json, sha256)`.
  - Implement: trend envelope 안에서만 bundle SHA를 생성하고 legacy production binding은 호출하지 않는다.
  - Tests: `test_profile_bundle_hash.py` — policy 한 항목 변경 시 hash/stale cascade, legacy fixture byte-equivalence.

## Phase 2 — Trend envelope·저장소·스키마

- [ ] **v1 JSON schema 9종을 작성한다.**
  - Files: `human_archive/schemas/trend_job_contract_v1.schema.json`, `trend_signal_manifest_v1.schema.json`, `trend_topic_candidate_v1.schema.json`, `trend_research_packet_v1.schema.json`, `trend_verified_script_v1.schema.json`, `resolved_profile_bundle_v1.schema.json`, `overlay_event_manifest_v1.schema.json`, `correction_action_manifest_v1.schema.json`, `studio_disclosure_manifest_v1.schema.json`.
  - Required examples: job의 `format_id=nollam_file_long`; signal의 provider ID/observed time/region/window/event fingerprint/source state/retention; candidate의 discovery 75 + evidence readiness 25; script의 sentence/claim/persona/voice lock/hash.
  - Tests first: `human_archive/tests/test_trend_schema_contracts.py`에 positive/negative fixtures와 기존 HA schema required 목록 불변 검사를 추가한다.

- [ ] **trend topic SQLite 저장소를 구현한다.**
  - Files: `human_archive/db/trend_topics.sqlite3`(migration script로 생성), `human_archive/scripts/lib/trend_store.py`.
  - Interface: `upsert_signal`, `upsert_candidate`, `record_observation`, `transition_status`; event_fingerprint가 cluster 유일 키이고 region/window는 observation 필드다.
  - Tests: `human_archive/tests/test_trend_store.py`에서 crosspost dedupe, status transition, tombstone/source state 분리를 검증한다.

## Phase 3 — Provider 수집·능력 정책

- [ ] **필수/선택 provider capability matrix를 고정한다.**
  - Files: `trend_source_providers.yaml`, `human_archive/scripts/lib/trend_sources.py`.
  - Required: offline fixture, Google Trends official RSS 또는 사람이 보존한 official export, 사람이 확인한 Google News 원문 링크.
  - Optional: X, Threads, Reddit, YouTube. 각 항목에 endpoint, auth, scope, quota/tier, retention/display permission, terms/policy version, collector identity를 기록한다.
  - Interface: `validate_capability(provider_config) -> CapabilityResult`; 선택 provider 실패는 `OPTIONAL_PROVIDER_UNAVAILABLE`로 기록한다.

- [ ] **수집 CLI와 fixture를 추가한다.**
  - Files: `human_archive/scripts/collect_trend_signals.py`, `human_archive/tests/fixtures/trend_signals/{it,entertainment,sports}/*.json`.
  - Interface: `collect_signals(input_dir, providers, now) -> trend_signal_manifest_v1`.
  - Tests: `human_archive/tests/test_trend_sources.py` — scraper fallback 차단, 권한 만료, optional-only 후보 차단, URL/provider ID 및 capture time 누락 FAIL.

## Phase 4 — 클러스터·선정·조사 패킷

- [ ] **event fingerprint와 origin/evidence 계층을 구현한다.**
  - Files: `human_archive/scripts/lib/trend_clustering.py`, `trend_selection.py`, `human_archive/scripts/generate_trend_topic_candidates.py`.
  - Implement: `origin_cluster_id/crosspost_parent_id`는 확산 신호, `corroboration_group_id`는 독립 근거로 분리; manipulation은 점수 감점이 아니라 QUARANTINED.
  - Score: discovery 75(확산·신선도·관심) + evidence readiness 25(공식 원문·독립 확인·권리·신선도), 24h/7d window.
  - Tests: `test_trend_clustering.py`, `test_trend_selection.py` — syndication/crosspost 중복, 동일 원문 재계산, quarantine, optional-only 차단.

- [ ] **research packet과 claim gate를 구현한다.**
  - Files: `human_archive/scripts/compile_trend_research_packet.py`, `human_archive/scripts/lib/trend_fact_gate.py`.
  - Implement: source state와 claim status 분리, non-Korean official 원문도 provenance/time/link 검증 시 PRIMARY_SOURCE, 한국어 번역은 `translation_of` edge; sports score/official filing/court order의 direct_record 예외; UNVERIFIED는 귀속된 비핵심 rumor explanation에만 허용.
  - Tests: `test_trend_fact_gate.py`, `test_translation_and_direct_record.py`, `test_freshness_and_legal_gate.py`.

## Phase 5 — 서사 대본·제목·썸네일 계약

- [ ] **Nollam 전용 대본 템플릿과 생성기를 추가한다.**
  - Files: `human_archive/templates/nollam_file_outline_prompt.j2`, `nollam_file_script_prompt.j2`, `human_archive/scripts/generate_trend_script.py`.
  - Interface: `generate_trend_script(packet, profile_bundle) -> trend_verified_script_v1`.
  - Implement: 12초 사건/질문, 15초 보상, 30초 맥락, 6단 서사(사건→확산→놀람→검증→반대 맥락→왜 중요한가), sentence별 claim/source/label 매핑; 기존 `generate_verified_script.py`와 분리.
  - Tests: `test_nollam_script_contract.py`, `test_title_thumbnail_scope.py`, `test_persona_and_forbidden_phrases.py`.

## Phase 6 — M2 음성·실제 오디오 타이밍

- [ ] **기존 TTS builder에 backward-compatible 명시 인자를 추가한다.**
  - Files: `human_archive/scripts/build_sentence_audio_master.py`, `human_archive/scripts/lib/tts_provider.py`.
  - Interface: 기존 기본값은 그대로 두고 keyword-only `voice_lock_id=None, voice=None, speed=None, total_step=None`을 추가한다. Nollam wrapper가 lock을 resolve해 provider에 M2/0.95/10을 전달한다.
  - Tests first: `human_archive/tests/test_nollam_audio_lock.py` — 기본 호출은 M4/0.94, Nollam 호출은 M2/0.95/10, lock 불일치·health fail·fallback은 FAIL.
  - Implement: `human_archive/scripts/build_nollam_audio.py`를 추가해 `voice_defaults.json`과 `media_rules_lock.json`의 M2_WARM 일치를 확인한 뒤 builder를 호출한다.

- [ ] **실제 오디오 기반 shot timing을 연결한다.**
  - Files: 기존 `human_archive/scripts/plan_narration_shots.py`를 호출하는 Nollam orchestration 모듈.
  - Verify: silence가 phrase duration을 대신하지 않으며 sentence timing/word timing manifest가 audio hash에 결속된다.

## Phase 7 — 신규 시각 자산·overlay·전용 postflight

- [ ] **overlay manifest compiler와 visual gate를 구현한다.**
  - Files: `human_archive/scripts/render_nollam_overlay.py`, `human_archive/scripts/lib/nollam_visual_gate.py`.
  - Interface: `compile_overlay_events(script, claims) -> overlay_event_manifest_v1`.
  - Implement: 확인/공식 발표/논쟁 중/미확인/반박됨/정정됨/해석/전망/반응 라벨 매핑, 최대 2행·14자, 대비율·색상 외 표식, base image no-glyph OCR 분리.
  - Tests: `test_nollam_visual_contract.py`, `test_overlay_accessibility.py`, 신규 자산 provenance/rights fixture.

- [ ] **Nollam 전용 16:9 postflight를 구현한다.**
  - Files: `human_archive/scripts/nollam_file_postflight.py`.
  - Checks: 1920x1080/25fps, 완료된 TTS/렌더의 실제 길이 14~26분(840~1560초), audio/video duration, claim/title/thumb scope, M2 lock, overlay manifest, profile bundle SHA, rights/AI disclosure, freshness 재조회, correction monitor handoff. 최종 렌더가 길이 범위를 벗어나면 delivery를 차단한다.
  - Tests: `test_nollam_postflight.py`; legacy `postflight_release.py` 회귀가 동일하게 통과하는지 별도로 확인한다.

## Phase 8 — 정정·공개·운영 문서

- [ ] **수동 정정·AI disclosure manifest workflow를 구현한다.**
  - Files: `human_archive/scripts/create_correction_action.py`, `create_studio_disclosure.py`, 관련 schema.
  - Interface: signed manifest 생성만 수행하며 외부 YouTube API/Studio mutation은 호출하지 않는다. CRITICAL/MATERIAL/MINOR와 제목·썸네일·설명·고정댓글·자막·번역·파생 Shorts surface를 전파한다.
  - Tests: `test_correction_lifecycle.py`, `test_disclosure_manifest.py` — 삭제≠철회, critical 재업로드 action, right-of-reply 24h/공익 긴급 6h 기록.

- [ ] **운영 문서를 opt-in 범위로만 갱신한다.**
  - Files: `CLAUDE.md`, `manual.md`, `human_archive/README.md`.
  - Add only: 공식 입력 경로, M2 job lock, run root, 수동 승인·정정·보존 절차. Unrelated legacy drift는 수정하지 않는다.
  - Test: 문서 경로 링크와 canonical command smoke check.

## Phase 9 — E2E dry run과 최종 검증

- [ ] **세 카테고리 private dry run을 실행한다.**
  - Files: `human_archive/scripts/run_nollam_dry_run.py`, `human_archive/tests/e2e/test_nollam_private_dry_run.py`.
  - Inputs: IT/tech 공식 발표, 영화·드라마 공식 발표, 스포츠 direct_record fixture.
  - Verify: release-ready까지 도달하되 외부 게시 없음; 정확성 오류, source gate 실패율, discovery→release-ready 시간만 측정한다.

- [ ] **최종 회귀·스키마·문서 검증을 수행한다.**
  - Commands:
    ```powershell
    pytest human_archive/tests -q
    python human_archive/scripts/nollam_file_postflight.py --run-root human_archive/runs/nollam_file/2026-09-01/example-topic/dry-run-001 --check-only
    ```
  - Verify: default profile/legacy output 불변, positive fixture 통과, negative fixture 전부 차단, v1 deferred 기능이 활성화되지 않음.
  - Commit: 각 Phase 커밋 후 마지막 검증 결과와 manifest SHA를 계획 문서에 기록한다.

## Review disposition

- **반영:** v1 범위 축소, legacy DAG 격리, M2 명시 lock, overlay manifest, 전용 postflight, event fingerprint 계층, source/claim 상태 분리, direct_record 예외, provider capability/retention, 정정 surface, 권리·AI disclosure, 공식 근거 링크.
- **보류/거부:** 기존 HA002 파일의 대규모 migration, 전 플랫폼 실시간 수집, 비공식 scraper, 자동 게시·자동 수정, `verified_script_v3` 재사용, Nollam 성과를 engineering acceptance에 포함하는 주장.
- **검증 근거:** 리뷰 문서의 각 지적을 실제 YAML/schema/loader/TTS/postflight/pacing 구현과 대조했으며, 현재 provider 기본 M4와 문서상 M2 운영 lock의 차이를 확인해 Nollam job-level override로 한정했다.
