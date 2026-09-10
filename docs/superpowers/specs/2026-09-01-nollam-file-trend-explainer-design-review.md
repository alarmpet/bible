# 리뷰: 놀람파일 트렌드 해설 프로필 설계

- 작성일: 2026-09-01
- 대상 문서: `docs/superpowers/specs/2026-09-01-nollam-file-trend-explainer-design.md`
- 문서 상태: 설계 검토 요청 (교차 검토 반영본)
- 대조 범위: `human_archive/` 코드·스키마·테스트, `CLAUDE.md` / `human_archive/README.md` 공식 워크플로우, `bible_healing` 음성 정본, 기존 쉽선비·HA002 설계/계획, `.agents/skills` 다큐 스킬, 인용된 플랫폼 API 문서

---

## 1. 총평

대상 문서는 **브랜드·시청자 약속·출처 역할 분리**가 분명하다. `DISCOVERY_ONLY`와 사실 증거의 분리, `source_state`와 claim 상태의 분리, 스크레이퍼 fail-closed, 기본 프로필 미변경, `verified_script_v3` 이름 재사용 금지, 역사 topic 스키마 비일반화는 현재 코드베이스와 맞춰 보면 올바른 선택이다. §4.1의 현황 감사도 코드와 일치한다.

다만 이 문서를 **그대로 구현 완료 기준**으로 쓰면 세 층이 충돌한다.

| 층 | 내용 | 판정 |
|---|---|---|
| A. 제품·편집 계약 | 놀람파일 약속, 문장 상태, 제목 금지, 고위험 게이트 | 채택 가능. 내부 모순만 정리하면 된다. |
| B. 시스템 감사 | 프로필 로더 미연결, `doodle_docu_12m` 누락, forbidden 테스트 불일치 | 사실이다. 다만 Phase 0을 놀람파일과 같은 변경 집합에 넣으면 쉽선비가 깨진다. |
| C. 구현 범위·워크플로우 | 4포맷, 실시간 수집, 13개 신규 스키마, 기존 CLI 일반화, 9:16 숏폼 | **현재 파이프와 맞지 않는다.** v1을 잘라야 한다. |

**한 줄 판정:** 편집 설계는 채택, 구현 설계는 조건부 채택. 구현 전에 (1) v1 포맷·신선도·수집 범위를 축소하고, (2) 쉽선비 계약 복구와 놀람파일 DAG를 분리하며, (3) 아래 모순을 문서에서 해소한 뒤 규범으로 승격할 것을 권한다.

---

## 2. 코드베이스·워크플로우 대조

### 2.1 설계 §4.1 감사 — 검증 결과

| 설계 주장 | 실제 | 판정 |
|---|---|---|
| 채널 프로필은 `doodle_seonbi_v1`, `human_archive_cinematic_v1`만 존재 | `human_archive/config/channel_profiles.yaml:3-32` | 맞음 |
| `channel_profile.schema.json`이 중첩 필드를 엄격히 검증하지 않음 | 스키마는 `schema_version`(const 1), `default_profile_id`, `profiles`만 요구. `additionalProperties` 제한 없음. `schema_validation.py`도 이 스키마를 로드하지 않음 | 맞음 |
| `channel_profiles.py`가 production에 연결되지 않음 | `load_channel_profile` 호출은 `tests/test_channel_profiles.py`뿐. `resolve_delivery_profile` 호출자 0 | 맞음 |
| 대본·샷 계약이 역사/쉽선비에 결합 | `verified_script_v2.schema.json` persona enum `ship_seonbi\|standard`. `generate_verified_script.py:62` CLI choices 동일, 기본 정책 `seonbi_narration_policy.yaml`. `compile_shot_contract.py:61`은 persona-report가 있으면 non-seonbi를 거부 | 맞음 |
| topic/source ledger가 최신성·소셜을 표현하지 못함 | `topics.schema.json` theme이 역사 enum, 상태 `AVAILABLE\|RESERVED\|USED\|ARCHIVED`. `source_ledger_v2.schema.json` source_type이 학술/공식 기록만 | 맞음 |
| `delivery_profile` vs `delivery_profile_id` 불일치 | YAML은 `delivery_profile`. 2026-08-27 계획은 `delivery_profile_id` | 맞음 |
| `doodle_docu_12m` 누락 | `delivery_profiles.yaml`은 `quick_3m`, `standard_docu`, `pilot`만 | 맞음 |
| forbidden 12개 vs 테스트 7개 | YAML 12개. 테스트는 `realistic_face`에서 끝. **현재 실패 중** (`test_channel_profiles.py::test_doodle_is_default_and_cinematic_is_selectable`) | 맞음 |

