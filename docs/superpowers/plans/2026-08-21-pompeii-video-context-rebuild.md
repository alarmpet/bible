# 폼페이 다큐 시청각 정합성 재구축 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사실관계가 검증된 새 대본과 실제 픽셀을 확인한 영상 자산을 불변 ID로 연결해, 문장·이미지·오디오·자막이 같은 의미와 시간축을 공유하는 15:00–16:30 폼페이 다큐 v2를 새 run에 만든다.

**Architecture:** `source ledger → canonical shot contract → provider asset lineage → pixel QA + human approval → measured audio/subtitle timeline → build-isolated render → machine postflight`를 단일 hash chain으로 묶는다. 어떤 게이트도 문자열 PASS나 파일명 존재만으로 통과하지 않으며 실패 시 publish 파일을 만들지 않는다.

**Tech Stack:** Python 3, pytest, Pydantic/JSON Schema, PyYAML, Playwright, Pillow/imagehash, SuperTonic3 M4, FFmpeg/ffprobe, ASS, PowerShell.

**Spec:** `docs/superpowers/specs/2026-08-21-pompeii-video-quality-audit-design.md`

## Global Constraints

- 현재 원본 `human_archive/runs/ep01_pompeii_18hours`와 `final_pompeii_ep01.mp4`는 수정·삭제·덮어쓰기하지 않는다.
- 새 작업 경로는 `human_archive/runs/ep01_pompeii_rebuild_v2`다. 파일럿 build ID는 `pilot-v2-001`, 전체 build ID는 `full-v2-001`로 시작한다. 같은 ID가 이미 있으면 덮어쓰지 말고 이 계획을 갱신해 다음 순번을 승인받는다.
- **파이프라인 및 규칙 격리**: `CLAUDE.md`, `manual.md`, `MEDIA_RULES.md`의 규칙은 구약 힐링(`bible_healing`) 전용 잠금(`media_rules_lock.json`)을 따른다. 인류사 다큐(`human_archive`)는 본 계획서와 `documentary_contract.yaml`, `narration_policy.yaml`을 단일 잠금 기준으로 사용하며 상호 코덱·음성 파라미터가 간섭되지 않도록 완전히 격리한다.
- **경로 및 플랫폼 격리**: `PATHS.md`의 레거시 절대경로(`C:\Users\amd\...`)를 참조하지 않는다. 모든 스크립트와 매니페스트는 저장소 루트 기준 상대 POSIX 경로만 기록하며, Windows 환경에서의 파일 교체는 `os.replace` 또는 임시파일 기반 Atomic Swap을 보장한다.
- **의존성 고정**: `pytest>=8.0.0`, `PyYAML>=6.0.0`, `requests>=2.30.0`, `pillow>=10.0.0`, `pydantic>=2.0.0`, `jsonschema>=4.20.0`, `playwright>=1.40.0`, `imagehash>=4.3.1`, `numpy>=1.24.0`, `scipy>=1.10.0`을 `requirements.lock.txt`에 명시하고 검증한다.
- 현재 JPG 68개는 새 결과에 재사용하지 않는다. 파일명만 재배열하거나 서비스 표식을 크롭해 구제하지 않는다.
- 생성 서비스의 이용약관과 export 권한을 준수한다. 깨끗한 결과를 정식으로 받을 수 없으면 허가된 스톡·공식 이미지·다른 제공자로 전환한다.
- 사실, 논쟁적 해석, AI 재현을 대본과 화면에서 구분한다. 확인되지 않은 피해자의 동기·가족관계·마지막 감정을 사실처럼 말하지 않는다.
- 권장 계약은 15:00–16:30, 첫 12초 핵심 질문, 첫 40초 고밀도 훅이다. 68이라는 shot 수는 목표가 아니며 대본 컴파일 결과(약 55~75샷)에 따라 결정한다.
- **시각 컷 밀도 및 예산 (Shot Budget Policy)**:
  - 0:00–0:12 (첫 12초): 1~2컷 초압축 훅 (반전 사실 + 핵심 질문)
  - 0:12–0:40 (첫 40초): 4~8초 단위 고밀도 컷 전환 (5~7컷, 단서·증거·현장)
  - 0:40–3:00 (챕터 1 후반): 1~2문장(6~10초) 단위 컷 전환 (15~20컷 배분, 전체 컷의 35~45% 집중)
  - 챕터 2 이후: 사건/주제 단위 10~18초 호흡 컷
- 화면 기준: 1920×1080, SAR 1:1, DAR 16:9, strict 25 CFR, pix_fmt `yuv420p`, range `tv`, matrix/primaries/transfer 각각 `bt709`.
- 오디오 기준: 48kHz mono, SuperTonic3 M4 (speed 0.94, pitch -0.8 st, total_step 10), EBU R128 -16±1 LUFS, 4× oversampled true peak ≤ -1dBTP, clipping 0. 허용 pause(0.2~0.5초)는 timeline에 선언하고 clean narration에서 `silencedetect=n=-50dB:d=0.5`로 미선언 무음을 차단한다.
- 자막 기준: 실제 음성 조각 경계(phrase WAV) 기반 단일 렌더링. 글자 수 비례 karaoke fallback은 금지한다. hard max 2줄·줄당 25자, 권장 14–22자, 1080p 기준 Fontsize 88~96px (Malgun Gothic, Outline 7, Shadow 3, MarginV 90), 최대 11 CPS와 최소 0.7초를 적용한다.
- 의미 기준: 모든 사용 shot이 `approval=approved`이고 required axes인 subject/place/era/action/result가 모두 pass여야 한다. partial은 contract에 미리 지정한 추상·establishing shot만 근거와 사람 waiver가 있을 때 허용한다. watermark·서비스 마크·금지 OCR text와 승인 누락은 0이어야 한다.
- 자동 테스트가 PASS여도 사람의 사실 계약 승인, 파일럿 승인, 전체 contact sheet 승인을 대체하지 않는다.
- production 변경 전 이 설계와 작업 제목·길이·고지 방식을 사용자에게 승인받는다.
- 현재 dirty worktree의 사용자 변경은 보존한다. 각 commit은 아래에 적은 파일만 정확히 stage하고, 관련 없는 파일은 포함하지 않는다.
- source/claim/script/fact/shot-plan 승인 JSON은 작은 재현성 산출물로 source control에 정확히 stage한다. media와 provider download는 commit하지 않는다. 승인 파일을 바꾸는 대신 새 build/review revision을 만들며 release report가 그 hash를 보존한다.

---

## Task 0: 원본 보존과 진단 기준선 고정

**Files:**

- Create: `human_archive/audits/ep01_pompeii_18hours_2026-08-21/baseline.json`
- Create: `human_archive/scripts/capture_run_baseline.py`
- Test: `human_archive/tests/test_capture_run_baseline.py`

- [x] **Step 1: 원본 run을 쓰지 않는 실패 테스트를 작성한다.**

  테스트는 출력 경로가 원본 run 내부이면 거부하고, run 전체와 당시 scripts/config/templates의 상대경로·SHA-256·bytes·mtime을 recursive inventory로 기록해야 한다. final MP4에는 ffprobe duration·stream·코덱을 추가한다. 이미지 68개, motion 68개, JSON, ASS, concat, 썸네일, legacy, 작업 디렉터리까지 누락 여부를 보고한다.

- [x] **Step 2: 테스트를 실행해 아직 구현이 없어 실패하는지 확인한다.**

  ```powershell
  python -m pytest human_archive/tests/test_capture_run_baseline.py -v
  ```

  Expected: import/file-not-found 또는 명시적 test failure.

- [x] **Step 3: read-only 기준선 캡처를 구현한다.**

  `capture_run_baseline.py`는 기존 파일을 읽기만 하고 감사 디렉터리에 JSON을 atomic write한다. 최소 필드는 inventory별 `relative_path`, `sha256`, `bytes`, `mtime_utc`, 집계 count/bytes와 final의 `duration_sec`, streams, 그리고 `captured_at_utc`, `git_head`, `working_tree_dirty`다. baseline 출력 자체와 `.audit_*`는 inventory에서 제외한다.

- [x] **Step 4: 대상 파일의 현재 고정값을 교차 확인한다.**

  ```powershell
  python human_archive/scripts/capture_run_baseline.py --run-root human_archive/runs/ep01_pompeii_18hours --code-root human_archive/scripts --config-root human_archive/config --template-root human_archive/templates --output human_archive/audits/ep01_pompeii_18hours_2026-08-21/baseline.json
  Get-FileHash -Algorithm SHA256 human_archive/runs/ep01_pompeii_18hours/final_pompeii_ep01.mp4
  ```

  Expected SHA-256: `DA91A7F62549B24434D9EDE94E55EEEE9E3287D871815E3618A7DDD649455BC9`.

- [x] **Step 5: 테스트를 다시 실행하고 원본 변경이 없는지 확인한다.**

  ```powershell
  python -m pytest human_archive/tests/test_capture_run_baseline.py -v
  python human_archive/scripts/capture_run_baseline.py --run-root human_archive/runs/ep01_pompeii_18hours --code-root human_archive/scripts --config-root human_archive/config --template-root human_archive/templates --verify-against human_archive/audits/ep01_pompeii_18hours_2026-08-21/baseline.json
  ```

  Expected: tests PASS, recursive inventory hash 변화 0. `human_archive`가 Git 미추적이어도 이 검사가 원본 보존을 증명한다.

