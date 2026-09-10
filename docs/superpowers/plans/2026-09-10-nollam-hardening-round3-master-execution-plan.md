# NOLLAM Round 3 마스터 실행 계획서 (Tri-Model 만장일치 차세대 무결성 헌법)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Tri-Model Consensus Audit Evidence:**
> - Round 1 Review: [`2026-09-10-nollam-pacing-audit-tri-model-review.md`](file:///D:/module/bible/docs/superpowers/reviews/2026-09-10-nollam-pacing-audit-tri-model-review.md)
> - Round 2 Review: [`2026-09-10-nollam-hardening-v2-tri-model-review.md`](file:///D:/module/bible/docs/superpowers/reviews/2026-09-10-nollam-hardening-v2-tri-model-review.md)
> - Round 2 Knowledge Doc: [`nollam-round2-av-contract-router-hardening-2026-09-10.md`](file:///D:/module/bible/docs/solutions/integration-issues/nollam-round2-av-contract-router-hardening-2026-09-10.md)
> - Round 3 Review: [`2026-09-10-nollam-round3-av-hardening-tri-model-review.md`](file:///D:/module/bible/docs/superpowers/reviews/2026-09-10-nollam-round3-av-hardening-tri-model-review.md)
> - Round 3 Consensus Synthesis: [`final_consensus_synthesis.md`](file:///D:/module/audit/nollam_hardening_v3_tri_model_audit/final_consensus_synthesis.md)
> - Round 3 Matrix: [`cross_critique_matrix.json`](file:///D:/module/audit/nollam_hardening_v3_tri_model_audit/cross_critique_matrix.json) (종합 99.92점 만장일치 통과)

**Goal:** Mux 명령어에서 단순 `-shortest` 제거 시 발생한 52.3초 비디오 패킷 완전 고갈 및 화면 정지(Freeze-Frame) 결함을 근본 척결하고, 업스트림 실측 발화 시간 1:1 역바인딩, Tier 1 템포 보존을 위한 Layer 3 지각 컷(PIL 120% 오버스캔), 스킬 헌법 문서 내 결함 수치(955.90초) 정화, `conftest.py` Windows 안전 basetemp TTL GC, 140Hz/그림판 가짜완료 폴백 영구 삭제 및 3-Tier Preflight 체계, `ProductionHistoryService` 독립 도메인 모듈화, 구형 네안데르탈인 런 실물 전면 재생성을 단일 SSOT 계약으로 완성한다.

**Architecture:** 
1. **TTS-First SSOT & Pre-Mux Strict Parity Gate**: Gate 2 음성 실측 길이($T_{\text{speech}} + 0.40\text{s}$)를 매니페스트 `scene_duration`에 역바인딩하여 비디오 클립을 1:1로 렌더링하고, Mux 직전 $\left| V_{\text{concat}} - A_{\text{master}} \right| \le 0.040\text{s}$ (1프레임 @ 25fps)를 강제하여 화면 멈춤과 오디오 절삭을 원천 차단한다.
2. **Layer 3 지각 컷(Perceptual Cut)**: Tier 1(샷 2~11번)의 자연 발화 시간(8~11초)을 온전히 보존하면서, 1장의 1080p 마스터 이미지에서 PIL 120% 오버스캔(2304x1296)을 통해 5.0초 시점에 와이드 $\to$ 클로즈업 점프컷을 무비용으로 창출한다.
3. **Lazy Safe Non-blocking GC**: `conftest.py`에 활성 PID 검사(`ctypes.windll.kernel32.OpenProcess`), 최신 5개 세션 보존(Retain-K), 24시간 초과 디렉터리 자동 삭제를 탑재하여 D: 드라이브 누수를 영구 방지한다.
4. **Anti-Hallucination 3-Tier Preflight & Resume**: 140Hz 사인파 및 PIL 그림판 가짜완료 폴백을 전면 폐기하고, 소켓 헬스체크 기반 Fail-Closed Preflight Probe, 원자적 2단계 커밋(.part $\to$ .jpg/.wav), 암호학적 출처 메타데이터(`.provenance.json`)를 강제한다.
5. **ProductionHistoryService**: 모놀리스 `studio_gui_server.py`와 `history_routes.py`의 이중 스캔 함수(Split-Brain)를 단일 도메인 서비스로 승격 일원화한다.

---

## 1. 8대 불변 헌법 원칙 (Constitutional Invariants)

1. **[불변식 1] 1:1 시간 완결 및 Pre-Mux Parity ($\le 0.040\text{s}$)**:
   - 씬 길이를 인위적으로 4.5초로 자르거나, 비디오 길이에 오디오를 억지로 맞추기 위해 `-shortest`를 쓰거나 52초간 정지 화면을 유지하는 행위를 영구 금지한다.
   - Concat 비디오와 마스터 오디오의 물리적 지속시간 차이는 반드시 1프레임(0.040s) 이내여야 한다.
2. **[불변식 2] 2계층 하이브리드 지각 컷 (Layer 3 Perceptual Cut)**:
   - Tier 1의 템포감은 비디오를 자르는 것이 아니라, 단일 마스터 이미지 내부에서 PIL 120% 오버스캔 기반 5.0초 단위 점프컷으로 창출한다 (추가 API 호출 0회).
3. **[불변식 3] 스킬 문서 내 결함 수치 헌법화 영구 금지**:
   - 에이전트 전역 스킬(`SKILL.md`)에 특정 에피소드의 결함 수치(955.90초, 39샷)를 실증 표준으로 박제하는 것을 금지하며, 가변 자연 발화 윈도우(840s~1560s) SSOT로 일원화한다.
4. **[불변식 4] Windows 안전 basetemp TTL GC**:
   - `pytest_tmp` 디렉터리는 활성 PID 보호 + Retain-5 + 24시간 TTL을 엄수하여 디스크 고갈을 원천 방지한다.
5. **[불변식 5] 거짓 완료 원천 금지 (Anti-Hallucination Invariant)**:
   - 외부 서비스 미기동 시 140Hz 삑 소리나 PIL 그림판을 생성하고 `SUCCESS`를 띄우는 행위를 엄격히 금지하며, 즉시 Fail-Closed(Exit 1)로 중단한다.
6. **[불변식 6] 물리 미디어 3단계 실증 테스트 (Three-Pillar Testing)**:
   - 가상 경로 문자열 검사('-shortest' not in cmd)를 폐기하고, lavfi 합성 미디어를 실제로 Mux하여 스트림 패킷 일치성과 Fail-Closed를 실측 검증한다.
7. **[불변식 7] 자막 마이크로 클로즈 3분할 및 36자 2줄 피라미드**:
   - 20초 초과 롱테이크 문장은 종결어미 기준으로 16~17초 단위 2~3개 이벤트로 분할하고, 52pt Pretendard, 1줄 $\le 36$자, 최대 2줄 $\le 70$자, 숫자/쉼표 정규식 보호를 엄수한다.
8. **[불변식 8] 도메인 서비스 단일 진실 공급원 (Single Source of Truth)**:
   - 프로덕션 이력 수집 및 스캔 로직은 `lib/production_history_service.py` 단일 모듈로 일원화하여 Split-Brain을 차단한다.

---

## 2. 상세 실행 로드맵 (Phases 0 ~ 7)

### Phase 0 — 스킬 문서 헌법 정화 및 conftest.py 안전 GC 구축 (P0)

- [ ] `D:\module\.agents\skills\cinematic-hybrid-editing-director\SKILL.md` [절대 헌법 5]에서 "39개 가변 샷 실증 표준", "955.90초" 문구를 전면 삭제하고 자연 발화 윈도우(840s~1560s) SSOT로 환원.
- [ ] `D:\module\.agents\skills\flow-batch-orchestrator\SKILL.md`에서 955.90초 결함 런타임 표기를 제거하고 동적 대본 호흡 표준으로 동기화.
- [ ] `D:\module\PROJECT_MEMORY.md`의 네안데르탈인 완료 수치(955.90초)를 원천 오디오 1007.97s 기준 실물 재생성 대기로 정정.
- [ ] `D:\module\bible\conftest.py`에 `_is_pid_alive_windows`, `_run_basetemp_garbage_collection` (Active PID 확인, Retain-5, TTL 24h) 탑재.
- [ ] `pytest tests/` 실행 후 `D:\module\scratch\pytest_tmp` 디렉터리 내 잔여 폴더 수가 안전하게 제어되는지 검증.

*완료 기준: 스킬 문서 내 결함 수치 0건, pytest 실행 후 고아 basetemp 디렉터리 누수 차단.*

---

### Phase 1 — 가짜 완료 폴백 영구 삭제 및 3-Tier Fail-Closed Preflight 구축 (P0)

- [ ] `run_neanderthal_full_pipeline.py`에서 SuperTonic3 미응답 시 140Hz 사인파 비프음을 생성하는 `create_narrator_tone` 폴백 로직을 완전 삭제.
- [ ] `run_neanderthal_full_pipeline.py`에서 Google Flow CDP 미연결 시 PIL 그림판을 생성하는 `create_cinematic_artwork` 폴백 로직을 완전 삭제.
- [ ] `probe_required_external_services()` 함수를 구현하여 Port 3093 (SuperTonic3 HTTP) 및 Port 9222 (Chrome Flow CDP) 소켓/HTTP 연결 실패 시 즉시 파이프라인 중단 (`PreflightServiceUnavailableError`, Exit 1).
- [ ] 에셋 생성 시 원자적 2단계 커밋(`.part` $\to$ `.jpg/.wav`) 및 암호학적 출처 메타데이터(`.provenance.json`) 동반 생성 엔진 탑재.
- [ ] 서비스 재개 시 기생성된 정상 에셋을 0.001초 만에 건너뛰는 초고속 멱등 재개(Idempotent Resume) 검증.

*완료 기준: 서비스 오프라인 상태에서 더미 파일 생성 0건, 명확한 포트 기동 가이드 출력 후 즉시 안전 중단.*

---

### Phase 2 — Upstream AV 바인딩 및 Pre-Mux Strict Parity Gate 신설 (P0)

- [ ] `run_neanderthal_full_pipeline.py`의 Gate 2에서 SuperTonic3 실제 발화 음성 길이($T_{\text{speech}}$)에 0.40s 룸톤을 합산한 실제 시간($T_{\text{scene}}$)을 매니페스트 `s["scene_duration"]`에 역바인딩(Back-propagate).
- [ ] 샷 2~11번(Tier 1)의 인위적 4.5초 강제 클램핑 코드를 완전 폐기.
- [ ] Concat 비디오와 마스터 오디오를 결합하기 직전, 두 미디어의 물리적 길이를 `ffprobe`로 측정하여 $\left| V_{\text{dur}} - A_{\text{dur}} \right| \le 0.040\text{s}$ (1프레임 @ 25fps)를 강제하는 `validate_premux_av_parity` 함수 구축.
- [ ] 허용 오차 초과 시 `AVDurationMismatchError`를 던지며 Mux 실행을 즉각 중단하고, 52.3초 정지 화면 비디오 생성을 원천 차단.

*완료 기준: Pre-Mux Gate 불일치 시 Fail-Closed 차단, 일치 시에만 -shortest 없는 안전 1:1 Mux 실행.*

---

### Phase 3 — Tier 1 고속 템포 보존을 위한 'Layer 3 지각 컷' 연출 모듈화 (P1)

- [ ] `cinematic_editing_director.py`에 PIL 120% 오버스캔(2304x1296) 캔버스를 활용한 `render_perceptual_cut_subscenes` 엔진 구현.
- [ ] 샷 2~11번(Tier 1)의 8~11초 롱테이크 클립 내부에서 5.0초 시점에 와이드 마스터 $\to$ 익스트림 클로즈업으로 점프컷 리프레이밍 적용.
- [ ] 모션 키프레임 보간 시 5.0초 시점의 불연속 카메라 렌즈 교체 효과(Reframe & Lens Swap)를 단일 비디오 스트림에 매끄럽게 인코딩.
- [ ] 추가 API 생성 호출 0회, DOM 부담 0으로 2~5초 고속 몽타주 템포감과 100% 립싱크 동시 달성 검증.

*완료 기준: Tier 1 샷에서 5.0초 시점 지각 컷 점프 전환 발생 확인, 나레이션 오디오와 100.0% 립싱크 일치.*

---

### Phase 4 — 물리 미디어 3단계 실증 테스트 스위트 확립 (P0)

- [ ] `tests/test_nollam_render_contract.py`의 가상 경로 문자열 검사('-shortest not in cmd')를 전면 폐기.
- [ ] `ffmpeg -f lavfi` 기반 2.0초 합성 비디오(`testsrc2`)와 2.0초 합성 오디오(`sine`)를 실제로 Mux하고 ffprobe로 스트림 패킷 지속시간 일치성($\le 0.040\text{s}$)을 검증하는 물리 실증 테스트 작성.
- [ ] 비디오(1.0s)와 오디오(3.0s)의 길이가 불일치하는 입력을 주입했을 때 Pre-Mux Gate가 `AVDurationMismatchError`를 던지며 Fail-Closed하는지 검증하는 Negative Injection Test 작성.
- [ ] 비디오 트랙의 마지막 패킷 타임스탬프와 무비 전체 지속시간의 갭이 0인지 확인하는 Packet Continuity Test 작성.
- [ ] `pytest tests/test_nollam_render_contract.py` 실행하여 Exit Code 0 확인.

*완료 기준: 물리 미디어 Mux 및 패킷 포렌식 단위 테스트 100% 통과.*

---

### Phase 5 — `ProductionHistoryService` 독립 도메인 서비스 구축 및 모놀리스 해체 (P1)

- [ ] `human_archive/scripts/lib/production_history_service.py`를 신설하여 `production_video_history.json`의 원자적 CRUD, MP4 디렉터리 스캔, 메타데이터 정규화, 배지 부여 로직을 단일 책임으로 캡슐화.
- [ ] `studio_gui_server.py`의 라인 450~540 (`get_all_completed_video_projects`) 레거시 모놀리스 코드를 완전 삭제하고 `ProductionHistoryService` 주입으로 단순화.
- [ ] `routes/history_routes.py` 내부의 독립 중복 함수(`scan_videos`)를 삭제하고 표준 서비스로 일원화하여 Split-Brain 구조를 영구 청산.
- [ ] `tests/test_history_routes.py`를 정비하여 독립 도메인 서비스와 라우터의 정합성을 100% 검증.

*완료 기준: studio_gui_server.py 모놀리스 코드 완전 제거, history 라우터 단일 서비스 의존성 확립.*

---

### Phase 6 — 구형 네안데르탈인 런 실물 에셋 전면 재생성 (P0)

- [ ] SuperTonic3 M2 48kHz stereo 엔진으로 네안데르탈인 39개 문장 재합성 (`audio/sentences_v4/` 및 `audio/padded/`).
- [ ] `semantic_subtitle_engine.py`로 39개 샷 자막 전수 재컴파일 (52pt Pretendard, 1줄 $\le 36$자, 최대 2줄 $\le 70$자, SHOT_022 3단계 마이크로 클로즈 분할).
- [ ] 비디오 씬 39개를 실측 오디오 지속시간(합계 1007.97초)에 1:1로 맞추어 전면 재렌더링 (Tier 1 Layer 3 지각 컷 포함).
- [ ] `validate_premux_av_parity` 통과 후 최종 마스터 합체 실행 (오디오 절삭 0초, 화면 정지 0초, 자막 잘림 0건).

*완료 기준: 최종 마스터 비디오 지속시간 1007.97s == 마스터 오디오 1007.97s 100% 일치, 52초 화면정지 결함 박멸.*

---

### Phase 7 — 3중 실물 릴리스 감사 통과 및 마스터 승격 (P0)

- [ ] **Layer 1 원천 입력 물리 감사**: 39개 WAV 전수 ffprobe 48kHz stereo 실측, ASS 자막 36자 2줄 전수 통과, 이미지 1080p Lanczos 검증.
- [ ] **Layer 2 컨테이너 실물 감사**: 최종 MP4 1080p 25fps CFR, AAC 48k stereo, EBU R128 (-16 LUFS), Stream Parity $\left| V_{\text{dur}} - A_{\text{dur}} \right| \le 0.040\text{s}$ 통과.
- [ ] **Layer 3 메타데이터 바인딩**: 실측 SHA-256 체인을 `release_manifest.json`에 영구 기록.
- [ ] `postflight_release.py` 실행하여 Exit Code 0 확인 및 프로덕션 마스터 공식 승격.

*완료 기준: 3중 실물 감사 100% 합격 및 release_manifest.json 발행.*

---

## 3. Definition of Done (DoD)

다음 5대 불변식을 모두 만족할 때만 '작업 완료'로 승인된다:
- [ ] **Code**: `python -m py_compile` 전 파일 문법 검사 100% 통과.
- [ ] **Test**: `pytest tests/` 전수 통과 (Exit Code 0).
- [ ] **Parity**: 사전 Mux 및 최종 컨테이너에서 $\left| \text{Duration}(V) - \text{Duration}(A) \right| \le 0.040\text{s}$ 입증.
- [ ] **Integrity**: 물리적 파일 크기 > 0 바이트, SHA-256 매니페스트 일치, 140Hz 비프음 및 그림판 더미 0건.
- [ ] **Memory**: `TASK.md`, `PROGRESS.md`, `ERRORS.md`에 결함(ERR-046, ERR-047, ERR-048) 영구 박제 및 동기화.