추가로 설계가 **적지 않은** 현재 결함:

- `channel_profiles.yaml:10` host_ratio `0.15–0.25` vs `visual_pacing_profiles.yaml` / `CLAUDE.md` 8–12%. HA002 계획도 이 충돌을 이미 적었다.
- 실제 출고 경로(EP02 v6)는 `compile_shot_contract.py`를 쓰지 않는다. `CLAUDE.md` 정본은 TTS-first `build_sentence_audio_master.py` → `plan_narration_shots.py` → Flow → motion → 자막 → `render_episode_v2.py`다.
- `artifact_lineage.py`는 v4 샘플 헬퍼이며 `profile_bundle_sha256`이 없다. production DAG에 연결되어 있지 않다.

### 2.2 실제 제작 워크플로우

공식 정본은 세 갈래다. 설계 §19는 이 차이를 거의 반영하지 않는다.

```text
[라이브 HA v5/v6 — CLAUDE.md / README 후반]
승인 대본 → SuperTonic3 문장 TTS → 실측 샷 타이밍
  → visual brief → Flow 요청 → 의미 재사용 승인
  → 파일럿 → 전체 이미지 QA·사람 승인
  → 25fps 모션 → 문장 자막 → 렌더 → postflight

[레거시 README 전반]
Pompeii ledger → generate_verified_script.py
  → verify_script_facts → validate_seonbi_persona
  → compile_shot_contract → postflight → release_episode

[설계 §19 놀람파일]
신호 수집 → cluster → score → research packet → outline
  → trend verified script → 문장별 fact/persona/editorial/legal
  → TTS → visual/rights/AI → render → 제목 게이트 → 최신성 재조회
  → 6h/24h/72h 모니터
```

기존 다큐 스킬(`.agents/skills/docu-*`, `google-flow-image-generator`, `karaoke-subtitle-builder`)은 16:9·K-웹툰/쉽선비·M4 또는 1920×1080 가라오케에 묶여 있다. 놀람파일에 그대로 쓰면 시각 언어와 음성이 역행한다.

### 2.3 음성 정본 — 문서와 런타임이 다르다

설계 §9.2는 `bible_healing/config/voice_defaults.json`을 엔진·보이스·speed·`total_step`의 단일 정본으로 두고 전역 M2 warm을 바꾸지 않는다고 한다.

| 출처 | 값 |
|---|---|
| `voice_defaults.json` narrator | M2, 0.95, total_step 10 |
| `media_rules_lock.json` narrator | M2, 0.95, total_step 10 |
| `CLAUDE.md` / `manual.md` | SuperTonic3 M2 warm |
| `seonbi_narration_policy.yaml` | `default_voice: M2`, speed 0.95, **pitch_semitones: -0.5**, 다른 EQ |
| `tts_provider.py:74-78` 기본값 | **voice=M4, speed=0.94** |
| `build_sentence_audio_master.py:208` | voice 인자 없이 호출 |
| EP02 `full-v6-001` provenance | **M4, 0.94** |

