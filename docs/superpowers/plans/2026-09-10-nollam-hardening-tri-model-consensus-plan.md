# NOLLAM 코드베이스·워크플로우·대본 페이싱 쇄신 계획 (삼사 만장일치 강화판 — Round 4 마스터 갱신)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Tri-Model Consensus Audit Evidence:**
> - Round 1 Review Report: [`D:\module\bible\docs\superpowers\reviews\2026-09-10-nollam-pacing-audit-tri-model-review.md`](file:///D:/module/bible/docs/superpowers/reviews/2026-09-10-nollam-pacing-audit-tri-model-review.md)
> - Round 2 Review Report: [`D:\module\bible\docs\superpowers\reviews\2026-09-10-nollam-hardening-v2-tri-model-review.md`](file:///D:/module/bible/docs/superpowers/reviews/2026-09-10-nollam-hardening-v2-tri-model-review.md)
> - Round 2 Knowledge Doc: [`D:\module\bible\docs\solutions\integration-issues\nollam-round2-av-contract-router-hardening-2026-09-10.md`](file:///D:/module/bible/docs/solutions/integration-issues/nollam-round2-av-contract-router-hardening-2026-09-10.md)
> - Round 3 Review Report: [`D:\module\bible\docs\superpowers\reviews\2026-09-10-nollam-round3-av-hardening-tri-model-review.md`](file:///D:/module/bible/docs/superpowers/reviews/2026-09-10-nollam-round3-av-hardening-tri-model-review.md)
> - Round 3 Master Execution Plan: [`D:\module\bible\docs\superpowers\plans\2026-09-10-nollam-hardening-round3-master-execution-plan.md`](file:///D:/module/bible/docs/superpowers/plans/2026-09-10-nollam-hardening-round3-master-execution-plan.md)
> - Round 3 Consensus Audit: [`D:\module\audit\nollam_hardening_v3_tri_model_audit\final_consensus_synthesis.md`](file:///D:/module/audit/nollam_hardening_v3_tri_model_audit/final_consensus_synthesis.md) (99.92점)
> - Round 4 Review Report: [`D:\module\bible\docs\superpowers\reviews\2026-09-10-nollam-round4-av-hardening-tri-model-review.md`](file:///D:/module/bible/docs/superpowers/reviews/2026-09-10-nollam-round4-av-hardening-tri-model-review.md)
> - Round 4 Master Execution Plan: [`D:\module\bible\docs\superpowers\plans\2026-09-10-nollam-hardening-round4-master-execution-plan.md`](file:///D:/module/bible/docs/superpowers/plans/2026-09-10-nollam-hardening-round4-master-execution-plan.md)
> - Round 4 Consensus Audit: [`D:\module\audit\nollam_hardening_v4_tri_model_audit\final_consensus_synthesis.md`](file:///D:/module/audit/nollam_hardening_v4_tri_model_audit/final_consensus_synthesis.md)
> - Round 4 Matrix & Score: [`D:\module\audit\nollam_hardening_v4_tri_model_audit\cross_critique_matrix.json`](file:///D:/module/audit/nollam_hardening_v4_tri_model_audit/cross_critique_matrix.json) (종합 99.92점 만장일치 통과)

**Goal:** `nollam_file_v1`을 선택했을 때 대본의 사실성·문맥 안전 분절·실측 TTS 호흡(0.35~0.50s 룸톤)·2계층 하이브리드 페이싱(마스터 71장 예산 + 120~145개 파생 지각 컷)·52.3초 오디오 절삭 및 립싱크 파탄 척결·자막 마이크로 클로즈 3분할(36자 2줄 엄수)·네안데르탈인 48kHz stereo 전면 재생성·3중 실물 감사(컨테이너/입력/메타데이터) 및 3-Tier 오프라인 격리 게이트가 하나의 불변 계약과 단일 파이프라인으로 연결되도록 시스템을 하드닝한다.

**Architecture:** 대본 문장(`sentence`), 의미 샷(`narration_shot`), 시청자 지각 컷(`perceptual_cut`)의 3계층 분리를 단일 진실 공급원(SSOT)으로 확립한다. 발화 오디오 길이를 인위적으로 클램핑하지 않고, SuperTonic3 M2 실측 발화 시간($T_{\text{speech}}$)에 0.40s(앞 0.15s + 뒤 0.25s) 유한 룸톤을 합산한 실제 시간($T_{\text{scene}}$)으로 비디오 클립과 자막을 1:1 일치 렌더링한다. 프로필 리졸버가 editorial/script/audio/visual/delivery 정책을 불변 `PipelineContext`로 해석하며, Google Flow CDP는 `max_in_flight=1` 단일 진행 게이트와 적응형 14~17s 지터 쿨다운을 전역 강제한다. 모션 엔진은 `smooth_subpixel_motion_engine.py`로 단일화하여 2단계 바이페이직 켄번즈를 정식 구동하고, 자막은 `semantic_subtitle_engine.py`(52pt Pretendard, 36자 2줄 피라미드)로 100% 직결한다.

**Tech Stack:** Python 3.13, pytest, JSON Schema, YAML 정책 파일, SuperTonic3 HTTP & ToneFixture, Google Flow CDP, PIL Subpixel Bicubic (120% Overscan), FFmpeg/ffprobe, existing Human Archive & NOLLAM manifests.

## Round 5 사후 감사 상태 — V4 기준선 보존 및 V5 하드닝으로 이관

2026-09-11 직접 검증에서 V4 MP4·미러 SHA-256과 root non-media 테스트 628 passed를 확인했다. 다만 `run_neanderthal_full_pipeline.py`가 planner effect ID를 실제 renderer profile로 전달하지 않아 현재 코드 규칙상 39개 planned effect가 모두 `push_in`으로 폴백되는 문제가 발견됐다. 또한 `postflight_release.py`는 manifest boolean을 읽지만 encoded MP4의 실제 motion/정지 프레임을 재계산하지 않으며, 일부 memory/skill/legacy manifest에는 과거 Bare-Tip 정책이 남아 있다.

따라서 아래 Round 4 구현 완료 표시는 V4의 Visible-First opening과 파일 무결성에 한정한 기준선 기록으로 취급한다. 실제 beat-aware/Tri-Phasic motion과 physical postflight를 완결할 후속 계획은 [`2026-09-11-nollam-v4-post-release-hardening-plan.md`](file:///D:/module/bible/docs/superpowers/plans/2026-09-11-nollam-v4-post-release-hardening-plan.md)에서 V5 candidate로 실행한다. V4 파일과 V2/V3 historical manifest는 덮어쓰지 않는다.

## Round 4 방향 전환 — Visible-First Opening 및 Beat-Aware Dynamic Motion

> 이 섹션은 아래 Phase 3·4·6·7에 남아 있는 기존 `씬 1번 베어팁 강제` 항목을 **정책상 supersede**한다. 기존 체크 표시는 과거 구현 이력으로 보존하지만, 다음 실행부터의 목표 계약은 이 섹션을 따른다.

- `SHOT_001`/`SCN_001`을 `bare_tip_whiteboard`로 강제하지 않는다. 첫 프레임부터 주제와 피사체가 즉시 식별되는 `FLOW_IMAGE`를 사용한다.
- `BARETIP_VIDEO`와 `--bare-tip` 렌더러는 삭제하지 않는다. 단, 본문에서 “손으로 그리는 설명”, “유물 구조 해설”, “과정 재구성”이 명시된 비오프닝 장면에만 선택적으로 허용한다. `order=1`, `opening`, `cold_open`에는 fail-closed로 금지한다.
- 첫 11초는 빈 화이트보드 1장을 오래 보여주는 구조가 아니라, 동일 내레이션 시간축 안에서 3개의 **보이는 FLOW 컷**(wide context → subject/action → evidence detail)으로 계획한다. 컷 경계는 오디오를 자르지 않고 perceptual cut만 교체한다.
- 효과 선택은 `MOTION_CYCLE` 단순 순환을 폐기하고, 대본 비트·시각 초점·샷 스케일·직전 효과·다음 장면의 초점을 함께 평가하는 결정론적 `beat-aware effect planner`로 전환한다.
- “후반부로 갈수록 느려지는 전환”은 화면 정지를 뜻하지 않는다. 후반 샷은 컷 빈도를 낮추되, 각 롱테이크 안에서 2~3개의 모션 국면·초점 이동·미세 리프레임을 유지한다.

### Round 4에서 실제로 확인된 근거

| 확인 대상 | 실측 결과 | 판정 |
|---|---:|---|
| 현재 `SHOT_001.jpg` | 1920×1080의 실제 빙하기 장면은 존재 | 원본 Flow 이미지는 첫 화면 후보로 사용 가능 |
| 현재 마스터 2.0초 프레임 | 베어팁 잉크 선화와 넓은 빈 캔버스가 주 화면, 자막만 하단 표시 | “첫 화면이 안 보인다”는 사용자 피드백과 일치 |
| `run_neanderthal_full_pipeline.py` | `idx == 0 or effect == "bare_tip_whiteboard"`로 첫 클립 강제 | 첫 씬 강제의 직접 원인 |
| `CinematicEditingDirector.plan_scene_effects()` | 첫 샷을 무조건 `bare_tip_whiteboard`로 지정 | 두 번째 강제 지점 |
| `build_cinematic_master_pipeline.py` | `planned[0]`이 베어팁인지 assert | CLI 실행 차단 지점 |
| `pacing_scheduler.py` | 첫 master 11초, 첫 cut `BARETIP_VIDEO`로 고정 | 시간표·에셋 바인딩 강제 지점 |
| `/api/cinematic/effects_plan` 및 GUI | opening 기본값·배너·뱃지가 베어팁을 성공 기준으로 표시 | 운영자가 잘못된 정책을 재선택할 수 있는 지점 |
| `smooth_subpixel_motion_engine.py` | 6개 단일 궤적과 고정 바이페이직 중심점, 피사체 초점 인자 없음 | 단조로운 효과의 구조적 원인 |

### Round 4 목표 데이터 계약

첫 opening group은 기존 `SHOT_001` 음성 시간축을 유지하면서 다음처럼 표현한다.

```json
{
  "shot_id": "SHOT_001",
  "scene_role": "opening_group",
  "asset_type": "FLOW_IMAGE",
  "cuts": [
    {"cut_id": "CUT_001", "asset_type": "FLOW_IMAGE", "visual_role": "context_wide", "duration_sec": 3.0},
    {"cut_id": "CUT_002", "asset_type": "FLOW_IMAGE", "visual_role": "subject_action", "duration_sec": 3.5},
    {"cut_id": "CUT_003", "asset_type": "FLOW_IMAGE", "visual_role": "evidence_detail", "duration_sec": 4.5}
  ],
  "motion_plan": {
    "family": ["reframe", "lateral_reveal", "macro_push"],
    "beat_bindings": ["question", "threat", "evidence"],
    "transition": ["hard_cut", "match_cut"]
  }
}
```

3초/3.5초/4.5초는 기본 프로필이며, 실제 `T_scene`이 11초가 아니면 같은 비율을 `T_scene`에 재분배한다. 어떤 경우에도 `T_speech`를 줄이거나 영상 끝을 오디오보다 먼저 닫지 않는다.

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
- [x] **과거 씬 1번 훅 2단계 분할 계획**: 11초 master를 6초 `BARETIP_VIDEO` + 5초 `FLOW_IMAGE`로 계획했으나, Round 4에서 이 기준을 폐기하고 첫 12초 3개 `FLOW_IMAGE` opening group으로 교체한다.
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
- [x] **과거 구현 이력**: `run_neanderthal_full_pipeline.py`에서 `srt-whiteboard-animation/scripts/stream_render.py --bare-tip`을 씬 1번에 합성했다. Round 4에서는 씬 1번 자동 합성을 제거하고 본문 선택 장면으로 제한한다.
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
| **Gate 3 (Pacing/Cut)** | 2계층 하이브리드 페이싱 | 마스터 이미지 예산 유지, 지각 컷 120~145개, 첫 12초 3개 `FLOW_IMAGE` opening group, 시간축 연속 |
| **Gate 4 (Prompt/Asset)** | 프롬프트 정화 & 다형성 에셋 | 조선/선비 잔재 0건, MP4/JPEG 다형성 스키마 검증 통과 |
| **Gate 5 (Flow CDP)** | 단일 진행 불변식 & 지터 쿨다운 | `max_in_flight=1`, 14~17s 쿨다운, 1장 1완결 무결성 |
| **Gate 6 (Cinema Render)** | 서브픽셀 바이페이직 & 자막 3분할 | 픽셀 저더 0건, 바이페이직 모션 실작동, 자막 36자 2줄 엄수, -18dB BGM 덕킹 |
| **Gate 7 (3-Tier Postflight)** | 3중 실물 감사 및 Stream Parity | **$|t_{\text{video}} - t_{\text{audio}}| \le 0.050\text{s}$**이며 **$|t_{\text{source-audio/scene}} - t_{\text{final-audio}}| \le 0.050\text{s}$**, WAV 48k stereo 39개 전수 합격, ASS 36자 초과 0건 |

---

## 5. 실행 우선순위 (Priority)

1. **P0 (치명적 릴리스 차단 결함)**: Phase 6 자막 마이크로 슬라이싱 및 3중 감사 엔진, Phase 7 구형 네안데르탈인 전면 재생성 (52초 오디오 절삭 치유).
2. **P1 (유지보수성 및 인프라 완결)**: DEFECT-03 레거시 scanner 2차 이동, 전 운영 문서 SHA 동기화, ERR-044 반복 실행 스트레스 검증.

---

## Round 4 전수 수정 인벤토리 및 실행 계획

### 6. 수정 범위 누락 방지 매트릭스

아래 목록은 `run_neanderthal_full_pipeline.py` 한 파일만 바꾸는 방식으로는 제거되지 않는 정책·계획·렌더·GUI·테스트 연결을 모두 열거한 것이다. `SHOT_001`이라는 일반적인 샷 식별자 자체는 삭제하지 않는다. 삭제 대상은 **첫 샷과 Bare-Tip을 자동으로 결합하는 규칙**이다.

| 우선순위 | 파일 | 현재 결합 | 필요한 변경 | 검증 |
|---|---|---|---|---|
| P0 | `human_archive/scripts/lib/cinematic_editing_director.py` | 첫 샷 강제 베어팁, 6개 모션 modulo 순환 | 첫 샷은 `FLOW_IMAGE` visible hook으로 계획; `beat-aware effect planner`에 역할·초점·최근 효과·다음 초점 입력 | planner unit test, opening asset type, 10-shot diversity |
| P0 | `human_archive/scripts/lib/pacing_scheduler.py` | 첫 11초가 `BARETIP_VIDEO` + `FLOW_IMAGE`로 고정 | 첫 master의 3개 perceptual cut을 모두 `FLOW_IMAGE`로 바인딩; 실제 `T_scene` 비율 재분배 | 300/960/1200/1560초 synthetic E2E |
| P0 | `human_archive/scripts/run_neanderthal_full_pipeline.py` | `idx == 0 or effect == "bare_tip_whiteboard"`로 첫 클립 강제 | opening은 일반 이미지 모션 렌더 경로로만 진입; 본문 선택 베어팁만 명시적 role로 허용 | command spy, no opening bare-tip invocation |
| P0 | `human_archive/scripts/build_cinematic_master_pipeline.py` | 첫 효과가 베어팁인지 assert | visible opening gate, 효과 가족 다양성 gate, 오디오·비디오 시간축 gate로 교체 | CLI planner contract test |
| P0 | `human_archive/scripts/smooth_subpixel_motion_engine.py` | push/pull/pan/tilt의 단일 궤적; 후반도 고정 중심 바이페이직 | focal point, direction, amplitude, phase list를 받는 모션 프로파일과 2~3단계 piecewise trajectory 추가 | trajectory continuity, crop bounds, dynamic-change tests |
| P0 | `human_archive/scripts/lib/motion_engine_v3.py` | canonical renderer adapter만 위임 | 새 profile을 canonical engine으로 전달하고 별도 궤적 계산을 금지 | adapter parity test |
| P0 | `human_archive/scripts/lib/asset_contract.py` | asset type만 검사; opening 위치 제약 없음 | `scene_role`/`opening_allowed` 정책을 검증하고 opening의 `BARETIP_VIDEO`를 거부 | schema and fail-closed tests |
| P0 | `human_archive/schemas/polymorphic_asset_contract_v1.schema.json` | `BARETIP_VIDEO`가 어디든 허용 | additive placement/role field와 opening prohibition을 schema 또는 gate에 명시 | JSON Schema validation |
| P0 | `human_archive/scripts/lib/nollam_visual_gate.py` | 오버레이 텍스트만 검사 | 첫 프레임 visibility score, non-background coverage, focus anchor, opening asset policy 추가 | blank/sparse/valid fixture |
| P0 | `human_archive/scripts/lib/visual_content_qa.py` 및 `visual_qa.py` | OCR 중심; 빈 화면 판정 없음 | 이미지 점유율·에지 밀도·주 피사체 존재 판정과 `REVIEW_REQUIRED` 상태 추가 | QA fixture and threshold report |
| P1 | `human_archive/scripts/lib/aligned_prompt_compiler.py` | `visual_mode`에 `bare_tip` 문자열이 있으면 BARETIP_VIDEO | `order=1` 또는 `scene_role=opening_group`의 bare-tip mode를 거부하고 visible FLOW request를 요구 | prompt compiler tests |
| P1 | `human_archive/scripts/generate_video_prompts.py` | 모션·주제 분리가 약하고 첫 컷의 visual intent가 부족 | prompt payload에 `scene_role`, `beat_type`, `focal_subject`, `shot_scale`, `transition_hint`를 바인딩 | request hash snapshot |
| P1 | `human_archive/scripts/flow_cdp_service.py` 및 `generate_flow_batch.py` | Flow 결과는 파일·해상도·SHA 중심으로 승인 | visibility gate와 opening role을 승인 조건에 연결; 실패 시 placeholder 금지 | Flow contract tests |
| P1 | `human_archive/scripts/historical_parallel_engine.py` | legacy `motions` 배열과 “Shot 0 Bare-Tip” 문서/페이싱 설명 | 첫 장면을 visible hook으로 생성하고 canonical planner에 intent만 전달; legacy motion 직접 선택 제거 | generated manifest assertions |
| P1 | `human_archive/scripts/lib/visual_brief_provider.py` | brief에 motion profile만 전달 | focal subject/action/place/scale/emotion/beat를 planner 입력으로 보존 | brief contract test |
| P1 | `human_archive/config/visual_pacing_profiles.yaml` | hook은 4~6초 정책이지만 opening asset·다양성 계약 없음 | 3-cut visible opening, 2~4초 opening cut, family streak/window/hold 규칙 추가 | YAML resolver test |
| P1 | `human_archive/config/delivery_profiles.yaml` | phase별 컷 범위만 있음 | opening/mid/late의 motion intensity, transition budget, long-take internal phase 정책 추가 | profile resolver snapshot |
| P1 | `human_archive/config/nollam_file_visual_policy.yaml` | 캔버스·기본 이미지 정책만 존재 | `opening_asset_policy`, visibility threshold, allowed/forbidden asset placement를 canonical style source로 추가 | policy hash + gate test |
| P1 | `human_archive/config/visual_density_rules.md` | 초반 정적 금지 원칙은 있으나 베어팁 예외와 실제 측정치 없음 | visible-first opening 및 후반 internal-motion 규칙으로 갱신 | policy text lint |
| P1 | `human_archive/scripts/routes/render_routes.py` | API가 opening을 베어팁 성공으로 표시 | `opening_effect`, `opening_asset_type`, diversity metrics를 반환; 기본값도 visible FLOW로 변경 | route response tests |
| P1 | `human_archive/static/index.html` | 버튼·배너·toast·뱃지가 베어팁 강제를 홍보, 56개 샷 문구 잔존 | “Visible-first opening / Beat-aware motion”으로 문구·뱃지·fallback 변경 | static UI text test |
| P1 | `human_archive/scripts/build_master_video_sequential_v5.py` | 독립 legacy 모션·하드코딩된 2단계 궤적 | canonical planner/engine을 호출하거나 legacy entrypoint를 명시적으로 비활성화 | legacy entrypoint audit |
| P1 | `human_archive/scripts/render_ken_burns_clips.py` | manifest의 `camera_motion`을 직접 사용 | planner가 만든 profile만 소비하고 알 수 없는 motion은 fail-closed | route/CLI contract |
| P1 | `human_archive/scripts/build_natural_docu_audio.py` | `SHOT_001`부터 고정 camera motion 배열 | 시각 계획에서 audio 생성이 모션을 결정하지 않도록 필드 제거 또는 read-only provenance로 변경 | manifest diff test |
| P1 | `human_archive/scripts/omni_video_pipeline.py` | 별도 push/orbit/whip prompt 체계 | canonical effect vocabulary와 매핑; 실제 렌더 미지원 효과는 Flow video asset으로만 허용 | vocabulary test |
| P2 | `human_archive/tests/test_bare_tip_renderer_contract.py` | opening renderer와 `--bare-tip`를 성공 기준으로 고정 | bare-tip renderer 자체의 본문 선택 기능은 유지하되 opening 금지 테스트로 전환 | updated contract tests |
| P2 | `human_archive/tests/test_pacing_scheduler.py`, `test_nollam_synthetic_e2e.py` | 첫 컷 BARETIP 기대 | 첫 3컷 FLOW 기대, 시간축 보존, opening cut 다양성 검증 | full selected suite |
| P2 | `human_archive/tests/test_nollam_prompt_profile.py`, `test_polymorphic_asset_contract.py` | opening bare-tip 허용 | opening rejection 및 body-only bare-tip acceptance를 동시에 검증 | prompt/schema tests |
| P2 | `human_archive/tests/test_render_routes.py`, `test_nollam_render_contract.py` | API/렌더 계약에 베어팁 invariant | visible-first response와 no-opening-render command 검증 | route/render tests |
| P2 | 신규 `human_archive/tests/test_cinematic_effect_planner.py` | 없음 | beat-aware scoring, 최근 효과 회피, shot scale/role 매핑 검증 | isolated pytest |
| P2 | 신규 `human_archive/tests/test_opening_visibility_gate.py` | 없음 | 실제 `SHOT_001`처럼 피사체가 큰 이미지 PASS, 빈 잉크 캔버스 FAIL | isolated pytest |
| P2 | 신규 `human_archive/tests/test_motion_diversity.py` | 연속 동일 모션만 검사 | family/axis/focal scale/window 및 내부 phase 변화 검증 | isolated pytest |
| P2 | `human_archive/runs/.../release_manifest.json` 및 `postflight_release.py` | 베어팁 오프닝을 release invariant로 기록 | `opening_asset_type=FLOW_IMAGE`, visibility evidence, effect metrics를 SHA 바인딩 | physical postflight |
| P2 | `D:\module\.agents\skills\cinematic-hybrid-editing-director\SKILL.md` | 미래 작업자에게 첫 씬 베어팁을 절대 규칙으로 지시 | mandatory 문구 제거; optional body insert와 visible-first/dynamic rules로 개정 | skill pressure scenario |
| P2 | `D:\module\PROJECT_MEMORY.md`, `D:\module\DECISIONS.md`, `D:\module\TASK.md`, `D:\module\PROGRESS.md` | 기존 ADR/기억에 베어팁 첫 장면이 전역 불변식으로 남음 | Round 4 superseding decision과 미실행 상태를 명시; 과거 기록은 삭제하지 않음 | SHA and consistency audit |

### 7. 권장 연출안과 대안 비교

#### 권장안 — Visible-first Beat-Aware Hybrid

첫 12초에 실제 주제 이미지를 3개 컷으로 배치한다. 첫 컷은 장소·규모를 한눈에 보여주는 `context_wide`, 두 번째 컷은 인물/행동이 읽히는 `subject_action`, 세 번째 컷은 멸종의 단서가 되는 뼈·도구·환경 흔적을 보여주는 `evidence_detail`이다. 각 컷은 동일 narration shot의 오디오를 공유하며, 컷 경계만 바꾼다. `FLOW_IMAGE`는 장면을 직접 설명하고, 모션은 컷의 의미를 강화하는 보조 수단으로 제한한다.

장점은 첫 프레임의 정보량이 높고, Google Flow 결과가 바로 화면에 보이며, Bare-Tip 제거가 오디오·자막 시간축을 흔들지 않는다는 점이다. 추가로 첫 장면의 3가지 시각 역할이 이후 본문의 `wide → action → detail → evidence` 반복 구조를 예고하므로 단순한 줌 효과보다 서사적 약속이 분명하다.

#### 대안 A — 첫 이미지만 FLOW_IMAGE로 교체하고 11초를 유지

수정량은 가장 작지만 11초 동안 한 장을 계속 보여주면 현재의 단조로움이 남는다. 단순한 안전 패치로는 채택하지 않는다.

#### 대안 B — 첫 12초를 실제 Flow 영상(HYPERFRAMES_VIDEO) 하나로 대체

움직임은 풍부해질 수 있지만, 외부 영상 생성 품질·코덱·첫/마지막 프레임·추가 비용에 의존한다. 정지 이미지 기반 파이프라인의 결정론적 QA가 약해지므로 2차 확장안으로만 남긴다.

### 8. 새 모션 언어 — 반복 목록이 아니라 편집 문법

현재의 `MOTION_CYCLE`은 효과 이름만 바꾸므로 이미지 내용과 무관하게 같은 줌·팬 패턴이 반복된다. 새 planner는 각 장면에 다음 입력을 받는다.

```text
scene_role       = opening_group | mechanism | crisis | evidence | reflection | outro
beat_type        = question | reveal | threat | contradiction | evidence | consequence | pause
shot_scale       = extreme_wide | wide | medium_action | close_up | macro | insert
focal_subject    = 인물/유물/지형/흔적 중 하나의 명시적 앵커
focal_position   = left | center | right | upper | lower
emotion          = curiosity | urgency | dread | wonder | grief | reflection
previous_profile = 직전 효과의 family/axis/scale
next_focal_hint  = 다음 장면에서 시선이 이동할 방향
```

planner는 후보를 만든 뒤 다음 순서로 점수화한다.

1. `beat_type`와 `shot_scale`에 맞지 않는 효과를 제거한다. 예를 들어 `evidence + macro`에는 중앙 고정 줌만 반복하지 않고, 짧은 lateral reveal 또는 detail push를 우선한다.
2. 직전 2개 장면과 같은 `motion_family`, 같은 축, 같은 focal scale을 피한다. 같은 효과 이름이 아니어도 `push_in`만 계속되면 단조로움으로 계산한다.
3. 다음 장면의 피사체 위치와 맞닿는 방향을 가산한다. 오른쪽으로 나가는 장면 뒤에는 다음 샷에서 왼쪽 피사체로 match cut을 만들 수 있게 한다.
4. chapter 역할에 따라 강도를 제한한다. opening은 빠른 reframe과 hard/match cut, mechanism은 설명용 reveal, crisis는 짧은 push·diagonal drift·충격 cut, reflection은 느린 drift와 focal lock을 사용한다.
5. 동률일 때만 deterministic seed와 shot id로 안정적으로 결정한다. 랜덤 선택은 재개·해시·회귀 검증을 깨므로 사용하지 않는다.

#### 효과 family와 사용 계약

| family | 구현 효과 | 적합한 장면 | 금지/주의 |
|---|---|---|---|
| `reframe` | push-in, pull-out, diagonal drift | 질문, 인물, 핵심 물체 | 같은 축 2회 이상 연속 금지 |
| `lateral_reveal` | pan-left/right, edge-to-center reveal | 지형·이동·인과 관계 | 초점이 화면 밖으로 나가지 않게 clamp |
| `vertical_reveal` | tilt-up/down | 규모·하늘·절벽·층위 | 자막 clear zone 침범 금지 |
| `evidence_macro` | macro push, detail lock, short rack-like crop | 유물·뼈·도구·흔적 | 저해상도·빈 표면은 금지 |
| `perceptual_cut` | 6~12프레임 reframe/hard cut | opening, 반전, 숫자·증거 강조 | 음성/자막 시간축은 유지 |
| `graphic_bridge` | 제한적 HyperFrames HUD/data card | 좌표·연대·비교·인과 도식 | 모든 장면에 사용하지 않음 |
| `optional_baretip` | 본문 설명용 BARETIP_VIDEO | 구조·과정·도식 직접 설명 | `order=1`/opening/cold_open 금지 |

#### 초반·중반·후반 속도 곡선

- **0~12초:** 3.0/3.5/4.5초 기본 컷. 컷마다 화면 정보가 달라야 하며 첫 0.5초 안에 주 피사체가 읽혀야 한다.
- **12~120초:** 2.5~5.0초 중심의 rapid reframe. 같은 이미지의 crop만 연속 사용하지 않고, wide/action/detail을 교차한다.
- **120~360초:** 5.0~12.0초. 설명 문장에는 reveal·지도·증거 insert를 사용하고, 숫자 문장에만 HUD를 배치한다.
- **360초 이후:** 12.0~30.0초의 narration shot을 허용하되, 6~10초마다 focal scale 또는 내부 phase가 한 번 바뀐다. 장면이 30초를 넘으면 최소 3 phase(`context drift → focal approach → evidence lock`)를 기록한다.
- **마지막 10%:** 컷 수는 줄이되 단순 static hold로 끝내지 않는다. pull-out·ambient drift·현대적 대응 이미지·짧은 final lock으로 서사를 닫는다.

### 9. 수치형 단조로움 방지 게이트

다음 수치는 첫 구현의 고정 acceptance criteria다. 실제 시청 데이터가 쌓이면 KPI로 보정하되, 그 전에는 완화하지 않는다.

- 첫 12초: `opening_cut_count == 3`, 모든 컷 `asset_type == FLOW_IMAGE`, `opening_visibility == PASS`.
- 첫 프레임: non-background coverage `>= 15%`, edge density `>= 0.035`, focal subject bounding box `>= 8%` of frame area. 임계값을 계산할 수 없는 경우 `REVIEW_REQUIRED`로 fail-closed한다.
- 전체 계획: 같은 `motion_family` 연속 최대 2회, 같은 axis 연속 최대 2회, 같은 focal scale 연속 최대 2회.
- 임의의 10-shot window: 서로 다른 motion family `>= 4`, 서로 다른 shot scale `>= 3`, `hyperframes_hud` 비율 `<= 20%`.
- Tier 1: 5초를 초과하는 단일 perceptual cut은 설명 사유가 없으면 FAIL. 단, narration shot 총시간은 음성 실측값을 따른다.
- Tier 2: 12초를 초과하는 cut은 두 phase 또는 evidence transition을 manifest에 기록한다.
- Tier 3: 20초 초과 shot은 내부 phase `phase_count >= 2`, 30초 초과 shot은 `phase_count >= 3`.
- 정지 판정: 연속 프레임의 crop/scale 변화량이 1.0초 이상 0에 가까우면 FAIL. 의도된 `pause`는 화면 내 미세 drift 또는 명시적인 `static_intent`와 사유를 가져야 한다.
- 전환: hard cut, match cut, dissolve, graphic bridge 중 하나를 manifest에 기록하고, 전환 직전·직후 초점 방향을 비교한다. 임의의 fade-in/out을 기본값으로 사용하지 않는다.

### 10. 단계별 실행 태스크

#### Task 1 — 계약·정책을 visible-first로 먼저 고정

**Files:**

- Modify: `human_archive/config/nollam_file_visual_policy.yaml`
- Modify: `human_archive/config/visual_pacing_profiles.yaml`
- Modify: `human_archive/config/delivery_profiles.yaml`
- Modify: `human_archive/schemas/polymorphic_asset_contract_v1.schema.json`
- Modify: `human_archive/scripts/lib/asset_contract.py`
- Test: `human_archive/tests/test_polymorphic_asset_contract.py`
- Test: new `human_archive/tests/test_opening_visibility_gate.py`

- [ ] `scene_role`, `opening_asset_type`, `opening_visibility`의 의미와 허용값을 정책에 추가한다. opening의 허용 asset type은 `FLOW_IMAGE`, 본문 선택 기능의 `BARETIP_VIDEO`는 `scene_role != opening_group` 조건에서만 허용한다.
- [ ] 기존 BARETIP body fixture는 유지하고 `order=1` 또는 `opening_group` fixture가 `ValueError`를 내는 테스트를 먼저 작성한다.
- [ ] 1920×1080 valid scene, 빈 ivory canvas, 작은 잉크 흔적 fixture를 구성한다. valid scene은 coverage 15% 이상과 edge density 0.035 이상을 만족시키고, 빈 canvas는 둘 중 하나라도 미달하게 만든다.
- [ ] `python -m pytest -q human_archive/tests/test_polymorphic_asset_contract.py human_archive/tests/test_opening_visibility_gate.py`를 실행한다. 새 opening rejection 테스트는 구현 전 FAIL이어야 한다.
- [ ] 최소 구현 후 같은 명령이 PASS하고, JSON schema·정책 SHA가 함께 기록되는지 확인한다.

#### Task 2 — planner를 modulo cycle에서 beat-aware scoring으로 교체

**Files:**

- Create: `human_archive/scripts/lib/cinematic_effect_planner.py`
- Modify: `human_archive/scripts/lib/cinematic_editing_director.py`
- Modify: `human_archive/scripts/lib/visual_brief_provider.py`
- Modify: `human_archive/scripts/historical_parallel_engine.py`
- Test: new `human_archive/tests/test_cinematic_effect_planner.py`

- [ ] pure function `plan_effect(scene, previous_profiles, next_scene=None, seed_text="") -> dict`의 반환 필드를 `effect`, `motion_family`, `axis`, `focal_scale`, `phase_plan`, `transition`, `reason_codes`로 고정한다.
- [ ] 첫 scene은 `effect != bare_tip_whiteboard`, `asset_type == FLOW_IMAGE`, `scene_role == opening_group`을 반환하도록 테스트를 작성한다.
- [ ] `question + extreme_wide`, `evidence + macro`, `threat + medium_action`, `reflection + wide` 각각에 대해 최소 2개의 합법 후보가 나오고, 최근 2개 profile을 반복하지 않는지 검증한다.
- [ ] `CinematicEditingDirector.plan_scene_effects()`는 scoring planner를 호출하고 기존 `theme_color`, pacing tier, subtitle 필드를 보존한다. direct `MOTION_CYCLE[index]` 선택은 제거한다.
- [ ] `historical_parallel_engine.py`는 `camera_motion` 문자열을 최종 결정을 위해 쓰지 않고, visual intent와 focal metadata를 전달한다.
- [ ] `python -m pytest -q human_archive/tests/test_cinematic_effect_planner.py human_archive/tests/test_motion_engine_v3.py`를 실행한다.

#### Task 3 — opening scheduling과 Neanderthal renderer 경로를 분리

**Files:**

- Modify: `human_archive/scripts/lib/pacing_scheduler.py`
- Modify: `human_archive/scripts/run_neanderthal_full_pipeline.py`
- Modify: `human_archive/scripts/build_cinematic_master_pipeline.py`
- Modify: `human_archive/scripts/lib/aligned_prompt_compiler.py`
- Modify: `human_archive/scripts/generate_video_prompts.py`
- Test: `human_archive/tests/test_pacing_scheduler.py`
- Test: `human_archive/tests/test_nollam_synthetic_e2e.py`
- Test: `human_archive/tests/test_bare_tip_renderer_contract.py`
- Test: `human_archive/tests/test_nollam_render_contract.py`

- [ ] `_tier_intervals(..., hook=True)`의 첫 11초 BARETIP 특수 처리를 제거하고 실제 `T_scene`에 대한 3개 opening cut interval을 계산한다.
- [ ] 첫 opening cut의 asset binding 세 개를 모두 `FLOW_IMAGE`로 만들고 각 cut에 `context_wide`, `subject_action`, `evidence_detail`을 기록한다.
- [ ] `run_neanderthal_full_pipeline.py`에서 `idx == 0` 조건을 제거한다. `bare_tip_required`는 `scene_role == "body_explanatory_insert" and effect == "optional_baretip"`처럼 명시적 본문 역할일 때만 참이 된다.
- [ ] opening cache 검사는 `.renderer.json`의 Bare-Tip provenance를 요구하지 않고, 이미지 SHA·visibility report·motion profile hash를 요구한다.
- [ ] `build_cinematic_master_pipeline.py`의 첫 효과 assert를 `FLOW_IMAGE + opening_visibility PASS + opening_cut_count == 3` 검증으로 교체한다.
- [ ] Bare-Tip command builder 테스트는 유지하되, opening scene이 해당 builder를 호출하지 않는 spy 테스트를 추가한다.
- [ ] `python -m pytest -q human_archive/tests/test_pacing_scheduler.py human_archive/tests/test_nollam_synthetic_e2e.py human_archive/tests/test_bare_tip_renderer_contract.py human_archive/tests/test_nollam_render_contract.py`를 실행한다.

#### Task 4 — canonical motion engine에 내부 변화와 focal point를 추가

**Files:**

- Modify: `human_archive/scripts/smooth_subpixel_motion_engine.py`
- Modify: `human_archive/scripts/lib/motion_engine_v3.py`
- Test: `human_archive/tests/test_biphasic_motion.py`
- Test: new `human_archive/tests/test_motion_diversity.py`

- [ ] 기존 `compute_trajectory(frame, total_frames, motion)` 호출 호환성을 유지하고, 새 선택 인자로 `profile`을 추가한다. profile이 없으면 기존 안전한 push-in 동작을 사용한다.
- [ ] `phase_plan`은 각 phase의 `duration_ratio`, `zoom_start`, `zoom_end`, `center_start`, `center_end`, `easing`을 갖는다. phase 경계에서 위치·줌이 연속이고 crop box가 캔버스 안에 있도록 clamp한다.
- [ ] `focal_position`에 따라 중앙 고정만 쓰지 않고 left/center/right/upper/lower focal anchor를 반영한다. 자막 clear zone을 침범하는 lower anchor는 자동으로 상향 조정하고 provenance에 `clamped_for_subtitles=true`를 남긴다.
- [ ] `perceptual_cut`은 영상 전체를 다시 자르지 않고 지정 프레임에서 reframe profile을 바꾸며, 오디오와 ASS 타임라인은 건드리지 않는다.
- [ ] 단위 테스트는 100개 프레임의 연속성, 최소·최대 crop bounds, 2/3 phase 변화량, `static_intent` 외 정지 1초 금지를 확인한다.
- [ ] `python -m pytest -q human_archive/tests/test_biphasic_motion.py human_archive/tests/test_motion_diversity.py human_archive/tests/test_motion_engine_v3.py`를 실행한다.

#### Task 5 — 프롬프트·Flow·에셋에 시각 초점 정보를 끝까지 전달

**Files:**

- Modify: `human_archive/scripts/lib/aligned_prompt_compiler.py`
- Modify: `human_archive/scripts/generate_video_prompts.py`
- Modify: `human_archive/scripts/flow_cdp_service.py`
- Modify: `human_archive/scripts/generate_flow_batch.py`
- Modify: `human_archive/scripts/lib/visual_content_qa.py`
- Modify: `human_archive/scripts/lib/visual_qa.py`
- Test: `human_archive/tests/test_nollam_prompt_profile.py`
- Test: `human_archive/tests/test_aligned_prompt_compiler.py`
- Test: `human_archive/tests/test_flow_batch_state.py`

- [ ] 모든 visual request에 `focal_subject`, `shot_scale`, `beat_type`, `scene_role`, `focal_position`, `transition_hint`를 넣고 request SHA에 포함한다.
- [ ] opening prompt에는 `one immediately readable primary subject`, `strong foreground-midground-background separation`, `no empty whiteboard`, `no sparse ink-only canvas`를 포함한다. 기존 no-text·bottom 18% 규칙은 유지한다.
- [ ] Flow 결과가 실제 파일·PIL decode·1920×1080·SHA를 통과해도 visibility gate를 통과하지 못하면 승인하지 않는다. 재시도는 동일 request hash에 대해 최대 2회이고, 조용한 사각형 fallback은 금지한다.
- [ ] 세 shot role의 prompt compile snapshot을 저장하고 legacy 조선/선비 키워드 회귀가 0건인지 확인한다.
- [ ] `python -m pytest -q human_archive/tests/test_nollam_prompt_profile.py human_archive/tests/test_aligned_prompt_compiler.py human_archive/tests/test_flow_batch_state.py`를 실행한다.

#### Task 6 — GUI와 운영 스킬이 새 정책을 말하도록 정리

**Files:**

- Modify: `human_archive/scripts/routes/render_routes.py`
- Modify: `human_archive/static/index.html`
- Modify: `D:\module\.agents\skills\cinematic-hybrid-editing-director\SKILL.md`
- Test: `human_archive/tests/test_render_routes.py`
- Test: `human_archive/tests/test_studio_static_ui.py`

- [ ] API response의 `opening_effect` 기본값을 visible Flow effect로 바꾸고 `opening_asset_type`, `opening_visibility`, `motion_diversity`를 반환한다.
- [ ] `invariants`에서 `bare_tip_opening_enforced`를 제거하고 `visible_first_opening_enforced`, `no_baretip_opening`, `motion_family_window_passed`를 사용한다.
- [ ] GUI의 버튼·배너·toast·motion badge에서 “베어팁 오프닝 강제” 문구를 제거하고 “Visible-first opening / Beat-aware motion”으로 교체한다. `56개 샷` 같은 오래된 고정 수량 문구도 현재 manifest count를 사용하도록 바꾼다.
- [ ] skill 문서에서 첫 씬 베어팁 절대 규칙을 제거하고, 본문 선택용 Bare-Tip·opening visibility·motion diversity 규칙을 명시한다. 이 변경은 `writing-skills` 지침에 따라 pressure scenario를 먼저 실행한 뒤 문서를 수정한다.
- [ ] `python -m pytest -q human_archive/tests/test_render_routes.py human_archive/tests/test_studio_static_ui.py`를 실행한다.

#### Task 7 — legacy entrypoint와 release manifest를 잠근다

**Files:**

- Modify: `human_archive/scripts/build_master_video_sequential_v5.py`
- Modify: `human_archive/scripts/render_ken_burns_clips.py`
- Modify: `human_archive/scripts/build_natural_docu_audio.py`
- Modify: `human_archive/scripts/omni_video_pipeline.py`
- Modify: `human_archive/scripts/postflight_release.py`
- Modify: `human_archive/scripts/lib/three_tier_postflight.py`
- Modify: `human_archive/tests/test_postflight_release.py`
- Modify: `human_archive/tests/test_release_gate_v2.py`

- [ ] legacy renderer는 canonical planner manifest가 없으면 `FAIL-CLOSED`하고 자체 모션 배열로 새 릴리스를 만들지 못하게 한다.
- [ ] release manifest에 `opening_asset_type`, `opening_visibility_report_sha256`, `effect_family_counts`, `max_family_streak`, `max_axis_streak`, `static_hold_violations`를 기록한다.
- [ ] 세 층 postflight는 첫 프레임 visibility, opening BARETIP 금지, 오디오·비디오 parity, 자막·WAV·SHA 검증을 모두 통과해야 PASS한다.
- [ ] 이전 릴리스에 `baretip_opening_verified=true`가 있어도 새 정책 릴리스로 승격하지 않는다. 과거 증거는 보존하고 `superseded_by=visible_first_opening_v1`를 기록한다.
- [ ] `python -m pytest -q human_archive/tests/test_postflight_release.py human_archive/tests/test_release_gate_v2.py`를 실행한다.

#### Task 8 — 네안데르탈인 실제 재렌더와 시청용 샘플 승인

**Files:**

- Create/Modify: `human_archive/runs/nollam_file/2026-09-09/iceage-neanderthal-sapiens-extinction/source/scene_script_manifest_v3.json`
- Create/Modify: `human_archive/runs/nollam_file/2026-09-09/iceage-neanderthal-sapiens-extinction/generation/visual_effect_plan_v2.json`
- Create/Modify: `human_archive/runs/nollam_file/2026-09-09/iceage-neanderthal-sapiens-extinction/generation/release_manifest.json`
- Create/Modify: `human_archive/runs/nollam_file/2026-09-09/iceage-neanderthal-sapiens-extinction/audit/visible_first_opening_report.json`

- [ ] 실제 TTS·Flow 서비스가 가동된 환경에서 39개 음성과 원천 SHA를 먼저 고정한다. 오디오 재합성 없이 영상만 교체하지 않는다.
- [ ] `SHOT_001`의 3개 FLOW 이미지가 각각 context/action/evidence role과 visibility gate를 통과하는지 contact sheet로 확인한다.
- [ ] 0~120초 샘플을 먼저 렌더하고 0초, 2초, 4초, 7초, 10초, 30초, 60초, 110초 프레임을 추출해 사람이 확인한다. 2초 시점에도 빈 캔버스가 보이면 FAIL한다.
- [ ] 120~360초에는 컷 family·shot scale·transition distribution을 확인하고, 360초 이후에는 30초 이상 shot의 internal phase가 실제 frame difference로 검출되는지 확인한다.
- [ ] `ffprobe`로 최종 video/audio duration을 비교하고 `|t_video - t_audio| <= 0.050s`, 원천 audio/scene timeline parity `<= 0.050s`를 확인한다.
- [ ] 새 release manifest에 입력·중간·최종 bytes/SHA/codec와 opening/effect QA를 기록한 뒤에만 릴리스 상태를 `OFFICIAL_PRODUCTION_RELEASE`로 올린다.

### 11. Gate 8 — 시각적 재미와 첫 화면 최종 합격 기준

Round 4는 기존 Gate 0~7에 다음 Gate 8을 추가한다.

| 항목 | 합격 기준 |
|---|---|
| 첫 프레임 가독성 | 첫 0.5초 안에 주요 피사체·장소·사건 방향이 식별되고 visibility gate PASS |
| Bare-Tip 위치 | `opening_group`/`cold_open`/`order=1`에 `BARETIP_VIDEO` 0건; 본문 선택 장면만 허용 |
| opening 변화 | 첫 12초 3개 FLOW 컷, wide/action/detail 역할 모두 존재 |
| 초반 지루함 방지 | 0~120초 단일 perceptual cut 5초 초과 0건(명시 사유 제외), 동일 family/axis 2회 초과 연속 0건 |
| 중반 리듬 | 10-shot window family 4종 이상, shot scale 3종 이상, HUD 20% 이하 |
| 후반 정지 방지 | 20초 초과 shot 2 phase 이상, 30초 초과 shot 3 phase 이상, 1초 이상 무변화 0건 |
| 서사-화면 정합 | 각 shot에 `beat_type`, `focal_subject`, `visual_role`, `transition`이 있고 narration claim과 연결 |
| AV 무결성 | 기존 Gate 7의 stream/source parity와 자막·WAV·SHA 조건 모두 PASS |

### 12. 작업 순서와 중단 조건

1. Task 1~3을 먼저 완료해 첫 씬 계약과 직접 렌더 경로를 바꾼다.
2. Task 4~5로 실제 모션 다양성과 Flow 입력을 연결한다.
3. Task 6~7로 GUI·스킬·legacy 경로의 재도입 가능성을 제거한다.
4. Task 8은 외부 TTS/Flow가 실제로 가동된 환경에서만 수행한다. 서비스가 꺼져 있으면 synthetic·contract 검증까지만 하고 릴리스 완료로 표시하지 않는다.
5. 새 테스트가 2회 연속 실패하면 재시도하지 않고 `ERRORS.md`에 원인·실패 명령·현재 증거를 기록한다. 특히 opening visibility 실패를 단순 threshold 완화로 통과시키지 않는다.

### 13. Round 4 완료 정의

- [ ] 코드·정책·GUI·스킬·테스트에서 첫 씬 베어팁 강제가 제거됐다.
- [ ] Bare-Tip은 본문 설명용 선택 기능으로만 남고, opening placement gate가 fail-closed로 동작한다.
- [ ] 첫 12초 실제 프레임은 3개 FLOW 역할로 구성되고 첫 화면 피사체 가독성 gate를 통과한다.
- [ ] 모션 효과가 단순 6개 순환이 아니라 beat/scale/focal/transition을 반영하며 다양성 수치 게이트를 통과한다.
- [ ] 후반 롱테이크에도 internal phase와 실측 frame difference가 존재한다.
- [ ] 네안데르탈인 새 마스터는 기존 오디오 절삭 문제를 재발시키지 않고 Gate 0~8, 물리 SHA, source parity를 모두 통과한다.
- [ ] 실제 구현 전까지는 기존 마스터를 수정된 릴리스로 표시하지 않는다.
