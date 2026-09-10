# NOLLAM 코드베이스·워크플로우·대본 페이싱 하드닝 계획 (삼사 감사 보강판)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `nollam_file_v1`을 실제로 선택했을 때 대본의 사실성·구조·실측 TTS 타이밍·초반 고속/후반 저속 화면 전환·시각 생성·렌더·릴리스 검증이 하나의 프로필과 하나의 계약으로 연결되도록 정리한다.

**Architecture:** 대본 문장(sentence), 내레이션 기준 의미 샷(narration shot), 실제 화면 전환(perceptual cut)을 서로 다른 계층으로 분리한다. 완료된 TTS 문장 타임라인을 시간의 단일 진실 공급원으로 삼고, 프로필 리졸버가 editorial/script/audio/visual/delivery 정책을 한 번만 해석한다. 이후 모든 산출물은 동일한 `pipeline_context`와 해시 체인을 공유하며, 레거시 ShipSeonbi와 NOLLAM 실행 경로는 어댑터 경계 뒤에 둔다.

**Tech Stack:** Python 3.13, pytest, JSON Schema, YAML 정책 파일, SuperTonic3 HTTP, Google Flow CDP, Pillow/OCR, FFmpeg/ffprobe, existing Human Archive manifests.

**Review Inputs:**

- 상세 리뷰: `D:\module\bible\docs\superpowers\reviews\2026-09-10-nollam-pacing-audit-tri-model-review.md`
- 삼사 강화안: `D:\module\bible\docs\superpowers\plans\2026-09-10-nollam-hardening-tri-model-consensus-plan.md`
- 감사 evidence archive: `D:\module\audit\nollam_hardening_tri_model_audit\final_consensus_synthesis.md`, `cross_critique_matrix.json`

---

## 1. 조사 범위와 기준선

조사 시작 전에 `D:\module\PROJECT_MEMORY.md`, `D:\module\TASK.md`, `D:\module\PROGRESS.md`, `D:\module\ERRORS.md`를 모두 읽었고, 실제 저장소는 `D:\module\bible`임을 확인했다. 현재 브랜치는 `feat/full-media-pipeline-freeze`이며 작업 트리는 이미 대규모 변경 상태다. 이번 작업에서는 기존 변경을 reset, checkout, clean하지 않는다.

정적 조사 대상은 다음과 같다.

- 핵심 오케스트레이션: `human_archive/scripts/studio_gui_server.py`, `human_archive/scripts/historical_parallel_engine.py`, `human_archive/scripts/tri_model_debate_engine.py`
- 대본·타이밍: `human_archive/scripts/lib/shot_timing.py`, `human_archive/scripts/lib/cinematic_editing_director.py`, `human_archive/scripts/build_sentence_audio_master.py`
- 시각·Flow: `human_archive/scripts/generate_visual_briefs.py`, `human_archive/scripts/lib/visual_brief_provider.py`, `human_archive/scripts/lib/aligned_prompt_compiler.py`, `human_archive/scripts/build_image_request_manifest_v5.py`, `human_archive/scripts/validate_image_requests.py`, `human_archive/scripts/generate_flow_batch.py`, `human_archive/scripts/flow_cdp_service.py`, `human_archive/scripts/run_neanderthal_full_pipeline.py`
- 모션·자막·출시: `human_archive/scripts/build_motion_clips_v2.py`, `human_archive/scripts/build_subtitles_v2.py`, `human_archive/scripts/render_episode_v2.py`, `human_archive/scripts/postflight_release.py`, `human_archive/scripts/lib/build_manifest.py`, `human_archive/scripts/lib/audio_timeline.py`, `human_archive/scripts/lib/provenance.py`
- 정책·스키마: `human_archive/config/*.yaml`, `human_archive/schemas/*.json`, `CLAUDE.md`, `human_archive/README.md`

실행 기준선은 다음과 같다.

- `python -m pytest --collect-only -q`: 513개 테스트 수집 성공.
- `python -m compileall -q human_archive/scripts`: 종료 코드 0. 단, `build_karaoke_subtitles.py`에 `\\k` 관련 `SyntaxWarning`이 남아 있다.
- `python -m pytest -q`: 476 passed, 18 failed, 19 errors. 실행 중 C 드라이브 임시 디렉터리가 `No space left on device`가 되어 후반 오류 대부분이 환경성 오류와 섞였다. D 드라이브 격리 재실행에서는 `human_archive/tests/test_sentence_audio_padding.py`의 `anullsrc` 무한 스트림이 약 17GB WAV를 만들며 중단되어, 이 실행도 “전체 통과”로 간주하지 않는다.
- `human_archive/tests/test_sentence_audio_padding.py:12-15`는 `anullsrc=r=48000:cl=mono`에 필터 레벨 duration이 없고 입력별 `-t`가 두 번째 입력 앞에 놓여 있다. 계획에서는 `anullsrc=r=48000:cl=mono:d=0.4`와 명시적인 전체 출력 `-t`를 함께 사용하고, 출력 바이트 상한을 둔다.
- 실제 산출물 `human_archive/runs/nollam_file/2026-09-09/iceage-neanderthal-sapiens-extinction/generation/master_1200s_manifest.json`: 39개 씬, 955.9초, 첫 씬 11초, 2~11번 씬 평균 약 4.5초, 후반 Tier 3 평균 약 41.2초, 최대 51.2초, 간격 0초·겹침 0초.
- 같은 매니페스트의 `SHOT_002`는 35자에서 `...거대한`으로 끝나고 `SHOT_003`은 `맹수를...`로 시작한다. `cinematic_editing_director.py:335-343`의 중앙 공백 절단이 원인이다.
- `SHOT_001`은 `scene_duration=11.0`초이며 51자 한 문장이다. 기존 베어팁/실사 전환 요구를 만족하려면 4~6초 베어팁 훅과 4~5초 실사 detail cut으로 분리할 별도 opening contract가 필요하다.
- 실제 최종 MP4: 1920×1080, 25fps, H.264 + AAC, 48kHz stereo, 955.68초. 즉 이번 구체 실행에는 “빠른 도입/느린 후반”이 실제 scene manifest에 반영되어 있다.

이 기준선은 페이싱 아이디어 자체가 없다는 뜻이 아니라, 같은 요구가 서로 다른 코드 경로에서 서로 다른 계약으로 구현되어 재현성과 릴리스 안전성이 낮다는 뜻이다.

## 2. 핵심 진단

### 2.1 파이프라인이 사실상 두 개이며 파일명만 일부 공유한다

현재는 다음 두 경로가 병존한다.

```text
NOLLAM/History-Ida 레거시
topic/archetype
  -> historical_parallel_engine
  -> tri_model_debate_engine
  -> generate_video_prompts / run_neanderthal_full_pipeline
  -> cinematic_editing_director / FFmpeg

v5/v6 narration-aligned 경로
approved script
  -> build_sentence_audio_master
  -> plan_narration_shots / lib.shot_timing
  -> generate_visual_briefs
  -> build_image_request_manifest_v5
  -> generate_flow_batch
  -> verify_visual_assets
  -> build_motion_clips_v2
  -> build_subtitles_v2
  -> render_episode_v2
  -> postflight_release / release_episode
```