- [x] **Step 6: 기준선 파일만 commit한다.**

  ```powershell
  git add human_archive/audits/ep01_pompeii_18hours_2026-08-21/baseline.json human_archive/scripts/capture_run_baseline.py human_archive/tests/test_capture_run_baseline.py
  git commit -m "test: lock Pompeii episode baseline"
  ```

---

## Task 1: 사실 장부와 새 서사 계약 승인

**Files:**

- Modify: `human_archive/templates/documentary_contract.yaml`
- Modify: `human_archive/config/narration_policy.yaml`
- Create: `human_archive/sources/pompeii_ep01_source_ledger.json`
- Create: `human_archive/schemas/source_ledger.schema.json`
- Create: `human_archive/scripts/validate_fact_contract.py`
- Test: `human_archive/tests/test_fact_contract.py`

- [x] **Step 1: 현재 허위/과장 명제가 실패하도록 계약 테스트부터 작성한다.**

  다음 조건을 테스트한다.

  - `core_paradox`에 “대다수가 머물렀다”, “18시간의 탈출 기회”, “재산 집착”이 들어가면 실패
  - 8월 24일, 인구 2만, 폼페이 500°C, 대 플리니우스 질식이 `certainty: fact`이면 실패
  - 모든 `claim_id`에 URL/DOI, 인용 위치, `support_level`, 허용 표현이 없으면 실패
  - 목표 길이가 900–990초 밖이면 실패
  - opening contract에 12초 내 질문과 40초 내 범위 제시가 없으면 실패
  - 재연·AI 이미지·논쟁적 연표 고지 문구가 없으면 실패

- [x] **Step 2: red 상태를 확인한다.**

  ```powershell
  python -m pytest human_archive/tests/test_fact_contract.py -v
  ```

  Expected: 현재 “대다수 잔류/재산 집착” 계약 때문에 FAIL.

- [x] **Step 3: source ledger schema와 검증기를 구현한다.**

  `claim_id`, `claim_text`, `source_type`, `title`, `author_or_agency`, `year`, `url_or_doi`, `locator`, `evidence_mode`, `directness`, `geographic_scope`, `temporal_scope`, `independence_group`, `peer_review_status`, `correction_or_retraction_status`, `relation`, `method`, `limitations`, `support_level`, `uncertainty`, `allowed_wording`, `forbidden_wording`, `reviewed_at`를 필수화한다. 검증 실패는 exit 1이다. 공식기관·1차 사료·동료평가는 단일 서열이 아니라 서로 다른 특성이므로 claim-source 관계별로 평가한다.

- [x] **Step 4: 최소 권위 출처 묶음을 claim 단위로 입력한다.**

  반드시 포함할 주제는 날짜 논쟁, 18–19시간의 의미, 분연주 26→32km, 인구 추정 범위, 다수 탈출 가능성, 폼페이 PDC 온도 논쟁, 대 플리니우스 사인 불명, 16세기 운하/1748년 발굴, 피오렐리 1863, 개별 휴대품 사례, 2024 DNA 관계 재해석이다.

- [x] **Step 5: 새 episode 계약을 작성한다.**

  권장 작업 제목은 `폼페이 최후의 밤 — 많은 이들은 떠났고, 누가 남았나`로 두고, 중심 질문은 “남은 사람의 단일 심리”가 아니라 시간대별 위험·이동 제약·불확실한 선택으로 바꾼다. `narration_policy.yaml`의 Chapter 1 45% 규칙은 첫 40초 4–8초 고밀도 규칙으로 명시적으로 교체한다.

- [x] **Step 6: 전체 사실 계약 검증을 실행한다.**

  ```powershell
  python human_archive/scripts/validate_fact_contract.py --contract human_archive/templates/documentary_contract.yaml --ledger human_archive/sources/pompeii_ep01_source_ledger.json
  python -m pytest human_archive/tests/test_fact_contract.py -v
  ```

  Expected: 두 명령 모두 exit 0.

- [x] **Step 7: 사용자에게 제목·핵심 질문·길이·AI 재현 고지를 검토받고 승인 기록을 남긴다.**

  승인 전에는 Task 2의 production shot contract를 확정하지 않는다. 승인 기록은 ledger와 별도인 `human_archive/runs/ep01_pompeii_rebuild_v2/source/approvals/story_contract.json`에 계약 hash와 함께 저장한다.

- [x] **Step 8: 승인된 사실 계약을 commit한다.**

  ```powershell
  git add human_archive/templates/documentary_contract.yaml human_archive/config/narration_policy.yaml human_archive/sources/pompeii_ep01_source_ledger.json human_archive/schemas/source_ledger.schema.json human_archive/scripts/validate_fact_contract.py human_archive/tests/test_fact_contract.py human_archive/runs/ep01_pompeii_rebuild_v2/source/approvals/story_contract.json
  git commit -m "docs: replace Pompeii premise with sourced contract"
  ```

---

## Task 1A: 주장 우선(claim-first) 대본 생성과 문장별 사실 역검증

**Files:**

- Create: `human_archive/scripts/build_source_snapshots.py`
- Create: `human_archive/scripts/build_claim_inventory.py`
- Create: `human_archive/scripts/generate_verified_script.py`
- Create: `human_archive/scripts/verify_script_facts.py`
- Create: `human_archive/scripts/lib/fact_verification.py`
- Create: `human_archive/schemas/source_snapshot_manifest.schema.json`
- Create: `human_archive/schemas/claim_inventory.schema.json`
- Create: `human_archive/schemas/verified_script.schema.json`
- Create: `human_archive/schemas/fact_check_report.schema.json`
- Generate after source review: `human_archive/runs/ep01_pompeii_rebuild_v2/source/source_snapshot_manifest.json`
- Generate after claim review: `human_archive/runs/ep01_pompeii_rebuild_v2/source/claim_inventory.json`
- Generate after script review: `human_archive/runs/ep01_pompeii_rebuild_v2/source/script_draft.json`
- Generate after verification: `human_archive/runs/ep01_pompeii_rebuild_v2/source/fact_check_report.json`
- Create after human review: `human_archive/runs/ep01_pompeii_rebuild_v2/source/approvals/fact_approval.json`
- Test: `human_archive/tests/test_verified_script_generation.py`
- Test fixtures: `human_archive/tests/fixtures/fact_verification/`

- [x] **Step 1: 대본 생성 전에 실패해야 할 사실 오류 fixture를 만든다.**

  최소 fixture는 다음을 포함한다.

  - 출처나 locator 없이 “시민 대다수가 남았다”고 단정한 문장
  - 헤르쿨라네움의 약 500°C 연구를 폼페이 `location_scope`로 바꾼 문장
  - 13:00에서 다음 날 06:00을 “18시간”이라고 계산한 문장
  - 상반된 온도 연구가 있는데 하나만 확정 사실로 쓴 문장
  - “금화를 지녔다”에서 “재산 집착 때문에 탈출하지 않았다”는 인과를 새로 만든 문장
  - 소 플리니우스의 미세눔 관찰을 폼페이 시민 전체 반응으로 확대한 문장
  - source snapshot에 없는 직접 인용문을 따옴표로 만든 문장
  - 승인된 claim에는 없는 “가장 잔혹한”, “단 1초도 없었다” 같은 최상급·정밀 수치를 덧붙인 문장
  - 제목·썸네일 문구·chapter card·영상 설명에 대본보다 강한 미승인 주장을 넣은 경우

- [x] **Step 2: 위 오류가 모두 red인지 확인한다.**

  ```powershell
  python -m pytest human_archive/tests/test_verified_script_generation.py -v
  ```

  Expected: generator/verifier가 아직 없거나 각 불량 fixture가 명시적으로 FAIL.

- [x] **Step 3: source snapshot manifest를 만든다.**

  `build_source_snapshots.py`는 각 공식 페이지·논문·PDF에 대해 `source_id`, URL/DOI, 제목, 저자·기관, 발행일, 조회시각, 정확한 페이지·절·표·그림·문단 locator, 원문 언어, 판본/번역자, 추출기 버전, 원본 객체 hash, canonical page hash, 허용 범위 내 evidence span, evidence-span hash, 접근 상태를 기록한다. 동적 메뉴·광고·조회 배너는 canonical page hash에서 제외하되 실제 근거 span은 별도 hash로 고정한다. 검증에 필요한 범위만 저장하고 전체 저작물을 복제하지 않는다. 페이지가 바뀌거나 접근할 수 없으면 이전 승인으로 조용히 통과하지 않고 `source_changed` 또는 `source_unavailable`로 보고한다.

- [x] **Step 4: 문장보다 먼저 claim inventory를 생성·승인한다.**

  각 claim은 다음 필드를 가진다.

  ```json
  {
    "claim_id": "POM-PDC-TEMP-001",
    "statement": "폼페이에 도달한 화쇄밀도류의 온도·노출시간과 주요 사망기전은 연구 대상과 추정 방법에 따라 해석이 다르다.",
    "type": "contested_fact",
    "source_ids": ["SRC-DELLINO-2021", "SRC-MASTROLORENZO-2010"],
    "locators": ["Results", "Discussion"],
    "entity_scope": ["Pompeii"],
    "time_scope": ["AD 79"],
    "conflict_group_id": "POM-PDC-MODELS",
    "measurement_target": ["gas-particle mixture", "deposit proxy"],
    "eruptive_unit": ["Pompeii distal PDC"],
    "victim_group": ["Pompeii victims"],
    "methods": ["flow model", "thermal proxy"],
    "assumptions": ["study-specific"],
    "result_bounds": ["study-specific"],
    "limitations": ["측정 대상과 모델이 동일하지 않음"],
    "source_weights": ["reviewer-assigned"],
    "reviewer_synthesis": "수치를 한 지역·한 사망기전으로 합치지 않는다.",
    "numeric_bounds": null,
    "allowed_wording": ["연구에 따라 추정이 다르다"],
    "forbidden_wording": ["폼페이는 500도였다"],
    "risk": "high"
  }
  ```

  `verified_fact`, `contested_fact`, `inference`, `absence_based_inference`, `reconstruction`, `editorial` 중 분류가 없으면 claim을 승인하지 않는다. high-risk claim은 claim에 직접적인 공식/1차/동료평가 근거를 우선하며, 상반 연구가 있으면 양쪽을 함께 등록한다. 같은 연구를 재인용한 공식 페이지와 2차 자료는 동일 `independence_group`으로 묶어 독립 근거 두 개로 세지 않는다.