정책은 M2, 실제 HA 합성은 M4다. 설계대로 `SupertonicHttpProvider` 기본값을 `voice_defaults.json`에 묶으면 **기존 v6 WAV·타이밍·재사용 해시가 전부 stale**이 된다. “전역 잠금을 변경하지 않는다”와 “HA TTS를 정본에 맞춘다”는 동시에 성립하지 않는다.

### 2.4 화면 언어 — 기존 금지가 놀람파일 필수 라벨과 충돌

`CLAUDE.md`와 내레이션 정렬 설계는 AI 기본 이미지에 글자·숫자·캡션을 금지하고, 날짜·라벨은 `overlay_event_manifest.json`으로 렌더러가 합성한다. 놀람파일 §9.1은 `확인` / `공식 발표` / `논쟁 중` / `미확인` 한글 라벨을 **필수**로 둔다.

기존 Flow OCR 게이트(글리프 발견 = FAIL)를 프로필 구분 없이 재사용하면 원문 카드·상태 라벨 장면이 전부 거절된다. 설계는 이 overlay 경로를 재사용 대상으로 명시하지 않았고, `overlay_event_manifest` 스키마 파일도 현재 저장소에 없다.

`postflight_release.py:46-71`은 duration을 `840–1560` / `170–190` / `30–180`으로 하드코딩하고 해상도를 **1920×1080**만 허용한다. `trend_short_75s`(45–90초, 9:16)와 `trend_explainer_8m`(6–10분)은 이 게이트를 통과하지 못한다.

---

## 3. 문제점

Severity: `blocker` = 구현 착수 전 문서 수정 필요, `bug` = 내부 모순 또는 코드와 충돌, `risk` = 운영·API·범위 위험, `nit` = 표기·누락.

### 3.1 v1이 현재 파이프로 만들 수 없는 제품을 한 번에 요구한다 — Severity: blocker

- 파일: 설계 §7, §15, §19, §20, §24
- 설명: 첫 릴리스가 동시에 (a) 실시간 다중 플랫폼 수집, (b) 4개 포맷(9:16 숏폼 포함), (c) 문장별 fact/persona/editorial/legal 승인, (d) 30분·2시간 freshness, (e) 24시간 반론 창, (f) 6h/24h/72h 상주 모니터를 요구한다. 현재 HA 한 편의 승인·TTS·Flow·렌더만으로도 수 시간~수일이다. `REALTIME` 30분·`FAST` 2시간 claim은 이 DAG와 양립하지 않는다. 반론 최소 6시간은 `오늘의 놀람` 목적과 모순된다.
- 제안: v1 범위를 아래로 고정한다.
  - 포맷: `nollam_file_long` 16:9만. 숏폼·반응지도·팩트체크는 v1.1.
  - freshness: `DAILY` / `STABLE`만. `REALTIME`/`FAST`는 파일럿 제외.
  - 수집: offline fixture + Google Trends RSS/공식 export + 사람 Google News. X/Threads/Reddit은 capability가 있을 때만 optional.
  - 승인: 패킷·대본·릴리스 3단. 문장별 legal은 고위험일 때만.
  - 모니터: private dry run에는 상주 담당자 필수 조건을 걸지 않는다.

### 3.2 기존 파일 “production binding”이 쉽선비 라이브 경로를 깨뜨린다 — Severity: blocker

