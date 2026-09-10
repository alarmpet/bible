# NOLLAM 하드닝 Round 4 삼사 만장일치 마스터 실행 계획서 (Visible-First Opening & Beat-Aware Motion)

- **문서 ID**: `PLAN-2026-09-10-NOLLAM-HARDENING-ROUND-4-MASTER`
- **일자**: 2026-09-10
- **기반 합의문**: [`final_consensus_synthesis.md`](file:///D:/module/audit/nollam_hardening_v4_tri_model_audit/final_consensus_synthesis.md) (99.92점 만장일치)
- **기반 리뷰 보고서**: [`REVIEW-2026-09-10-NOLLAM-HARDENING-ROUND-4`](file:///D:/module/bible/docs/superpowers/reviews/2026-09-10-nollam-round4-av-hardening-tri-model-review.md)
- **전역 결정 기록**: [`DECISIONS.md`](file:///D:/module/DECISIONS.md) ([ADR-016])
- **작업 관리 보드**: [`TASK.md`](file:///D:/module/TASK.md) ([FEATURE-036])
- **결함 아카이브**: [`ERRORS.md`](file:///D:/module/ERRORS.md) ([ERR-050])

---

## 1. 실행 목표 및 아키텍처 불변식 (Invariants)

1. **[Visible-First Opening]**: 씬 1번(0~12초)에서 상아색 빈 캔버스([ERR-050])를 영구 박멸하고, 대본/오디오 SSOT(11.0초) 안에서 3-Cut 극실사 35mm FLOW 오프닝 트릴로지(`context_wide` 3.0s $\to$ `subject_action` 3.5s $\to$ `evidence_detail` 4.5s)를 안착시킨다.
2. **[2-Tier Asset Hierarchy]**: 논리 샷 ID(`shot_id=SHOT_001`)와 물리 에셋 ID(`asset_id=SHOT_001_cut01~03`)를 분리하여 `generate_flow_batch.py` 및 매니페스트의 덮어쓰기 결함([DEFECT-A])을 원천 방지한다.
3. **[Single-Pipe Physical Render]**: 3-Cut 오프닝은 개별 MP4 Concat 대신 단일 FFmpeg 파이프 내 PIL 프레임 스위칭(Perceptual Cut)으로 렌더링하여 지터 0.000s, 오디오 드리프트 0.000s, 무비용 6프레임 디졸브를 달성한다.
4. **[Beat-Aware Motion Grammar]**: 6대 기계적 modulo 순환(`idx % 6`)을 완전 폐기하고, 7대 비트(`question`, `reveal`, `threat`, `contradiction`, `evidence`, `consequence`, `pause`) 기반의 결정론적 `CinematicEffectPlanner`를 탑재한다.
5. **[Tri-Phasic Long-Take Pacing]**: 후반부 30초 이상 롱테이크는 Ambient Drift(35%) $\to$ Dynamic Approach(35%) $\to$ Focal Lock(30%) 3단계 내부 모션을 의무화하고, 25프레임 슬라이딩 누적 MAE $\ge 0.85$로 정지 화면(Static Hold)을 박멸한다.
6. **[Gate 8 Multi-Dimensional Verification]**: 첫 프레임 가시성(`coverage >= 15%`, `edge density >= 0.035`, `bbox >= 8%`)과 특수 씬(설원/동굴) Lab 분산 방어, 모션 다양성(연속 동일 family/axis $\le 2$, 10-shot 윈도우 $\ge 4$종 family), 오프닝 베어팁 0건(`baretip_in_opening_rejected: true`)을 Fail-Closed로 강제한다.
7. **[Backward Compatibility]**: 직전 FEATURE-035 마스터(1,008.00s) 매니페스트는 `HISTORICAL_PRODUCTION_RELEASE`로 동결 보존하고, 신규 마스터는 `release_manifest_v4.json`으로 분리 발행한다.
8. **[Constitutional Skill Amendment]**: `cinematic-hybrid-editing-director/SKILL.md` 절대 헌법 1을 개정하고 베어팁을 본문 설명용 선택 기능으로 재정의한다.

---

## 2. 8대 단계별 실행 태스크 (Task 1 ~ Task 8)

### Task 1 — 계약·정책을 Visible-First 및 Gate 8으로 고정 (P0)
- **수정 대상 파일**:
  - `human_archive/config/nollam_file_visual_policy.yaml`
  - `human_archive/config/visual_pacing_profiles.yaml`
  - `human_archive/config/delivery_profiles.yaml`
  - `human_archive/schemas/polymorphic_asset_contract_v1.schema.json`
  - `human_archive/scripts/lib/asset_contract.py`
- **신규 테스트 파일**:
  - `human_archive/tests/test_opening_visibility_gate.py`
  - `human_archive/tests/test_polymorphic_asset_contract.py` (갱신)
- **세부 작업**:
  1. 정책 및 스키마에 `scene_role: "opening_group"`, `asset_type: "FLOW_IMAGE"`, `visual_role: ["context_wide", "subject_action", "evidence_detail"]` 추가.
  2. `BARETIP_VIDEO`는 `scene_role != "opening_group"` 및 `order != 1` 조건에서만 허용(`optional_baretip`), 오프닝 위치 시 `ValueError` 발생 강제.
  3. 1920x1080 캔버스 기준 Lab 명도 국소 분산($\sigma_{\\text{local}}^2 \ge 6.0$), CLAHE 적응형 Canny edge density($\ge 0.035$), coverage($\ge 15%$) 검증 함수 구현.
  4. 오프닝 베어팁 시도 시 Fail-Closed 차단 단위 테스트 작성 및 통과 확인.

### Task 2 — 비트 인지형 모션 플래너(`cinematic_effect_planner.py`) 신설 및 DI 결합 (P0)
- **신규 생성 파일**:
  - `human_archive/scripts/lib/cinematic_effect_planner.py`
  - `human_archive/tests/test_cinematic_effect_planner.py`
- **수정 대상 파일**:
  - `human_archive/scripts/lib/cinematic_editing_director.py`
  - `human_archive/scripts/lib/visual_brief_provider.py`
  - `human_archive/scripts/historical_parallel_engine.py`
- **세부 작업**:
  1. `CinematicEffectPlanner.plan_effect(scene, previous_profiles, next_scene, seed_text) -> dict` 구현.
  2. 7대 비트 매핑: `question` $\to$ `reframe_push`, `reveal` $\to$ `lateral_reveal`, `threat` $\to$ `rapid_push`, `contradiction` $\to$ `counter_axis_pan`, `evidence` $\to$ `evidence_macro`, `consequence` $\to$ `slow_pull_out`, `pause` $\to$ `ambient_drift`.
  3. 최근 2개 샷 동일 family/axis 감점 및 10-shot 윈도우 다양성 점수화 알고리즘 탑재.
  4. 오프닝 전용 인터페이스 `plan_opening_group()` 구현 (3-Cut 역할 및 디졸브 트랜지션 계획).
  5. `CinematicEditingDirector`에 플래너를 생성자 주입(DI)하고 기존 modulo `MOTION_CYCLE[index]` 완전 삭제.

### Task 3 — 오프닝 스케줄러 분리 및 네안데르탈인 렌더 경로 정합 (P0)
- **수정 대상 파일**:
  - `human_archive/scripts/lib/pacing_scheduler.py`
  - `human_archive/scripts/run_neanderthal_full_pipeline.py`
  - `human_archive/scripts/build_cinematic_master_pipeline.py`
  - `human_archive/scripts/lib/aligned_prompt_compiler.py`
- **테스트 파일**:
  - `human_archive/tests/test_pacing_scheduler.py`
  - `human_archive/tests/test_nollam_synthetic_e2e.py`
  - `human_archive/tests/test_bare_tip_renderer_contract.py`
- **세부 작업**:
  1. `pacing_scheduler.py`에서 첫 11초 BARETIP 분기를 제거하고 3개 `FLOW_IMAGE` 오프닝 컷(3.0s, 3.5s, 4.5s) 스케줄러로 교체.
  2. `run_neanderthal_full_pipeline.py` L824 `idx == 0` 베어팁 강제 조건 완전 삭제.
  3. L713 `SHOT_001 Bare-Tip source unavailable` 하드코딩 에러 메시지 척결.
  4. L858~874의 씬 1번 무조건 1080x600 패딩(`color=0xF5EBD7`) 분기를 오프닝 경로에서 제거.
  5. L905 concat list 쓰기 시 `c.resolve().as_posix()` 정규화 적용 ([DEFECT-B] 방어).
  6. `build_cinematic_master_pipeline.py`의 `assert planned[0] == bare_tip_whiteboard`를 Gate 8 가시성 통과 단언으로 교체.

### Task 4 — 서브픽셀 모션 엔진 Tri-Phasic 궤적 및 슬라이딩 정지 감지 탑재 (P0)
- **수정 대상 파일**:
  - `human_archive/scripts/smooth_subpixel_motion_engine.py`
  - `human_archive/scripts/lib/motion_engine_v3.py`
- **신규/수정 테스트 파일**:
  - `human_archive/tests/test_motion_diversity.py` (신규)
  - `human_archive/tests/test_biphasic_motion.py` (갱신)
- **세부 작업**:
  1. `smooth_subpixel_motion_engine.py`에 `compute_tri_phasic_trajectory` 구현 (Ambient Drift 35% $\to$ Dynamic Approach 35% $\to$ Focal Lock 30%).
  2. `focal_position`에 따른 left/center/right/upper/lower 앵커 반영 및 하단 자막 클리어존 보호를 위한 Y축 75% 자동 클램핑(`clamped_for_subtitles=true`).
  3. 25프레임(1.0초) 슬라이딩 누적 $\text{MAE} \ge 0.85$ 및 도함수 검증기 탑재하여 롱테이크 정지 화면 원천 방어.
  4. `render_composite_opening_clip` 구현: 단일 MP4 파이프 내 PIL 프레임 스위칭 및 6프레임 `Image.blend` 크로스 디졸브 적용.

### Task 5 — 프롬프트 컴파일러 1:3 매핑 및 Flow CDP 가시성 게이트 바인딩 (P1)
- **수정 대상 파일**:
  - `human_archive/scripts/lib/aligned_prompt_compiler.py`
  - `human_archive/scripts/generate_video_prompts.py`
  - `human_archive/scripts/flow_cdp_service.py`
  - `human_archive/scripts/generate_flow_batch.py`
  - `human_archive/scripts/lib/visual_content_qa.py`
- **테스트 파일**:
  - `human_archive/tests/test_nollam_prompt_profile.py`
  - `human_archive/tests/test_aligned_prompt_compiler.py`
  - `human_archive/tests/test_flow_batch_state.py`
- **세부 작업**:
  1. `aligned_prompt_compiler.py`에 2계층 식별자(`shot_id=SHOT_001`, `asset_id=SHOT_001_cut01~03`) 바인딩.
  2. `generate_flow_batch.py`의 딕셔너리 덮어쓰기 결함([DEFECT-A])을 `asset_id` 고유 키 방식으로 수정.
  3. 씬 1번 프롬프트 3종 생성:
     - `SHOT_001_cut01`: 35mm 극실사 빙하기 유라시아 설원 절벽 전경 (`context_wide`).
     - `SHOT_001_cut02`: 혹한 속 동굴 앞 모피를 입은 사냥꾼 무리의 생존 행동 (`subject_action`).
     - `SHOT_001_cut03`: 4만 년 전 빙하기 인류의 거대 두개골 화석 및 투창기 유물 디테일 (`evidence_detail`).
  4. Flow CDP 다운로드 에셋에 대해 Gate 8 가시성 검증기 통과를 승인 필수 조건으로 바인딩.

### Task 6 — GUI 및 전역 스킬 헌법 동기화 (P1)
- **수정 대상 파일**:
  - `human_archive/scripts/routes/render_routes.py`
  - `human_archive/static/index.html`
  - `D:\module\.agents\skills\cinematic-hybrid-editing-director\SKILL.md`
- **테스트 파일**:
  - `human_archive/tests/test_render_routes.py`
  - `human_archive/tests/test_studio_static_ui.py`
- **세부 작업**:
  1. `render_routes.py`의 `/api/cinematic/effects_plan` 응답에서 `bare_tip_opening_enforced`를 제거하고 `visible_first_opening_enforced: true`, `motion_diversity` 메타데이터 반환.
  2. `index.html`의 버튼, 배너, 뱃지에서 "베어팁 오프닝 강제" 문구를 "Visible-First 오프닝 / Beat-Aware 모션"으로 교체.
  3. `cinematic-hybrid-editing-director/SKILL.md` 절대 헌법 1을 "3-Cut Visible FLOW 오프닝 (Visible-First Invariant)"으로 공식 개정하고, 베어팁을 "본문 설명용 선택적 인서트"로 재정의.

### Task 7 — 릴리스 매니페스트 버전 분리 및 3중 Postflight 잠금 (P1)
- **수정 대상 파일**:
  - `human_archive/scripts/postflight_release.py`
  - `human_archive/scripts/lib/three_tier_postflight.py`
  - `human_archive/scripts/build_master_video_sequential_v5.py`
  - `human_archive/scripts/render_ken_burns_clips.py`
- **테스트 파일**:
  - `human_archive/tests/test_postflight_release.py`
  - `human_archive/tests/test_release_gate_v2.py`
- **세부 작업**:
  1. `postflight_release.py`에 `release_schema_version` 다형성 검증기 탑재:
     - v2 (`HISTORICAL_PRODUCTION_RELEASE`): 기존 1,008s 마스터 매니페스트 정상 통과 보장.
     - v3 (`OFFICIAL_PRODUCTION_RELEASE_V4`): Gate 8(첫 프레임 가시성 PASS, 오프닝 베어팁 0건, 모션 다양성 통과) 필수 검증.
  2. `release_manifest_v4.json` 독립 발행 체계 확립 ([DEFECT-C] 방어).
  3. 레거시 렌더러가 canonical planner 없이 임의 모션으로 실행되는 경로를 Fail-Closed 차단.

### Task 8 — 네안데르탈인 신규 릴리스 승격 및 시청용 샘플 검증 (P0)
- **대상 디렉터리**: `human_archive/runs/nollam_file/2026-09-09/iceage-neanderthal-sapiens-extinction/`
- **산출물**:
  - `generation/clips/SHOT_001.mp4` (3-Cut Visible FLOW 복합 클립, 11.000s)
  - `NOLLAM-NEANDERTHAL-EXTINCTION-FULL-MASTER.mp4` (신규 렌더 마스터)
  - `generation/release_manifest_v4.json` (Gate 8 바인딩)
- **세부 작업**:
  1. `SHOT_001` 3개 에셋(`_cut01.jpg`, `_cut02.jpg`, `_cut03.jpg`) 가시성 검증 통과 확인.
  2. 0~12초 구간 0.0s, 0.5s, 2.0s, 4.0s, 7.0s, 10.0s 프레임을 추출하여 상아색 빈 화면 0건 및 피사체 즉각 식별 확인.
  3. 후반부 30초 이상 샷의 3단계 내부 모션 및 25프레임 MAE 실측 검증.
  4. Pre-Mux Parity $|V_{\text{dur}} - A_{\text{dur}}| \le 0.040\text{s}$ 및 원천 오디오 Parity 검증.
  5. `postflight_release.py` Gate 8 전수 검증 통과(Exit Code 0) 후 `OFFICIAL_PRODUCTION_RELEASE_V4` 승격.

---

## 3. 검증 게이트 및 Definition of Done (DoD)

| 게이트 | 검증 항목 | 합격 기준 |
| :--- | :--- | :--- |
| **Gate 8.1** | 첫 프레임 가시성 | 0.5s 시점 `coverage >= 15%`, `edge density >= 0.035`, `bbox >= 8%`, Lab 분산 통과 |
| **Gate 8.2** | 오프닝 베어팁 금지 | `order=1`/`opening_group`에 `BARETIP_VIDEO` 0건 (`baretip_in_opening_rejected: true`) |
| **Gate 8.3** | 오프닝 3-Cut 다양성 | 첫 12초 3개 FLOW 컷(`context_wide`, `subject_action`, `evidence_detail`), 디졸브 6프레임 |
| **Gate 8.4** | 모션 다양성 윈도우 | 동일 family/axis 연속 $\le 2$, 임의 10-shot 윈도우 family $\ge 4$, scale $\ge 3$, HUD $\le 20%$ |
| **Gate 8.5** | 후반 롱테이크 정지 방지 | 30s+ 샷 3-Phase 강제, 25프레임 누적 MAE $\ge 0.85$, 도함수 $\ge 3.0\text{px}$ |
| **Gate 8.6** | AV 스트림/원천 Parity | $|t_{\text{video}} - t_{\text{audio}}| \le 0.040\text{s}$, 원천 오디오 대비 $\le 0.040\text{s}$ 완벽 일치 |
| **Gate 8.7** | 하위 호환성 및 테스트 | 기존 1,008s v2 매니페스트 보존, 전체 회귀 테스트 통과 (`pytest` Exit Code 0) |

---

## 4. 실행 우선순위 및 중단 조건

1. **우선순위**: Task 1~4 (핵심 계약, 플래너, 모션 엔진, 오프닝 결합) $\to$ Task 5~7 (프롬프트, GUI/스킬, 릴리스 잠금) $\to$ Task 8 (실물 재렌더 및 승격).
2. **Fail-Fast 중단 조건**:
   - 단위/회귀 테스트 2회 연속 실패 시 즉시 루프 중단 및 `ERRORS.md` 기록.
   - 0.5s 시점 가시성 게이트 미달 시 단순 임계값 완화 절대 금지 (CLAHE 전처리 및 프롬프트 재조정 수행).
   - 오프라인 환경(포트 3093/9222 미기동)에서 가짜 렌더를 생성하고 성공을 선언하는 행위 원천 차단 ([ERR-048] 불변식 준수).