- [x] **Step 5: 승인된 claim만 입력으로 받는 대본 생성기를 구현한다.**

  `generate_verified_script.py`는 raw web 검색 결과나 기억을 직접 대본으로 바꾸지 않는다. 승인된 claim card, 서사 계약, 허용 표현만 model/context에 넣는다. 출력은 자유 텍스트가 아니라 문장별 JSON이다.

  ```json
  {
    "sentence_id": "s-001",
    "text": "서기 79년 가을로 보는 견해가 유력하지만 정확한 날짜는 논쟁 중입니다.",
    "claim_ids": ["POM-DATE-001"],
    "statement_type": "contested_fact",
    "certainty": "qualified",
    "disclosure": null
  }
  ```

  claim이 없는 역사 서술은 생성할 수 없다. 이 규칙은 본문뿐 아니라 제목, 12초 훅, thumbnail copy, chapter card, 화면 정보 그래픽, 영상 설명에도 적용한다. `editorial`은 의견임을 문장과 화면에서 표시하고, `reconstruction`은 AI 재현 고지를 자동 요구한다.

- [x] **Step 6: 독립적인 post-generation fact verifier를 구현한다.**

  생성기가 자기 결과를 스스로 PASS시키지 않게 별도 모듈과 별도 report를 사용한다. 검증 순서는 다음과 같다.

  1. schema·claim 존재·source locator·source hash 확인
  2. 인물·장소·시대 scope 확인
  3. 숫자·단위·날짜·시간 산술 확인
  4. 문장 간 타임라인·수치·인과 모순 확인
  5. 문장이 claim의 `allowed_wording` 범위를 넘었는지 확인
  6. 독립 evidence judge가 요약 메모가 아니라 원 evidence span과 문장의 entailment를 `supported`, `qualified`, `unsupported`, `conflicting`으로 판정
  7. 모든 공개 역사 문장을 사람 fact reviewer에게 강제 라우팅하고, high-risk와 `contested_fact`는 원문 locator·방법·한계까지 심층 대조

  evidence judge를 구성할 수 없으면 의미 검증을 건너뛰지 않고 build를 `verification_unavailable`로 차단한다. 자동 judge는 triage와 오류 탐지 전용이며 어떤 역사 문장도 단독으로 출판 승인하지 않는다. report에는 judge 모델·버전, prompt hash, evidence input hash, 판정, 신뢰도, 근거 설명을 기록한다. 같은 모델/공급자/프롬프트 계열의 두 호출을 독립된 두 근거로 세지 않는다.

- [x] **Step 7: 직접 인용·수치·인과에 강화 규칙을 적용한다.**

  - 따옴표 인용은 source snapshot의 동일 문구와 locator가 있을 때만 허용
  - 단위 변환과 시간 간격은 코드로 재계산하고 원문 숫자와 둘 다 기록
  - 장소가 다른 연구는 `location_scope`가 일치하지 않으면 사용 금지
  - 관찰 사실에서 심리·동기·인과를 새로 만들면 `unsupported_addition`
  - “모두”, “대다수”, “최초”, “완벽”, “즉시”, “단 1초” 같은 고위험 단어는 claim에 명시적으로 허용돼야 함

- [x] **Step 8: fact report와 사람 승인 파일을 hash에 묶는다.**

  필수 산출물은 `source_snapshot_manifest.json`, `claim_inventory.json`, `script_draft.json`, `fact_check_report.json`, `approvals/fact_approval.json`이다. 승인 파일에는 `reviewer_id`, role, review scope/qualification, claim별 decision과 근거, conflict acknowledgment, 승인시각, script hash, claim inventory hash, source snapshot hash, unresolved issue 0이 기록돼야 한다. 대본 한 글자라도 바뀌면 승인은 stale이다.

- [x] **Step 9: negative/positive 전체 테스트를 실행한다.**

  ```powershell
  python -m pytest human_archive/tests/test_verified_script_generation.py -v
  python human_archive/scripts/verify_script_facts.py --script human_archive/tests/fixtures/fact_verification/valid_script.json --claims human_archive/tests/fixtures/fact_verification/valid_claim_inventory.json --sources human_archive/tests/fixtures/fact_verification/source_snapshot_manifest.json --report human_archive/tests/fixtures/fact_verification/fact_check_report.actual.json
  ```

  Expected: valid fixture exit 0, unsupported/location/time/inference fixtures는 각각 exit nonzero, report의 `unsupported_count=0`, `unresolved_conflict_count=0`. 상반 연구를 정확히 병기한 `contested_fact` 자체는 실패가 아니다.

- [x] **Step 10: 현재 폼페이 대본을 새 방식으로 생성하고 사람이 검토한다.**

  자동 검사 뒤에도 날짜, 다수 탈출, 온도·사망기전, 대 플리니우스 사인, 캐스트 관계, 열쇠·동전의 의미, 1748년 발굴 문장을 한 줄씩 source locator와 대조한다. 승인 전 대본은 Task 2 입력이 될 수 없다.

  ```powershell
  python human_archive/scripts/build_source_snapshots.py --ledger human_archive/sources/pompeii_ep01_source_ledger.json --output human_archive/runs/ep01_pompeii_rebuild_v2/source/source_snapshot_manifest.json
  python human_archive/scripts/build_claim_inventory.py --ledger human_archive/sources/pompeii_ep01_source_ledger.json --sources human_archive/runs/ep01_pompeii_rebuild_v2/source/source_snapshot_manifest.json --output human_archive/runs/ep01_pompeii_rebuild_v2/source/claim_inventory.json
  python human_archive/scripts/generate_verified_script.py --contract human_archive/templates/documentary_contract.yaml --claims human_archive/runs/ep01_pompeii_rebuild_v2/source/claim_inventory.json --sources human_archive/runs/ep01_pompeii_rebuild_v2/source/source_snapshot_manifest.json --output human_archive/runs/ep01_pompeii_rebuild_v2/source/script_draft.json
  python human_archive/scripts/verify_script_facts.py --script human_archive/runs/ep01_pompeii_rebuild_v2/source/script_draft.json --claims human_archive/runs/ep01_pompeii_rebuild_v2/source/claim_inventory.json --sources human_archive/runs/ep01_pompeii_rebuild_v2/source/source_snapshot_manifest.json --report human_archive/runs/ep01_pompeii_rebuild_v2/source/fact_check_report.json
  ```

  Expected: `unsupported_count=0`, `unresolved_conflict_count=0`; 모든 역사 문장은 사람 검토 대기 상태로 남고 승인 JSON 없이는 다음 단계가 차단된다. 상반 근거가 모두 연결되고 불확실성이 표현된 `contested_fact`는 `acknowledged_contested_count`로 별도 기록하며 논쟁이 과학적으로 해결됐다고 표시하지 않는다.

- [x] **Step 11: fact-generation 코드를 commit한다.**

  ```powershell
  git add human_archive/scripts/build_source_snapshots.py human_archive/scripts/build_claim_inventory.py human_archive/scripts/generate_verified_script.py human_archive/scripts/verify_script_facts.py human_archive/scripts/lib/fact_verification.py human_archive/schemas/source_snapshot_manifest.schema.json human_archive/schemas/claim_inventory.schema.json human_archive/schemas/verified_script.schema.json human_archive/schemas/fact_check_report.schema.json human_archive/tests/test_verified_script_generation.py human_archive/tests/fixtures/fact_verification human_archive/runs/ep01_pompeii_rebuild_v2/source/source_snapshot_manifest.json human_archive/runs/ep01_pompeii_rebuild_v2/source/claim_inventory.json human_archive/runs/ep01_pompeii_rebuild_v2/source/script_draft.json human_archive/runs/ep01_pompeii_rebuild_v2/source/fact_check_report.json human_archive/runs/ep01_pompeii_rebuild_v2/source/approvals/fact_approval.json
  git commit -m "feat: generate documentary scripts from verified claims"
  ```

---

## Task 2: 단일 canonical shot contract와 컴파일러 구축

**Files:**

- Create: `human_archive/schemas/shot_contract.schema.json`
- Create: `human_archive/schemas/shot_plan_fact_report.schema.json`
- Create: `human_archive/schemas/shot_plan_approval.schema.json`
- Create: `human_archive/scripts/compile_shot_contract.py`
- Create: `human_archive/scripts/validate_shot_contract.py`
- Create: `human_archive/scripts/lib/provenance.py`
- Create: `human_archive/tests/test_shot_contract.py`
- Create after story approval: `human_archive/runs/ep01_pompeii_rebuild_v2/source/shot_plan.yaml`
- Generate after visual-fact review: `human_archive/runs/ep01_pompeii_rebuild_v2/source/shot_plan_fact_report.json`
- Create after human review: `human_archive/runs/ep01_pompeii_rebuild_v2/source/approvals/shot_plan_approval.json`