- 파일: 설계 §20.1; `human_archive/scripts/lib/channel_profiles.py`; `generate_verified_script.py`; `compile_shot_contract.py`; `artifact_lineage.py`
- 설명: 로더는 지금 테스트 전용이다. 여기에 `doodle_docu_12m` 미존재, host_ratio 15–25% vs 8–12%가 그대로 있다. YAML을 v6 시각 게이트에 연결하면 EP02가 실패한다. `compile_shot_contract.py`는 라이브 v6 경로에 없고, `generate_verified_script.py`는 Pompeii/쉽선비 기본값이다. `verified_script_v2` persona enum과 `sentence_audio_manifest`의 seonbi `beat` 필드는 놀람파일 문장 유형을 받지 못한다. `artifact_lineage.py`에 `profile_bundle_sha256`를 넣고 공통 산출물에 필수화하면 v6 아티팩트가 스키마 미달이다.
- 제안:
  - Phase 0(쉽선비 계약 복구)와 놀람파일 구현을 **별도 릴리스**로 나눈다.
  - 놀람파일은 `trend_job_contract_v1` → `trend_verified_script_v1` 신규 DAG만 탄다. 기존 CLI를 “하드코딩 enum 제거” 명목으로 일반화하지 않는다.
  - 공통 산출물 일반화는 **optional 필드** 또는 trend envelope 전용으로 제한한다. 기존 episode contract required 목록에 bundle SHA를 넣지 않는다.
  - host_ratio 단일 정본을 Phase 0에 명시한다. 설계는 forbidden 목록과 `doodle_docu_12m`만 적었다.

### 3.3 음성 정본을 HA TTS 기본값에 묶으면 기존 에피소드가 stale이 된다 — Severity: blocker

- 파일: 설계 §9.2, §10 YAML `audio:`; `tts_provider.py:74-78`; `build_sentence_audio_master.py:208`
- 설명: 놀람파일이 M2 warm을 쓰는 것은 맞다. 그러나 그 수단이 “전역 provider 기본값을 voice_defaults에 맞추는 것”이면 EP02 v6(M4/0.94)이 깨진다. 채널 YAML 예시가 engine/voice/speed/total_step를 **인라인 복제**해 §9.2의 “ID와 해시만 참조, 중복 정의 금지”와 모순된다. `seonbi_narration_policy.yaml`은 pitch -0.5와 다른 필터를 들고 있어 정본이 이미 세 벌이다(`voice_defaults`, `media_rules_lock`, seonbi policy).
- 제안: 놀람파일 narration policy는 `voice_defaults.json`의 **설정 ID + SHA-256만** 참조한다. HA `SupertonicHttpProvider` 기본값은 이 설계에서 건드리지 않는다. YAML 예시의 `audio:` 블록을 삭제하거나 `voice_lock_id` / `voice_lock_sha256`만 남긴다. 정본 우선순위를 `media_rules_lock.json` = `voice_defaults.json` > 프로필 참조 해시로 한 줄로 적는다.

### 3.4 점수·클러스터·차단 규칙이 서로 다른 말을 한다 — Severity: bug

- 파일: 설계 §13.1, §13.2, §3.2, §11, §16
- 설명:
  1. 조작·조율 cluster는 “단순 감점하지 않고 `QUARANTINED`”(§13.1)인데, 감점표는 “단일 플랫폼 신호 **또는 조작 의심: -20**”(§13.2)이다.
  2. “동일 사건을 하나의 event cluster로 병합”과 “canonical fingerprint **+ region/window** 유일성”이 충돌한다. 4시간 창과 24시간 창의 같은 사건은 두 cluster가 된다.
  3. 재난·사망·범죄 피해 소비는 “즉시 차단”(§13.2)인데 §16은 조건 충족 시 제작을 허용한다. 파일럿은 이 영역을 주력으로 삼지 않는다고만 한다.
  4. 실명 의혹은 “-50 **또는** 즉시 차단”이라 자동 판정이 불가능하다.
  5. discovery 75점에 `충분한 설명 깊이`, `72시간 이후 가치`, `쉽게 설명 가능`이 들어 있다. 이 값은 source probe **이전**에 계산하라고 되어 있어 측정 시점이 없다.
  6. 감점이 75점 discovery에서 빠지는지 100점 final에서 빠지는지 없다.