첫 경로는 `target_shots`, 3-tier metadata, `bare_tip`, adaptive Flow cooldown을 사용한다. 두 번째 경로는 문장 TTS 우선·human approval·v5 visual brief를 사용하지만, 실제 구현은 ShipSeonbi/Joseon prompt와 legacy manifest field를 강하게 전제한다. 두 경로는 `asset_manifest.json`, `master_audio_48k.wav`, `subtitles.ass` 같은 이름을 공유하지만 `shot_id/scene_id`, `startSeconds/start_sec`, `scene_audio_manifest/sentence_audio_manifest`, schema version과 필수 hash 필드가 달라서 end-to-end 연결이 깨질 수 있다.

### 2.2 현재 가장 큰 문제는 “프로필은 NOLLAM인데 구현은 ShipSeonbi 또는 레거시”라는 점이다

- `channel_profiles.yaml`, `CLAUDE.md`, delivery 설정은 `nollam_file_v1`, `trend_explainer_20m`, 포토리얼 시네마틱, 호스트 0%를 표방한다.
- `aligned_prompt_compiler.py`의 기본 STYLE은 Korean editorial ink-doodle illustration이다.
- `narration_visual_brief_prompt.j2`와 fallback provider는 Joseon palace, Chwiseondang, King Sukjong, ShipSeonbi 세계관에 고정되어 있다.
- `validate_image_requests.py`는 요청 수 95~120, 호스트 8~12%, Joseon 금칙어를 요구한다. NOLLAM 정책의 호스트 0%, 130~150 perceptual cuts / 70~80 unique images와 충돌한다.
- `compile_shot_contract.py`는 persona report가 주어지면 `ship_seonbi`를 강제한다.

따라서 NOLLAM 주제인 Neanderthal, San José, 기후·과학·트렌드 이슈가 v5 경로로 들어가면 prompt가 주제에 맞지 않거나 validator에서 거부되거나, fallback이 조선 궁궐 장면을 내보낼 위험이 있다.

### 2.3 페이싱은 데이터에는 있으나 모든 렌더 경로에서 실행되지 않는다

현재 페이싱 관련 구현이 서로 다르다.

1. `visual_pacing_profiles.yaml`의 `nollam_decay_20m`은 cold open 4.0초에서 outro 12.5초까지 7구간의 점진적 감쇠를 정의한다.
2. `cinematic_editing_director.py`는 10%/20%/70% Tier와 Tier 3 30~60초(실제 코드 일부는 30~65초) 씬을 만든다. 900/1200/1500초에는 fixed override도 남아 있다.
3. `historical_parallel_engine.py`는 문장 길이 기반 약식 시간을 만들고, `generate_variable_pacing_script`는 기존 씬에 tier metadata를 붙이는 수준이다. 늦은 구간의 장면을 실제로 병합하지 않는다.
4. `lib/shot_timing.py`는 실제 TTS row를 소비하는 좋은 기반이지만 반환 `profile_id`가 `narration_aligned_hybrid_v1`로 고정되고 NOLLAM 7-zone 감쇠를 적용하지 않는다.
5. `build_motion_clips_v2.py`는 대부분의 shot에 약 3.5% zoom과 crop 변형만 적용하고, brief의 `motion_profile`, tier, late-stage biphasic timing을 읽지 않는다. `lib/motion_engine_v3.py`도 이 경로에 연결되지 않았다.

즉 실제 Neanderthal 산출물은 의도한 곡선을 보여주지만, 그 곡선을 만드는 규칙이 공통 scheduler가 아니라 실행 경로별 특수 구현이다. 다음 주제에서 같은 결과를 보장할 수 없다.

### 2.4 대본·팩트체크·TTS 순서가 일부 경로에서 시간 정보를 낡게 만든다

- `tri_model_debate_engine.py` Round 3가 이미 계산한 shot의 `display_text`/`tts_text`를 바꾼 뒤 기존 duration을 재사용할 수 있다. 텍스트가 바뀌면 TTS, 자막, shot timing, visual prompt, hash가 모두 다시 계산되어야 한다.
- `historical_parallel_engine.py`의 `target_shots`는 문장을 샘플링해 줄이거나, 모자라면 공백/쉼표 기준으로 나누는 legacy API가 남아 있다. 이 API는 ERR-005, ERR-007, ERR-019 유형을 재발시킬 수 있다.
- `target_duration_sec=1200`과 권장 shot count가 여러 topic fixture에 반복되지만, 실제 정책은 840~1560초의 자연 runtime이다. 정확한 1200초를 맞추기 위한 scaling과 실제 TTS 측정이 섞여 있다.
- `build_sentence_audio_master.py` CLI 기본값이 `fixture`이며, 실제 provider 기본 voice는 M4/speed 0.94이다. NOLLAM 정책은 M2_WARM/M2, speed 0.95, total_step 10이다. fixture·voice·speed·server/model version이 reuse key에 완전히 들어가지 않는다.

### 2.5 manifest/schema/hash 계약이 연결 지점에서 깨질 여지가 높다

- `asset_manifest.schema.json`은 schema version 1, `contract_sha256`, `created_at_utc`, 제한된 status를 요구하지만 `generate_flow_batch.py`는 version 2와 `SUBMITTED`/`REVIEW_REQUIRED`를 만들 수 있다.
- `render_episode_v2.py`는 `build_manifest.json`에 `upstream_artifacts` 중첩 구조를 쓰지만 schema는 flat SHA 필드를 요구한다.
- `render_episode_v2.py`, `build_motion_clips_v2.py`, `build_subtitles_v2.py`가 `scene_audio_manifest.json`을 기대하지만 표준 TTS 단계의 산출물은 `sentence_audio_manifest.json` 또는 `shot_timing_manifest.json`이다.
- `lib/build_manifest.py`는 contract/asset/audio/subtitle를 찾지만 실제 모든 upstream hash와 timing manifest를 동등하게 검증하지 않는다.
- `compute_object_sha256`가 대문자 hex를 반환하는 부분과 schema의 lowercase pattern이 충돌할 수 있다.
- `render_episode_v2.py`는 build manifest를 작성하지만 schema validation과 final postflight를 한 번에 보장하지 않는다.

### 2.6 Flow 자동화 구현이 세 갈래로 중복되어 상태가 달라진다

- `flow_cdp_service.py`
- `run_neanderthal_full_pipeline.py`
- `generate_flow_batch.py`

최근 ERR-027에 기록된 strict zero-concurrency, adaptive 14~17초/오류 25초/10회 성공 후 30초 cooldown, canvas idle/error-card GC는 `run_neanderthal_full_pipeline.py` 쪽에 더 많이 있고, v5의 `generate_flow_batch.py`는 stable URL 두 번 확인을 중심으로 한다. stable URL은 올바른 card와의 association, spinner 종료, 이전 카드 재사용을 증명하지 않는다. 또한 `asset_has_download_evidence`는 row field만 보고 실제 파일 존재·내용·hash를 확인하지 않아 stale row가 pending generation을 건너뛸 수 있다.

### 2.7 GUI와 legacy engine의 결합도가 너무 높다

