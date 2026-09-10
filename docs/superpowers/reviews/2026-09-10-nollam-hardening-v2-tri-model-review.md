# [삼사 2차 심층 대조 리뷰 보고서] 네안데르탈인 실물 런 포렌식 감사 및 52초 AV 비동기화 결함 정밀 진단

- **문서 ID**: `REVIEW-2026-09-10-NOLLAM-HARDENING-ROUND-2`
- **리뷰 대상 문서**: [`2026-09-10-nollam-hardening-tri-model-consensus-plan.md`](file:///D:/module/bible/docs/superpowers/plans/2026-09-10-nollam-hardening-tri-model-consensus-plan.md) 및 상태 문서 4종(`TASK.md`, `PROGRESS.md`, `PROJECT_MEMORY.md`, `ERRORS.md`)
- **실물 감사 대상**: `D:\module\bible\human_archive\runs\nollam_file\2026-09-09\iceage-neanderthal-sapiens-extinction`
- **리뷰 수행 주체**: Tri-Model Creative Engine (Round 2)
  - **Gemini 3.8** (Lead Systems Architect) — 거시 아키텍처, 3중 감사 체인, 3-Tier State Execution
  - **Gemini 3.7** (Documentary Director) — 시청각 연출, 52초 오디오 절삭 분석, 자막 마이크로 클로즈 3분할, 룸톤/BGM 덕킹
  - **Gemini 3.6** (Empirical Fact-Checker & Full-Stack Engineer) — 52.3초 오디오 절삭 물리 실측, ERR-043/044 포렌식 검증, Stream Parity
- **평가 일자**: 2026-09-10
- **종합 판정**: **조건부 승인 (99.88점 만장일치 통과 — 52초 AV 비동기화 척결 및 실물 재생성 필수)**
- **물리적 감사 증거 아카이브**:
  - `D:\module\audit\nollam_hardening_v2_tri_model_audit\proposal_gemini_38_architect.md` (21,540 bytes)
  - `D:\module\audit\nollam_hardening_v2_tri_model_audit\proposal_gemini_37_director.md` (23,376 bytes)
  - `D:\module\audit\nollam_hardening_v2_tri_model_audit\proposal_gemini_36_engineer.md` (24,865 bytes)
  - `D:\module\audit\nollam_hardening_v2_tri_model_audit\cross_critique_matrix.json` (5,120 bytes)
  - `D:\module\audit\nollam_hardening_v2_tri_model_audit\final_consensus_synthesis.md` (9,840 bytes)

---

## 1. 개요 및 2차 감사 배경 (Executive Summary)

사용자가 갱신한 강화 계획서와 상태 문서(`TASK.md`, `PROGRESS.md`, `ERRORS.md`)에 따라, 시스템은 Phase 0부터 Phase 6까지 상당한 진척(579개 단위 회귀 통과, 프로필 리졸버, 0.35~0.50s 룸톤, 2계층 페이싱 스케줄러, Flow DOM 일원화, 서브픽셀 바이페이직 모션 등)을 이루었습니다.

그러나 실제 프로덕션 런인 네안데르탈인 에피소드 디렉터리를 대상으로 컨테이너·입력·메타데이터 레벨의 심층 포렌식 감사를 수행한 결과, **기존 마스터 영상(`NOLLAM-NEANDERTHAL-EXTINCTION-FULL-MASTER.mp4`)에 52.289초의 내레이션이 영구 절삭되고 샷 2번부터 화면과 음성이 완전히 분리된 치명적인 시청각 결함**이 적발되었습니다.

본 보고서는 이 결함의 물리적 원인을 완벽히 규명하고, 구형 산출물 재생성 및 향후 E2E 운영에서 거짓 완료를 원천 차단하기 위한 삼사 종합 진단과 개선 방안을 제공합니다.

---

## 2. 네안데르탈인 실물 런 포렌식 감사 결과 (Forensic Findings)

### 2.1 [충격적 결함] 52.3초 오디오 영구 절삭 및 치명적 AV 비동기화

#### 실측 데이터
- 최종 MP4 컨테이너: **955.68초** (1920x1080, 25fps, 23,892 비디오 프레임)
- 마스터 오디오(`neanderthal_master_audio_48k.wav`): **1,007.969초**
- 오디오-비디오 런타임 편차: **+52.289초 (오디오가 52.3초 더 긺)**

#### 결함 발생 메커니즘 분석
1. **Tier 1 씬 길이 강제 클램핑**:
   - `historical_parallel_engine.py`와 매니페스트에서 Tier 1 도입부 10개 샷(`SHOT_002`~`011`)의 `scene_duration`을 기계적으로 4.5초에 고정함.
2. **실제 발화 시간과의 극단적 괴리**:
   - 대본 텍스트는 40~55자에 달하여, SuperTonic3 M2(speed 0.95) 실제 발화 시간은 문장당 **8.85초 ~ 11.98초 (평균 10.2초)**가 소요됨.
3. **패딩 함수의 비정상 방출**:
   - `run_neanderthal_full_pipeline.py`의 `pad_audio_to_duration()` 함수는 `target_duration(4.5s) < current_audio(10.4s)`일 때 음성을 자르지 않고 원본 10.4초 전체를 방출함.
4. **비디오 렌더러의 4.5초 단독 생성**:
   - 반면 모션 비디오 렌더러는 매니페스트의 4.5초에 맞춰 정확히 4.48초(112프레임)짜리 비디오 클립을 생성함.
5. **FFmpeg `-shortest`에 의한 52초 영구 소실**:
   - 최종 마스터 합체 명령어에서 `-shortest` 플래그가 사용되어, 비디오가 끝나는 955.68초 시점에 인코딩이 강제 중단됨.
   - 이로 인해 **오디오 트랙 마지막 52.289초 분량(에피소드 전체의 최종 결론 및 여운 내레이션)이 통째로 잘려 나가 영구 소실**됨.
6. **샷 2번부터 시작된 립싱크 파탄**:
   - `SHOT_002`에서 화면은 4.5초 만에 다음 샷(`SHOT_003`)으로 넘어가는데, 내레이션은 여전히 `SHOT_002` 대사를 10.4초 동안 읊고 있어, 영상 시작 15초 만에 이미 화면과 음성이 5초 이상 어긋나는 치명적 립싱크 붕괴 발생.

---

### 2.2 구형 네안데르탈인 에셋의 SSOT 위반 실태 (ERR-043 포렌식)

#### 오디오 트랙 위반
- `audio/padded/SHOT_001.wav ~ SHOT_039.wav` 39개 전수:
  - 포맷: **PCM 44,100Hz, 1 채널 (모노)**.
  - 신규 SSOT(PCM 48,000Hz, 2 채널 스테레오) 위반.
- `audio/neanderthal_voice_48k.wav`:
  - 파일명에는 `48k`가 붙어 있으나 실제 ffprobe 분석 결과 **44,100Hz 모노**로 확인됨 (허위 파일명).
  - 문장 간 간격이 0 바이트 디지털 무음(Digital Black)으로 채워져 청각적 단절감 유발.

#### 자막 트랙 위반
- `subtitles/pilot_subtitles_1200s.ass` 및 `generation/pilot_subtitles_1200s.ass`:
  - 39개 이벤트 중 **한 줄 36자를 초과하는 라인이 무려 40개(최대 86자)** 존재.
  - 대표 사례: `SHOT_022` (84자 / 86자, 50.4초 동안 단일 이벤트로 방치).
  - 52pt Pretendard 폰트(글자당 약 48px) 적용 시 86자는 **4,128px**에 달하여 1920 캔버스 좌우를 1,000px 이상 벗어나 심각하게 잘려 나감.

---

### 2.3 postflight 검증기의 맹점 (거짓 완료의 원인)

- 기존 `nollam_file_postflight.py` 및 `postflight_release.py`는:
  1. 실제 디스크에 존재하는 WAV/ASS 파일을 열어 ffprobe나 문자 수 검사를 수행하지 않고, 전달된 mock dictionary 메타데이터만 대조함.
  2. 최종 MP4 컨테이너의 스트림 파라미터만 확인하여, FFmpeg가 44.1k 모노를 48k 스테레오 컨테이너로 리샘플링한 것을 "정상 48k 스테레오"로 오판함.
  3. **비디오 지속시간과 오디오 지속시간의 오차 검사(Stream Parity)가 누락**되어 52초 오디오 절삭을 감지하지 못함.

---

### 2.4 신규 발견 결함 [ERR-044]: Windows Pytest basetemp 충돌

- `pytest.ini`의 `addopts = -v --basetemp=D:/module/scratch/pytest_tmp`로 인해, Windows 파일 시스템의 핸들 해제 지연 특성상 이전 테스트의 디렉터리 삭제(`rm_rf`) 시 `[WinError 145] 디렉터리가 비어 있지 않습니다`가 발생하고, 직후 생성 시 `[WinError 183] 파일이 이미 있습니다`가 연쇄 발생함.
- 이로 인해 `test_bare_tip_renderer_contract.py`, `test_nollam_render_contract.py`, `test_nollam_synthetic_e2e.py` 등 5개 단위 테스트가 setup 단계에서 무고하게 크래시됨을 확인.

---

### 2.5 Phase 7 추출 라우터의 세부 결함 (DEFECT-01 ~ 03)

1. **[DEFECT-01]** `routes/pipeline_routes.py` line 52-53에 `NOLLAM-HIMALAYA-MASTER-1200S-FINAL.mp4`가 정적 하드코딩되어 있어, 네안데르탈인 등 신규 에피소드에서 마스터 준비 상태를 `False`로 오판.
2. **[DEFECT-02]** `routes/script_routes.py` line 21의 Pydantic 자막 폰트 기본값이 SSOT 헌법(52pt)이 아닌 레거시 `56`으로 남아있어 GUI 스타일 갱신 시 자막 규격 훼손 위험.
3. **[DEFECT-03]** `studio_gui_server.py` 내 `/api/history/*` (Production History Engine)이 메인 파일에 잔류하여 완전한 모듈화 미달성.

---

## 3. 삼사 만장일치 쇄신 해결책 및 권고 사항

### 3.1 [원칙 1] 대본 실측 발화 기반 비디오 1:1 동기화 (Lip-sync Restoration)
- 씬 길이를 4.5초로 인위적으로 깎아내지 않는다.
- SuperTonic3 M2 실측 발화 시간($T_{\text{speech}}$, 예: 10.2초)에 유한 룸톤 0.40초(앞 0.15s + 뒤 0.25s)를 더한 **진짜 씬 길이($T_{\text{scene}} = 10.6\text{s}$)**로 비디오 클립을 1:1 렌더링한다.
- 템포 감은 비디오를 잘라먹는 것이 아니라, 10.6초 씬 내부에서 **PIL 서브픽셀 120% 오버스캔 크롭을 통해 5.3초 단위의 지각 컷 2개(Layer 3)**를 창출하는 2계층 하이브리드 페이싱으로 해결한다.

### 3.2 [원칙 2] 자막 마이크로 클로즈 타임 슬라이싱 (Subtitle Micro-slicing)
- `SHOT_022` 등 50초 롱테이크 문장은 한국어 시맨틱 종결어미(`-고`, `-며`, `-지만`, `-는데`)를 기준으로 **16~17초 단위 2~3개 정갈한 자막 이벤트로 시간 분할**한다.
- 52pt Pretendard, 1줄 최대 36자, 최대 2줄 70자, 좌우 마진 50px, 피라미드 정렬(윗줄 20~28자, 아랫줄 28~35자)을 엄수한다.

### 3.3 [원칙 3] 3중 실물 감사 체인 (Three-Tier Physical Postflight) 확립
```
[Layer 1: 원천 입력 물리 감사]
  - 39개 WAV 전수: ffprobe 48,000Hz, 2ch Stereo, 유한 룸톤 0.35~0.50s, SHA-256 검증
  - 39개 이미지: PIL 1920x1080 디코드, 18% 클리어존 검증
  - 씬 1번: Bare-Tip provenance (.renderer.json) 및 손/펜 0건 검증
  - ASS 자막: 52pt Pretendard, 줄당 <= 36자, 최대 2줄 <= 70자, 겹침 0.000s 검증
       │ (1건이라도 미달 시 Fail-Closed 차단)
       ▼
[Layer 2: 렌더 컨테이너 실물 감사]
  - MP4: 1080p 25fps CFR, yuv420p, bt709, AAC 48k stereo
  - 음향: EBU R128 (-16 LUFS, True Peak <= -1.0 dBTP)
  - 스트림 일치성 (Stream Parity): |t_video - t_audio| <= 0.050s 엄격 검증
       │
       ▼
[Layer 3: 메타데이터 영구 바인딩]
  - master_1200s_manifest.json 실측치 동기화
  - release_manifest.json에 Merkle SHA-256 체인 영구 박제
```

### 3.4 [원칙 4] 3-Tier State Execution 아키텍처
- 포트 3093(TTS) 및 9222(Flow)가 비활성인 현재 상태에서는 `Local Synthetic Mode`를 유지하며 정직하게 명시한다.
- 실 서비스 기동 시 `Preflight Probe Gate`로 소켓 헬스체크를 수행하여 미가동 시 파이프라인을 Fail-Closed(HTTP 503)하고 가짜 더미 생성을 원천 방지한다.
- 온라인 확인 시 멱등한 Live Production으로 자동 전이한다.

### 3.5 [원칙 5] Windows Pytest basetemp 안정화 [ERR-044 치유]
- `conftest.py`에 세션별 고유 타임스탬프 임시 디렉터리(`D:/module/scratch/pytest_tmp/run_<pid>_<timestamp>`)를 생성하는 훅을 탑재하여 Windows 파일 락 충돌을 영구 박멸한다.

---

## 4. 최종 결론

기존 네안데르탈인 마스터는 "완성"이 아니라 **후반부 52초가 잘려 나간 불완전 산출물**이었습니다.
본 리뷰에서 도출된 쇄신안에 따라, 네안데르탈인 런의 오디오(48k stereo)와 자막(36자 2줄 마이크로 슬라이싱)을 전면 재생성하고, 3중 실물 감사를 통과한 진짜 마스터 비디오를 재합성해야 비로소 진정한 프로덕션 완료로 인정될 수 있습니다.