- 제안: 점수표를 자동 가능 항목(속도, 동시성, 검색, 1차/독립 준비도, 식별, 한국 관련성, 권리)과 사람 항목으로 나눈다. 조작은 quarantine만, 감점표에서 삭제한다. cluster 유일 키는 `event_fingerprint`만으로 두고 window는 observation 속성으로 둔다. 재난·실명은 §16 게이트가 점수보다 우선함을 한 문장으로 못 박고, “-50 또는 차단”을 제거한다.

### 3.5 번역본·원문 규칙이 충돌한다 — Severity: bug

- 파일: 설계 §3.3, §11 `REJECTED`
- 설명: 지역 정책은 “번역본만으로 사실을 확정하지 않고 **가능한 경우** 원문을 확인한다.” `REJECTED` 표는 “번역·요약본만 존재”를 사용 불가로 둔다. 해외 영화·IT 원문이 영어/일본어뿐이고 한국어 번역 보도만 있을 때 파일럿 3카테고리 중 2개가 막힐 수 있다.
- 제안: `REJECTED`는 원문을 확인할 수 없고 번역의 출처·시각도 없는 경우로 좁힌다. 원문 언어가 한국어가 아닌 확정 가능한 공식문은 `PRIMARY_SOURCE`로 허용하고, 번역본은 `translation_of` 엣지로 묶는다.

### 3.6 `오늘의 놀람` 최소 길이와 비트 시각이 맞지 않는다 — Severity: bug

- 파일: 설계 §7.1, §24 인수 11
- 설명: 길이는 45–90초. 권장 구조는 확인 경계를 **45–75초**에 둔다. 45초 영상에서는 그 구간이 시작과 동시에 끝이다. 인수 11은 “45초 **내** 확인 경계”라서 구조표와 의미가 다르다. 중간 포맷 인수(8초 내 질문, 20초 내 맥락)는 §7.3·§7.4에 없다. `놀람파일` 절대 시각(0–30초)과 비율 밴드(5–25% …)는 6분 영상에서 겹친다(5%=18초).
- 제안: 모든 비트를 **상한(until)** 으로 통일한다. 숏폼은 3 / 15 / 40초 상한. 롱폼 도입부는 12 / 15 / 30초 상한, 이후만 비율. 45초 버전에서는 확인 경계를 40초 이전으로 당긴다.

### 3.7 `반응지도`는 v1 소셜 인용 금지와 충돌한다 — Severity: bug

- 파일: 설계 §7.3, §12.3
- 설명: 포맷 목적은 Reddit·Threads·X의 반복 질문·관점 설명이다. 동시에 v1은 Reddit 사용자 게시물 직접 인용·화면 캡처를 금지하고, 소셜은 `DISCOVERY_ONLY`다. 구현자가 댓글 카드를 그리면 정책 위반, 유형만 말하면 “반응지도” 시각 계약이 비어 있다.
- 제안: v1에서 `reaction_map_mid`를 제외하거나, “집계된 질문 유형 다이어그램만, 원문 카드·핸들·아바타 금지”를 포맷 계약에 박는다.

### 3.8 스키마 v2 `oneOf`와 공통 산출물 결속이 미명세다 — Severity: bug

- 파일: 설계 §10, §10.1, §20
- 설명: 현재 파일 루트 `schema_version`은 const 1이다. v2가 파일 버전인지 프로필 버전인지 없다. nollam YAML 예시에 프로필 버전 필드가 없다. “공통 산출물에 프로필 결속 정보만 일반화”는 episode contract required 추가처럼 읽히며, 그러면 기존 HA 산출물이 전부 실패한다. 신규 스키마 13개는 파일명만 있고, `trend_job_contract_v1`의 `format_id` 필수 위치·필드 목록이 없다. claim ledger 필드만 텍스트 나열이다.
- 제안: 파일 루트는 v2로 올리고, 프로필 객체는 `oneOf` [legacy_v1_profile, v2_profile]로 나눈다. 신규 프로필은 v2만. `format_id`는 job contract 필수. 공통 결속은 trend envelope에만 넣고, HA v6 아티팩트에는 넣지 않는다고 명시한다. 구현 전 `trend_job_contract_v1` / `trend_signal_manifest_v1` / `trend_verified_script_v1`의 required 필드를 설계에 표로 추가한다.