`studio_gui_server.py`는 약 5,610줄이며 GUI route, job state, topic routing, Flow 상태, render orchestration, legacy/new pipeline adapter가 한 파일에 공존한다. 오류 재현과 profile별 실행 경로 확인이 어렵고, UI에서 “완료”로 보이지만 실제 release gate까지 통과했는지 분리되어 있지 않다.

### 2.8 테스트는 품질 규칙을 많이 갖고 있지만 실행 환경과 경로 경계가 약하다

513개 테스트가 있다는 것은 장점이다. 다만 이번 기준선은 C 드라이브 여유 공간 0바이트로 인해 pytest `tmp_path`, Pillow image fixture, FFmpeg 산출물이 연쇄 실패했다. 테스트가 D 드라이브 격리 temp root를 사용하지 않고, 장시간/대형 미디어 테스트와 순수 contract unit test가 한 실행에 섞여 있다. 또한 `human_archive/flow_automation/tests`는 현재 `pytest.ini`의 testpaths에 포함되지 않아 별도 실행이 필요하다.

### 2.9 삼사 리뷰에서 확인된 사실과 채택 조건

상세 리뷰와 강화 계획의 결론을 그대로 구현 완료로 간주하지 않는다. 다음 항목은 코드와 실제 산출물에서 재확인된 사실이다.

- `test_sentence_audio_padding.py`의 무제한 `anullsrc`와 C 드라이브 `%TEMP%` 사용은 디스크 고갈의 직접 원인이다. 필터 레벨 duration, 전체 출력 `-t`, 파일 바이트 상한, D 드라이브 `--basetemp`를 함께 적용한다.
- `cinematic_editing_director.py:335-343`의 중앙 공백 분할은 실제 `SHOT_002`/`SHOT_003` 비문 사례와 일치한다. 문장 분할은 `split_sentence_by_semantic_clause`로 이동하며, 조사·어미·주어/목적어가 끊긴 결과를 테스트에서 차단한다.
- `run_neanderthal_full_pipeline.py:858-860`은 `bare_tip_whiteboard`를 허용된 motion type으로 해석하지 못하면 `push_in`으로 치환한다. `render_bare_tip_ink_stream_clip()`도 예외 시 일반 push-in으로 fallback한다. 따라서 “베어팁 탑재”는 메타데이터가 아니라 실제 MP4 asset과 성공적인 합성 검증으로만 인정한다.
- `smooth_subpixel_motion_engine.py`에는 120% overscan과 단일 trajectory는 있지만 `render_biphasic_ken_burns()`가 없다. 매니페스트의 `biphasic_motion` metadata만으로 구현 완료를 주장하지 않으며, 실제 두 단계 trajectory와 frame-level test를 추가한다.

다만 리뷰 문서의 “17GB 사건이 이미 교정 완료”, “GUI 6,171줄/인라인 HTML 3,850줄”, “삼사 99.85점”, “최종 영상의 M2·BGM sidechain” 같은 표현은 현재 작업에서 코드 변경이나 독립 증거로 완료 검증된 사실이 아니다. 계획서에서는 이를 **채택할 요구사항 또는 검증 대상**으로 취급한다. 특히 `pytest.ini`를 곧바로 `D:/module/scratch/pytest_tmp`로 고정할 때는 병렬 실행 충돌과 기존 사용자 파일 보존을 먼저 테스트한다.

원본 계획의 중요한 보정은 다음과 같다.

1. NOLLAM v5/v6를 완성된 정규 경로로 취급하지 않는다. 현재 v5/v6는 narration timing의 장점만 재사용하고, NOLLAM 시네마틱 엔진은 `smooth_subpixel_motion_engine.py`와 기존 6-vector director를 합성해 보존한다.
2. 7-zone cut 목표를 130~150개의 Google Flow 원본 생성으로 해석하지 않는다. 20분 기준 Flow master image는 71장 안팎으로 제한하고, 120~145개의 지각 컷은 120% overscan derived render로 만든다.
3. “씬 1번”은 하나의 narration shot이 아니라 `BARETIP_VIDEO` opening cut과 `FLOW_IMAGE` detail cut을 가진 opening group으로 모델링한다.
4. 정식 기본 페이싱은 누적 발화 비율 기반 7-zone으로 두고, 30~60초 Tier 3 long take는 별도 renderer option으로 유지한다. 그래야 짧은 15분 런과 긴 25분 런에서 absolute seconds가 곡선을 왜곡하지 않는다.

## 3. 대본 주제와 구조 진단 기준

### 3.1 권장 주제 구조

NOLLAM은 “사건 나열”보다 한 문장의 핵심 질문을 끝까지 추적하는 설명형 다큐가 되어야 한다. 권장 구조는 정책의 5 phase를 유지하되, 시각 페이싱의 7 zone과 별개로 관리한다.

| 대본 phase | 내용 기능 | 필수 검증 |
|---|---|---|
| Hook, 0~10% | 결과·반전·핵심 질문을 먼저 제시 | 첫 반전 20초 이내, 첫 15초 4 sentence, 과장/결론 선취 금지 |
| Context, 10~30% | 시공간·용어·비교 기준을 설명 | roadmap 120초 이내, 인물/장소/단위 정의 |
| Evidence, 30~70% | 1차 자료·관측·연구를 주장 단위로 검증 | claim/source mapping, 반대 증거, 확실성 등급 |
| Paradigm, 70~90% | 기존 설명이 깨지는 지점과 새 해석 | 새 주장 추가 시 재팩트체크, 반복 요약 금지 |
| Outro, 90~100% | 질문을 현재 의미로 되돌리고 잔여 불확실성 제시 | 새 핵심 사실을 마지막에 처음 소개하지 않음 |

각 문장은 다음 필드를 가져야 한다.

```text
sentence_id
phase
zone_hint
spoken_text
display_text
claim_ids
source_ids
fact_grade
certainty
visual_intent
preferred_boundary
```

`spoken_text`가 확정되기 전에는 TTS를 만들지 않는다. fact-check가 spoken text를 바꾸면 그 지점부터 downstream을 stale로 만들고 TTS부터 재생성한다. `display_text`만 정정 가능한 경우에도 변경 허용 범위와 승인 hash를 남긴다.

### 3.2 문장·내레이션 샷·화면 컷을 분리한다

이번 프로젝트의 “씬”이라는 말은 세 가지를 혼용하고 있다.

- `sentence`: 실제 음성 파일 하나와 연결되는 말 단위.
- `narration_shot`: 한 개 이상의 문장을 하나의 의미·주장·이미지 계약으로 묶은 단위.
- `perceptual_cut`: 같은 이미지의 derived crop/zoom을 포함해 시청자가 인식하는 실제 화면 전환.

이 계층을 분리하면, 한 문장을 2~3개의 빠른 cold-open cut으로 보여주거나 후반 하나의 이미지에서 두 단계 Ken Burns를 사용할 수 있다. 반대로 내레이션 shot을 30~60초로 만들기 위해 음성을 늘이거나 문장을 샘플링하는 일은 금지한다.

### 3.3 권장 NOLLAM 페이싱 곡선

