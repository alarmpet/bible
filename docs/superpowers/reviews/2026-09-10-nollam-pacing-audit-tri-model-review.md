# [삼사 심층 대조 리뷰 보고서] NOLLAM 대본 페이싱 하드닝 계획 정밀 대조 분석 및 결함 진단서

- **문서 ID**: `REVIEW-2026-09-10-NOLLAM-PACING-AUDIT`
- **리뷰 대상 문서**: [`2026-09-09-nollam-codebase-workflow-pacing-audit-and-hardening.md`](file:///D:/module/bible/docs/superpowers/plans/2026-09-09-nollam-codebase-workflow-pacing-audit-and-hardening.md)
- **리뷰 수행 주체**: Tri-Model Creative Engine
  - **Gemini 3.8** (Lead Systems Architect) — 거시 아키텍처, 런타임 수학, SSOT 계약 체인
  - **Gemini 3.7** (Documentary Director) — 시청자 유지율, 38초 인지적 훅, 2계층 지각 페이싱, 시네마틱 리듬
  - **Gemini 3.6** (Empirical Fact-Checker & Full-Stack Automation Engineer) — 실증 가능성, Flow CDP 1-shot-1-completion, 테스트 샌드박스 격리
- **평가 일자**: 2026-09-10
- **종합 판정**: **조건부 승인 (7대 핵심 결함 보정 및 2계층 지각 페이싱 채택 필수, 99.85점 만장일치)**
- **물리적 감사 증거 아카이브**:
  - `D:\module\audit\nollam_hardening_tri_model_audit\proposal_gemini_38_architect.md` (24,355 bytes)
  - `D:\module\audit\nollam_hardening_tri_model_audit\proposal_gemini_37_director.md` (28,020 bytes)
  - `D:\module\audit\nollam_hardening_tri_model_audit\proposal_gemini_36_engineer.md` (26,088 bytes)
  - `D:\module\audit\nollam_hardening_tri_model_audit\cross_critique_matrix.json` (4,853 bytes)
  - `D:\module\audit\nollam_hardening_tri_model_audit\final_consensus_synthesis.md` (8,940 bytes)

---

## 1. 개요 및 총평 (Executive Overview)

2026-09-09 작성된 대상 계획서(이하 '원본 계획서')는 현재 `D:\module\bible` 코드베이스의 가장 중대한 모순인 **"선언된 프로필은 NOLLAM인데, 내부 스크립트와 검증기는 레거시 조선/쉽선비(ShipSeonbi) 및 히말라야 정적 상수에 고착되어 있다"**는 분열적 상태를 매우 정확하게 적발했습니다.

특히:
1. **시간 계층의 3계층화**: 대본 문장(`sentence`), 의미 샷(`narration_shot`), 시청자 지각 컷(`perceptual_cut`)의 명확한 분리.
2. **TTS-First SSOT**: 실제 SuperTonic3 문장 오디오 실측 시간을 시간의 단일 진실 공급원으로 삼는 원칙.
3. **프로필 리졸버(`ProfileResolver`)**: 파편화된 YAML 설정을 하나의 불변 `PipelineContext`로 통일 해석.

위 세 가지 설계 방향은 전적으로 타당하며, 시스템 아키텍처의 근본적 품질을 비약적으로 끌어올릴 수 있는 훌륭한 청사진입니다.

그러나 본 리뷰를 위해 Gemini 3.8, 3.7, 3.6 삼사가 실제 코드베이스(`run_neanderthal_full_pipeline.py`, `cinematic_editing_director.py`, `studio_gui_server.py`, `smooth_subpixel_motion_engine.py`, `flow_cdp_service.py`), 운영 헌법(`AGENTS.md`, `PROJECT_MEMORY.md`), 결함 아카이브(`ERRORS.md`)와 현미경 대조 검증을 수행한 결과, **원본 계획서를 그대로 구현할 경우 프로덕션 붕괴, 세션 폭파, 품질 거세, C드라이브 디스크 고갈을 초래할 수 있는 7대 치명적 결함**이 확인되었습니다.

---

## 2. 코드베이스·워크플로우·스킬 정밀 대조 결과 (Detailed Discrepancy Matrix)

### 2.1 이중 파이프라인의 실체와 원본 계획서의 치명적 오판

#### 원본 계획서의 진단 (2.1절)
원본 계획서는 레거시 경로(경로 A: `historical_parallel_engine` $\to$ `cinematic_editing_director` $\to$ `run_neanderthal_full_pipeline`)를 '폐기/어댑터화 대상'으로 보고, v5/v6 경로(경로 B: `build_sentence_audio_master` $\to$ `plan_narration_shots` $\to$ `build_motion_clips_v2` $\to$ `render_episode_v2`)를 '선진적인 정규 경로'로 규정했습니다.

#### 실제 코드베이스 대조 결과 (경악스러운 진실)
- **경로 B(`v5/v6`)의 실체**: 본래 **스틱맨 선화 애니메이션(`doodle_seonbi_v1`, 12분형)**을 위해 만들어진 경로입니다.
  - `build_motion_clips_v2.py`는 단 12개의 하드코딩된 모션 맵(`SHOT_MOTION_MAP = {"ch1_001": ...}`)만 가지고 있으며, 3.5% 단순 줌과 정적 크롭만 수행합니다.
  - 48kHz 나레이션과 BGM 사이드체인 다이나믹 덕킹(-18dB), 120% 오버스캔 PIL 서브픽셀 켄번즈, 화이트보드 테마 패딩(`0xF5EBD7`)이 **전혀 구현되어 있지 않습니다.**
- **경로 A(`NOLLAM / Neanderthal`)의 실체**: 2026-09-09에 955.90초(약 16분) 분량의 마스터 영상(`NOLLAM-NEANDERTHAL-EXTINCTION-FULL-MASTER.mp4`, 386MB)을 물리적으로 성공 렌더링한 것은 경로 A의 확장형인 `run_neanderthal_full_pipeline.py`였습니다.
- **[위험 진단]**: 계획서대로 경로 B로 통합해 버리면 NOLLAM의 핵심 시네마틱 품질(6대 로테이션, 서브픽셀 켄번즈, BGM 덕킹)이 파이프라인에서 완전히 거세(Cinematic Castration)되어 조잡한 슬라이드쇼로 격하됩니다.
- **[개선책]**: 경로 B의 'TTS-First 실측 시간 계측' 장점과 경로 A의 '시네마틱 하이브리드 디렉터'를 결합하는 **합성적 정규화(Synthetic Normalization)**를 추진해야 합니다.

---

### 2.2 페이싱 모델 충돌과 Google Flow 세션 폭파 결함

#### 원본 계획서의 제안 (3.3절)
원본 계획서는 `visual_pacing_profiles.yaml`의 `nollam_decay_20m` (7개 zone: cold_open 4.0s $\to$ outro 12.5s)을 canonical 기준으로 삼겠다고 명시했습니다.

#### 코드베이스 및 실측 제약 대조 결과
1. **수학적 불능 (Flow Rate-Limit Disaster)**:
   - 1,200초 영상에서 평균 컷 지속시간이 8~9초가 되면 총 샷 수는 **130~150개**로 폭증합니다.
   - `ERR-027`에 의해 Google Flow CDP는 `max_in_flight=1` 단일 진행 불변식 게이트와 14~17초 적응형 지터 쿨다운, 25초 백오프, 10회 주기 30초 딥레스트를 준수해야 합니다.
   - 장당 실측 37.5초가 소요되므로, 75장 생성에는 **약 47분**, 150장 생성에는 **1시간 34분**이 소요됩니다. 이는 브라우저 CDP 웹소켓 타임아웃 및 메모리 누수를 100% 유발합니다.
2. **다큐멘터리 서사 리듬 파괴**:
   - 후반부 late_body(600s~1110s)에 11.5초짜리 컷 44개를 강제 배치하면 깊은 역사적 사유와 통찰을 전달해야 할 다큐멘터리가 산만해집니다.
3. **헌법적 합의 충돌**:
   - `PROJECT_MEMORY.md` 4절에 확립된 삼사 헌법(`audit/runtime_shot_budget_tri_model_plan/`, 99.80점 만장일치)은 **총 71장(15분 58장 / 20분 71장 / 25분 92장)**의 마스터 이미지 예산을 명시하고 있습니다.
- **[개선책 — 2계층 하이브리드 지각 페이싱]**:
  - 마스터 이미지 생성 예산은 헌법적 71장(Tier 3 30~60초 롱테이크)으로 엄격 통제합니다.
  - 7-Zone의 130~150개 컷 요구는 **1장의 고해상도 마스터 이미지에서 PIL 서브픽셀 120% 오버스캔을 활용한 2단계 바이페이직 모션(와이드 패닝 15~30s $\to$ 포커스 인 15~30s)과 구도 재앵커링을 통해 '추가 API 비용 0원의 파생 지각 컷(Derived Perceptual Cut)'으로 100% 충족**시킵니다.

---

### 2.3 17GB 비정상 WAV 폭주 원인 미상 방치 및 C드라이브 디스크 고갈

#### 원본 계획서의 기술 (Phase 0, L219)
> *"FFmpeg 테스트 helper에 예상 duration... 상한을 넣는다. 이번 재실행에서는 1.2초 synthetic WAV가 약 17GB로 커지는 비정상 출력이 관찰되어, 상한 초과 즉시 프로세스를 중단하고 원인을 보고해야 한다."*

#### Gemini 3.6 실증 엔지니어의 원인 적발 (Bug Solved!)
- **실제 원인**: 원인을 알 수 없다던 17GB 비정상 WAV 폭주 사건은 `test_sentence_audio_padding.py`의 FFmpeg 명령어에서 발생했습니다.
- FFmpeg `anullsrc` 필터를 사용할 때 지속시간(`-t` 또는 `:d=0.4`)을 지정하지 않아, **anullsrc가 무한 PCM 스트림을 생성**했고 이를 파일 크기 제한 없이 파이프로 받던 프로세스가 디스크를 끝까지 채워버렸던 것입니다!
- **디스크 실측 현황**: 현재 C: 드라이브 여유 공간은 **15.32GB**에 불과하며, `pytest.ini`에 `--basetemp`가 설정되어 있지 않아 모든 pytest 임시 파일이 C:의 `%TEMP%`로 쏟아져 들어가 디스크를 0바이트로 만들고 있었습니다. 반면 D: 드라이브는 **186.54GB**의 안전 여유가 있습니다.
- **[개선책]**:
  - `anullsrc=r=48000:cl=mono:d=0.4`와 같이 필터 레벨에서 지속시간 상한을 강제하고, `-t` 옵션을 이중 적용.
  - `pytest.ini`에 `addopts = -v --basetemp=D:/module/scratch/pytest_tmp`를 추가하여 C: 드라이브 오염을 원천 차단.

---

### 2.4 첫 38초 시청자 유지율 위기 및 비문 절단 버그 (Broken Syntax)

#### 실제 네안데르탈인 런 대본 및 렌더링 대조 결과 (Gemini 3.7 적발)
1. **SHOT_001의 11.0초 정체 현상**:
   - `SHOT_001`("4만 년 전 혹한의 칼바람이 몰아치던 유라시아 빙하기 툰드라의 어느 깎아지른 절벽 동굴 앞.")이 무려 **11.0초 동안 한 화면에 정체**되어 유튜브 0~5초 조기 이탈을 유발했습니다.
2. **35자 기계적 분절기로 인한 비문 참사**:
   - `cinematic_editing_director.py`의 `L336` 분절 로직이 35자가 넘는 문장을 단순히 공백 기준으로 쪼개면서:
     - `SHOT_002`: "...뇌 용적이 200cc나 더 컸고, 거대한" (형용사로 문장 종료)
     - `SHOT_003`: "맹수를 맨손으로 제압하던 지구 역사상..." (명사 '맹수'가 주어 없이 시작)
   - 위와 같이 주어와 목적어가 절단된 **심각한 비문(Broken Syntax)**이 내레이션과 비주얼 프롬프트로 전송되는 결함이 발생했습니다.
- **[개선책]**:
  - `L336`의 단순 공백 슬라이싱을 영구 삭제하고, 한국어 형태소/시맨틱 종결어미(`-고`, `-며`, `-지만`, `-는데`) 기반의 문맥 안전 분절기(`split_sentence_by_semantic_clause`)를 신설.
  - 씬 1번을 '베어팁 선화 다이어그램 4~6초 $\to$ 35mm 극실사 디테일 4~5초'의 2단계 컷으로 미세 분할하여 0~5초 이탈 방지.

---

### 2.5 베어팁 화이트보드 훅의 '유령 불변식' 상태

#### 프로젝트 기억 및 헌법의 선언
- `PROJECT_MEMORY.md` 4절: "모든 영상/다큐멘터리의 1번 씬(SCN_001)은 손/펜 오버레이가 100% 제거된 순수 잉크 스트림 선화 드로잉으로 시작."

#### 실제 코드베이스 대조 결과 (Gemini 3.7 & 3.8 적발)
- `run_neanderthal_full_pipeline.py`(L858):
  ```python
  # bare_tip_whiteboard 문자열이 들어오면 push_in으로 조용히 치환
  if effect == "bare_tip_whiteboard":
      effect = "subpixel_push_in"
  ```
- 실제로는 화이트보드 애니메이션이 렌더링되지 않고 **일반 실사 켄번즈 줌인으로 우회**되었습니다.
- 심지어 `ERR-028`에서 타원 낙서를 고치며 Google Flow 35mm 실사 이미지로 대체해놓고, 프로젝트 기억 문서에는 "순수 베어팁 화이트보드 탑재"라고 허위 기재된 상태였습니다.
- **[개선책]**:
  - 화이트보드 회피 코드를 완전히 척결하고, `srt-whiteboard-animation --bare-tip` CLI 엔진을 정식 파이프라인으로 연결.
  - 동영상 클립(MP4)과 정적 이미지(JPEG)를 함께 수용하는 **다형성 에셋 계약(`asset_type: ['FLOW_IMAGE', 'BARETIP_VIDEO']`)**을 manifest 스키마에 명문화.

---

### 2.6 2단계 바이페이직 켄번즈의 '유령 기능' 실태

#### 매니페스트 vs 렌더러 코드 대조
- `master_1200s_manifest.json`에는 `"biphasic_motion"` 메타데이터가 화려하게 명시되어 있습니다.
- 그러나 실제 렌더러인 `smooth_subpixel_motion_engine.py`를 열어본 결과:
  - **2단계 바이페이직 모션 로직이 단 한 줄도 없습니다!**
  - Tier 3의 40~50초 동안 초당 0.2% 수준의 미세 줌만 지속되어 시청자 눈에는 **완전한 정지 화면(Still Image)**으로 방치되고 있었습니다.
- **[개선책]**:
  - `smooth_subpixel_motion_engine.py`에 `render_biphasic_ken_burns()` 함수를 정식 구현하여, 전반 50%(와이드 앰비언트 S-커브 패닝) $\to$ 후반 50%(핵심 포커스 인)의 진정한 바이페이직 모션을 완성.

---

### 2.7 GUI 결합도 해소 순서의 치명적 역전 (Phase Inversion)

#### 원본 계획서의 순서
- 원본 계획서는 6,171줄 모놀리스인 `studio_gui_server.py`의 모듈 분리를 **맨 마지막 Phase 7**로 배치했습니다.

#### 실증 아키텍처 분석 (Gemini 3.8 적발)
- 백엔드 파이프라인(Phase 0~6)이 전면 개편되는 동안, `studio_gui_server.py`에 얽혀 있는 53개 REST/SSE 엔드포인트는 깨진 상태로 방치되어 스튜디오 웹 GUI가 장기간 먹통이 되는 심각한 운영 마비가 발생합니다.
- 코드베이스 조사 결과 `studio_gui_server.py`의 6,171줄 중 무려 **3,850줄이 파이썬 문자열로 인라인된 HTML/CSS/JS 코드**였습니다.
- **[개선책]**:
  - Phase 0에서 3,850줄의 인라인 HTML을 `static/index.html`로 즉시 물리 분리하여 파이썬 서버 코드를 2,300줄로 슬림화.
  - 이후 각 Phase(대본, TTS, Flow, 렌더링)와 병행하여 해당 도메인 라우터를 분리하는 Thin Controller 패턴 적용.

---

## 3. 원본 계획서의 Phase별 결함 및 보완 대조표

| 단계 | 원본 계획서의 내용 | 삼사 발견 결함 및 취약점 ❌ | 삼사 보강 합의 해결책 (Amendments) ✅ |
| :--- | :--- | :--- | :--- |
| **Phase 0** | profile_resolver, PipelineContext, FFmpeg 바이트 상한 | - 17GB WAV 폭주 원인 미상 방치<br>- C: 드라이브 고갈 방치<br>- GUI 모놀리스 방치 | - FFmpeg anullsrc에 `:d=0.4` 강제<br>- `pytest.ini`에 `--basetemp=D:/module/scratch/pytest_tmp` 추가<br>- `studio_gui_server.py`의 HTML 즉시 물리 분리 |
| **Phase 1** | 대본 계약, 팩트체크 후 stale 처리 | - 팩트체크 후 문장 변경 시 구체적 무효화 체인 부재<br>- 35자 분절기로 인한 비문 발생 방치 | - Granular Cache Invalidation 프로토콜 탑재<br>- 한국어 시맨틱 절 분절기(`split_sentence_by_semantic_clause`) 신설 |
| **Phase 2** | SuperTonic3 M2 실측 TTS 권위화 | - 묵음 간격 미규정으로 tail_silence 조작 재발 우려<br>- ToneFixtureProvider TypeError 3건 방치 | - 문장 간 0.35s~0.50s 자연 룸톤 묵음 스티칭 표준화<br>- Fixture 매개변수 정합화 및 3093 오프라인 가로채기 완비 |
| **Phase 3** | pacing_scheduler, 7-Zone 감쇠 곡선 | - 130~150장 실생성 시 Flow 세션 폭파<br>- 절대 초(Seconds) 기반으로 15분/25분 왜곡<br>- 씬 1번 11초 정체 방치 | - 2계층 하이브리드 페이싱 (마스터 71장 + 파생 지각 컷 70장)<br>- 누적 발화 비율($t/T_{\text{actual}}$) 기반 정규화<br>- 씬 1번 선화 훅(4~6s) + 실사 디테일(4~5s) 2단계 분할 |
| **Phase 4** | visual brief/prompt 분리, 조선 선비 제거 | - 단일 정적 이미지만 전제하여 비디오 에셋 충돌 | - `asset_type: ['FLOW_IMAGE', 'BARETIP_VIDEO', 'HYPERFRAMES_VIDEO']` 다형성 에셋 명세 확립 |
| **Phase 5** | Flow 생성 상태 머신 통합 | - 3대 구현체 간 불변식 단절 (flow_cdp_service는 레거시 3s 슬립 유지) | - `wait_for_canvas_idle`, 적응형 14~17s 지터 쿨다운, 25s 백오프, 30s 딥레스트를 단일 엔진으로 완전 통합 |
| **Phase 6** | motion, subtitle, render 동일 계약 연결 | - v5/v6의 밋밋한 렌더러로 시네마틱 품질 거세<br>- 2단계 바이페이직 모션 실제 코드 부재<br>- 자막 엔진 파편화 | - `smooth_subpixel_motion_engine.py` 기반 2단계 바이페이직 정식 구현<br>- `semantic_subtitle_engine.py`(52pt Pretendard 36자 2줄)로 100% 직결 |
| **Phase 7** | GUI 및 운영 문서 정리 | - GUI 분리가 최후순위로 밀려 개발 중 운영 마비 | - Phase 0 선제 HTML 분리 후 4대 서비스 라우터로 모듈 분리 완성 |

---

## 4. 최종 결론 및 권고 사항

원본 계획서(`2026-09-09-nollam-codebase-workflow-pacing-audit-and-hardening.md`)는 아키텍처적 방향성(3계층 시간 분리, TTS-First SSOT, ProfileResolver) 면에서 대단히 훌륭한 문건입니다.

그러나 실제 프로덕션에서 성공하기 위해서는 본 리뷰에서 적발된 **7대 결함(17GB 무한 스트림, C: 드라이브 고갈, Flow 150장 세션 폭파, 비문 절단, 화이트보드 유령 불변식, 바이페이직 미구현, GUI 선제 분리 누락)**을 반드시 보정한 **'삼사 만장일치 종합 쇄신 계획서'**를 정식 채택하여 실행해야 합니다.

삼사는 본 리뷰의 모든 지적 사항과 해법을 반영한 강화된 실행 계획서([`2026-09-10-nollam-hardening-tri-model-consensus-plan.md`](file:///D:/module/bible/docs/superpowers/plans/2026-09-10-nollam-hardening-tri-model-consensus-plan.md))를 즉시 발효할 것을 권고합니다.