### 3.9 Phase 0 `doodle_docu_12m` 처방이 기존 HA002 계획과 반대다 — Severity: bug

- 파일: 설계 §20, §25 Phase 0; `docs/superpowers/plans/2026-08-31-ha002-context-sample-quality-rebuild.md:465`
- 설명: 놀람파일은 누락 프로필을 **추가**하고 `doodle_seonbi_v1` 참조를 유지한다. HA002 계획은 기본 프로필을 존재하는 `standard_docu`로 **바꾸고** 샘플은 `quick_3m` override다. 둘 다 “참조를 고친다”고 하지만 정본 ID가 다르다. 설계가 HA002 계획을 대체하는지 병행하는지가 없다.
- 제안: 쉽선비 기본 delivery는 `doodle_docu_12m`를 YAML에 추가하는 쪽이 기존 채널 의도에 맞다(`600–840초`, 2026-08-27 계획). HA002 샘플만 `quick_3m` override. 이 결정을 Phase 0에 적고 HA002 계획의 “standard_docu로 교체” 항목을 superseded로 표시한다.

### 3.10 fail-closed 수집은 권한 없으면 발견 단계가 공집합이 된다 — Severity: risk

- 파일: 설계 §12.6, §21, §27
- 설명: 필수 capability 부재 시 `SOURCE_UNAVAILABLE`. X Trends `GET /2/trends/by/woeid/{woeid}`는 문서상 존재하지만 유료 티어다. 한국 WOEID는 설계에 없다. 삭제 24시간 반영에 인용한 Compliance Streams는 엔터프라이즈 성격이다. Threads `/keyword_search`는 App Review 전에는 **인증 사용자 본인 글만** 검색한다. Google Trends 공식 API(2025-07 alpha)는 참고 자료에 없고, RSS/CSV/사람 export만 있다. CSV를 브라우저로 받는 경로는 X 스크레이핑 금지와 경계가 흐리다. Reddit Pro는 API가 아니다(이 점은 설계가 올바르게 구분함).
- 제안: v1 **required** provider를 Google Trends(공식 RSS 또는 사람이 보존한 export) + 사람 Google News 링크로 축소한다. X/Threads/Reddit/YouTube는 capability matrix에서 `optional`로 두고, 없어도 discovery를 막지 않는다. 삭제 준수는 보유 `source_id`에 대한 lookup 폴링으로 정의하고, Compliance Stream을 v1 필수로 두지 않는다. Google Trends API alpha 수용 여부를 §27에 추가한다.

### 3.11 핵심 claim 게이트가 스포츠·공식 기록 파일럿을 과도하게 막는다 — Severity: risk

- 파일: 설계 §11.1, §23
- 설명: 핵심 claim은 `PRIMARY_SOURCE 1 + INDEPENDENT_CONFIRMATION 1`이다. 신디케이트·통신사 복제는 한 corroboration group이다. 리그 공식 스코어의 “독립 확인”이 통신사 전재면 독립이 1이 되지 않는다. 파일럿 카테고리 3(스포츠)이 자주 `PRIMARY_ONLY`로 떨어져 제목·결론에 못 쓴다.
- 제안: 경기 결과·공시·법원 등 **권위 원문이 사건 기록 자체인 경우**는 `direct_record` + 원문 1로 core를 허용하고, 독립 확인은 supporting에 둔다. 의혹·해석·규모 주장만 독립 확인을 강제한다.

### 3.12 법률 참고가 실제 게이트보다 좁다 — Severity: risk