이번 조사에서 실제로 확인된 39씬 결과는 강한 3-tier 곡선이며 방향성 검증에는 성공했다. 하지만 39개의 의미 shot만으로 20분을 채우면 30~51초의 긴 원본 이미지 구간이 생긴다. 삼사 합의에 따라 NOLLAM의 원본 생성 예산은 20분 기준 약 71장의 master image(15분 58장, 25분 92장)를 상한으로 두고, 실제 시청자 전환은 derived perceptual cut으로 확장한다. 7-zone은 Google Flow 요청 수가 아니라 시간·편집 목표로 해석한다.

정식 `nollam_decay_20m`의 기본 목표는 다음과 같다.

| zone | 시간 의미 | target | 허용 범위 | 의도 |
|---|---:|---:|---:|---|
| cold_open | 0~15초 | 4.0초 | 3~5초 | 즉시 주제 제시, 가장 빠른 전환 |
| hook | 15~60초 | 4.5초 | 3.5~6초 | 질문·반전 강화 |
| roadmap | 60~120초 | 6.5초 | 5~9초 | 시청자에게 탐색 지도 제공 |
| early_body | 120~300초 | 8.5초 | 6~12초 | 설명을 안정화 |
| body | 300~600초 | 10.0초 | 7~14초 | 증거 중심의 호흡 |
| late_body | 600초~outro 전 | 11.5초 | 8~15초 | 긴 사고 단위와 derived motion |
| outro | 마지막 90초 | 12.5초 | 9~18초 | 결론·잔상·여운 |

스케줄러는 measured sentence audio의 경계를 존중하면서 위 목표에 가장 가까운 cut을 선택한다. 목표를 맞추려고 음성을 늘리거나 줄이지 않으며, 해당 구간의 문장이 지나치게 짧으면 여러 문장을 하나의 narration shot으로 묶는다. 반대로 한 문장이 hard max를 넘으면 대본 편집 검토로 되돌린다.

강한 3-tier 모드가 필요한 경우에는 `source_shot_duration`과 `perceptual_cut_duration`을 분리하고, 후반 30~60초 long take 안에서 2-stage motion을 사용한다. 기본 NOLLAM 모드에서는 master image 1장당 1개 이상의 derived cut을 계획하여 총 120~145개의 perceptual cut을 목표로 한다. 이때 화면 cut 수를 늘리거나 줄이는 것이 narration audio와 claim coverage를 변경해서는 안 된다. `master_image_count`, `narration_shot_count`, `perceptual_cut_count`, `asset_type`을 각각 매니페스트에 기록한다.

## 4. 목표 아키텍처

```text
profile_resolver
  -> PipelineContext(profile, policy hashes, run id, source capability)

verified_script
  -> sentence_contract.json
  -> SuperTonic3 measured sentence audio
  -> sentence_audio_manifest.json
  -> pacing_scheduler(profile + measured audio)
  -> narration_shot_manifest.json
  -> perceptual_cut_plan.json
  -> visual brief / image request contract
  -> one Flow state machine
  -> asset manifest + visual approval
  -> motion clips using cut plan
  -> subtitles from sentence windows
  -> render + strict postflight
  -> release package
```

핵심 원칙은 다음과 같다.

1. 프로필은 CLI 기본값이나 파일명으로 추측하지 않고 한 번만 resolve한다.
2. 실제 TTS row의 start/end/duration이 시간의 단일 진실 공급원이다.
3. 모든 downstream artifact에는 `profile_id`, `schema_version`, `source_sha256`, `parent_digests`, `run_id`를 포함한다.
4. 실패한 단계는 `REVIEW_REQUIRED` 또는 `FAILED`로 멈추며 fixture/fallback/stale asset로 조용히 대체하지 않는다.
5. old pipeline은 즉시 삭제하지 않고 adapter와 deprecation warning으로 보존한다. 기능 삭제나 롤백은 하지 않는다.

## 4.1 변경 파일 매트릭스와 TDD 실행 순서

| 작업 단위 | 생성 파일 | 수정 파일 | 검증 파일/명령 |
|---|---|---|---|
| 환경·프로필 | `human_archive/scripts/lib/profile_resolver.py`, `human_archive/tests/test_profile_resolver.py` | `pytest.ini`, `studio_gui_server.py` | `python -m pytest human_archive/tests/test_profile_resolver.py -q` |
| 문장 계약 | `human_archive/scripts/lib/semantic_clause_splitter.py`, `human_archive/scripts/lib/script_contract.py`, `human_archive/tests/test_semantic_clause_splitter.py` | `cinematic_editing_director.py`, `historical_parallel_engine.py`, `tri_model_debate_engine.py` | `python -m pytest human_archive/tests/test_semantic_clause_splitter.py human_archive/tests/test_script_contract_nollam.py -q` |
| 오디오 SSOT | `human_archive/tests/test_nollam_audio_contract.py` | `build_sentence_audio_master.py`, `lib/tts_provider.py`, `lib/audio_timeline.py` | `python -m pytest human_archive/tests/test_nollam_audio_contract.py -q` |
| 페이싱 | `human_archive/scripts/lib/pacing_scheduler.py`, `human_archive/tests/test_nollam_pacing_scheduler.py` | `lib/shot_timing.py`, `lib/cinematic_editing_director.py` | `python -m pytest human_archive/tests/test_nollam_pacing_scheduler.py -q` |
| Prompt·asset | `human_archive/tests/test_nollam_prompt_profile.py` | `aligned_prompt_compiler.py`, `visual_brief_provider.py`, `validate_image_requests.py`, `schemas/asset_manifest.schema.json` | `python -m pytest human_archive/tests/test_nollam_prompt_profile.py -q` |
| Flow | `human_archive/scripts/lib/flow_generation_state.py`, `human_archive/tests/test_flow_state_machine.py` | `generate_flow_batch.py`, `flow_cdp_service.py`, `run_neanderthal_full_pipeline.py` | `python -m pytest human_archive/tests/test_flow_state_machine.py -q` |
| Motion·render | `human_archive/tests/test_nollam_render_contract.py`, `test_nollam_postflight_strict.py` | `smooth_subpixel_motion_engine.py`, `build_motion_clips_v2.py`, `build_subtitles_v2.py`, `render_episode_v2.py`, `postflight_release.py` | `python -m pytest human_archive/tests/test_nollam_render_contract.py human_archive/tests/test_nollam_postflight_strict.py -q` |

각 작업 단위는 다음 순서를 지킨다.

1. 실패해야 하는 regression test를 먼저 추가한다.
2. 해당 테스트 하나만 `python -m pytest <exact-test>::<exact-test-name> -q`로 실행해 FAIL 원인을 확인한다.
3. 최소 구현을 추가하고 동일 테스트를 다시 실행한다.
4. 관련 모듈에 `python -m py_compile <exact-file-list>`를 실행한다.
5. 해당 Phase의 전체 테스트를 실행한 뒤에만 체크박스를 갱신한다.
6. 실제 파일 산출물은 `Get-Item` 크기, `Get-FileHash -Algorithm SHA256`, `ffprobe` 결과를 함께 저장한다.

## 5. 실행 계획

### Phase 0 — 조사 산출물·실행 환경 고정