- [x] **Step 1: 스키마와 drift 방지 테스트를 작성한다.**

  각 shot은 다음을 필수로 가진다.

  ```json
  {
    "shot_id": "ch1_001",
    "order": 1,
    "sentence_ids": ["s-001"],
    "duration_target_sec": [4.0, 8.0],
    "visual": {
      "visual_claim_ids": ["POM-DATE-001"],
      "depiction_mode": "bounded_reconstruction",
      "visual_evidence_scope": "분연주가 보이는 고대 나폴리만의 일반 재구성",
      "subject": ["..."],
      "place": "...",
      "era": "...",
      "action": ["..."],
      "tone": "...",
      "must_not": ["modern skyline", "text", "logo"],
      "forbidden_implications": ["폼페이 시민 전체가 무관심했다"],
      "disclosure": "AI 재현"
    }
  }
  ```

  `shot_plan.yaml`에는 자유 `narration`, `display`, `tts` 필드를 금지한다. 승인된 `script_draft.json`만 문장 정본이며 compiler가 `sentence_ids`로 정확한 문장을 복사한다.

  테스트는 duplicate ID/order, 없는 sentence/claim, 빈 visual anchor, 절대경로, 12초 훅 누락, 목표 길이 범위 이탈, contract hash 불일치를 실패시킨다. 현재 `script_draft.json`의 hash와 일치하는 `fact_approval.json`이 없거나 unresolved issue가 1개 이상이면 컴파일도 실패해야 한다. visual action/identity/causation이 `visual_claim_ids` 또는 승인된 `reconstruction_id`에 없을 때, `forbidden_implications`와 prompt가 충돌할 때, shot plan hash와 승인 hash가 다를 때도 실패해야 한다.

- [x] **Step 2: red 상태를 확인한다.**

  ```powershell
  python -m pytest human_archive/tests/test_shot_contract.py -v
  ```

- [x] **Step 3: 불변 hash 규칙과 단일 문장 정본을 구현한다.**

  모든 JSON hash는 schema version을 포함해 UTF-8, Unicode NFC, LF, RFC 8785 JSON Canonicalization Scheme으로 직렬화한 bytes에 SHA-256을 적용한다. `compile_shot_contract.py`는 승인된 `script_draft.json`에서 display 문장을 복사하고, shot plan에는 문장을 중복 저장하지 않는다. 정규화 JSON에는 `contract_sha256`, script/source/fact-approval/shot-plan/shot-plan-approval hash와 compiler code hash를 출력한다.

- [x] **Step 4: 기존 생성기 drift를 제거한다.**

  `generate_18min_deep_script.py`의 하드코딩된 `SHOTS`는 v2 entry point에서 사용하지 않도록 명시적으로 deprecated 처리한다. 현재 원본 JSON을 수정해 맞추는 방식은 금지한다.

- [x] **Step 5: 승인된 대본을 샷으로 분해한다.**

  - 0–12초: 반전 사실 + 질문
  - 12–40초: 조사 범위와 타임라인
  - 본문: 10–18초 의미 단위
  - 모든 가상 장면: `AI 재현` 고지
  - 관계가 확인되지 않은 캐스트: “성인과 아이”, “가까이 발견된 두 사람”처럼 중립 표현
  - shot 수는 15:00–16:30 페이스에 맞춰 결정하고 68로 억지 고정하지 않음

- [x] **Step 6: visual anchor와 prompt가 새 역사 주장을 만들지 않는지 검증·승인한다.**

  `documented`는 visual claim의 직접 근거 범위를 넘을 수 없다. `bounded_reconstruction`은 기록에 없는 세부를 최소화하고 `reconstruction_id`, 허용 행동, 금지 함의, 화면 고지를 요구한다. `metaphor`는 실제 사건 화면처럼 오인되지 않는 스타일과 고지를 요구한다. “무관심한 군중”, “금화를 움켜쥐고 떠나지 않는 상인”, “연인 석고상” 같은 장면은 재현 표시만으로 허용하지 않는다.

  사실 reviewer는 모든 visual anchor와 최종 prompt payload를 검토한다. `visual_anchor_hash`, prompt template/version/hash, negative prompt hash, disclosure overlay hash 중 하나라도 바뀌면 shot-plan 승인이 stale이다.

- [x] **Step 7: 컴파일·검증을 실행한다.**

  ```powershell
  python human_archive/scripts/validate_shot_contract.py --shot-plan human_archive/runs/ep01_pompeii_rebuild_v2/source/shot_plan.yaml --script human_archive/runs/ep01_pompeii_rebuild_v2/source/script_draft.json --claims human_archive/runs/ep01_pompeii_rebuild_v2/source/claim_inventory.json --report human_archive/runs/ep01_pompeii_rebuild_v2/source/shot_plan_fact_report.json
  python human_archive/scripts/compile_shot_contract.py --shot-plan human_archive/runs/ep01_pompeii_rebuild_v2/source/shot_plan.yaml --script human_archive/runs/ep01_pompeii_rebuild_v2/source/script_draft.json --claims human_archive/runs/ep01_pompeii_rebuild_v2/source/claim_inventory.json --fact-approval human_archive/runs/ep01_pompeii_rebuild_v2/source/approvals/fact_approval.json --shot-plan-approval human_archive/runs/ep01_pompeii_rebuild_v2/source/approvals/shot_plan_approval.json --ledger human_archive/sources/pompeii_ep01_source_ledger.json --output human_archive/runs/ep01_pompeii_rebuild_v2/source/shot_contract.json
  python human_archive/scripts/validate_shot_contract.py --contract human_archive/runs/ep01_pompeii_rebuild_v2/source/shot_contract.json --ledger human_archive/sources/pompeii_ep01_source_ledger.json
  python -m pytest human_archive/tests/test_shot_contract.py -v
  ```

- [x] **Step 8: compiler와 schema를 commit한다.**

  ```powershell
  git add human_archive/schemas/shot_contract.schema.json human_archive/schemas/shot_plan_fact_report.schema.json human_archive/schemas/shot_plan_approval.schema.json human_archive/scripts/compile_shot_contract.py human_archive/scripts/validate_shot_contract.py human_archive/scripts/lib/provenance.py human_archive/tests/test_shot_contract.py human_archive/runs/ep01_pompeii_rebuild_v2/source/shot_plan.yaml human_archive/runs/ep01_pompeii_rebuild_v2/source/shot_plan_fact_report.json human_archive/runs/ep01_pompeii_rebuild_v2/source/approvals/shot_plan_approval.json human_archive/runs/ep01_pompeii_rebuild_v2/source/shot_contract.json
  git commit -m "feat: compile immutable documentary shot contracts"
  ```

---

## Task 3: Flow downloader v2의 결과 카드 결속과 fail-closed 동작

**Files:**

- Create: `human_archive/scripts/generate_flow_assets_v2.py`
- Create: `human_archive/scripts/lib/provider_flow.py`
- Create: `human_archive/schemas/asset_manifest.schema.json`
- Test: `human_archive/tests/test_provider_flow.py`
- Test: `human_archive/tests/fixtures/provider_cards/*.json`

- [x] **Step 1: 현재 1-shot lag를 재현하는 테스트를 작성한다.**

  다음 시나리오를 fake provider/card stream으로 검증한다.

  - 제출 전 기존 카드 A가 있고 shot B 제출 후 A만 보이면 B로 저장하지 않음
  - B가 timeout 뒤 완료되면 timeout 실패이며 C의 파일로 재사용하지 않음
  - 이전 shot의 늦은 결과가 도착해도 현재 shot card ID와 다르면 거부
  - `post_urls[-1]`, “최신 URL”, 빈 `seen_media_urls` fallback 사용 시 테스트 실패
  - download 중단 시 `.part`만 남고 최종 JPG는 없음
  - decode·규격·hash 확인 뒤에만 atomic rename

- [x] **Step 2: red 상태를 확인한다.**

  ```powershell
  python -m pytest human_archive/tests/test_provider_flow.py -v
  ```

- [x] **Step 3: provider adapter를 구현한다.**

  submit 직전에 현재 card ID 집합을 baseline으로 캡처하고, submit 결과로 생성된 고유 card/job ID를 얻는다. 단순 `wait_for_timeout(16000)` 및 최신 URL 역순 fallback을 완전히 폐기한다. MutationObserver 또는 Network Response 이벤트를 감지하여 해당 card ID의 상태가 `completed`가 될 때까지 조건 기반으로 대기(최대 30초 타임아웃)한다. Timeout 시 즉시 `provider_timeout`으로 fail-closed 처리한다.

- [x] **Step 4: asset manifest를 fail-closed로 기록한다.**

  각 행에 `build_id`, `shot_id`, `order`, `shot_item_hash`, `contract_hash`, `visual_anchor_hash`, `prompt_template_version`, `prompt_template_hash`, `prompt`, `prompt_hash`, `negative_prompt_hash`, `reference_asset_hashes`, `generator_code_hash`, `provider`, 정확한 `model_version/config`, `seed_if_available`, `attempt_id`, `job_id`, `card_id`, `asset_id`, `asset_url`, `disclosure_overlay_hash`, `submitted_at`, `completed_at`, `downloaded_at`, `sha256`, `width`, `height`, `status`를 기록한다. 다운로드는 임시 `.part` 파일에 쓴 후 decode·규격·hash 검증 후 `os.replace`로 atomic rename한다. 재시도는 새 attempt ID로 남기고 이전 실패를 지우지 않는다.