- 파일: 설계 §16, §27
- 설명: 게이트는 명예·사생활·선거·저작권·개인정보를 다루는데 참고 링크는 형법 제307조·제310조·민법이다. 정보통신망법 제70조, 개인정보보호법, 저작권법, 공직선거법이 없다. 설계 스스로 “법률 자문을 대체하지 않는다”고 한 것과 맞추려면 참고 목록을 게이트 항목과 대응시켜야 한다.
- 제안: 조문 링크를 게이트 표와 1:1로 보강하고, 구현 산출물에 법률 의견을 요구하지 말 것(이미 올바름)을 유지한다.

### 3.13 인수 기준이 파일럿 범위를 초과한다 — Severity: risk

- 파일: 설계 §23, §24
- 설명: 파일럿은 세 카테고리 private dry run이다. 인수 22는 “뉴스·영화·연예·IT·스포츠 임의 주제 5개”와 독립 검수자 3명을 요구한다. 인수 12·17도 독립 검수다. 검수자 자격·Rubric 수집 방법이 없다. 인수 11의 중간 포맷 타이밍은 v1에서 포맷을 빼면 무의미하다.
- 제안: 구현 완료 = §24 1–10, 13–16, 18–21 + 롱폼 타이밍. 검수자·5주제 브랜드 테스트는 Phase 3 공개 파일럿 완료 기준으로 옮긴다.

### 3.14 grouping ID 세 종의 관계가 없다 — Severity: nit

- 파일: 설계 §13.1, §11.1, §14.2
- 설명: `origin_cluster_id`, `crosspost_parent_id`, `corroboration_group_id`, event fingerprint가 신호 중복 제거와 증거 중복 계산에 섞여 있다.
- 제안: 신호 계층(`origin_cluster_id` / `crosspost_parent_id`)과 증거 계층(`corroboration_group_id`)을 표로 분리한다.

### 3.15 기존 문서 드리프트를 놀람파일 작업에 섞지 말 것 — Severity: nit

- 파일: 설계 §20.1 `CLAUDE.md`, `manual.md`, `README.md`
- 설명: 세 문서는 이미 승인 소스 문자열이 코드와 어긋난다. 코드 `fact_review_approval.py`는 `explicit_user_confirmation_in_codex_thread` const이고, 문서는 `antigravity_thread`를 넘긴다. 놀람파일 절을 추가하면서 이 불일치를 “顺便” 고치면 리뷰 범위가 폭발한다.
- 제안: 공식 문서에는 **opt-in 프로필이 기본 경로가 아니다**는 한 절만 추가한다. 쉽선비 명령 예시는 Phase 0에서만 손본다.

---

## 4. 잘 된 점 (유지)

구현 축소와 무관하게 유지해야 하는 결정이다.

- 슬로건과 여섯 질문. 시청자에게 판정을 대신하지 않겠다는 약속이 채널을 규정한다.
- 소셜 = 발견, 공식 원문 + 독립 확인 = 사실. 이 한 줄이 기존 역사 ledger와 가장 크게 다른 핵심이다.
- `source_state=deleted`를 `FALSE`/`RETRACTED`로 자동 승격하지 않음.
- 신디케이트·보도자료 복제를 독립 확인으로 세지 않음.
- 비공식 스크레이퍼·타인 세션 우회 금지.
- `nollam_file_v1.is_default = false`, `verified_script_v3` 이름 비재사용, `topics.schema.json` 비일반화, 역사 DB와 trend DB 분리.
- YouTube는 파일 교체가 불가하므로 CRITICAL은 비공개·재업로드.
- 제목 절대 금지 표현과 조건부 숫자 표현의 구분.
- 범죄 수사판 비주얼 금지, 상태 라벨을 색만으로 전달하지 않음.

---

## 5. 워크플로우 권고 (구현 시)

기존 스킬을 오케스트레이터로 쓰지 않는다. 재사용할 것은 **아이디어와 v5/v6 스크립트 패턴**이다.