- [ ] `pytest.ini`의 기본 임시 디렉터리를 프로젝트 내부가 아닌 `D:/module/scratch/pytest_tmp`로 지정하고, 실행 전 디렉터리 생성·쓰기·여유 공간 검사를 수행한다. 기존 사용자 파일이 있으면 덮어쓰지 않는다.
- [ ] `human_archive/tests/test_sentence_audio_padding.py:10-16`의 fixture 명령을 다음 계약으로 교체한다. 두 duration 제한과 출력 크기 상한을 모두 검사한다.

```python
["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono:d=0.4",
 "-f", "lavfi", "-i", "sine=frequency=440:duration=0.8",
 "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[a]", "-map", "[a]",
 "-t", "1.25", "-c:a", "pcm_s16le", str(path)]
```

- [ ] FFmpeg helper가 프로세스 timeout, return code, stderr, expected duration, 최대 출력 bytes를 확인하도록 하고, 예기치 않은 무한 스트림을 즉시 중단한다. 1초 안팎 synthetic WAV가 수십 MB를 넘으면 테스트 실패로 처리한다.
- [ ] 대형 미디어 테스트에 `@pytest.mark.media_heavy`를 부여해 일반 contract test와 실행을 분리한다. `human_archive/flow_automation/tests`는 native/브라우저 capability marker를 통해 별도 실행한다.
- [ ] `studio_gui_server.py`의 인라인 HTML/CSS/JS를 `human_archive/static/index.html`로 먼저 분리하고, 서버가 파일을 읽지 못할 때 명확한 startup error를 반환하도록 한다. 이 작업은 Phase 7 전에 완료한다.
- [ ] `human_archive/scripts/lib/profile_resolver.py`를 추가하고 `channel_profiles.yaml`, `delivery_profiles.yaml`, `visual_pacing_profiles.yaml`, `script_policy_v3.yaml`, `audio_mix_policy.yaml`의 profile ID를 한 번에 resolve한다.
- [ ] `PipelineContext` dataclass를 추가해 `profile_id`, policy hash, run root, source capability, publishability, schema versions를 보관한다.
- [ ] `human_archive/tests/test_profile_resolver.py`에서 `nollam_file_v1` 기본 선택, unknown profile fail-closed, legacy profile 명시 선택, policy hash 재현성을 검증한다.

완료 기준: profile resolver의 출력이 모든 downstream 단계에 전달되고, 기존 dirty 파일은 변경하지 않으며, C 드라이브 공간 고갈 없이 contract unit test를 반복 실행할 수 있다.

### Phase 1 — 대본 계약과 주제 구조 정규화

- [ ] `human_archive/schemas/sentence_contract_v1.schema.json`을 추가한다. spoken/display 분리, phase, claim/source, fact grade, certainty, visual intent를 필수화한다.
- [ ] `human_archive/scripts/lib/semantic_clause_splitter.py`를 추가하고 `split_sentence_by_semantic_clause(text, max_chars=35)` API를 정의한다. 우선순위는 문장부호 → 한국어 연결어미(`-고`, `-며`, `-지만`, `-는데`) → 조사/어미 안전 공백이며, 주어·목적어·수식어가 고립된 결과를 반환하지 않는다.
- [ ] `human_archive/scripts/lib/script_contract.py`를 추가해 문장 ID 순서, 길이, phase 비율, 첫 15초 hook, 첫 반전/핵심 질문/roadmap deadline, 금칙 표현, claim coverage를 검증한다.
- [ ] `historical_parallel_engine.py`에서 `target_shots`를 문장 샘플링 도구로 사용하는 경로를 deprecated adapter로 감싼다. 문장 삭제·임의 중복·공백/쉼표 단편화를 기본 동작에서 제거한다.
- [ ] `tri_model_debate_engine.py`의 fact-check 후 spoken text가 바뀌면 duration·TTS·subtitles·prompts·hash를 모두 stale 처리하도록 변경한다. 정정된 text를 기존 시간에 덮어쓰지 않는다.
- [ ] `cinematic_editing_director.py:335-343`의 35자 중앙 공백 절단을 제거하고 semantic clause splitter를 호출한다. `SHOT_001`은 opening group으로 바인딩해 4~6초 `BARETIP_VIDEO`와 4~5초 `FLOW_IMAGE` detail cut이 합쳐지도록 한다.
- [ ] tri-model 단계가 실제 독립 provider 호출인지, static proposal/sleep 기반 simulation인지 상태 필드로 구분한다. simulation이면 release 가능한 fact-check로 표시하지 않는다.
- [ ] 대본 생성 결과에 `structure_signature`를 저장한다. 예: phase 경계, 핵심 질문 위치, claim 수, 반증 수, conclusion 위치.
- [ ] `human_archive/tests/test_script_contract_nollam.py`, `human_archive/tests/test_semantic_clause_splitter.py`, `human_archive/tests/test_factcheck_invalidates_downstream.py`를 추가한다. Neanderthal의 `SHOT_002`/`SHOT_003` 사례를 regression fixture로 고정한다.

완료 기준: 대본 정정 후 stale downstream이 자동으로 차단되고, 주제만 바꿔도 Joseon/ShipSeonbi 장면이 생성되지 않으며, 5 phase 계약이 자동 검증된다.

### Phase 2 — 실제 TTS를 시간의 단일 진실 공급원으로 고정

- [ ] `build_sentence_audio_master.py`의 publishable 기본 모드를 `supertonic3`로 바꾸고 `fixture`는 명시적 non-publishable test mode로 제한한다.
- [ ] `ToneFixtureProvider`와 호출부의 `silence_duration`/fixture parameter 계약을 맞추고, 로컬 3093 서버를 호출하지 않는 오프라인 mock provider를 별도 명시한다. fixture가 production provider처럼 보고되지 않게 한다.
- [ ] CLI에 `--voice`, `--speed`, `--total-step`, `--voice-lock-id`, `--provider-version`을 노출하고 NOLLAM profile이 M2/speed 0.95/step10을 강제하도록 한다.
- [ ] TTS reuse key에 provider, model/server version, voice, speed, total_step, audio filter, text hash를 포함한다. 현재 text hash만으로 다른 음성 결과를 재사용할 수 있는 경로를 제거한다.
- [ ] `sentence_audio_manifest.json`을 authoritative manifest로 확정한다. 각 문장에 measured duration, active bounds, gap before, start/end, wav sha256, provider provenance를 저장한다.
- [ ] 연속 문장 사이에 0.35~0.50초의 자연 룸톤을 스티칭하고, 목표 runtime을 맞추기 위한 임의의 수십 초 `tail_silence` 삽입을 금지한다. 룸톤 파일의 hash·sample format·실제 길이를 manifest에 기록한다.
- [ ] `lib/audio_timeline.py`의 target loudness/sample format을 NOLLAM 정책과 통일한다. 정책은 -14 LUFS, -1 dBTP, 48kHz stereo 24-bit를 표준으로 정하고 legacy mono/16-bit는 adapter로 명시한다.
- [ ] ffmpeg/ffprobe 실패를 삼키지 말고 명확한 `AudioBuildError`로 올린다. 출력 파일이 존재한다는 이유만으로 성공 처리하지 않는다.
- [ ] `human_archive/tests/test_nollam_audio_contract.py`에 voice lock, provider version, measured boundaries, gap/overlap, fixture release rejection, reuse invalidation을 추가한다.