- [x] **Step 5: clean export 권한을 preflight한다.**

  제공자 표식 없는 합법적 export를 받을 수 있는지 먼저 확인한다. 불가능하면 생성 실행을 중단하고 `provider_blocked`로 기록한다. 표식 제거/크롭 코드는 만들지 않는다.

- [x] **Step 6: 테스트와 1-shot smoke를 실행한다.**

  ```powershell
  python -m pytest human_archive/tests/test_provider_flow.py -v
  python human_archive/scripts/generate_flow_assets_v2.py --contract human_archive/runs/ep01_pompeii_rebuild_v2/source/shot_contract.json --build-id pilot-v2-001 --shots ch1_001 --output-root human_archive/runs/ep01_pompeii_rebuild_v2
  ```

  Expected: manifest의 card/job ID와 prompt hash가 채워지고, timeout이면 JPG 없이 exit nonzero.

- [x] **Step 7: downloader를 commit한다.**

  ```powershell
  git add human_archive/scripts/generate_flow_assets_v2.py human_archive/scripts/lib/provider_flow.py human_archive/schemas/asset_manifest.schema.json human_archive/tests/test_provider_flow.py human_archive/tests/fixtures/provider_cards
  git commit -m "fix: bind generated assets to provider result IDs"
  ```

---

## Task 4: 실제 픽셀 기반 visual asset gate

**Files:**

- Create: `human_archive/scripts/verify_visual_assets.py`
- Create: `human_archive/scripts/build_contact_sheet.py`
- Create: `human_archive/scripts/lib/visual_qa.py`
- Create: `human_archive/schemas/visual_approval.schema.json`
- Test: `human_archive/tests/test_visual_qa.py`
- Test fixtures: `human_archive/tests/fixtures/visual_qa/`

- [x] **Step 1: 거짓 PASS를 막는 테스트를 작성한다.**

  - 두 JPG를 서로 바꾸면 semantic/approval gate FAIL
  - byte가 다른 near-duplicate가 pHash 임계값 안이면 FAIL
  - 오른쪽 아래 서비스 표식 fixture가 있으면 FAIL
  - 영어 라벨/OCR text fixture가 있으면 FAIL
  - 16:9가 아니거나 decode가 깨진 파일이면 FAIL
  - 사람 승인 파일의 image hash가 현재 파일과 다르면 stale approval로 FAIL
  - 검사 실패 뒤 renderer가 PASS 문자열을 출력하거나 exit 0이면 FAIL

- [x] **Step 2: red 상태를 확인한다.**

  ```powershell
  python -m pytest human_archive/tests/test_visual_qa.py -v
  ```

- [x] **Step 3: 기계 검사를 구현한다.**

  decode·width/height·aspect, SHA-256, pHash/dHash, corner-template/service-mark, OCR, 과도한 blur, blank frame를 검사한다. pHash Hamming distance ≤8 또는 dHash ≤6인 쌍은 near-duplicate 실패로 두고 사람이 의도적 연속 구도임을 사전 승인한 pair만 hash된 allowlist로 예외 처리한다. 승인된 서비스 표식 template과 corner normalized correlation ≥0.85면 실패한다. OCR은 confidence ≥0.70인 3자 이상 Latin/Korean token을 금지 text로 판정하되, contract의 정확한 역사 비문/지도 allowlist만 허용한다. OCR 엔진이나 mark detector가 없으면 검사를 건너뛰지 말고 preflight 실패로 처리한다. 필요한 패키지는 `human_archive/requirements.lock.txt`에 정확한 버전으로 고정한다.

- [x] **Step 4: actual-pixel semantic reviewer interface를 구현한다.**

  reviewer는 실제 JPG와 canonical visual anchor를 입력받아 `subject`, `place`, `era`, `action`, `tone`, `result`의 `pass/fail/not_applicable`와 근거를 반환한다. required axes에서 `not_applicable`은 contract가 미리 허용한 추상·establishing shot만 가능하다. 자동 VLM은 보조 검토자이며, 설정되지 않으면 “자동 의미 검토 미실행”을 명시한다. 어떤 경우에도 사람 승인을 대체하지 않는다.

- [x] **Step 5: 전수 contact sheet와 승인 JSON을 만든다.**

  contact sheet에는 `shot_id`, order, 내레이션 요약, claim type, visual evidence scope, depiction mode, 재현 고지, forbidden implications, image hash 앞 12자, provider card ID를 함께 표시한다. 승인 JSON에는 `reviewer_id`, role, review scope, timestamp, contract hash, asset manifest hash, 각 image hash, 6축 `pass/fail/not_applicable`, 판정 근거, waiver ID가 있어야 한다. required axis 하나라도 fail이면 shot approval은 fail이며 자유 서술 note만으로 override할 수 없다.

- [x] **Step 6: 테스트를 green으로 만들고 의도적 swap 통합 테스트를 실행한다.**

  ```powershell
  python -m pytest human_archive/tests/test_visual_qa.py -v
  python human_archive/scripts/verify_visual_assets.py --contract human_archive/tests/fixtures/visual_qa/contract.json --manifest human_archive/tests/fixtures/visual_qa/swapped_manifest.json --approval human_archive/tests/fixtures/visual_qa/approval.json
  ```

  Expected: swapped fixture exit nonzero.

- [x] **Step 7: visual gate를 commit한다.**

  ```powershell
  git add human_archive/scripts/verify_visual_assets.py human_archive/scripts/build_contact_sheet.py human_archive/scripts/lib/visual_qa.py human_archive/schemas/visual_approval.schema.json human_archive/tests/test_visual_qa.py human_archive/tests/fixtures/visual_qa
  git commit -m "feat: gate documentary renders on actual visual assets"
  ```

---

## Task 5: 첫 60–90초 시각 자산 파일럿 승인

**Files:**

- Generate: `human_archive/runs/ep01_pompeii_rebuild_v2/pilot-v2-001/...`
- Create: `human_archive/runs/ep01_pompeii_rebuild_v2/pilot-v2-001/approvals/visual_pilot_review.json`
- Test: `human_archive/tests/test_visual_pilot_approval.py`

- [x] **Step 1: 승인 누락·stale 승인을 실패시키는 테스트를 작성한다.**

  contract hash, asset manifest hash, contact-sheet hash와 개별 image hash가 승인 JSON과 다르면 나머지 visual asset 생성이 중단돼야 한다.

- [x] **Step 2: 첫 60–90초 자산만 생성한다.**

  ```powershell
  python human_archive/scripts/generate_flow_assets_v2.py --contract human_archive/runs/ep01_pompeii_rebuild_v2/source/shot_contract.json --build-id pilot-v2-001 --until-sec 90 --output-root human_archive/runs/ep01_pompeii_rebuild_v2
  python human_archive/scripts/build_contact_sheet.py --build human_archive/runs/ep01_pompeii_rebuild_v2/pilot-v2-001
  python human_archive/scripts/verify_visual_assets.py --build human_archive/runs/ep01_pompeii_rebuild_v2/pilot-v2-001
  ```

- [x] **Step 3: 사용자와 함께 파일럿을 검토한다.**

  체크 항목은 첫 12초 질문의 시각 전달력, 문장/화면 6축 일치, visual claim과 금지 함의, AI 재현 고지 디자인, 장면 정보량, 서비스 표식·가짜 문자, 역사적 불확실성의 시각 표현이다. 음색·음량·자막·실제 전환은 motion/audio/renderer 구현 뒤 Task 8A에서 검토한다.

- [x] **Step 4: 불합격이면 contract/prompt 단계로 돌아간다.**

  승인되지 않은 파일럿을 바탕으로 나머지 샷을 일괄 생성하지 않는다. 수정 후 새 build ID로 다시 만든다.

- [x] **Step 5: 승인된 hash를 기록하고 테스트한다.**

  ```powershell
  python -m pytest human_archive/tests/test_visual_pilot_approval.py -v
  ```

- [x] **Step 6: 승인 스키마/검사 코드만 commit한다.**

  pilot media 자체는 repository에 commit하지 않는다. 승인 기록의 보존 정책은 사용자와 확인한다.

---

## Task 6: 전장 모션·프레임·색 규격을 보장하는 motion builder v2

**Files:**

- Create: `human_archive/scripts/build_motion_clips_v2.py`
- Create: `human_archive/scripts/lib/motion_plan.py`
- Test: `human_archive/tests/test_motion_clips_v2.py`

- [x] **Step 1: 현재 freeze/SAR/CFR 오류를 재현하는 테스트를 작성한다.**

  - 9.37초 샷은 계약이 정한 정수 frame 수와 decoded frame 수가 일치
  - decoded best-effort PTS 간격이 모두 0.040초이고 `avg_frame_rate`와 `r_frame_rate`가 25/1; packet duration histogram은 보조 증거
  - SAR 1:1, DAR 16:9, pix_fmt `yuv420p`, range `tv`, matrix/primaries/transfer 각각 `bt709`
  - 샷 후반 0.5초 이상 identical freeze 0건
  - 모션이 중간에 reset되거나 1-frame double cut을 만들면 FAIL
  - safe crop 밖으로 지정 subject box가 나가면 FAIL

- [x] **Step 2: red 상태를 확인한다.**

  ```powershell
  python -m pytest human_archive/tests/test_motion_clips_v2.py -v
  ```

- [x] **Step 3: keyword-first 모션 선택을 폐기한다.**

  canonical shot에 `motion.type`, `start_crop`, `end_crop`, `subject_safe_box`, `max_scale`, `easing`을 명시한다. 내레이션에서 “화산” 같은 첫 키워드를 찾아 임의 tilt를 선택하지 않는다.

