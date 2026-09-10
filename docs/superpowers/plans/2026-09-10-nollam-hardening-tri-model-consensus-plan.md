# NOLLAM 코드베이스·워크플로우·대본 페이싱 쇄신 계획 (삼사 만장일치 강화판 — Round 3 마스터 갱신)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Tri-Model Consensus Audit Evidence:**
> - Round 1 Review Report: [`D:\module\bible\docs\superpowers\reviews\2026-09-10-nollam-pacing-audit-tri-model-review.md`](file:///D:/module/bible/docs/superpowers/reviews/2026-09-10-nollam-pacing-audit-tri-model-review.md)
> - Round 2 Review Report: [`D:\module\bible\docs\superpowers\reviews\2026-09-10-nollam-hardening-v2-tri-model-review.md`](file:///D:/module/bible/docs/superpowers/reviews/2026-09-10-nollam-hardening-v2-tri-model-review.md)
> - Round 2 Knowledge Doc: [`D:\module\bible\docs\solutions\integration-issues\nollam-round2-av-contract-router-hardening-2026-09-10.md`](file:///D:/module/bible/docs/solutions/integration-issues/nollam-round2-av-contract-router-hardening-2026-09-10.md)
> - Round 3 Review Report: [`D:\module\bible\docs\superpowers\reviews\2026-09-10-nollam-round3-av-hardening-tri-model-review.md`](file:///D:/module/bible/docs/superpowers/reviews/2026-09-10-nollam-round3-av-hardening-tri-model-review.md)
> - Round 3 Master Execution Plan: [`D:\module\bible\docs\superpowers\plans\2026-09-10-nollam-hardening-round3-master-execution-plan.md`](file:///D:/module/bible/docs/superpowers/plans/2026-09-10-nollam-hardening-round3-master-execution-plan.md)
> - Round 3 Consensus Audit: [`D:\module\audit\nollam_hardening_v3_tri_model_audit\final_consensus_synthesis.md`](file:///D:/module/audit/nollam_hardening_v3_tri_model_audit/final_consensus_synthesis.md)
> - Round 3 Matrix & Score: [`D:\module\audit\nollam_hardening_v3_tri_model_audit\cross_critique_matrix.json`](file:///D:/module/audit/nollam_hardening_v3_tri_model_audit/cross_critique_matrix.json) (종합 99.92점 만장일치 통과)

**Goal:** `nollam_file_v1`을 선택했을 때 대본의 사실성·문맥 안전 분절·실측 TTS 호흡(0.35~0.50s 룸톤)·2계층 하이브리드 페이싱(마스터 71장 예산 + 120~145개 파생 지각 컷)·52.3초 오디오 절삭 및 립싱크 파탄 척결·자막 마이크로 클로즈 3분할(36자 2줄 엄수)·네안데르탈인 48kHz stereo 전면 재생성·3중 실물 감사(컨테이너/입력/메타데이터) 및 3-Tier 오프라인 격리 게이트가 하나의 불변 계약과 단일 파이프라인으로 연결되도록 시스템을 하드닝한다.

**Architecture:** 대본 문장(`sentence`), 의미 샷(`narration_shot`), 시청자 지각 컷(`perceptual_cut`)의 3계층 분리를 단일 진실 공급원(SSOT)으로 확립한다. 발화 오디오 길이를 인위적으로 클램핑하지 않고, SuperTonic3 M2 실측 발화 시간($T_{\text{speech}}$)에 0.40s(앞 0.15s + 뒤 0.25s) 유한 룸톤을 합산한 실제 시간($T_{\text{scene}}$)으로 비디오 클립과 자막을 1:1 일치 렌더링한다. 프로필 리졸버가 editorial/script/audio/visual/delivery 정책을 불변 `PipelineContext`로 해석하며, Google Flow CDP는 `max_in_flight=1` 단일 진행 게이트와 적응형 14~17s 지터 쿨다운을 전역 강제한다. 모션 엔진은 `smooth_subpixel_motion_engine.py`로 단일화하여 2단계 바이페이직 켄번즈를 정식 구동하고, 자막은 `semantic_subtitle_engine.py`(52pt Pretendard, 36자 2줄 피라미드)로 100% 직결한다.

**Tech Stack:** Python 3.13, pytest, JSON Schema, YAML 정책 파일, SuperTonic3 HTTP & ToneFixture, Google Flow CDP, PIL Subpixel Bicubic (120% Overscan), FFmpeg/ffprobe, existing Human Archive & NOLLAM manifests.

---

## 1. 조사 범위 및 확정된 기준선 (Baseline)

### 1.1 정적 조사 대상
- 핵심 오케스트레이션: `studio_gui_server.py`, `historical_parallel_engine.py`, `tri_model_debate_engine.py`
- 라우터 모듈: `routes/flow_routes.py`, `routes/render_routes.py`, `routes/pipeline_routes.py`, `routes/script_routes.py`, `routes/media_routes.py`
- 대본·타이밍: `lib/shot_timing.py`, `lib/cinematic_editing_director.py`, `build_sentence_audio_master.py`
- 시각·Flow: `generate_video_prompts.py`, `lib/aligned_prompt_compiler.py`, `flow_cdp_service.py`, `run_neanderthal_full_pipeline.py`, `generate_flow_batch.py`, `lib/flow_dom_maintenance.py`
- 모션·자막·출시: `smooth_subpixel_motion_engine.py`, `lib/semantic_subtitle_engine.py`, `render_episode_v2.py`, `postflight_release.py`, `lib/three_tier_postflight.py`
- 정책·스키마: `human_archive/config/*.yaml`, `human_archive/schemas/*.json`, `PROJECT_MEMORY.md`, `AGENTS.md`

### 1.2 실증 기준선 (Empirical Baseline)
- **테스트 수집**: 현재 587개 테스트 수집, `-m "not media_heavy"` 기준 586개 선택·586개 통과 확인. Round 2 리뷰의 579개 통과 표기는 이전 실행 기준으로 정정한다.
- **디스크 상태**: C: 여유 15.32GB (위험), D: 여유 186.54GB (안전). 모든 pytest 및 FFmpeg 임시 출력은 D: 드라이브(`D:/module/scratch/pytest_tmp`)로 격리 강제.
- **17GB WAV 폭주 원인**: `test_sentence_audio_padding.py`의 `anullsrc`에서 지속시간 옵션 누락으로 인한 무한 스트림 결함 확인 및 교정 완료.
- **네안데르탈인 실물 감사 실측 결과**:
  - MP4 컨테이너: 955.68초 (1920x1080, 25fps, 23,892프레임), AAC 48kHz stereo, -18dB 덕킹.
  - 마스터 오디오(`neanderthal_master_audio_48k.wav`): **1007.969396초** (최종 MP4 비디오 대비 **+52.289396초** 오버런).
  - FFmpeg `-shortest` 플래그로 인해 **후반부 52.289초 내레이션이 영구 절삭/소실**되었고, 샷 2부터 화면과 음성이 5초 이상 어긋난 립싱크 파탄 확인.
  - 입력 WAV 39개 전수 44.1kHz mono, 입력 ASS 자막 40개 라인이 36자 초과(최대 86자) 확인. 전면 재생성 필수.

---

## 2. 핵심 아키텍처 원칙 (Constitutional Invariants)

1. **시간의 단일 진실 공급원 (TTS-First SSOT) 및 립싱크 일치성**:
   - 씬 길이를 기계적으로 4.5초에 맞추기 위해 음성을 자르거나 비디오를 단독 절삭하는 행위를 영구 금지한다.
   - SuperTonic3 M2 실측 발화 시간($T_{\text{speech}}$)에 0.40s(앞 0.15s + 뒤 0.25s) 유한 룸톤을 더한 **진짜 씬 길이($T_{\text{scene}}$)**로 비디오 클립과 자막을 1:1 일치 렌더링한다.
   - 비디오 지속시간과 오디오 지속시간의 오차는 **Stream Parity ($|t_{\text{video}} - t_{\text{audio}}| \le 0.050\text{s}$)**를 100% 만족해야 한다.
2. **2계층 하이브리드 지각 페이싱 (Two-Tier Perceptual Pacing)**:
   - **Layer 2 (Narration Shot / Master Image)**: 헌법적 샷 예산 수식에 따라 20분 기준 **총 71장 (58~92장)**으로 통제하여 Google Flow CDP 세션 안전선(ERR-027)을 엄수한다.
   - **Layer 3 (Perceptual Cut)**: 1장의 고해상도 마스터 이미지에서 PIL 서브픽셀 120% 오버스캔과 2단계 바이페이직 모션을 적용하여 **총 120~145개의 지각 컷(4~12.5s 템포)**을 무비용으로 창출한다.
3. **첫 38초 시청자 유지율 헌법 (Retention Invariant)**:
   - 씬 1번 11초 정체 이탈을 금지하고, **전반 6초 순수 베어팁 선화 훅 + 0.35s 크로스페이드 + 후반 5초 35mm 실사 디테일 컷**으로 2단계 미세 분할한다.
   - 20초 이내 첫 반전, 38초 이내 서사 로드맵 안착을 자동 검증한다.
4. **자막 마이크로 클로즈 타임 슬라이싱 (Subtitle Micro-slicing)**:
   - 50초 롱테이크 문장은 한국어 시맨틱 종결어미(`-고`, `-며`, `-지만`, `-는데`)를 기준으로 **16~17초 단위 2~3개 정갈한 자막 이벤트로 시간 분할**한다.
   - 52pt Pretendard, 1줄 최대 36자, 최대 2줄 70자, 좌우 마진 50px, 피라미드 정렬(윗줄 20~28자, 아랫줄 28~35자)을 엄수한다.
5. **3중 실물 감사 체인 (Three-Tier Physical Postflight Gate)**:
   - **Layer 1 (원천 입력 물리 감사)**: 39개 WAV 전수 ffprobe 48kHz stereo 실측, ASS 52pt & 줄당 <=36자 & 최대 2줄 <=70자 실측. 1건이라도 미달 시 Fail-Closed 차단.
   - **Layer 2 (컨테이너 실물 감사)**: MP4 1080p 25fps CFR, AAC 48k stereo, EBU R128 (-16 LUFS), Stream Parity ($|t_{\text{video}} - t_{\text{audio}}| \le 0.050\text{s}$) 검증.
   - **Layer 3 (메타데이터 바인딩)**: 실측 SHA-256 체인을 `release_manifest.json`에 영구 박제.
6. **3-Tier State Execution 아키텍처 (오프라인/온라인 전이)**:
   - 포트 3093/9222 비활성 시에는 `Local Synthetic Mode`로 안전 격리하여 거짓 완료를 원천 차단한다.
   - 실 서비스 기동 시 `Preflight Probe Gate`를 통해 미가동 시 즉각 Fail-Closed(HTTP 503) 차단하며, 가동 확인 시 100% 멱등한 `Live Production`으로 전이한다.
7. **Windows Pytest Basetemp 충돌 영구 치유 [ERR-044]**:
   - `conftest.py`에 프로세스 ID 및 타임스탬프 기반의 세션 격리 임시 디렉터리 훅을 탑재하여 `[WinError 145/183]` 파일 락 충돌을 원천 박멸한다.

---

## 3. 상세 실행 로드맵 (8단계 실행 계획)

### Phase 0 — 환경 격리, 결함 박멸 및 프로필 리졸버 선제 구축 (P0)

- [x] `pytest.ini`에 `addopts = -v --basetemp=D:/module/scratch/pytest_tmp`를 추가하고, C: 드라이브 임시 파일 유입을 차단한다.
- [x] `tests/test_sentence_audio_padding.py`의 FFmpeg `anullsrc` 필터에 `:d=0.4`를 명시하고 `-t` 옵션을 강제하여 17GB 무한 PCM 스트림 버그를 원천 소거한다.
- [x] 대형 미디어 테스트에 `@pytest.mark.media_heavy` 마커를 부여하여 일반 단위 테스트와 실행을 물리적으로 격리한다.
- [x] `studio_gui_server.py`의 약 3,850줄 인라인 HTML/CSS/JS 문자열을 `human_archive/static/index.html`로 물리 분리하고, 서버 코드를 2,300줄로 슬림화한다.
- [x] `human_archive/scripts/lib/profile_resolver.py`를 신설하여 `channel_profiles.yaml`, `visual_pacing_profiles.yaml`, `delivery_profiles.yaml`을 단일 `PipelineContext` 불변 객체로 해석한다.
- [x] `human_archive/tests/test_profile_resolver.py`를 작성하여 `nollam_file_v1` 기본 선택, unknown profile fail-closed, policy hash 재현성을 검증한다.
- [x] 프로젝트 루트 `conftest.py`에 프로세스·나노초 기반 세션별 고유 임시 디렉터리 훅을 탑재하여 Windows pytest basetemp 충돌([ERR-044])을 격리한다. 현재 동일 원인의 5개 테스트 연쇄 크래시는 재현되지 않았으므로 스트레스 재현은 별도 운영 검증으로 남긴다.

*완료 기준: pytest 실행 시 C: 드라이브 용량 소모 0MB, profile_resolver 단위 테스트 통과, GUI 인라인 HTML 분리 완료, ERR-044 회귀 0건.*

---

### Phase 1 — 대본 계약, 문맥 안전 분절 및 역방향 무효화 (P0)

- [x] `human_archive/schemas/sentence_contract_v1.schema.json`을 배포한다 (`spoken_text`, `display_text`, `phase`, `claim_ids`, `fact_grade`, `visual_intent` 필수화).
- [x] `cinematic_editing_director.py`의 L336 35자 단순 공백 슬라이싱을 완전 폐기하고, 한국어 형태소/시맨틱 종결어미(`-고`, `-며`, `-지만`, `-는데`) 기반의 `split_sentence_by_semantic_clause`를 구현한다.
- [x] `human_archive/scripts/lib/script_contract.py`를 신설하여 문장 순서, 필수 필드, 5-Phase, 20초 이내 반전, 38초 로드맵 데드라인을 검증한다.
- [x] `lib/downstream_invalidation.py`에 문장 내용 변경 샷을 content hash로 식별하고 하위 artifact row를 `BLOCKED + stale`로 fail-closed 처리하는 세분화된 무효화 체인을 구현한다.
- [x] `human_archive/tests/test_script_contract_nollam.py`와 `test_semantic_clause_splitter.py`를 작성하여 비문 발생 0건 및 팩트체크 무효화 루프를 검증한다.

*완료 기준: 대본 문장 분절 시 명사/조사 절단 비문 0건, 팩트체크 수정 시 stale 체인 정상 발동.*

---

### Phase 2 — SuperTonic3 실측 TTS SSOT 및 0.35~0.50s 룸톤 스티칭 (P0)

- [x] `build_sentence_audio_master.py`의 publishable 기본 모드를 `supertonic3`로 고정하고, `ToneFixtureProvider`의 `silence_duration` 매개변수 불일치(TypeError 3건)를 수정한다.
- [x] 오프라인 테스트 환경에서 3093 포트를 무방비 호출하지 않도록 `ToneFixtureProvider` 모의 인터페이스를 완전 정합화한다.
- [x] 문장 간 호흡 묵음을 **정확히 0.35s~0.50s의 유한 deterministic low-level room-tone**으로 스티칭하고, 사전 추정 시간에 맞추기 위해 수십 초의 `tail_silence`를 채워 넣던 조작 경로를 차단한다.
- [x] `sentence_audio_manifest.json`에 각 문장별 실측 duration, start/end, `wav_sha256`, provider provenance와 0.35~0.50s room-tone provenance를 기록하도록 확장한다.
- [x] `test_sentence_audio_timeline.py`와 `test_audio_timeline_v2.py`에서 실측 시간 정합성, 0.35~0.50s 범위, 유한 오프라인 fixture 및 비제로 룸톤 브리지를 검증한다.

*완료 기준: 문장별 WAV와 마스터 오디오 간 오차 0.001s 이내, tail_silence 0건, 오프라인 테스트 100% 통과.*

---

### Phase 3 — 2계층 하이브리드 페이싱 스케줄러 구현 (P0)

- [x] `human_archive/scripts/lib/pacing_scheduler.py`를 신설하여 master shot과 perceptual cut을 분리한다.
- [x] **런타임 비율 정규화**: 7-Zone 경계를 절대 초가 아닌 누적 발화 비율($t/T_{\text{actual}}$)로 계산하여 가변 런타임에 대응한다.
- [x] **마스터 샷 예산(Layer 2)**: canonical `calculate_variable_shot_budget`에서 15분 58장 / 20분 71장 / 25분 92장의 스케줄을 생성한다.
- [x] **파생 지각 컷(Layer 3) 계획**: 마스터별 2개 reframe cut을 생성하여 20분 기준 142개 컷과 70개 derived variant를 산출한다.
- [x] **씬 1번 훅 2단계 분할 계획**: 11초 master를 6초 `BARETIP_VIDEO` + 5초 `FLOW_IMAGE` 지각 컷으로 바인딩한다.
- [x] `test_pacing_scheduler.py`에서 15분/20분/25분 예산, 7-Zone 비율, 단조 템포, 훅 분할, 120~145 컷 범위를 검증한다.

*완료 기준: 마스터 이미지 수량 71장 유지, 지각 컷 120개 이상 달성, 씬 1번 11초 정체 해소.*

---

### Phase 4 — 시네마틱 프롬프트 분리 및 다형성 에셋 계약 (P1)

- [x] `human_archive/config/nollam_file_visual_policy.yaml`을 canonical style source로 로드·검증하고, 조선 궁궐/선비/잉크두들 키워드가 요청에 유입되면 fail-closed한다.
- [x] `human_archive/scripts/lib/aligned_prompt_compiler.py`에 NOLLAM 전용 컴파일러를 추가하여 4-Look 로테이션, 하단 18% 클리어존, exact 4 자막 배제문, 정책 SHA와 1920x1080/25fps 캔버스를 바인딩한다.
- [x] `human_archive/schemas/polymorphic_asset_contract_v1.schema.json`과 `lib/asset_contract.py`를 추가하고 `FLOW_IMAGE` 생성 매니페스트에 타입을 기록한다. `BARETIP_VIDEO`·`HYPERFRAMES_VIDEO`의 duration/fps 계약도 검증한다.
- [x] `human_archive/tests/test_nollam_prompt_profile.py`를 작성하여 역사/현대 주제 모두에서 레거시 키워드 0건, 4-Look, 훅 에셋 타입, 배치 진입점과 다형성 요청 무결성을 검증한다.

*완료 기준: NOLLAM 프롬프트에서 조선/선비 잔재 0건, 다형성 에셋 스키마 검증 통과.*

---

### Phase 5 — Google Flow 단일 진행 불변식 전역 일원화 (P0)

- [x] Flow 상태 판정은 `flow_generation_state.py`, 브라우저 DOM 복구/GC는 `lib/flow_dom_maintenance.py`로 분리해 ERR-027 핵심 정책을 일원화했다.
- [x] `flow_cdp_service.py`, `generate_flow_batch.py`, `run_neanderthal_full_pipeline.py`, `run_san_jose_20min_flow_production.py`가 공통 idle/error/GC 모듈을 호출하도록 리팩토링했다.
- [x] `asset_has_download_evidence`와 공용 `validate_download_evidence`를 실제 파일 존재, 바이트 크기, PIL 디코드, 1920x1080 해상도, SHA-256 검증으로 강화했다.
- [x] `test_flow_state_machine.py`, `test_flow_dom_maintenance.py`, `test_flow_batch_state.py`에서 idle gate, 지터 쿨다운, 공통 DOM 계약, 다운로드 해시/물리 검증을 검증했다.

*완료 기준: 3대 Flow 진입점이 단일 상태 머신 공유, 동시성 1 초과 0건, 다운로드 실측 무결성 100%.*

---

### Phase 6 — 시네마틱 하이브리드 렌더러 및 자막 SSOT 직결 (P0)

- [x] `smooth_subpixel_motion_engine.py`로 모션 렌더 엔진을 단일화하고, 바이페이직 궤적을 정식 구현했다.
- [x] `run_neanderthal_full_pipeline.py`의 `bare_tip_whiteboard` 회피 코드(`push_in` 치환)를 제거하고, `srt-whiteboard-animation/scripts/stream_render.py --bare-tip`을 씬 1번에 정식 합성한다.
- [x] 네안데르탈인 전용 자막 생성기를 `semantic_subtitle_engine.py`(52pt Pretendard, 한 줄 최대 36자, 최대 2줄 70자, MarginV=55)로 직결했다.
- [x] `render_episode_v2.py`에 선택적 `bgm.wav` 입력 시 -18dB BGM gain + 음성 sidechaincompress/dynamic ducking을 결합했다.
- [ ] 자막 마이크로 클로즈 타임 슬라이싱 로직을 정식 탑재하여 50초 롱테이크 문장을 16~17초 단위 2~3개 자막 이벤트로 자동 분할한다.
- [ ] 3중 실물 감사 엔진(`human_archive/scripts/lib/three_tier_postflight.py`)을 신설하여 Stream Parity ($|t_{\text{video}} - t_{\text{audio}}| \le 0.050\text{s}$)를 fail-closed로 검증한다.

*완료 기준: 렌더링 시 픽셀 저더 0건, 바이페이직 모션 실작동, 자막 36자 2줄 엄수, Stream Parity 0.050s 이내 달성.*

---

### Phase 7 — 구형 네안데르탈인 전면 재생성, GUI 잔여 결함 수정 및 릴리스 (P0)

- [x] **DEFECT-01 수정**: `routes/pipeline_routes.py`의 `NOLLAM-HIMALAYA-MASTER-1200S-FINAL.mp4` 하드코딩을 제거하고 활성 에피소드의 candidate/output/root에서 master/final MP4를 동적으로 탐색한다.
- [x] **DEFECT-02 수정**: `routes/script_routes.py`의 `font_size: int = 56` 기본값을 SSOT 52pt로 정합한다.
- [x] **DEFECT-03 1차 분리**: `/api/history/videos`·`/api/history/stream/{video_id}` 엔드포인트를 `routes/history_routes.py` factory로 이동하고 기존 Production History Engine은 collector 의존성으로 주입해 UI 메타데이터를 보존했다.
- [ ] **DEFECT-03 2차 정리**: `studio_gui_server.py`에 남은 레거시 `get_all_completed_video_projects()` scanner 구현을 `history_routes.py` 또는 별도 service로 완전히 이동하고 서버에는 DI wiring만 남긴다.
- [ ] **구형 네안데르탈인 전면 클린 리빌드**:
  1. SuperTonic3 M2 48kHz stereo로 39개 문장 음성을 재합성한다.
  2. 문장 간 0.35~0.50s 룸톤을 스티칭하여 `neanderthal_master_audio_48k.wav`를 재구축한다.
  3. 자막 마이크로 클로즈 3분할로 `pilot_subtitles_1200s.ass`(36자 2줄 피라미드)를 전수 재생성한다.
  4. 씬 1번 베어팁 선화(6s) + 실사 디테일(5s) 및 2~39번 실사 모션 클립을 실측 오디오 길이에 1:1 일치시켜 렌더링한다.
  5. 최종 마스터 비디오를 재합성하고 3중 실물 감사를 통과시킨다.
- [ ] `postflight_release.py`에 Layer 1(WAV 48k stereo 39개 전수, ASS 36자 2줄 전수), Layer 2(최종 Stream Parity <= 0.05s **및 원천 오디오/실측 씬 타임라인 대비 최종 오디오 parity <= 0.05s**), Layer 3(실측 SHA Merkle 체인) 감사를 바인딩한다. 최종 MP4 내부 스트림만 비교하는 검사는 52초 절삭을 놓칠 수 있으므로 단독 합격 기준으로 사용하지 않는다.
- [ ] `PROJECT_MEMORY.md`, `TASK.md`, `PROGRESS.md`, `ERRORS.md`에 최종 SHA-256과 실측 런타임을 동기화한다.

*완료 기준: 52초 오디오 절삭 0건, 자막 36자 초과 0건, WAV 44.1k 모노 0건, 3중 실물 감사 100% PASS.*

### Round 2 리뷰 판정 보정 (2026-09-10)

- **채택**: 원천 WAV 1007.969396초와 최종 MP4 비디오 955.680초의 52.289396초 차이, 실제 최종 mux의 `-shortest`, 44.1kHz mono 입력 39개, 자막 36자 초과 40개 라인, 정적 master 경로와 56pt 기본값은 코드·ffprobe·ASS 전수 검사로 확인됐다.
- **부분 채택**: ERR-044는 고정 `--basetemp`와 실제 잔여 디렉터리로 구조적 위험을 확인했고 세션 격리 훅을 적용했다. 다만 리뷰에 적힌 특정 5개 테스트의 동시 연쇄 크래시는 현재 독립 재현하지 않았으므로 재현 사실로 확정하지 않는다.
- **보정**: 최종 MP4 내부 video/audio parity만으로는 원천 오디오 절삭을 탐지할 수 없다. Gate 7은 최종 스트림 parity와 원천 오디오·실측 씬 타임라인 대비 최종 오디오 parity를 모두 요구한다.
- **보존**: history API는 factory로 분리했지만 기존 Production History Engine의 표시 메타데이터를 collector DI로 유지했다. 레거시 scanner의 완전 이동은 동작 회귀 없이 별도 후속 단계로 둔다.

---

## 4. 검증 게이트 및 테스트 계획 (Verification Gates)

| 게이트 | 검증 항목 | 합격 기준 (Acceptance Criteria) |
| :--- | :--- | :--- |
| **Gate 0 (Env/Infra)** | D: 드라이브 샌드박스 & ERR-044 치유 | C: 드라이브 소모 0MB, Windows pytest basetemp 충돌 0건 |
| **Gate 1 (Script/Fact)** | 시맨틱 분절 & 팩트체크 stale | 비문 발생 0건, 팩트체크 수정 시 하위 산출물 자동 invalidation |
| **Gate 2 (Audio SSOT)** | 실측 TTS & 0.35~0.50s 룸톤 | 48kHz stereo, `tail_silence` 0건, 39개 전수 SHA-256 바인딩 |
| **Gate 3 (Pacing/Cut)** | 2계층 하이브리드 페이싱 | 마스터 이미지 71장, 지각 컷 120~145개, 씬 1번 2단계 분할 |
| **Gate 4 (Prompt/Asset)** | 프롬프트 정화 & 다형성 에셋 | 조선/선비 잔재 0건, MP4/JPEG 다형성 스키마 검증 통과 |
| **Gate 5 (Flow CDP)** | 단일 진행 불변식 & 지터 쿨다운 | `max_in_flight=1`, 14~17s 쿨다운, 1장 1완결 무결성 |
| **Gate 6 (Cinema Render)** | 서브픽셀 바이페이직 & 자막 3분할 | 픽셀 저더 0건, 바이페이직 모션 실작동, 자막 36자 2줄 엄수, -18dB BGM 덕킹 |
| **Gate 7 (3-Tier Postflight)** | 3중 실물 감사 및 Stream Parity | **$|t_{\text{video}} - t_{\text{audio}}| \le 0.050\text{s}$**이며 **$|t_{\text{source-audio/scene}} - t_{\text{final-audio}}| \le 0.050\text{s}$**, WAV 48k stereo 39개 전수 합격, ASS 36자 초과 0건 |

---

## 5. 실행 우선순위 (Priority)

1. **P0 (치명적 릴리스 차단 결함)**: Phase 6 자막 마이크로 슬라이싱 및 3중 감사 엔진, Phase 7 구형 네안데르탈인 전면 재생성 (52초 오디오 절삭 치유).
2. **P1 (유지보수성 및 인프라 완결)**: DEFECT-03 레거시 scanner 2차 이동, 전 운영 문서 SHA 동기화, ERR-044 반복 실행 스트레스 검증.