완료 기준: TTS가 없거나 fixture이면 publishable 경로가 fail-closed이며, 대본 문장과 실제 WAV 경계만으로 전체 시간축을 재구성할 수 있다.

### Phase 3 — 공통 페이싱 스케줄러 구현

- [ ] `human_archive/scripts/lib/pacing_scheduler.py`를 추가한다. 입력은 resolved profile, sentence audio rows, chapter/phase metadata이며 출력은 `narration_shot_manifest.json`과 `perceptual_cut_plan.json`이다.
- [ ] `nollam_decay_20m` 7-zone 목표/최소/하드 최대를 YAML에서 읽고, cumulative audio time으로 zone을 계산한다. 코드에 900/1200/1500 fixed override를 남기지 않는다.
- [ ] 짧은 문장은 semantic boundary와 claim 단위가 유지되는 한 묶고, 긴 문장은 대본 편집 검토로 돌린다. 문장 중간을 글자 수로 자르지 않는다.
- [ ] 20분 기준 master image 예산을 71장(15분 58장, 25분 92장)으로 제한하고, Google Flow 원본 생성 수와 perceptual cut 수를 다른 필드로 기록한다. 130~150개의 Flow 원본을 생성하는 방식은 채택하지 않는다.
- [ ] 첫 15초는 빠른 cut target을 적용하되 첫 씬을 무조건 11초로 고정하지 않는다. opening group은 4~6초 `BARETIP_VIDEO`와 4~5초 `FLOW_IMAGE` detail cut으로 만든다.
- [ ] late body/outro에는 `biphasic_motion`을 실제 cut plan으로 저장한다. `stage_1`/`stage_2` 전환 시각, easing, focal anchor, overscan 요구를 포함한다.
- [ ] `cinematic_editing_director.py`의 `plan_variable_pacing_effects`가 duration을 무시하고 effect만 붙이는 동작을 제거한다. director는 scheduler가 만든 cut plan을 소비하는 renderer adapter가 된다.
- [ ] 120% overscan·구도 재앵커링으로 master image당 derived cut을 생성해 perceptual cut 120~145개를 달성한다. `master_image_count`, `narration_shot_count`, `perceptual_cut_count`의 관계를 검증하고 audio/claim coverage는 변경하지 않는다.
- [ ] legacy `generate_variable_pacing_script`는 metadata-only path가 아닌 adapter로 유지하되 새 scheduler를 호출하게 한다.
- [ ] `human_archive/tests/test_nollam_pacing_scheduler.py`에 5분, 16분, 20분, 26분, 짧은 hook, 긴 문장, phase 경계, no-gap/no-overlap, monotonically non-decreasing target curve를 추가한다.

완료 기준: 입력 대본 길이와 실제 TTS가 달라도 도입부 평균 cut duration이 후반부보다 짧고, 목표 구간을 넘어갈 때 오디오를 왜곡하지 않으며, 20분뿐 아니라 14~26분 범위에서 곡선이 재현된다.

### Phase 4 — visual brief와 prompt를 프로필·주제에 맞게 분리

- [ ] `human_archive/config/nollam_file_visual_policy.yaml`을 canonical style source로 삼고, photorealistic cinematic과 legacy doodle style을 별도 renderer profile로 분리한다.
- [ ] `human_archive/scripts/lib/aligned_prompt_compiler.py`에 profile-specific compiler를 추가한다. `nollam_file_v1`에서는 ink-doodle/Joseon 문구를 사용하지 않는다.
- [ ] `narration_visual_brief_prompt.j2`의 Joseon 고정 규칙을 `profile`과 `topic_context` 변수로 바꾸고, 역사 주제·과학 주제·트렌드 주제의 era/material/source 표현을 별도 정책으로 둔다.
- [ ] `visual_brief_provider.py`의 fallback은 production provider가 아니라 explicit fixture provider로 표시한다. unknown narration에 generic palace scene을 만들지 않는 fail-closed 동작을 유지한다.
- [ ] direct depiction ratio, host ratio, motif diversity를 profile에서 읽는다. NOLLAM host ratio 0%를 ShipSeonbi 8~12% validator와 섞지 않는다.
- [ ] `validate_image_requests.py`의 95~120 요청 수와 Joseon placeholder를 제거하고, profile별로 `narration_shot_count`, `perceptual_cut_count`, `unique_image_count`를 검증한다.
- [ ] `human_archive/schemas/asset_manifest.schema.json`에 `asset_type` enum을 추가한다: `FLOW_IMAGE`, `BARETIP_VIDEO`, `HYPERFRAMES_VIDEO`. 각 asset은 path, codec/container, dimensions 또는 video stream, duration, sha256, request/cut binding을 asset type에 맞게 필수화한다.
- [ ] opening cut의 `BARETIP_VIDEO`, Flow master의 `FLOW_IMAGE`, HyperFrames 파생 컷의 `HYPERFRAMES_VIDEO`를 하나의 asset manifest에서 검증하고, JPEG 전용 코드가 MP4를 조용히 건너뛰지 않게 한다.
- [ ] `human_archive/tests/test_nollam_prompt_profile.py`에서 Neanderthal/San José/비역사 주제 prompt가 조선 궁궐·선비 fallback을 포함하지 않는지, base image에 Hangul/숫자/내부 ID가 없는지 검증한다.

완료 기준: 같은 visual mode라도 profile에 따라 스타일만 바뀌며, 주제·claim·narration identity가 보존되고, NOLLAM 유효 요청이 legacy ShipSeonbi validator 때문에 거부되지 않는다.

### Phase 5 — Flow 생성 상태 머신 하나로 통합

- [ ] `human_archive/scripts/lib/flow_generation_state.py`를 추가해 `DISCOVERED → SUBMITTED → WAITING_IDLE → CARD_BOUND → DOWNLOADED → VERIFIED → REVIEW_REQUIRED/FAILED` 상태를 정의한다.
- [ ] `generate_flow_batch.py`, `flow_cdp_service.py`, `run_neanderthal_full_pipeline.py`의 중복 상태 전이를 이 state machine adapter로 통합한다. 기존 기능은 제거하지 말고 호출 경로를 하나로 모은다.
- [ ] strict zero-concurrency를 보장하고, stable URL만으로 성공 처리하지 않는다. URL이 현재 request의 card ID, prompt hash, 생성 완료 상태와 일치하는지 확인한다.
- [ ] adaptive cooldown 정책을 프로필/Flow capability에서 읽고, 14~17초 기본, error 25초, 10회 성공 후 30초 같은 운영 규칙을 한 곳에서 관리한다.
- [ ] `asset_has_download_evidence`를 실제 파일 존재, byte size, Pillow decode, dimensions, recomputed SHA, manifest row와의 일치 검증으로 확장한다. stale row는 pending을 건너뛰지 못하게 한다.
- [ ] canvas error card, spinner, 이전 카드 재사용, 다운로드 URL 변경을 모두 명시적 failure/review 상태로 기록한다.
- [ ] `human_archive/tests/test_flow_state_machine.py`와 `test_flow_batch_resilience.py`에 zero concurrency, wrong-card URL, stale row, error card, retry limit, cooldown, interrupted run resume을 추가한다.