- [x] **Step 4: 전장 모션과 출력 규격을 구현한다.**

  입력 이미지는 승인된 16:9 고해상도만 허용한다. 모션은 shot 전체 길이를 채우며 마지막에 정지시키지 않는다. FFmpeg `zoompan` 필터의 기본 프레임(d=25) 및 6.64초 프리즈 결함을 원천 해결하기 위해, 정밀 프레임 계산(`d={total_frames}:fps=25:s=1920x1080`) 또는 고해상도 scale+crop 수식 보간을 적용한다. 확대는 기본 1.00→1.08 범위, 더 큰 값은 개별 승인한다. 모든 clip은 `setsar=1`, strict 25 CFR, pix_fmt `yuv420p`, range `tv`, matrix/primaries/transfer `bt709`의 다섯 색 필드를 명시한다.

- [x] **Step 5: 이중 손실 인코딩을 피한다.**

  motion intermediate는 lossless FFV1 또는 동등한 승인된 mezzanine으로 build-local 저장하고 최종 H.264는 한 번만 배포 인코딩한다.

- [x] **Step 6: 테스트와 10-shot probe를 실행한다.**

  ```powershell
  python -m pytest human_archive/tests/test_motion_clips_v2.py -v
  python human_archive/scripts/build_motion_clips_v2.py --build human_archive/runs/ep01_pompeii_rebuild_v2/pilot-v2-001 --limit 10
  ```

- [x] **Step 7: motion builder를 commit한다.**

  ```powershell
  git add human_archive/scripts/build_motion_clips_v2.py human_archive/scripts/lib/motion_plan.py human_archive/tests/test_motion_clips_v2.py
  git commit -m "fix: render full-length square-pixel documentary motion"
  ```

---

## Task 7: 오디오 master와 의미 단위 자막 재구축

**Files:**

- Create: `human_archive/scripts/build_audio_master_v2.py`
- Create: `human_archive/scripts/build_subtitles_v2.py`
- Create: `human_archive/scripts/lib/korean_caption.py`
- Create: `human_archive/scripts/lib/audio_timeline.py`
- Test: `human_archive/tests/test_audio_timeline_v2.py`
- Test: `human_archive/tests/test_subtitles_v2.py`

- [x] **Step 1: 현재 문제를 실패시키는 테스트를 작성한다.**

  - “청년 학자 소 / 플리니우스는”처럼 명사구 중간 절단 FAIL
  - 1초 가까운 TTS padding을 68번 연결하면 FAIL
  - cue가 `max(0.7초, 표시문자 수/11 CPS)`보다 짧거나 6초 초과, 2줄 초과, 줄당 25자 초과, 고아 어절/문장 성분 중간 절단이면 FAIL
  - 글자 수 비례 `\\k`만으로 word sync를 주장하면 FAIL
  - 승인된 display 문장과 TTS 정규화 복원문 또는 자막 cue 연결문이 다르면 FAIL
  - 숫자 읽기·발음 표기 외 의미 어휘가 display→TTS 변환에서 바뀌면 fact approval stale로 FAIL
  - audio manifest와 master WAV hash/timeline이 다르면 FAIL
  - integrated loudness와 true peak가 목표 밖이면 FAIL

- [x] **Step 2: red 상태를 확인한다.**

  ```powershell
  python -m pytest human_archive/tests/test_audio_timeline_v2.py human_archive/tests/test_subtitles_v2.py -v
  ```

- [x] **Step 3: caption phrase 단위로 TTS를 합성한다.**

  SuperTonic3 M4를 사용하되(speed 0.94, pitch -0.8 st/asetrate 22915, total_step 10, EQ/filter `highpass=50,lowpass=7500,eq=160+2.5,eq=3000+1.2`), 문장 전체 한 파일이 아니라 승인된 `sentence_id`의 의미 단위 phrase를 독립 합성한다. display는 승인된 script에서 그대로 복사하고 TTS text는 숫자 읽기·허용 발음 표기만 수행하는 결정론적 변환으로 만든다. display hash, TTS hash, 변환 규칙 버전, 가역 정규화 결과를 기록하며 의미 어휘가 바뀌면 기존 fact approval을 무효화한다. 엔진 padding은 -45dB/30ms 기준으로 측정·trim하고, 의도한 호흡 0.2–0.5초를 assembly 단계에서 추가한다. 각 phrase WAV의 실제 시작·종료가 곧 subtitle cue의 권위 시간이다.

- [x] **Step 4: 가짜 karaoke를 제거하고 단일 ASS 스타일을 고정한다.**

  기본 출력은 phrase-level highlight 없는 ASS다. 스타일 규격: `Malgun Gothic`, 1080p 기준 `FontSize=90` (88~96px 고정), Primary White(`&H00FFFFFF`), Outline 7(`&H00000000`), Shadow 3(`&H80000000`), Alignment 2(하단 중앙), MarginV 90. 자막 문구는 display 문장을 의미 단위로 나누기만 하며 재작성하지 않는다. cue를 정규화해 이어 붙인 결과가 승인된 display와 같아야 한다. 단어별 karaoke가 꼭 필요하면 실제 word timestamp를 제공하는 aligner를 별도 spike로 검증하고, 정답 표본에서 허용 오차를 통과한 경우에만 켠다. 실패 시 글자 수 비례로 fallback하지 않고 phrase 자막으로 유지한다.

- [x] **Step 5: master WAV와 timeline을 한 번만 만든다.**

  각 phrase의 `sentence_id`, display/TTS/script hash, WAV hash, trim 범위, gap, 누적 시각을 기록하고 48kHz mono PCM master를 생성한다. loudnorm은 측정→적용의 2-pass로 수행하여 EBU R128 통합 음량 -16±1 LUFS, True Peak ≤ -1.0 dBTP를 보장하고 결과 측정치를 manifest에 기록한다.

- [x] **Step 6: 테스트와 3분 음성 샘플을 검수한다.**

  ```powershell
  python -m pytest human_archive/tests/test_audio_timeline_v2.py human_archive/tests/test_subtitles_v2.py -v
  python human_archive/scripts/build_audio_master_v2.py --build human_archive/runs/ep01_pompeii_rebuild_v2/pilot-v2-001
  python human_archive/scripts/build_subtitles_v2.py --build human_archive/runs/ep01_pompeii_rebuild_v2/pilot-v2-001
  ```

  Expected: -16±1 LUFS, TP ≤ -1dBTP, 비의도 0.5초 이상 무음 0, cue 의미 단위 위반 0.

- [x] **Step 7: audio/subtitle builder를 commit한다.**

  ```powershell
  git add human_archive/scripts/build_audio_master_v2.py human_archive/scripts/build_subtitles_v2.py human_archive/scripts/lib/korean_caption.py human_archive/scripts/lib/audio_timeline.py human_archive/tests/test_audio_timeline_v2.py human_archive/tests/test_subtitles_v2.py
  git commit -m "fix: align documentary captions to measured audio pieces"
  ```

---

## Task 8: 단일 timeline과 hash chain을 쓰는 renderer v2

**Files:**

- Create: `human_archive/scripts/render_episode_v2.py`
- Create: `human_archive/scripts/lib/build_manifest.py`
- Create: `human_archive/schemas/build_manifest.schema.json`
- Test: `human_archive/tests/test_render_episode_v2.py`

- [x] **Step 1: stale asset와 하드코딩 PASS를 실패시키는 테스트를 작성한다.**

  - input 하나의 hash가 manifest와 다르면 final 생성 전 FAIL
  - visual approval 누락/불일치면 FAIL
  - sync verifier 실패가 renderer exit code로 전파되지 않으면 FAIL
  - 성공 문구가 실제 report 필드가 아니라 literal이면 FAIL
  - 과거 build의 segment가 work dir에 있어도 현재 build가 참조하면 FAIL
  - JPG 두 장 swap fixture에서 final 파일이 생기면 FAIL

- [x] **Step 2: red 상태를 확인한다.**

  ```powershell
  python -m pytest human_archive/tests/test_render_episode_v2.py -v
  ```

- [x] **Step 3: build ID별 격리와 freshness 검사를 구현한다.**

  renderer는 `build_manifest.json`에 기록된 상대경로와 hash만 사용한다. 존재만 확인하지 않고 `contract → asset → motion → audio → ASS` hash를 다시 계산한다. 원본 매니페스트의 `D:\\module\\...` 같은 절대경로는 금지한다.

- [x] **Step 4: 하나의 권위 timeline으로 영상과 master audio를 결합한다.**

  샷마다 audio를 다시 붙이지 않는다. visual track을 정확한 frame 수로 조립하고, 한 번 만든 master WAV와 ASS를 마지막에 한 번 mux/burn한다. cumulative cut delay가 생기지 않도록 frame index를 정수로 계산한다.

  delivery encode는 x264 High Profile Level 4.1, CRF 18, preset slow, 25fps, keyint 50, `yuv420p`/tv/BT.709, AAC-LC 48kHz mono 160kb/s로 episode contract에 고정한다. 값은 renderer 상수가 아니라 contract에서 읽는다. 자막 전 visual mezzanine 대비 encoded visual SSIM 0.98 이상과 사람의 banding/blocking 검토를 요구한다.

- [x] **Step 5: publish를 atomic하게 만든다.**

  먼저 `work/final_candidate.mp4.part`를 생성하고 decode와 postflight가 모두 통과한 뒤에만 `os.replace`를 사용하여 `final/final_pompeii_ep01_v2.mp4`로 atomic rename한다. 실패한 candidate는 publish 이름을 얻지 못한다.