| 기존 자산 | 놀람파일 v1 |
|---|---|
| `build_sentence_audio_master.py` TTS-first | 재사용. voice/speed는 job의 voice lock 해시로 명시 전달(기본값 M4를 바꾸지 않음) |
| `plan_narration_shots.py` 9–15초 샷 바닥 | 롱폼만 부분 재사용. 숏폼은 별도 pacing |
| Flow + `generate_flow_batch.py` | 트렌드 visual compiler가 있을 때만. 쉽선비 overlay·K-웹툰 스킬 금지 |
| OCR no-glyph | 프로필별. 라벨·원문 카드는 overlay 합성 후 검사 |
| `postflight_release.py` | delivery profile을 읽도록 확장하기 **전에** 놀람파일 전용 postflight를 둔다 |
| `docu-qa-verifier` / `google-flow-image-generator` / `docu-tts-synthesizer` | 사용하지 않음 |
| `karaoke-subtitle-builder` | 16:9 롱폼 참고만. 상태 라벨·9:16은 별도 계약 |

권장 구현 순서:

1. **Phase 0만** (쉽선비): `doodle_docu_12m` 추가, forbidden 테스트 12개로 수정, delivery ID 존재 테스트, host_ratio 정본 문서화. 로더를 v6에 연결하지 않음.
2. **계약만**: `nollam_file_v1` opt-in YAML + 참조 policy 파일 + strict schema. 테스트는 “unknown ref FAIL, default는 여전히 doodle”.
3. **offline DAG**: fixture 신호 → cluster → score → research packet → trend script. 네트워크 provider 없음.
4. **음성·화면**: M2를 job 인자로 합성, 상태 라벨 overlay, 16:9 롱폼 1편 dry run.
5. provider adapter는 capability가 실제로 확보된 뒤에만 연다.

---

## 6. 설계 문서에 반영할 최소 수정 목록

구현 계획 작성 전에 대상 문서에서 아래를 고친다.

1. v1 범위 상자: 포맷 1개, freshness DAILY/STABLE, 수집 fixture+optional API, 숏폼/반응지도/실시간 제외.
2. §20.1에서 `generate_verified_script.py`, `compile_shot_contract.py`, `artifact_lineage.py` production cascade, 공통 산출물 required bundle 필드를 삭제하거나 “HA 경로 비변경”으로 제한.
3. §9.2 / §10 YAML 음성 중복 제거, HA TTS 기본값 변경 금지를 명시.
4. §13 점수·quarantine·cluster 키 모순 해소.
5. `REJECTED` 번역본 조항과 §3.3 정합.
6. §7 비트 시각을 상한으로 통일, 45초 숏폼 구조 수정. v1에서 빼는 포맷은 표에서 `deferred` 표시.
7. schema v2 = 파일 루트 + 프로필 `oneOf`, job `format_id` 위치, 신규 스키마 required 필드 표.
8. Phase 0 vs HA002 `standard_docu` 교체안 결정.
9. provider required/optional 분리, 한국 X WOEID, Compliance Stream 비필수.
10. 스포츠 공식 기록의 core 게이트 예외.
11. 인수 22·독립 검수를 Phase 3로 이동.
12. host_ratio 충돌을 Phase 0 범위에 추가.

---

## 7. 판정

| 항목 | 결과 |
|---|---|
| 브랜드·편집 계약 | 채택 |
| 출처 역할·claim 상태 모델 | 채택 (번역·스포츠 core·점수표만 수정) |
| 현황 감사 §4.1 | 채택 (사실) |
| 분리형 프로필 구조 | 방향 채택, 공통 산출물 일반화는 거부 |
| 기존 CLI 일반화 | 거부 |
| 4포맷 + 실시간 수집 v1 | 거부, 축소 후 재검토 |
| 구현 착수 | 위 §6 반영 전 **보류** |

문서 상태를 `설계 검토 요청`에서 `리뷰 반영 대기`로 바꾸고, §6를 반영한 뒤 구현 계획을 별도 문서로 쓰는 것을 권한다.