완료 기준: Flow 한 장 생성의 성공 조건이 실제 파일·카드·요청 hash까지 증명되고, 세 개의 Flow 구현 중 어느 entrypoint에서도 동일한 상태/재시도 규칙이 적용된다.

### Phase 6 — motion, subtitle, render를 동일한 timing contract에 연결

- [ ] `build_motion_clips_v2.py`가 `perceptual_cut_plan.json`과 `narration_shot_manifest.json`을 직접 읽도록 변경한다. `scene_audio_manifest.json` 단독 의존과 누락 시 6초 fallback을 제거한다.
- [ ] `smooth_subpixel_motion_engine.py`의 trajectory를 actual renderer에 연결하고 `render_biphasic_ken_burns()`를 구현한다. 전반 50%는 와이드 앰비언트 S-curve pan, 후반 50%는 focal push-in이며 120% overscan과 crop-safe bounds를 검증한다. `lib/motion_engine_v3.py`는 중복 구현이 되지 않도록 adapter로 전환한다.
- [ ] FFmpeg `Popen`의 return code와 stderr를 확인하고, missing image는 skip하지 않고 fail-closed한다. 출력 clip의 exact duration/frame count를 ffprobe로 검증한다.
- [ ] `build_subtitles_v2.py`가 문장 WAV의 실제 start/end를 사용하도록 한다. shot 내부 문자 수 비례 시간 배분은 fallback으로만 남긴다.
- [ ] subtitle font, line width, max lines, bottom safe zone을 NOLLAM visual policy에서 읽는다. 현재 54pt/Malgun/22 chars, 프로젝트 메모리의 52pt/36 chars, NOLLAM YAML의 14 chars가 동시에 존재하는 문제를 하나의 profile setting으로 해소한다.
- [ ] 한국어 조사·어미·숫자 comma·문장부호를 보존하는 pixel-width 기반 분할을 사용하고, ASS parser가 malformed event를 삼키지 않게 한다.
- [ ] `render_episode_v2.py`는 sentence → shot → perceptual cut join을 검증한 뒤 render한다. 기존 output을 즉시 삭제하지 말고 atomic temp output과 archive/rollback metadata를 사용한다.
- [ ] `build_manifest.schema.json`과 실제 writer를 동일한 version으로 맞추고, flat/nested upstream hash 중 하나만 공식 계약으로 남긴다.
- [ ] `postflight_release.py`를 NOLLAM 전용 postflight와 연결해 codec, duration delta, audio sample/channel, subtitle integrity, no gap/overlap, visual approval hash, Flow provenance를 검사한다.
- [ ] `human_archive/tests/test_nollam_render_contract.py`와 `test_nollam_postflight_strict.py`를 추가한다.
- [ ] `run_neanderthal_full_pipeline.py`의 `bare_tip_whiteboard` → `push_in` 조용한 치환과 `render_bare_tip_ink_stream_clip()`의 일반 Ken Burns fallback을 제거한다. `srt-whiteboard-animation --bare-tip`의 실제 `BARETIP_VIDEO` 출력과 opening group 합성을 검증한다.

완료 기준: 최종 MP4의 video duration, master audio duration, 마지막 subtitle end가 허용 오차 안에서 일치하고, 모든 화면 전환이 cut plan과 대응하며, motion/자막 단계에서 누락 파일을 조용히 건너뛰지 않는다.

### Phase 7 — GUI·릴리스·운영 문서 정리

- [ ] `studio_gui_server.py`에서 profile selection, job orchestration, Flow controls, render/release route를 서비스 모듈로 분리한다. GUI는 상태를 표시하고, 실제 gate 판정은 shared pipeline service가 담당하게 한다.
- [ ] GUI에 `profile_id`, current stage, upstream stale 여부, human approval hash, publishability, 마지막 실패 원인을 명시한다. “생성 완료”와 “릴리스 가능”을 같은 상태로 표현하지 않는다.
- [ ] NOLLAM run directory에 source contract, sentence audio, shot plan, cut plan, visual request, asset, approval, render, postflight를 모두 연결하는 index manifest를 추가한다.
- [ ] `CLAUDE.md`, `human_archive/README.md`, `PROJECT_MEMORY.md`에서 legacy 3-tier와 canonical NOLLAM 7-zone의 역할을 구분해 문서화한다. 30~60초는 기본 규칙이 아니라 선택형 long-take renderer임을 명시한다.
- [ ] `ERRORS.md`에 이번 조사에서 확인한 신규/재확인 항목을 기록한다: schema mismatch, profile/style mismatch, measured timing invalidation, Flow state duplication, C-drive test exhaustion.
- [ ] `TASK.md`에는 실제 구현 phase만 체크하고, `PROGRESS.md`에는 산출물 경로·파일 크기·SHA-256을 기록한다. 전체 테스트와 postflight가 통과하기 전에는 완료로 표시하지 않는다.

완료 기준: UI에서 동일 run의 모든 계약과 gate 상태를 추적할 수 있고, 문서·테스트·매니페스트가 같은 profile ID와 schema version을 사용한다.

## 6. 테스트·검증 게이트

각 Phase는 다음 순서로 검증한다.

1. 해당 Phase의 unit/contract 테스트를 실행한다.
2. `python -m py_compile` 또는 `python -m compileall -q`로 변경 모듈 문법을 확인한다.
3. synthetic 5분/16분/20분/26분 run으로 timing·hash·schema를 검증한다.
4. 대표 실제 주제 Neanderthal과 비역사/트렌드 주제를 각각 dry-run해 prompt/profile leak를 확인한다.
5. Flow는 network generation 없이 state-machine fixture로 먼저 검증하고, 실제 CDP는 1회 1장 smoke와 pilot로 확장한다.
6. pilot은 cold-open 대표 12개와 coverage 대표 8개를 사용하되, full build가 pilot manifest를 재사용하지 않는지 확인한다.
7. 마지막에 `python -m pytest -q`를 D 드라이브 격리 temp root에서 실행하고, `human_archive/flow_automation/tests`도 별도로 실행한다.
8. final MP4에 대해 ffprobe, subtitle QA, visual QA, provenance/hash check, NOLLAM postflight를 모두 실행한다.

### Gate 0~7 필수 합격 기준

| Gate | 검증 범위 | 필수 합격 기준 |
|---|---|---|
| Gate 0 | 환경·프로필 | C 드라이브 임시 파일 0MB, D 드라이브 temp 사용, `nollam_file_v1` 해석 및 policy hash 고정 |
| Gate 1 | 대본·팩트 | 시맨틱 분절 비문 0건, 첫 15초 hook, 20초 이내 반전, 38초 이내 roadmap, 팩트 수정 시 downstream stale |
| Gate 2 | 오디오 SSOT | 실제 TTS provenance, 문장 경계·룸톤 0.35~0.50초, tail silence 조작 0건, gap/overlap 0건 |
| Gate 3 | 페이싱·컷 | 15/20/25분 master image 예산 58/71/92장, perceptual cut 120~145개, opening 2단계, 후반 target 증가 |
| Gate 4 | Prompt·asset | NOLLAM 스타일·주제 일치, ShipSeonbi leak 0건, `FLOW_IMAGE`/`BARETIP_VIDEO`/`HYPERFRAMES_VIDEO` 스키마 통과 |
| Gate 5 | Flow CDP | `max_in_flight=1`, idle/card binding 검증, 14~17초 지터·25초 backoff·30초 rest, 실제 파일 hash 확인 |
| Gate 6 | Motion·render | `smooth_subpixel_motion_engine.py`의 biphasic 함수가 frame-level로 작동, 52pt/36자/2줄 자막, codec·duration·audio 확인 |
| Gate 7 | GUI·release | 4대 router와 53개 endpoint smoke 통과, approval/hash/postflight 연결, 문서 동기화 완료 |