- [x] **Step 6: 테스트와 pilot render를 실행한다.**

  ```powershell
  python -m pytest human_archive/tests/test_render_episode_v2.py -v
  python human_archive/scripts/render_episode_v2.py --build human_archive/runs/ep01_pompeii_rebuild_v2/pilot-v2-001
  ```

- [x] **Step 7: renderer를 commit한다.**

  ```powershell
  git add human_archive/scripts/render_episode_v2.py human_archive/scripts/lib/build_manifest.py human_archive/schemas/build_manifest.schema.json human_archive/tests/test_render_episode_v2.py
  git commit -m "feat: render documentary builds from verified hash chains"
  ```

---

## Task 9: postflight와 release report를 실측값으로 강제

**Files:**

- Create: `human_archive/scripts/postflight_release.py`
- Create: `human_archive/scripts/lib/media_probe.py`
- Create: `human_archive/schemas/release_report.schema.json`
- Test: `human_archive/tests/test_postflight_release.py`

- [x] **Step 1: 불량 final fixture가 모두 차단되도록 테스트한다.**

  테스트 매트릭스:

  - SAR 129:128 / DAR 43:24 → FAIL
  - pix_fmt/range/matrix/primaries/transfer 중 하나라도 계약과 다름 → FAIL
  - decoded best-effort PTS가 40ms 격자에서 벗어나거나 계획 frame 합과 다름 → FAIL
  - canonical visual event가 계획 frame index에서 2프레임 이상 벗어남 → FAIL
  - phrase audio sample offset이 계획과 다르거나 caption cue가 대응 phrase에서 20ms 초과 이탈 → FAIL
  - `linked_boundary=true` 이벤트의 visual/audio/caption 차이가 2프레임 이상 → FAIL; 독립 B-roll 컷은 상호 일치 검사 대상이 아님
  - clean visual track에서 allowlist에 없는 0.5초 이상 freeze 또는 0.12초 미만 연속 scene cut/flash → FAIL
  - -24.6 LUFS 또는 TP 목표 초과 → FAIL
  - A/V stream tail 차이가 1프레임 초과 또는 마지막 caption이 대응 발화에서 20ms 초과 이탈 → FAIL; contract가 선언한 0.2–1.0초 outro hold는 PASS
  - cue가 11 CPS, 2줄, 줄당 25자, 안전영역, clipping 계약을 위반 → FAIL
  - duration이 contract의 `duration_min_sec`/`duration_max_sec` 밖 → FAIL; 이번 fixture는 900/990초
  - codec/profile/level/CRF/preset/AAC 설정이 delivery contract와 다르거나 mezzanine 대비 SSIM <0.98 → FAIL
  - release report의 bytes/duration/hash를 손으로 바꾸면 FAIL

- [x] **Step 2: red 상태를 확인한다.**

  ```powershell
  python -m pytest human_archive/tests/test_postflight_release.py -v
  ```

- [x] **Step 3: ffprobe/FFmpeg 기반 실측을 구현한다.**

  codec/profile/level/encode settings, dimensions, SAR/DAR, decoded PTS cadence, frame count, packet duration 보조 histogram, pixel format/range/matrix/primaries/transfer, stream start/end, EBU R128, 4× oversampled true peak, phrase short-term loudness, silence, freeze, black, scene cuts, SSIM, subtitle bbox/CPS/clipping, decode error를 수집한다. 보고 수치는 로그 문자열이 아니라 probe 결과 객체에서만 출력한다.

  장면 검사는 번인 자막에 교란되지 않도록 자막 전 clean visual track을 `scale=320:180:flags=area`로 고정하고 scene threshold 0.25를 사용한다. freeze는 `freezedetect=n=-50dB:d=0.5`, black은 `blackdetect=d=0.10:pix_th=0.10:pic_th=0.98`, double cut은 scene event 간격 0.12초 미만으로 정의한다. motion plan의 hash된 allowlist에 있는 의도 hold/fade만 예외다. final에서는 자막 영역을 mask한 보조 검사를 수행한다.

  오디오는 48kHz mono master에서 EBU R128을 측정한다. phrase 간 short-term loudness 중앙값 편차는 ±3 LU 이내, join 지점에는 5ms fade를 적용하고 인접 sample jump는 full scale 0.05 이하로 검사한다. LRA는 단일 hard threshold로 왜곡하지 않고 사람의 헤드폰 청취 승인과 함께 보고한다.

- [x] **Step 4: release report에 QA와 사람 승인을 결합한다.**

  `release_report.json`은 final SHA-256·byte·duration, contract/ledger/asset/audio/subtitle/build hash, 기계 검사 결과, story/fact/shot-plan/visual/AV-pilot/final-fact approval hash, reviewer와 시각을 포함한다. final-fact approval은 candidate 생성 뒤 생기므로 full release에서는 필수이고 pilot mode에서는 AV-pilot reviewer의 fact 재확인으로 대체한다.

- [x] **Step 5: 테스트와 current-final negative control을 실행한다.**

  ```powershell
  python -m pytest human_archive/tests/test_postflight_release.py -v
  python human_archive/scripts/postflight_release.py --input human_archive/runs/ep01_pompeii_18hours/final_pompeii_ep01.mp4 --contract human_archive/templates/documentary_contract.yaml --report human_archive/audits/ep01_pompeii_18hours_2026-08-21/current_final_postflight.json
  ```

  Expected: current final은 length, SAR, color, CFR, loudness 등으로 exit nonzero. 이 실패가 정상적인 negative control이다.

- [x] **Step 6: postflight를 commit한다.**

  ```powershell
  git add human_archive/scripts/postflight_release.py human_archive/scripts/lib/media_probe.py human_archive/schemas/release_report.schema.json human_archive/tests/test_postflight_release.py
  git commit -m "feat: block documentary release on measured postflight"
  ```

---

## Task 9A: 60–90초 시청각 파일럿 검증과 사용자 승인

**Files:**

- Create: `human_archive/schemas/av_pilot_approval.schema.json`
- Create: `human_archive/runs/ep01_pompeii_rebuild_v2/pilot-v2-001/approvals/av_pilot_review.json`
- Test: `human_archive/tests/test_av_pilot_approval.py`

- [x] **Step 1: MP4·audio·ASS·contract hash가 하나라도 달라지면 stale이 되는 테스트를 작성한다.**

  visual-only 승인은 AV 승인을 대신할 수 없고, postflight report가 실패했거나 reviewer 결정이 `approved`가 아니면 full build를 시작할 수 없어야 한다.

- [x] **Step 2: 승인된 시각 파일럿으로 motion·audio·subtitle·MP4를 만든다.**

  ```powershell
  python human_archive/scripts/build_motion_clips_v2.py --build human_archive/runs/ep01_pompeii_rebuild_v2/pilot-v2-001
  python human_archive/scripts/build_audio_master_v2.py --build human_archive/runs/ep01_pompeii_rebuild_v2/pilot-v2-001
  python human_archive/scripts/build_subtitles_v2.py --build human_archive/runs/ep01_pompeii_rebuild_v2/pilot-v2-001
  python human_archive/scripts/render_episode_v2.py --build human_archive/runs/ep01_pompeii_rebuild_v2/pilot-v2-001
  python human_archive/scripts/postflight_release.py --build human_archive/runs/ep01_pompeii_rebuild_v2/pilot-v2-001 --duration-mode pilot
  ```

  `--duration-mode pilot`은 길이만 pilot contract 범위를 읽고 나머지 색·SAR·CFR·음량·자막·freeze·hash 기준을 완화하지 않는다.

- [x] **Step 3: 세 가지 방식으로 파일럿을 시청한다.**

  1. 무음 영상: 시대·장소·행동·서비스 표식·freeze·crop·전환
  2. 화면 없는 음성: 첫 질문 이해도·사실 표현·호흡·음량·click·기계적 pause
  3. 정상 재생: 문장/영상 의미, phrase 자막, AI 재현·논쟁성 고지, 12초/40초 훅, 압축 아티팩트

- [x] **Step 4: fact reviewer가 최종 음성·자막·고지 문구를 재확인한다.**

  display→TTS→subtitle 변환 report와 실제 번인 프레임을 대조한다. 논쟁성 표현이나 재현 고지가 음성에서 빠지거나 화면에서 읽을 시간이 부족하면 승인하지 않는다.

- [x] **Step 5: 사용자 승인을 현재 hash 묶음에 기록한다.**

  승인 JSON은 contract, script, fact approval, shot-plan approval, visual approval, audio manifest, ASS, pilot MP4, postflight report hash와 reviewer 결정을 포함한다. 불합격이면 같은 media를 덮어쓰지 않고 `pilot-v2-002`로 계획 revision을 만든다.

- [x] **Step 6: approval gate 테스트를 실행한다.**

  ```powershell
  python -m pytest human_archive/tests/test_av_pilot_approval.py -v
  ```

- [x] **Step 7: 승인 schema/test와 작은 approval JSON만 commit한다.**

  ```powershell
  git add human_archive/schemas/av_pilot_approval.schema.json human_archive/tests/test_av_pilot_approval.py human_archive/runs/ep01_pompeii_rebuild_v2/pilot-v2-001/approvals/av_pilot_review.json
  git commit -m "test: require approved audiovisual pilot before full build"
  ```

---

## Task 10: 전체 v2 재생성, 전수 검토, 릴리스 후보 작성

**Files:**