### 필수 acceptance criteria

- [ ] NOLLAM profile을 명시하면 prompt/style/voice/font/pacing/delivery가 모두 NOLLAM으로 resolve된다.
- [ ] fixture TTS, generic fallback, stale visual asset, missing Flow card, missing approval은 publishable 결과를 만들지 못한다.
- [ ] 실제 TTS 시간 기준으로 첫 zone의 평균 cut이 마지막 zone보다 짧고, zone target이 후반으로 갈수록 단조롭게 증가한다.
- [ ] 첫 15초에 hook이 존재하고, 첫 반전은 20초 이내, 핵심 질문은 40초 이내, roadmap은 120초 이내다.
- [ ] 전체 runtime은 정확히 1200초로 왜곡하지 않고 measured duration 기준 840~1560초 범위에서 평가한다.
- [ ] 모든 sentence/shot/cut이 순서대로 1회 이상 커버되고 audio gap/overlap이 없다.
- [ ] NOLLAM은 host 0%를 지키고, base image에는 subtitle·Hangul·internal ID가 없다.
- [ ] 최종 매니페스트는 contract/audio/timing/asset/subtitle/approval/render hash를 하나의 검증 가능한 lineage로 연결한다.
- [ ] 최종 영상은 1920×1080, 25fps, H.264/AAC, 48kHz stereo, 정책 loudness를 만족한다.
- [ ] 테스트가 환경성 디스크 부족으로 실패하지 않으며, 실패 시 오류가 원인별로 분리되어 기록된다.

## 7. 우선순위와 실행 순서

### P0 — 릴리스 차단 위험

1. Phase 0의 D 드라이브 테스트 격리·무한 `anullsrc` 차단·profile resolver·GUI HTML 선제 분리
2. Phase 1의 semantic clause splitter와 fact-check granular invalidation
3. Phase 2의 실제 TTS·provenance lock·0.35~0.50초 룸톤
4. Phase 3의 authoritative two-tier pacing scheduler와 71장/120~145컷 계약
5. Phase 5의 Flow 실제 파일·card·hash 검증
6. Phase 6의 polymorphic asset·motion·subtitle·render contract

### P1 — 품질과 재현성

1. 대본 fact-check 후 downstream invalidation
2. NOLLAM prompt/style 분리
3. motion engine 연결과 subtitle actual timing
4. schema/hash 통합
5. postflight 강화

### P2 — 유지보수성과 운영성

1. GUI 모듈 분리
2. legacy adapter/deprecation 정리
3. 테스트 temp/media marker 분리
4. 문서·ERRORS·PROGRESS 동기화

## 8. 예상 리스크와 대응

- 기존 NOLLAM 결과가 강한 3-tier에 맞춰져 있으므로, 7-zone으로 전환하면 shot 수가 늘 수 있다. 이를 regression으로 보지 말고 `narration_shot`과 `perceptual_cut`을 분리해 시각적 호흡을 보존한다.
- ShipSeonbi용 테스트가 새 NOLLAM prompt compiler를 오염시킬 수 있다. profile parameter를 fixture에 명시하고, legacy 테스트는 adapter 경계 안에서만 유지한다.
- 실제 SuperTonic3 서버가 없는 환경에서는 production test를 실행할 수 없다. deterministic fixture는 unit test에만 사용하고, release gate에서는 provider provenance를 요구한다.
- 대형 FFmpeg 테스트는 디스크를 빠르게 소모한다. D 드라이브 격리 temp root, 작은 synthetic media, marker 기반 serial execution을 사용한다.
- Flow DOM 변경은 CDP 코드에 영향을 줄 수 있다. provider adapter contract와 실제 1장 smoke를 먼저 통과시킨 뒤 batch로 확장한다.

## 9. 현재 결론

프로젝트의 핵심 아이디어인 “대본 길이에 따라 총 runtime을 유연하게 잡고, 도입부는 빠르게, 후반부는 느리게 전환한다”는 실제 Neanderthal 산출물에서 효과가 확인됐다. 그러나 현재 코드베이스는 이 결과를 하나의 재현 가능한 제품 규칙으로 보장하지 않는다. 가장 먼저 해야 할 일은 새 효과를 추가하는 것이 아니라, NOLLAM profile을 실제 실행 경로의 단일 진실 공급원으로 만들고, 문장 TTS → narration shot → perceptual cut의 세 시간 계층을 명시하는 것이다.

이 계획은 구현 전용 계획이다. 계획을 실행할 때는 각 Phase를 작은 TDD 단위로 진행하고, 한 Phase의 테스트·스키마·실제 파일 검증이 통과하기 전에는 다음 Phase의 production Flow나 full render로 넘어가지 않는다.

## 10. 2026-09-10 삼사 감사 반영 기록

상세 리뷰와 삼사 강화 계획을 대조한 결과, 원본 계획에 다음 보강을 반영했다.

- 17GB WAV의 원인을 `anullsrc` 무한 PCM 스트림으로 명시하고, 필터 duration·전체 `-t`·timeout·bytes cap·D 드라이브 temp 격리를 Phase 0에 추가했다.
- 실제 `SHOT_001` 11초 정체와 `SHOT_002`/`SHOT_003` 비문을 regression fixture로 고정하고, 중앙 공백 분할을 semantic clause splitter로 교체하도록 Phase 1을 구체화했다.
- NOLLAM 기본 원본 생성 수는 20분 71장으로 제한하고 120~145개 화면 전환은 derived perceptual cut으로 생성하도록 Phase 3의 수량 의미를 수정했다.
- 문장 사이 0.35~0.50초 룸톤, `FLOW_IMAGE`/`BARETIP_VIDEO`/`HYPERFRAMES_VIDEO` 다형성 에셋, `smooth_subpixel_motion_engine.py` 기반 `render_biphasic_ken_burns()`, 베어팁 fallback 금지를 Phase 2·4·6에 반영했다.
- GUI HTML 분리를 최종 단계가 아니라 Phase 0 선행 작업으로 이동했다.
- Gate 0~7을 추가해 환경·대본·오디오·페이싱·에셋·Flow·렌더·GUI/릴리스 합격 조건을 독립적으로 판정하게 했다.

이 문서의 위 항목은 모두 **구현 계획**이다. 리뷰 문서가 “교정 완료”라고 표현한 항목도 실제 코드 변경과 해당 테스트 통과 전에는 완료로 표시하지 않는다.