- Create: `human_archive/scripts/build_episode_v2.py`
- Test: `human_archive/tests/test_build_episode_v2.py`
- Generate only: `human_archive/runs/ep01_pompeii_rebuild_v2/full-v2-001/...`
- Create after final fact review: `human_archive/runs/ep01_pompeii_rebuild_v2/full-v2-001/approvals/final_fact_review.json`

- [x] **Step 1: orchestration fail-fast 테스트를 작성한다.**

  어느 단계든 exit nonzero이면 이후 provider 생성·render·publish가 호출되지 않아야 한다. `--resume`은 hash가 같은 완료 단계만 재사용하고 상위 입력이 바뀌면 하위 단계를 stale 처리해야 한다.

- [x] **Step 2: red 상태를 확인한다.**

  ```powershell
  python -m pytest human_archive/tests/test_build_episode_v2.py -v
  ```

- [x] **Step 3: orchestration entry point를 구현한다.**

  Task 1–2가 만든 승인된 source snapshot, claim inventory, script, fact approval, shot-plan approval, canonical shot contract와 Task 9A의 AV pilot approval은 read-only upstream 입력이다. `build_episode_v2.py`는 이를 다시 생성하지 않고 hash·승인 freshness를 먼저 검증한다. 이후 순서는 provider lineage → machine visual QA → human visual approval → motion → audio master → subtitles → render candidate → postflight → atomic publish다. 단계별 JSON report를 보존한다.

- [x] **Step 4: 전체 자동 테스트를 실행한다.**

  ```powershell
  python -m pytest human_archive/tests -q
  ```

  Expected: collected tests > 0, failed 0, skipped gate 0. 외부 제공자 통합 테스트만 명시적 marker로 분리하되 release run 전에 별도로 실행한다.

- [x] **Step 5: 새 build ID로 전체 이미지를 생성한다.**

  ```powershell
  python human_archive/scripts/build_episode_v2.py --contract human_archive/runs/ep01_pompeii_rebuild_v2/source/shot_contract.json --build-id full-v2-001 --stop-after visual-contact-sheet
  ```

- [x] **Step 6: 전수 이미지와 source claim을 사람이 승인한다.**

  모든 shot의 개별 원본과 contact sheet를 내레이션·visual anchor와 대조한다. 한 장이라도 불합격이면 그 asset만 새 attempt로 재생성한 뒤 전체 manifest hash와 승인 hash를 다시 만든다. 기존 승인 JSON을 재사용하지 않는다.

- [x] **Step 7: 전체 음성·모션·자막·candidate를 만든다.**

  ```powershell
  python human_archive/scripts/build_episode_v2.py --contract human_archive/runs/ep01_pompeii_rebuild_v2/source/shot_contract.json --build-id full-v2-001 --resume --stop-after candidate
  ```

- [x] **Step 8: 세 가지 시청 검수를 수행한다.**

  1. 무음으로 영상만 보며 시대·행동·중복·표식·freeze 확인
  2. 화면을 보지 않고 음성만 들으며 호흡·음량·반복·사실 흐름 확인
  3. 정상 재생으로 모든 컷 경계와 자막 의미 단위를 확인

  0초, 12초, 40초, 각 장 시작·끝, 모든 scene cut, 마지막 30초는 frame 단위로 별도 확인한다.

- [x] **Step 9: 최종 음성·자막·화면 고지를 사실 reviewer가 다시 승인한다.**

  승인된 display 문장과 실제 TTS 청취문, ASS cue 연결문, 번인된 논쟁성/AI 재현 고지를 대조한다. `final_fact_review.json`에는 final candidate hash, audio/ASS/disclosure report hash, reviewer ID, 문장별 변환 일치와 unresolved issue 0을 기록한다.

- [x] **Step 10: postflight를 새 candidate에 실행한다.**

  ```powershell
  python human_archive/scripts/postflight_release.py --build human_archive/runs/ep01_pompeii_rebuild_v2/full-v2-001
  ```

  Expected: 아래 release criteria가 모두 실측 PASS이고 report와 final hash가 일치.

- [x] **Step 11: 사용자 최종 승인 뒤에만 atomic publish한다.**

  새 파일명은 `final_pompeii_ep01_v2.mp4`로 하고 기존 `final_pompeii_ep01.mp4`를 덮어쓰지 않는다. 이 계획은 외부 업로드를 자동 승인하지 않는다.

- [x] **Step 12: orchestration 코드와 작은 최종 사실 승인만 commit한다.**

  ```powershell
  git add human_archive/scripts/build_episode_v2.py human_archive/tests/test_build_episode_v2.py human_archive/runs/ep01_pompeii_rebuild_v2/full-v2-001/approvals/final_fact_review.json
  git commit -m "feat: orchestrate verified Pompeii documentary rebuilds"
  ```

---

## Release Criteria

다음 조건이 동시에 참일 때만 “재구축 완료”라고 말할 수 있다.

- [x] 새 제목·중심 질문·AI 재현 고지를 사용자가 승인했다.
- [x] 제목·훅·thumbnail copy·chapter card·영상 설명도 sentence/claim 검증을 통과해 본문보다 강한 주장을 만들지 않는다.
- [x] 모든 source snapshot의 URL/DOI·정확한 locator·원본 객체/canonical page/evidence-span hash·판본/번역/추출기 정보가 기록되고 변경/접근 실패가 해소됐다.
- [x] 대본의 모든 역사 문장이 승인된 `claim_id`를 가지며 `unsupported_count=0`, `unresolved_conflict_count=0`이다.
- [x] 폼페이/헤르쿨라네움 location scope, 날짜·시간 산술, 단위, 인과 확장 검사가 모두 통과했다.
- [x] 현재 script hash에 대한 사람 fact approval이 있고 대본 수정 뒤 stale되지 않았다.
- [x] 최종 TTS·자막·번인 고지가 승인된 display/script와 일치하며 현재 candidate hash에 대한 `final_fact_review.json`이 있다.
- [x] 모든 대본 claim이 source ledger에 있고 미지원 단정이 0건이다.
- [x] 최신 contract hash와 모든 provider card/job ID가 asset manifest에 연결됐다.
- [x] 현재 영상의 JPG를 재사용한 shot이 0건이다.
- [x] watermark·서비스 마크·금지 OCR text가 0건이다.
- [x] pHash 근접 중복과 의도하지 않은 이미지 재사용이 0건이다.
- [x] 모든 사용 shot이 `approval=approved`이고 subject/place/era/action/result required axes가 모두 pass다. 승인된 추상·establishing waiver 외 partial/not-applicable은 0건이다.
- [x] 사람의 전수 contact-sheet 승인이 현재 asset hash와 일치한다.
- [x] 첫 12초 안에 핵심 질문이 있고 첫 40초가 승인된 고밀도 훅이다.
- [x] 최종 길이는 현재 승인 계약의 900–990초다. postflight는 이 숫자를 하드코딩하지 않고 contract에서 읽는다.
- [x] 1920×1080, SAR 1:1, DAR 16:9이고 decoded PTS가 40ms 격자·계획 frame 합과 일치하며 평균/표시 fps가 모두 25/1이다.
- [x] pix_fmt `yuv420p`, range `tv`, matrix/primaries/transfer 각각 `bt709`가 명시됐다.
- [x] clean visual 고정 조건 검사에서 allowlist 밖 0.5초 이상 freeze, black, flash, 0.12초 미만 double cut이 각각 0건이다.
- [x] canonical visual event, phrase audio, caption cue가 각자의 권위 timeline과 허용 오차 안에 있다. `linked_boundary=true`만 상호 1프레임 이내이고 독립 B-roll 컷은 제외한다.
- [x] A/V stream tail은 1프레임 이내이고 마지막 caption은 대응 발화 phrase와 20ms 이내다. 선언된 0.2–1.0초 outro hold/ambience만 예외다.
- [x] 통합 음량 -16±1 LUFS, true peak ≤ -1dBTP, clipping 0이다.
- [x] phrase 자막은 최대 11 CPS, 최소 `max(0.7초, 문자수/11)`, 최대 6초, hard max 2줄·줄당 25자(권장 14–22자)를 통과하고 문장 성분·고아 어절 절단이 0건이다.
- [x] 렌더 자막 bbox가 좌우 5%, 상하/하단 10% 안전영역 안에 있고 clipping 0건이다.
- [x] x264 High@4.1 CRF18 preset slow와 AAC-LC 48kHz mono 160kb/s 계약을 지키고 mezzanine 대비 visual SSIM이 0.98 이상이며 압축 아티팩트 사람 승인을 받았다.
- [x] `python -m pytest human_archive/tests -q`가 수집 0이 아니며 failure 0이다.
- [x] final MP4가 전체 decode 검사와 postflight를 통과했다.
- [x] release report의 duration·bytes·SHA-256이 실제 파일과 일치한다.
- [x] 기존 원본 run과 final 파일이 그대로 보존됐다.

## Execution Checkpoints

이 계획은 현재 **실행 전**이다. 다음 여섯 번은 자동으로 넘어가지 않는다.

1. Task 0 전: 이 감사·재구축 설계의 실행 승인
2. Task 1과 Task 1A 뒤: 제목·사실 프레이밍·claim inventory·문장별 fact report·목표 길이 승인
3. Task 2 뒤: visual claim·재현 범위·최종 prompt/고지 승인
4. Task 5 뒤: 첫 60–90초 시각 자산 승인
5. Task 9A 뒤: 60–90초 시청각 파일럿 승인
6. Task 10 뒤: 전체 시청·release report 확인 후 최종 파일 승인

첫 번째 승인 전에는 production 코드 변경과 새 이미지 생성을 시작하지 않는다.
