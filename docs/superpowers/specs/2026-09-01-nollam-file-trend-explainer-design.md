# 놀람파일 트렌드 해설 프로필 설계

- 문서 상태: 리뷰 반영 완료 — 구현 계획 작성 기준
- 작성일: 2026-09-01
- 프로필 ID: `nollam_file_v1`
- 표시 이름: `놀람파일`
- 영문 보조 표기: `NOLLAM FILE`
- 기본 프로필 여부: `false`
- 선행 결정: 2026-09-01 사용자 승인 — `놀람파일` 추천 방향 채택

## 1. 결정 요약

`놀람파일`은 뉴스, 영화, 연예, 드라마, IT·테크, 스포츠, 인터넷 문화에서 빠르게 확산하는 이야기를 발견하고, 사람들이 왜 놀랐는지와 실제로 확인된 사실을 한국어로 쉽게 설명하는 트렌드 해설 프로필이다.

핵심 브랜드 문장은 다음과 같다.

> 놀람은 입구, 맥락은 본문, 판단은 시청자.

슬로건은 다음과 같다.

> 놀람은 짧게, 이해는 깊게.

이 프로필은 속보 복제, 커뮤니티 반응 낭독, 분노 유도, 연예인 사생활 소비를 목표로 하지 않는다. Reddit, Threads, X, Google Trends, YouTube 등은 주제를 발견하는 `DISCOVERY_ONLY` 신호로 사용하고, 사실은 공식 원문과 독립적인 신뢰 출처로 확정한다.

첫 릴리스는 기존 기본 프로필을 변경하지 않는 opt-in 프로필로 제공한다. 기존 `doodle_seonbi_v1`과 역사 콘텐츠 계약은 그대로 보존한다.

### v1 범위 상자

- 활성 포맷: `nollam_file_long` 하나
- 화면: 16:9, 1920×1080, 25fps
- freshness: `DAILY`와 `STABLE`만
- 필수 탐색 입력: offline fixture, Google Trends 공식 RSS/사람이 보존한 공식 export, 사람이 확인한 Google News 원문 링크
- X, Threads, Reddit, YouTube 자동 provider: capability가 확보될 때만 선택적으로 활성화하며 없어도 v1 discovery를 차단하지 않음
- 숏폼·반응지도·팩트체크·REALTIME/FAST freshness·무인 게시·상주 모니터: v1.1 이후로 연기

## 2. 시청자 약속

모든 영상은 아래 여섯 질문에 답해야 한다.

1. 정확히 무슨 일이 있었나?
2. 왜 하필 지금 커졌나?
3. 사람들이 무엇을 놀라워하거나 문제 삼았나?
4. 무엇이 확인됐고 무엇이 주장·추정인가?
5. 반대쪽 설명이나 빠진 맥락은 무엇인가?
6. 그래서 시청자에게 왜 중요한가?

시청자가 영상 시청 후 얻어야 하는 결과는 “누가 맞는지 대신 결정해 주었다”가 아니라 “어디까지가 사실이고 쟁점이 무엇인지 스스로 설명할 수 있다”이다.

## 3. 대상과 범위

### 3.1 우선 시청자

- 한국어로 최신 이슈를 이해하고 싶은 18~44세 시청자
- 사건 자체는 접했지만 배경과 맥락을 따라가기 어려웠던 시청자
- 해외 Reddit·Threads·X에서 시작한 화제를 한국적 맥락으로 이해하고 싶은 시청자
- 자극적인 반응 모음보다 짧고 명확한 설명을 선호하는 시청자

### 3.2 콘텐츠 카테고리

- `news`
- `film`
- `entertainment`
- `drama`
- `it_tech`
- `sports`
- `internet_culture`

정치, 선거, 금융, 의료, 범죄, 재난, 미성년자 관련 주제는 범위에 포함될 수 있으나 고위험 게이트를 통과해야 한다. 초기 파일럿에서는 이 영역을 주력으로 삼지 않는다.

### 3.3 지역 정책

- 시청자 기준: `KR`
- 신호 수집 범위: `KR`, `global`
- 해외 이슈는 한국 시청자와의 연결점을 명시할 수 있을 때 우선한다.
- 번역본만으로 사실을 확정하지 않고 가능한 경우 원문을 확인한다.

## 4. 기존 시스템 감사와 설계 선택

### 4.1 확인된 현황

- `human_archive/config/channel_profiles.yaml`에는 현재 `doodle_seonbi_v1`, `human_archive_cinematic_v1`만 존재한다.
- `human_archive/schemas/channel_profile.schema.json`은 중첩 프로필 필드를 엄격하게 검증하지 않는다.
- `human_archive/scripts/lib/channel_profiles.py`의 프로필 로더는 테스트 외 production 경로에 연결되지 않아 YAML만 추가하면 실제 산출물에 영향을 주지 않는다.
- `episode_contract_v2`, `verified_script_v2`, `generate_verified_script.py`, `compile_shot_contract.py`는 역사 콘텐츠와 쉽선비 페르소나에 결합되어 있다.
- 현재 topic inventory와 source ledger는 역사 자료 중심이므로 최신성, 수정·삭제 상태, 소셜 신호, 보도·공식 발표를 충분히 표현하지 못한다.
- `delivery_profile`과 과거 계획 문서의 `delivery_profile_id` 명칭이 불일치한다.
- `doodle_seonbi_v1`이 참조하는 `doodle_docu_12m` delivery profile 누락과 forbidden 목록 테스트 불일치가 존재한다.

### 4.2 선택

단순 YAML 확장이 아닌 분리형 프로필 구조를 채택한다.

- 채널 정체성: `channel_profile`
- 편집 원칙: `editorial_profile`
- 조사·팩트 정책: `research_policy`
- 화자·문체: `narration_policy`
- 화면 언어: `visual_profile`
- 영상 길이·출력: `delivery_profile`
- 게시·정정: `publication_policy`

기존 역사 계약을 억지로 일반화하지 않는다. trend 전용 계약을 추가하고 공통 산출물에는 프로필 결속 정보만 일반화한다.

## 5. 대안과 선택 이유

### 5.1 선택안: `놀람파일`

- 조사 자료, 타임라인, 원문, 쟁점을 열어 본다는 약속이 선명하다.
- 뉴스부터 영화·IT·스포츠까지 확장 가능하다.
- 상세 해설과 짧은 브리핑을 하나의 브랜드로 묶을 수 있다.
- 범죄·미스터리 전용으로 오해하지 않도록 시각 언어를 밝고 현대적으로 제한한다.

### 5.2 보류안: `놀람해설소`

- 기능 전달은 쉽지만 브랜드 고유성이 상대적으로 약하다.

### 5.3 보류안: `왜놀랐지?`

- 친근하고 제목 문법이 좋지만 일반 문장이라 검색 독점력이 낮다.

### 5.4 제외안: `놀란`

- 한국어 형용사와 고유명사 의미가 겹친다.
- 영화 카테고리에서 Christopher Nolan과 검색 충돌이 크다.

## 6. 브랜드와 화자 페르소나

### 6.1 브랜드 값

| 항목 | 값 |
|---|---|
| Display name | `놀람파일` |
| English | `NOLLAM FILE` |
| Profile ID | `nollam_file_v1` |
| Persona ID | `nollam_explainer` |
| Editorial profile | `nollam_trend_v1` |
| Research policy | `trend_verified_v1` |
| Narration policy | `nollam_file_narration_v1` |
| Visual profile | `nollam_file_visual_v1` |
| Default delivery | `trend_explainer_8m` |
| Publication policy | `trend_safe_release_v1` |

### 6.2 화자 정의

화자는 `온라인 이슈 조사관 + 설명을 잘하는 친구`다.

- 호기심 40%: 왜 갑자기 모두 이 이야기를 하는지 묻는다.
- 명료함 30%: 전문용어와 배경을 일상어로 번역한다.
- 검증적 의심 20%: 최초 게시물, 공식 발표, 후속 정정을 확인한다.
- 절제된 유머 10%: 상황의 아이러니를 짚되 사람을 조롱하지 않는다.

위 비율은 방향을 설명하는 값이며 자동 점수로 사용하지 않는다. 실제 승인은 다음 관찰 가능한 rubric으로 판단한다.

- 전문용어 첫 등장 직후 쉬운 설명 존재율 100%
- 화자의 조사 능력을 과시하는 자기 언급 0건
- 사람이나 집단을 조롱하는 유머 0건
- 모든 `reported_claim`과 `allegation`의 귀속 누락 0건
- 독립 검수자의 명료성 평가 평균 4/5 이상

권장 문장 톤:

> 처음 보면 황당합니다. 그런데 원문과 시간순서를 같이 보면 쟁점은 조금 달라집니다.

### 6.3 화자 금지 규칙

- 과장된 감탄사를 반복하지 않는다.
- 특정 팬덤, 정당, 기업, 플랫폼의 편을 먼저 정하지 않는다.
- “제가 조사해 보니”, “사료를 검증해 보니”처럼 제작 과정을 본문보다 앞세우지 않는다.
- 모르는 내용을 추측으로 메우지 않는다.
- 피해자, 일반인, 외모, 말투를 웃음의 대상으로 삼지 않는다.
- 시청자에게 댓글 공격, 신고, DM, 좌표 찍기를 유도하지 않는다.

## 7. 콘텐츠 포맷

각 영상은 정확히 하나의 주 포맷을 선언한다.

`format_id`는 필수이며 각 포맷은 별도 delivery profile과 결속한다. v1은 `nollam_file_long`만 활성화하고 나머지는 v1.1 deferred 계약으로 기록한다.

| 포맷 | `format_id` | Delivery profile | 길이·화면 |
|---|---|---|---|
| 오늘의 놀람 | `today_surprise_short` | `trend_short_75s` | v1.1 deferred: 45~90초, 9:16 |
| 놀람파일 | `nollam_file_long` | `trend_explainer_8m` | 6~10분, 16:9 |
| 반응지도 | `reaction_map_mid` | `trend_reaction_5m` | v1.1 deferred: 4~7분, 16:9 |
| 진짜 놀랄 일인가 | `reality_check_mid` | `trend_factcheck_4m` | v1.1 deferred: 3~6분, 16:9 |

`반응지도`라는 이름은 대립과 분노를 전제하는 기존 후보 `댓글전쟁`을 대체한다. 운영 문서와 화면에서는 `댓글전쟁`을 사용하지 않는다.

### 7.1 `오늘의 놀람` (v1.1 deferred)

- 길이: 45~90초
- 목적: 무엇이 발생했고 왜 지금 확산했는지 빠르게 설명
- 필수: 현재 확인된 사실 1개, 귀속된 `PRIMARY_ONLY` 또는 `DISPUTED` 사항 1개 이하, 원문 링크
- `UNVERIFIED` 주장은 숏폼에서도 사실이나 결론으로 사용할 수 없다.
- 금지: 복잡한 실명 의혹, 여러 반론이 필요한 사건을 억지로 축약

권장 구조:

1. 0~3초: 의외성 또는 핵심 질문
2. 3~15초: 실제 발생 사실
3. 15~45초: 사람들이 놀란 이유와 빠진 맥락
4. 45~75초: 확인·미확인 경계
5. 마지막: 다음 확인 지점

### 7.2 `놀람파일`

- 길이: 6~10분
- 기본 delivery profile: `trend_explainer_8m`
- 목적: 발단, 타임라인, 원문, 반론, 의미를 한 편의 이야기로 설명

권장 구조:

1. 0~12초: 사건과 중심 질문
2. 12~15초: 시청자가 얻게 될 설명 보상
3. 15~30초: 이해에 필요한 최소 배경
4. 전체 길이의 5~25%: 무슨 일이 있었는지 시간순 정리
5. 전체 길이의 25~55%: 왜 놀라운지와 배경
6. 전체 길이의 55~80%: 서로 다른 주장과 확인 결과
7. 전체 길이의 80~95%: 시청자에게 미치는 의미
8. 마지막 5%: 확정, 미확정, 다음 확인 포인트

### 7.3 `반응지도` (v1.1 deferred)

- 길이: 4~7분
- 목적: Reddit·Threads·X의 반복 질문과 관점을 2~4개 쟁점으로 묶어 설명
- 커뮤니티 게시물은 사실 증거가 아니라 질문·반응 유형으로만 사용한다.
- 표본 기간, 플랫폼, 지역, 검색어, 선정 방법과 대표성 한계를 표시한다.
- 극단적인 댓글 몇 개를 전체 여론처럼 표현하지 않는다.

### 7.4 `진짜 놀랄 일인가` (v1.1 deferred)

- 길이: 3~6분
- 목적: 과장된 헤드라인, 바이럴 통계, 루머의 실제 규모와 사실성 검증
- 반박 대상 원문을 정확히 보존하고 허수아비 주장을 만들지 않는다.

## 8. 스토리와 대본 규칙

### 8.1 내러티브 원칙

- 첫 문장은 검증된 의외성, 모순, 변화 중 하나로 시작한다.
- 검증 절차는 화면 뒤에서 엄격하게 수행하되 대본은 이야기 중심으로 쓴다.
- 숫자는 비교 기준이나 생활 크기로 번역한다.
- 전문용어는 첫 등장 직후 한 문장으로 쉽게 풀어 쓴다.
- 시간순서가 중요한 사건은 날짜와 시각을 화면과 음성에서 일치시킨다.
- 주장과 반론은 누가, 언제, 어떤 근거로 말했는지 귀속한다.
- 결말은 `확정된 것 / 아직 모르는 것 / 다음 확인 포인트`로 닫는다.

### 8.2 문장 상태

대본의 모든 factual sentence는 `claim_id`를 가져야 한다. 문장은 다음 중 하나로 분류한다.

- `fact`
- `reported_claim`
- `allegation`
- `opinion`
- `prediction`
- `social_reaction`

귀속 없는 `allegation`은 허용하지 않는다. `opinion`, `prediction`은 사실처럼 발음하거나 자막 처리하지 않는다.

### 8.3 재미를 만드는 방식

- 놀람의 원인은 “사람이 황당하다”가 아니라 예상과 실제의 차이에서 찾는다.
- 한 영상은 중심 질문 하나와 보조 질문 최대 3개만 갖는다.
- `오늘의 놀람`은 10~20초, 중간 포맷은 30~45초, `놀람파일`은 45~75초마다 새로운 정보, 반전, 질문 해소 중 하나가 발생해야 한다.
- 사실 확인 자체보다 확인 결과가 기존 인상을 어떻게 바꾸는지를 보여준다.
- 밈과 유머는 이해를 돕는 경우에만 사용하며 사실을 대체하지 않는다.

## 9. 비주얼·음성 설계

### 9.1 시각 방향

기본 모티프는 `현대적인 디지털 사건 파일`이다. 범죄 수사판, 공포 썸네일, 자극적인 속보 화면처럼 보이지 않아야 한다.

| 용도 | 색상 |
|---|---|
| 기본 차콜 | `#151922` |
| 오프화이트 | `#F5F2E8` |
| 핵심 강조 옐로 | `#FFC857` |
| 보조 오렌지 | `#F28C28` |
| 링크·데이터 블루 | `#3F6FE5` |
| 오류·반박 전용 레드 | `#D64545` |

화면 상태는 문장 유형과 claim 상태를 함께 사용해 결정한다.

| Sentence type / Claim status | 화면 라벨 | 필수 조건 |
|---|---|---|
| `fact + CONFIRMED` | `확인` | claim ID와 검증 source ID |
| `reported_claim + PRIMARY_ONLY` | `공식 발표` | 발언 주체·시각·원문 귀속 |
| `reported_claim/allegation + DISPUTED` | `논쟁 중` | 충돌 출처와 evidence weight |
| 승인된 비핵심 `UNVERIFIED` 소개 | `미확인` | 루머 설명 목적, 귀속, editor approval |
| `FALSE` | `반박됨` | 반박 근거와 반박 시각 |
| `CORRECTED/OUTDATED/RETRACTED` | `정정됨` | 이전·현재 상태와 변경 시각 |
| `opinion` | `해석` | 화자 또는 인용 주체 표시 |
| `prediction` | `전망` | 가정과 불확실성 표시 |
| `social_reaction` | `반응` | 플랫폼·기간·표본 범위 |

`FALSE`와 `UNVERIFIED`를 `확인` 라벨로 표시할 수 없다. 라벨·자막·대본 상태가 다르면 빌드를 실패시킨다.

AI 기본 이미지에는 글자·숫자·캡션을 생성하지 않는다. 상태 라벨과 날짜·출처는 overlay_event_manifest_v1이 렌더 단계에서 합성한다. OCR gate는 base image와 overlay composite를 별도로 검사하며, profile이 허용한 overlay glyph를 이미지 생성 실패로 오인하지 않는다.

추가 규칙:

- 굵은 한글 산세리프 두 굵기만 사용한다.
- 원문 카드는 출처, 작성 시각, 수정 여부를 함께 표시한다.
- 비공개·보호·친구 전용 계정, 유출 메시지는 명시적 당사자 동의와 법률 승인 없이는 수집·인용·화면화하지 않는다.
- 공개 일반인 계정은 필요한 경우에도 사용자명·프로필 사진 등 식별자를 최소화한다.
- 썸네일은 주 피사체 1개, 쟁점 1개, 보조 요소 1개 이하로 제한한다.
- 합성 놀란 표정, 무관한 유명인, 폭발 효과, 가짜 삭제 UI를 금지한다.
- 빨간 원·화살표는 합계 1개 이하로 제한한다.
- 본문 텍스트 대비율은 WCAG 기준 4.5:1 이상, 큰 텍스트는 3:1 이상이어야 한다.
- 상태는 색상만으로 전달하지 않고 라벨과 아이콘을 함께 사용한다.

### 9.2 음성

기존 운영 잠금을 상속한다.

- 엔진: SuperTonic3
- 보이스: `M2`
- 톤: `warm`
- speed: `0.95`
- `total_step`: `10`
- fallback voice: 금지

이 설계는 전역 TTS provider 기본값을 변경하지 않는다. 현재 provider 기본값 M4/0.94와 EP02 기존 M4 산출물을 보존한다. 놀람파일 job만 voice_lock_id=M2_WARM을 명시하고 bible_healing/config/voice_defaults.json과 bible_healing/config/media_rules_lock.json의 M2 lock record가 일치하는지 확인한 뒤 voice=M2, speed=0.95, total_step=10을 명시 인자로 전달한다. 두 lock record가 불일치하면 FAIL이다. pitch, filter, silence 정책은 해당 lock record에서 상속하고 프로필에 중복 정의하지 않는다. 보이스 파일, 합성 manifest, 최종 오디오에는 실제 사용된 엔진·보이스·설정 해시를 기록한다. M2 전용 실패 규칙은 합성 narrator track에만 적용하며, 권리 승인된 원본 인터뷰·직접 인용 오디오는 별도 asset rights 계약을 따른다.

## 10. 프로필 계약

권장 프로필 형태는 다음과 같다.

```yaml
nollam_file_v1:
  display_name: "놀람파일"
  is_default: false
  profile_kind: trend_explainer
  editorial_profile_id: nollam_trend_v1
  research_policy_id: trend_verified_v1
  narration_policy_id: nollam_file_narration_v1
  visual_profile_id: nollam_file_visual_v1
  delivery_profile_id: trend_explainer_8m
  voice_lock_id: M2_WARM
  format_delivery_map:
    today_surprise_short: trend_short_75s
    nollam_file_long: trend_explainer_8m
    reaction_map_mid: trend_reaction_5m
    reality_check_mid: trend_factcheck_4m
  publication_policy_id: trend_safe_release_v1
  content:
    language: ko
    regions: [KR, global]
    categories:
      [news, film, entertainment, drama, it_tech, sports, internet_culture]
    social_role: DISCOVERY_ONLY
```

모든 참조 ID는 실제 설정에 존재해야 하며, unknown reference는 즉시 실패한다. 자동 기본값이나 silent fallback을 사용하지 않는다.

`delivery_profile_id`를 schema version 2의 canonical 필드로 확정한다. 기존 schema version 1의 `delivery_profile`은 legacy 입력에서만 한시적으로 읽고 내부 manifest에는 `delivery_profile_id`로 정규화한다. 두 필드가 동시에 존재하면 실패한다. legacy 제거 시점은 모든 기존 프로필 migration과 회귀 테스트 통과 후 별도 릴리스로 결정한다.

### 10.1 프로필 결속

다음 trend envelope 산출물만 `channel_profile_id`, `resolved_profile_bundle_id`, `profile_bundle_sha256`을 가져야 한다. 기존 HA v5/v6 episode·audio·visual 산출물은 required 필드를 변경하지 않는다.

- trend job contract
- trend signal manifest
- trend topic candidate
- trend research packet
- trend outline 및 verified script
- trend fact/persona/editorial approval
- trend visual/audio/render manifest
- trend publication/release manifest

`resolved_profile_bundle_v1`은 channel, editorial, research, narration, visual, delivery, publication 설정의 canonical JSON과 각 SHA-256을 포함한다. `profile_bundle_sha256`은 이 해시 묶음 전체에서 계산한다. v1에서는 기존 artifact_lineage.py와 HA episode contract를 수정하지 않고 trend envelope 내부 lineage로만 사용한다. 참조 정책 하나라도 바뀌면 trend downstream 승인은 stale이 되고 재생성 또는 재승인이 필요하다.

## 11. 출처 역할 정책

`source_type`은 자료의 고유 유형이고, 증거 역할은 소스 전체가 아니라 각 `claim-source edge`에 기록한다. 같은 회사 보도자료도 “회사가 발표했다”에는 직접 기록이지만 제품 성능 주장에는 자기 진술일 수 있다.

| 정책 분류 | 예시 | 허용 용도 | 규칙 |
|---|---|---|---|
| `PRIMARY_SOURCE` | 정부·법원·공시·리그 공식 기록, 원본 인터뷰, 논문, 보안 권고, 릴리스 노트 | 사건·수치·일정·직접 발언의 직접 기록 | 핵심 claim에 최소 1개 필수 |
| `INDEPENDENT_CONFIRMATION` | 편집 책임이 명확한 독립 언론·전문 매체 | 원문 해석, 맥락, 독립 확인 | 핵심 claim에 최소 1개 필수 |
| `DISCOVERY_ONLY` | Google Trends, Reddit, Threads, X, YouTube 차트·검색·댓글 | 이슈 탐지, 질문·반응 유형 발견 | 외부 사실·전체 여론의 근거로 사용 금지 |
| `REJECTED` | 익명 폭로, 출처 없는 캡처, 삭제 글 재업로드, 출처·시각 없는 번역·요약본, 합성 여부 불명 자료 | 사용 불가 | claim parent면 빌드 실패 |

각 claim-source edge는 다음 `evidence_relation` 중 하나를 갖는다.

- `direct_record`
- `self_statement`
- `independent_observation`
- `expert_analysis`
- `reaction`

공식 계정 게시물은 보통 `self_statement`다. “그 기관이나 인물이 그렇게 발표했다”만 증명하며 발표 내용이 참이라는 사실까지 자동으로 증명하지 않는다.

### 11.1 핵심 사실 게이트

- 사건 결론에 영향을 주는 핵심 claim: `PRIMARY_SOURCE 1 + INDEPENDENT_CONFIRMATION 1`
- 경기 결과, 공시, 법원 주문처럼 권위 원문 자체가 사건 기록인 direct_record core claim은 원문 1개로 허용하고 독립 확인은 supporting 검증으로 둔다.
- 인물 의혹: 공식 절차 원문과 독립 확인 2개, 당사자 반론, 사람 승인
- 일반 배경 사실: 권위 있는 직접 자료 1개 또는 독립적인 신뢰 출처 2개
- 동일 통신사 기사, 보도자료 복제, 신디케이트 기사는 하나의 `corroboration_group_id`로 계산
- 원문이 존재하지 않거나 확인할 수 없는 사건은 initial release에서 발행하지 않음

한국어가 아닌 원문이라도 출처·발행 시각·원문 링크를 확인할 수 있으면 PRIMARY_SOURCE로 허용한다. 한국어 번역은 해당 원문을 가리키는 translation_of edge로 기록하며 번역본만으로 새 사실을 추가하지 않는다.

`claim_criticality`는 `core|supporting|context` 중 하나다. `PRIMARY_ONLY`는 정확히 귀속된 자기 발표 또는 비핵심 배경에서만 허용하며 제목, 썸네일, 핵심 결론에는 사용할 수 없다. `DISPUTED`는 양측을 정확히 귀속하되 분량과 확신도를 억지로 동일하게 맞추지 않고 `evidence_weight`와 증거의 질·양에 비례해 설명한다.

## 12. 플랫폼 신호 정책

### 12.1 Google Trends

- 관심 급등 탐지에 사용한다.
- 0~100 값은 시간·지역 내 상대 관심도이며 절대 검색량이나 찬반 여론이 아니다.
- 서로 다른 지역·기간의 0~100 값을 직접 비교하지 않는다.
- exact search term, Topic, Trending Now exact match, Explore broad match를 `query_mode`로 구분한다.
- `query/topic`, `query_mode`, `country`, `window`, `first_seen_at`, `peak`, `rising_related_queries`, `captured_at`을 저장한다.
- 4시간, 24시간, 7일 관측 창을 지원한다.

### 12.2 X

- 공식 Trends, recent search, post counts만 사용한다.
- 모니터링은 지역을 고정하고 개인화 신호와 구분한다.
- 브라우저 스크래핑을 금지한다.
- 삭제·비공개·정지·수정 상태를 compliance 정책에 따라 반영한다.
- official API 접근이 없거나 지역 trends capability가 없으면 `SOURCE_UNAVAILABLE`로 실패하고 스크래핑으로 우회하지 않는다.
- 플랫폼, 지역, 관측 시각 없이 “X가 폭발했다”고 표현하지 않는다.

### 12.3 Reddit

- 반복되는 질문, 오해, 감정 패턴을 발견하는 데 사용한다.
- Reddit Pro Trends는 공개·SFW·영어 대화 일부를 다루는 내부 발견 도구이며 국가별 전체 여론이 아니다.
- Reddit Pro 화면, 지표, AI 요약, 타인의 글·댓글을 영상에 공개·다운로드·재게시하지 않는다. `reddit_pro_publication_allowed: false`를 기본값으로 둔다.
- v1에서는 Reddit 일반 사용자 게시물의 직접 인용과 화면 캡처를 금지하고, 집계된 질문 유형만 사용한다.
- Reddit Pro 수동 snapshot adapter와 승인된 공식 Reddit API adapter를 서로 다른 provider로 취급한다. Reddit Pro를 API로 가정하지 않는다.
- 사용자명, 아바타, 개인별 반응 이력은 저장하지 않는다.

### 12.4 Threads

- 공식 Threads API `keyword_search`의 `TOP`, `RECENT`를 사용한다.
- 같은 키워드를 두 모드로 관찰하여 인기성과 발생 시점을 구분한다.
- collector는 `threads_basic`, `threads_keyword_search` 권한을 확인한다.
- 비공식 스크레이퍼를 사용하지 않는다.

### 12.5 YouTube와 Google News

- 영상 포맷, 시청자 질문, 보도 후보를 발견하는 데 사용한다.
- YouTube `mostPopular`을 전체 분야의 보편적 트렌드 순위로 취급하지 않는다.
- 뉴스·IT·스포츠 탐지를 한 차트에 의존하지 않는다.
- 랭킹 자체를 사실 인증이나 대중 전체의 의견으로 해석하지 않는다.

### 12.6 Provider capability와 개인정보 최소화

각 provider adapter는 endpoint, API version, auth 방식, OAuth scope, quota/tier, 지역·시간 창 지원, 허용 보존 기간, 표시·인용 권한, terms version, policy 확인 시각을 capability matrix로 선언한다. signal manifest에는 다음을 기록한다.

| Provider | v1 접근 | 인증·권한 | Fail-closed 조건 |
|---|---|---|---|
| Google Trends | Trending Now RSS/CSV 또는 사람이 보존한 공식 export | 공개 기능, region/window 고정 | export provenance나 query mode 불명 |
| X | `/2/trends/by/woeid/:id`, recent search/counts | 승인 app, Bearer token, 사용 tier 확인 | 권한·quota·지역 trends·삭제 준수 수단 부재 |
| Reddit Pro | 사람 운영자의 내부 발견 snapshot | Reddit Pro 접근, 외부 공개 금지 | 영어 공개 SFW 범위 밖 또는 게시·다운로드 필요 |
| Reddit API | 승인된 공식 API adapter | 승인 app/Devvit 및 허용 scope | 접근 승인·보존 권한 부재 |
| Threads | `/keyword_search` TOP/RECENT | `threads_basic`, `threads_keyword_search` | scope·App Review·quota 부재 |
| YouTube | Data API `search.list`, `videos.list` | API project/key 또는 필요한 OAuth | quota 소진·약관 버전 만료 |
| Google News | 공식 검색 화면을 통한 사람 발견과 원문 링크 | 자동 수집 계약 없음 | 자동 대량 수집이 필요하면 v1에서 미지원 |

v1 required provider set은 offline fixture, Google Trends 공식 RSS/사람이 보존한 export, 사람이 확인한 Google News 링크다. X·Threads·Reddit·YouTube는 optional provider이며 capability가 없을 때 `OPTIONAL_PROVIDER_UNAVAILABLE`을 기록하고 v1 discovery를 계속할 수 있다. 다만 특정 후보가 optional provider 신호에만 의존하면 해당 후보는 제작하지 않는다.

`api_name`, `api_version`, `oauth_scopes`, `terms_version`, `policy_checked_at`, `collector_identity`, `capability_result`

필수 capability가 없거나 정책 확인이 만료되면 `SOURCE_UNAVAILABLE`로 fail-closed 한다. 비공식 scraper나 다른 사용자의 로그인 세션으로 우회하지 않는다.

다음 행위를 금지한다.

- 개인별 sentiment profile 생성
- 건강·정치·종교 등 민감 속성 추론
- 여러 플랫폼 계정의 동일인 연결
- 사용자 위치 추적
- 발견 목적을 넘는 원문·식별자 장기 보관

signal store에는 주제 발견에 필요한 집계값과 최소 source ID만 남긴다.

소셜 신호를 대본에 언급할 때는 다음 형태만 허용한다.

> 9월 1일 오전 10시 기준, X 한국 지역 트렌드에 이 키워드가 올랐습니다.

다음 표현은 정량 근거와 범위가 없으면 금지한다.

- 전 세계가 분노했다.
- 모두가 놀랐다.
- 온라인 여론은 이렇다.
- Reddit이 인정했다.

## 13. 후보 수집, 클러스터링, 점수

### 13.1 수집 흐름

1. v1에서는 24시간·7일 창으로 플랫폼별 신호를 수집한다. 4시간 창은 v1.1로 연기한다.
2. 동일 사건, 인물, 제품, 작품을 하나의 event cluster로 병합하며 cluster key는 event_fingerprint 하나로 둔다. 지역·window는 관측 속성이다.
3. `origin_cluster_id`, `crosspost_parent_id`로 동일 원글의 플랫폼 간 재게시와 신디케이트 기사를 중복 제거한다.
4. 근거 준비도 25점을 제외한 `discovery_score` 75점을 계산한다.
5. discovery score 40/75 이상 후보에 lightweight source probe를 수행한다.
6. 원문·독립 검증·식별 가능성으로 `evidence_readiness_score` 25점을 계산한다.
7. 두 점수를 합친 final score와 위험 게이트를 적용한다.
8. 상위 후보마다 “사람들이 정확히 무엇을 놀라워하는가?”라는 중심 질문 하나를 고정한다.
9. 최종 통과 후보만 research packet으로 승격한다.

서로 다른 플랫폼에 존재해도 동일 원글에서 파생됐으면 독립 신호 하나로 계산한다. 봇·조작·조율 정황이 있는 cluster는 단순 감점하지 않고 `QUARANTINED`로 두며 해소 전 제작하지 않는다.

### 13.2 100점 점수표

| 항목 | 점수 |
|---|---:|
| 확산 속도 | 10 |
| 2개 이상 플랫폼의 독립 동시성 | 10 |
| 검색 관심 증가 | 5 |
| 예상 밖의 사실·반전 | 10 |
| 한 문장으로 설명되는 중심 질문 | 8 |
| 충분한 설명 깊이 | 8 |
| 72시간 이후에도 남는 가치 | 4 |
| 1차 자료 준비도 | 10 |
| 독립 검증 준비도 | 10 |
| 인물·날짜·상태 식별 가능성 | 5 |
| 쉽게 설명 가능 | 8 |
| 권리 안전한 시각화 가능성 | 6 |
| 한국 시청자 관련성 | 6 |

감점으로 위험을 희석하지 않는다. 아래 조건은 점수와 무관한 차단 또는 보류다.

- 조작·조율 정황: QUARANTINED
- 실명 의혹·사생활·미성년자·재난·사망·범죄 피해: §16 고위험 게이트
- 권리 불명확·출처 없는 캡처·삭제 원글: source gate FAIL
- REALTIME·FAST freshness: v1 DEFERRED_FRESHNESS

판정:

- discovery score 40/75 미만: source probe 없이 폐기 또는 watchlist
- final score 70~100점이며 evidence readiness 18/25 이상: 제작 후보
- 50~69점: `WATCHLIST`, 제작 금지
- 0~49점: 폐기
- 점수와 무관하게 고위험·권리·provider·freshness 게이트 실패 시 제작 금지

## 14. Research packet과 claim ledger

### 14.1 Claim 상태

| 상태 | 의미 | 대본 사용 |
|---|---|---|
| `CONFIRMED` | 원문과 독립 검증이 일치 | 단정 가능 |
| `PRIMARY_ONLY` | 직접 원문은 있으나 독립 확인 전 | 귀속된 비핵심 자기 발표에만 사용 |
| `DISPUTED` | 신뢰 가능한 소스끼리 충돌 | 정확히 귀속하고 evidence weight에 비례해 설명 |
| `UNVERIFIED` | 소셜 주장만 있거나 증거 부족 | 사실·결론 사용 금지; 승인된 루머 해설에서만 미확인으로 소개 |
| `FALSE` | 충분한 근거로 반박됨 | 허위 주장 해설 목적에서만 사용 |
| `OUTDATED` | 후속 상황으로 변경됨 | 최신 상태와 변경 시각을 함께 설명 |
| `CORRECTED` | 원소스 또는 보도가 정정됨 | 이전·현재 내용을 함께 표시 |
| `RETRACTED` | 주장 주체가 명시적으로 철회함 | 철회 과정 해설에서만 예외 승인 후 사용 |
| `LEGAL_REVIEW` | 명예·사생활·범죄 혐의 위험 | 사람 승인 전 발행 차단 |

소스의 기술적 상태는 claim 상태와 분리한다.

`source_state = active|edited|deleted|private|unavailable`

게시물 삭제는 허위 인정이나 주장 철회를 뜻하지 않는다. `deleted`만으로 claim을 `FALSE` 또는 `RETRACTED`로 바꿀 수 없다.

`UNVERIFIED`는 `reported_claim` 또는 `allegation`, `claim_criticality != core`, 명확한 귀속, `usage_context = rumor_explanation`, editor approval을 모두 갖춘 경우 본문에서만 소개할 수 있다. 제목, 썸네일, 도입 결론, 최종 결론에서는 금지한다. `RETRACTED` 과정을 다루려면 `withdrawal_exception_id`, 공익성 판단, 편집·법률 승인과 승인된 script hash가 필요하다. 미승인 `LEGAL_REVIEW`는 모든 노출면에서 빌드를 차단한다.

### 14.2 필수 데이터

```text
topic_signal:
  signal_id, platform, query, region, window, query_mode,
  first_seen_at_utc, observed_at_utc, rank_or_volume,
  velocity, canonical_url, discovery_only,
  origin_cluster_id, crosspost_parent_id, coordination_risk,
  source_state, retention_class

claim_ledger:
  claim_id, exact_claim, sentence_type, status,
  claim_criticality, usage_context,
  event_at_utc, published_at_utc, updated_at_utc,
  captured_at_utc, freshness_deadline_utc,
  primary_source_ids, independent_source_ids,
  contradicting_source_ids, corroboration_group_ids,
  evidence_relations, evidence_weights,
  attribution, person_risk, rights_status, source_states,
  editor_approval_id, legal_approval_id, withdrawal_exception_id,
  reviewed_at_utc, reviewer_id, expires_at_utc

correction_log:
  correction_id, discovered_at_utc, affected_claim_ids,
  old_text, corrected_text, reason, action,
  source_ids, approved_by, published_at_utc
```

## 15. 최신성 및 정정 SLA

`freshness_class`별 기본 max age를 사용한다.

| Class | 기본 max age | 예시 |
|---|---:|---|
| `REALTIME` | 30분 | v1 deferred: 경기 점수, 선거 개표, 주가, 당일 일정 |
| `FAST` | 2시간 | v1 deferred: 진행 중인 속보, 수사·법원 상태, 긴급 서비스 장애 |
| `DAILY` | 24시간 | 기업·제작사·구단 발표, 제품 릴리스 |
| `STABLE` | 90일 | 정적 정의, 확정된 과거 배경, 장기 정책 설명 |

v1 후보와 release는 `DAILY` 또는 `STABLE`만 허용한다. `REALTIME`·`FAST` claim이 하나라도 있으면 v1에서 `DEFERRED_FRESHNESS`로 차단한다.

release manifest는 claim별 `last_verified_at_utc`, `max_age_seconds`, `verification_result`를 고정한다. 소스가 더 짧은 만료 시간을 제시하면 더 엄격한 값을 사용한다.

| 시점 | 규칙 |
|---|---|
| 최초 수집 | event/published/updated/observed 시각, URL, 작성자 유형, 지역 저장 |
| 기획 승인 | 각 claim의 freshness class 안에서 원문 재확인 |
| 대본 잠금 | 모든 동적 claim이 max age 안인지 검사 |
| 업로드 직전 | `REALTIME`과 `FAST` claim 재검증 |
| 발행 후 | 첫 6시간 집중 모니터링, 24시간·72시간 재확인 |
| `CRITICAL` 오류 | 30분 내 공개 중단 판단, 2시간 내 비공개·재편집·수정본 결정 |
| `MATERIAL` 오류 | 2시간 내 영향 평가, 6시간 내 관련 노출면 정정 |
| `MINOR` 오류 | 6시간 내 설명란·고정 댓글·자막 정정 |
| 반론 접수 | 2시간 내 수신 기록, 24시간 내 반영 여부 결정 |
| 원소스 상태 변경 | 1시간 내 `source_state` 갱신 및 claim 영향 평가 |

정정 대상은 제목, 썸네일, 설명, 고정 댓글, 자막, 번역 자막, 파생 Shorts, 커뮤니티 글, publication manifest를 포함한다. 제목·썸네일 오류는 설명란 정정만으로 끝내지 않는다. YouTube는 기존 영상 파일 교체가 불가능하므로 핵심 결론이 틀린 `CRITICAL` 오류는 원본 비공개 또는 삭제, 수정본 재업로드, 이전·수정 URL 상태와 상호 링크 기록을 기본으로 한다.

freshness deadline을 넘긴 research packet은 자동 승인되지 않으며 재조회와 재승인이 필요하다.

### 15.1 소셜 데이터 보존과 삭제 준수

- raw 소셜 본문, 캡처, 임베딩은 signal manifest에 직접 넣지 않는다.
- 제작 후보가 아닌 signal raw cache는 provider 약관이 허용하는 범위 안에서 기본 7일 이내 폐기한다.
- X 삭제·비공개·정지·수정 이벤트는 최대 24시간 안에 snapshot, screenshot, cache, render, embedding, 백업 파생본에 반영한다.
- v1은 보유 source ID를 주기적으로 lookup/polling해 삭제 준수를 확인한다. X Compliance Stream은 optional provider이며 v1 required dependency가 아니다.
- Reddit과 Threads도 각 provider 정책과 승인 목적을 넘겨 보관하지 않는다.
- 삭제 대상에는 짧은 글을 재식별할 수 있는 content hash도 포함한다.
- 삭제 후에는 `source_id`, 삭제 이벤트, 처리 시각, 처리 결과만 가진 최소 compliance tombstone을 별도 보존한다.
- 이미 게시된 영상에 삭제 콘텐츠가 포함됐다면 공익성, 인용 필요성, provider 정책을 재검토하고 편집·비공개·삭제 action manifest를 생성한다.

## 16. 고위험·존엄·법적 게이트

| 위험 | 필수 조건 |
|---|---|
| 범죄·성폭력·학폭·약물 등 실명 의혹 | 공식 절차 상태, 원문 1개, 독립 확인 2개, 합리적 반론 기회, 사람·법률 승인 |
| 열애·이혼·건강·가족·비공개 메시지 | 당사자 또는 공식 대리인의 공개 확인 없으면 제외 |
| 미성년자 | 기본 비식별화, 학교·주소·개인 계정·가족정보 금지 |
| 자살·재난·사망·테러 | 속보 경쟁 금지, 비선정적 제목·썸네일, 피해 장면 최소화, 광고 적합성 검토 |
| 정치·선거 | 관할 선거기관 원문, 정확한 시각·절차, 반대 자료, 게시 직전 재검증 |
| 금융·의료·법률 | 공식 공시·규제기관·논문·지침, 행동 권유 금지, 전문가 검토 |
| 유출물·해킹 자료 | 원문 파일 재배포 금지, 공익성과 합법적 보도 검토 |
| 영화·드라마 | 제목·썸네일·도입부 스포일러 라벨과 범위 표시 |
| 실존 인물 AI 재연 | 오인 가능 장면 금지 또는 명확한 재연 표시와 플랫폼 공개 |

인물 관련 반론 요청은 기본 24시간의 응답 창을 제공한다. 긴급한 공익 사안도 최소 6시간을 보장하며 보낸 질문 전문, 연락 수단, 수신 확인, 답변 마감, 회신 상태를 보존한다. “답변 없음”은 실제 응답 창이 종료된 뒤에만 표기한다.

`legal_approval_id`는 검토자 자격, 관할, 검토 범위, 만료 시각, 승인된 정확한 제목·썸네일·대본 hash에 결속한다. 법률·편집 승인 레코드는 `public_interest`, `necessity`, `proportionality`, `privacy_intrusion`, `reasonable_verification`, `right_of_reply`, `public_figure_status`를 포함한다.

사실이라는 이유만으로 인물 관련 콘텐츠가 자동 승인되지는 않는다. 공익성, 특정 가능성, 사생활 침해, 피해 규모를 별도 심사한다. 이는 법률 자문을 대체하지 않는다.

## 17. 저작권·재사용·AI 공개

- 타 플랫폼 영상 모음, 영화·드라마 장면 모음, 스포츠 하이라이트 재편집을 영상의 본체로 만들지 않는다.
- 모든 제3자 자산은 `rights_basis = OWNED|LICENSED|PUBLIC_DOMAIN|CC|STATUTORY_EXCEPTION|EMBED_ONLY` 중 하나를 가져야 한다.
- `LICENSED`일 때만 `license_id`, 권리자, 허용 범위, 상업 이용 여부, 만료일이 필수다.
- `STATUTORY_EXCEPTION`은 관할법, 이용 목적, 정확한 분량·초수, 변형성, 시장 대체 여부, 법률 승인 ID를 요구한다.
- 비평·보도 목적이어도 필요한 최소 분량만 사용한다.
- 출처 표시나 “공정 이용” 문구만으로 권리 승인을 대체하지 않는다.
- 영상의 주된 가치는 자체 설명, 분석, 시각화, 독창적 서사여야 한다.
- 실제 인물·장소·사건을 현실적으로 바꾸거나 존재하지 않은 현실 장면을 만든 AI 콘텐츠는 `ai_disclosure_required: true`로 기록하고 YouTube Studio 공개값을 설정한다.
- 실제 인물이 체포, 범죄, 불륜, 질병 등을 겪는 것처럼 보이는 AI 재연은 원칙적으로 금지한다.
- AI 생성 음악과 실제 타인의 목소리를 현실적으로 복제한 음성도 공개 검토 대상이다. 실존 인물 음성 복제는 명시적 권리와 편집·법률 승인이 없으면 금지한다.
- 비현실적 도식·일러스트 재연은 화면에 `AI 재연` 또는 `설명용 이미지`를 표시한다.
- 실제 사건 footage는 권리 승인과 별개로 `footage_event_at`, `location`, `original_uploader`, `provenance_status`, `misattribution_check`를 통과해야 한다. 과거·타지역 영상을 현재 사건처럼 제시하지 않는다.

자산별 rights record:

```text
asset_id
rights_basis
asset_license_id
rights_owner
commercial_use_allowed
rights_expires_at_utc
jurisdiction
statutory_exception_analysis
legal_approval_id
footage_event_at
location
original_uploader
provenance_status
misattribution_check
```

release 단위 AI disclosure record:

```text
ai_disclosure_required
ai_disclosure_reason
ai_media_type: image|video|music|voice
real_person_or_event
studio_value: YES|NO
studio_submitted_at_utc
youtube_video_id
```

자산 권리 만료는 해당 자산과 그 downstream render/release만 stale 처리한다.

## 18. 제목과 썸네일 계약

### 18.1 제목 공식

- `[사건]이 커진 24시간, 원문부터 정리`
- `[제품/작품] 논란, 확인된 사실은 3가지`
- `Reddit에서 시작된 [논쟁], 실제 쟁점은 무엇인가`
- `[인물/팀] 발표 뒤 반응이 갈린 이유`

제목은 `대상 + 실제 변화 또는 질문 + 범위`를 드러내야 한다. 영상이 답하지 못하는 질문은 제목에 사용하지 않는다.

다음 표현은 근거 유무와 관계없이 절대 금지한다.

- 전 세계가 난리
- 모두가 충격
- 미쳤다
- 소름
- 완전히 끝났다
- 삭제되기 전에
- 언론이 숨긴
- 본문이 밝히지 못하는 `진짜 이유`

다음 표현은 정확한 범위와 source ID가 있을 때만 조건부 허용한다.

- 최초
- 역대 최고·최저
- 확정
- 숫자 순위
- 특정 플랫폼에서 폭발·급증

`100% 확정`, `역대급`처럼 범위가 불명확한 표현은 사용하지 않는다.

루머는 제목에서 사실처럼 단정하지 않고 `주장`, `루머`, `확인 전`을 표시한다.

### 18.2 썸네일

- 문구는 최대 2행, 공백 포함 14자 이내로 제한한다.
- 제목은 사실을, 썸네일은 긴장이나 질문을 담당한다.
- 당사자의 표정을 합성·과장하지 않는다.
- 모든 인물, 제품, 숫자는 영상 핵심 내용에 직접 등장해야 한다.
- 존재하지 않는 게시물, 알림창, 삭제 표시, 순위표를 만들지 않는다.
- `충격`, `경악`, `발칵`, `초토화`를 기본 문구로 쓰지 않는다.
- 320×180 축소 상태에서 주 피사체와 문구를 식별할 수 있어야 한다.
- 제목·썸네일의 검증 가능한 주장도 source ID와 연결한다.
- 제목과 썸네일만 본 독립 검수자가 영상의 대상과 중심 질문을 정확히 설명해야 한다.

## 19. End-to-end 제작 흐름

```text
offline fixture·Google Trends 공식 export/RSS·사람이 확인한 Google News 원문 링크 수집
  -> event cluster 병합·중복 제거
  -> topic score 및 위험 사전 분류
  -> 중심 질문 확정
  -> source snapshot + claim ledger
  -> pre-outline research eligibility gate
  -> outline 생성
  -> trend verified script 생성
  -> 문장별 fact/persona/editorial/legal 승인
  -> script/claim/profile bundle hash 잠금
  -> SuperTonic3 M2 warm 합성
  -> 실제 오디오 기반 문장·샷 타이밍 측정
  -> visual brief 및 신규/권리 안전 자산 생성
  -> visual/rights/AI disclosure 승인
  -> motion·자막·render
  -> title/thumbnail claim gate
  -> 최신성 재조회
  -> nollam_file_postflight
  -> render/release 승인
  -> 6h/24h/72h 정정 모니터링
```

각 단계는 앞 단계의 manifest와 SHA-256을 입력으로 받는다. 입력이 변경되면 승인과 downstream 산출물을 자동 stale 처리한다.

v1은 외부 플랫폼을 자동 수정하거나 자동 게시하지 않는다. release 전 `studio_disclosure_manifest`, 오류·삭제·반론 발생 시 `correction_action_manifest`를 서명해 생성하고 지정된 사람 운영자가 YouTube Studio에서 수행한다. publication manifest는 게시 담당자, 모니터 담당자, 6h/24h/72h 확인 시각, 이의 제기 연락 경로를 가져야 한다. 해당 시간대 모니터 담당자가 없으면 공개 승인을 차단한다.

v1 구현은 기존 라이브 HA v5/v6의 정본 순서를 참고하되 그 DAG에 연결하지 않는다. 재사용 가능한 단계는 `build_sentence_audio_master.py`의 실제 TTS와 `plan_narration_shots.py`의 오디오 기반 타이밍뿐이며, nollam job이 voice lock을 명시 인자로 전달한다. 기존 docu-* 스킬, 쉽선비 overlay, 레거시 `postflight_release.py`는 사용하지 않는다. 상태 라벨·출처 카드는 overlay_event_manifest로 합성하고 nollam 전용 postflight에서 검증한다.

## 20. 신규 계약과 설정

다음 파일을 구현 단계에서 추가한다.

- `human_archive/config/nollam_file_editorial_policy.yaml` — `nollam_trend_v1`
- `human_archive/config/nollam_file_narration_policy.yaml` — `nollam_file_narration_v1`
- `human_archive/config/nollam_file_visual_policy.yaml` — `nollam_file_visual_v1`
- `human_archive/config/trend_research_policy.yaml` — `trend_verified_v1`
- `human_archive/config/trend_publication_policy.yaml` — `trend_safe_release_v1`
- `human_archive/config/trend_source_providers.yaml`
- `human_archive/config/delivery_profiles.yaml` 내 `trend_short_75s`, `trend_explainer_8m`, `trend_reaction_5m`, `trend_factcheck_4m`
- `human_archive/schemas/nollam_file_editorial_policy_v1.schema.json`
- `human_archive/schemas/nollam_file_narration_policy_v1.schema.json`
- `human_archive/schemas/nollam_file_visual_policy_v1.schema.json`
- `human_archive/schemas/trend_research_policy_v1.schema.json`
- `human_archive/schemas/trend_publication_policy_v1.schema.json`
- `human_archive/schemas/trend_source_providers_v1.schema.json`
- `human_archive/schemas/resolved_profile_bundle_v1.schema.json`
- `human_archive/schemas/trend_job_contract_v1.schema.json`
- `human_archive/schemas/trend_signal_manifest_v1.schema.json`
- `human_archive/schemas/trend_topic_candidate_v1.schema.json`
- `human_archive/schemas/trend_research_packet_v1.schema.json`
- `human_archive/schemas/trend_verified_script_v1.schema.json`
- `human_archive/schemas/overlay_event_manifest_v1.schema.json`
- `human_archive/schemas/correction_action_manifest_v1.schema.json`
- `human_archive/schemas/studio_disclosure_manifest_v1.schema.json`

권장 모듈:

- `human_archive/scripts/lib/trend_sources.py`
- `human_archive/scripts/lib/trend_clustering.py`
- `human_archive/scripts/lib/trend_selection.py`
- `human_archive/scripts/lib/trend_fact_gate.py`
- `human_archive/scripts/collect_trend_signals.py`
- `human_archive/scripts/generate_trend_topic_candidates.py`
- `human_archive/scripts/compile_trend_research_packet.py`
- `human_archive/scripts/nollam_file_postflight.py`
- `human_archive/templates/nollam_file_outline_prompt.j2`
- `human_archive/templates/nollam_file_script_prompt.j2`

기존 `verified_script_v3` 이름은 HA002 역사 파이프라인이 사용·예약하므로 trend 계약에 재사용하지 않는다.

profile schema version 2는 strict nested validation을 사용하고 schema version 1 legacy profile을 `oneOf`로 읽는다. 새 프로필은 version 2로만 작성한다. 기존 `doodle_seonbi_v1` 참조를 바꾸지 않고 누락된 `doodle_docu_12m` delivery profile을 추가하며, 현재 YAML의 12개 forbidden 항목을 정본으로 삼아 오래된 7개 exact-list 테스트를 수정한다. 이 Phase 0은 놀람파일 구현과 별도 릴리스이며, 현재 운영 정본 host ratio 8~12%를 문서화하고 HA002 quick_3m override와 충돌하지 않게 한다. 놀람파일 계획은 HA002의 `standard_docu`/`quick_3m` 결정이나 기존 결과물을 대체하지 않는다.

trend topic 저장소는 `human_archive/db/trend_topics.sqlite3`에 두고 역사 전용 topic DB와 분리한다. 상태는 `DISCOVERED|WATCHLIST|QUARANTINED|RESERVED|APPROVED|EXPIRED|REJECTED|PUBLISHED`이며 event_fingerprint를 cluster 유일 키로 사용하고 지역·window는 observation 속성으로 저장한다. run root는 `human_archive/runs/nollam_file/<YYYY-MM-DD>/<topic_slug>/<run_id>/`를 사용한다. 충분한 공통 패턴이 확인되기 전 `topics.schema.json`을 일반화하지 않는다.

### 20.1 기존 파일 변경 경계

- `human_archive/config/channel_profiles.yaml`: schema version 2와 `nollam_file_v1` opt-in 추가
- `human_archive/schemas/channel_profile.schema.json`: legacy v1 + strict v2 `oneOf`
- `human_archive/config/delivery_profiles.yaml`: 누락된 legacy profile 및 네 trend delivery profile 추가
- `human_archive/scripts/lib/channel_profiles.py`: trend envelope 안에서만 참조 resolve와 bundle 생성. 기존 HA v5/v6 production binding은 변경하지 않음
- `human_archive/tests/test_channel_profiles.py`: 현재 12개 forbidden 목록과 strict reference 회귀 테스트
- `CLAUDE.md`, `manual.md`, `human_archive/README.md`: 새 opt-in 프로필, 공식 경로, M2 job lock, 운영·정정 절차만 추가한다. 기존 문서의 unrelated drift는 이 작업 범위에서 수정하지 않는다.

다음 기존 파일은 놀람파일 v1에서 수정하지 않는다: `artifact_lineage.py`, `generate_verified_script.py`, `persona_validation.py`, `compile_shot_contract.py`, `postflight_release.py`. trend 전용 postflight와 신규 trend script contract를 사용한다.

기존 쉽선비 결과를 바꾸는 migration은 허용하지 않는다. 공통 loader와 lineage 변경은 legacy fixture가 byte-equivalent 또는 명시적으로 승인된 normalized-equivalent임을 입증해야 한다.

### 20.2 v1 스키마 최소 필드

| 스키마 | v1 필수 필드 |
|---|---|
| `trend_job_contract_v1` | `schema_version`, `job_id`, `profile_id`, `profile_bundle_sha256`, `format_id=nollam_file_long`, `freshness_class`, `run_root`, `source_provider_ids` |
| `trend_signal_manifest_v1` | `signal_id`, `platform`, `canonical_url_or_provider_id`, `observed_at_utc`, `region`, `window`, `event_fingerprint`, `source_state`, `discovery_role=DISCOVERY_ONLY`, `retention_class` |
| `trend_topic_candidate_v1` | `candidate_id`, `event_fingerprint`, `discovery_score`, `evidence_readiness_score`, `final_score`, `status`, `center_question`, `freshness_class` |
| `trend_research_packet_v1` | `packet_id`, `candidate_id`, `claims`, `source_snapshots`, `claim_ledger`, `risk_gate`, `freshness_deadline_utc`, `profile_bundle_sha256` |
| `trend_verified_script_v1` | `script_id`, `job_id`, `format_id`, `sentences`, `claim_ids`, `persona_id`, `voice_lock_id`, `script_hash` |

신규 trend envelope에만 위 필드를 required로 둔다. 기존 HA v5/v6 artifact schema의 required 목록에는 추가하지 않는다.

## 21. 실패 처리

다음 조건은 명시적 `FAIL`이며 자동 우회하지 않는다.

- unknown profile 또는 참조 policy ID
- 기본 프로필이 둘 이상이거나 없음
- evidence snapshot의 URL, capture time, 허용된 integrity metadata 누락
- 동일 원출처를 독립 근거로 중복 계산
- 단일 소셜 게시물만으로 외부 사실 claim 확정
- stale research packet
- core·제목·썸네일·결론의 `UNVERIFIED`, 예외 승인 없는 `RETRACTED`, 미승인 `LEGAL_REVIEW` claim 사용
- 삭제를 철회 또는 허위 인정으로 자동 판정
- 대본보다 강한 제목·썸네일 주장
- `rights_basis` 또는 필수 권리 정보가 없는 제3자 자산
- provenance를 확인하지 못한 실제 사건 footage
- AI 공개 필요 상태와 Studio 값 불일치
- narrator track의 M2 warm 외 음성 또는 fallback 음성
- `profile_bundle_sha256`가 downstream manifest와 불일치
- required provider capability·권한 부재 또는 만료된 policy check
- optional provider 부재를 scraper fallback으로 우회하거나 optional 신호만으로 후보를 승격
- 비공개·보호 계정 콘텐츠 또는 금지된 개인 프로파일링

실패 메시지는 단계, 대상 ID, 누락 필드, 기대 상태, 재시도 방법을 포함해야 한다.

## 22. 테스트 전략

### 22.1 Positive fixtures

- 공식 경기 결과 + 리그 원문 + 독립 스포츠 보도
- 공개 제품 발표 + 공식 릴리스 노트 + 독립 기술 분석
- 제작사 공개 발표 + 작품 공식 정보 + 독립 엔터테인먼트 보도

### 22.2 Negative fixtures

- 단일 X 계정 루머
- 삭제된 Threads 게시물 재업로드 캡처
- freshness deadline이 지난 research packet
- 같은 통신사 기사를 세 출처로 오인한 후보
- 사실 claim보다 강한 제목
- 출처 표시 없는 커뮤니티 반응 일반화
- 권리 불명확 영화·스포츠 클립
- 실존 인물에 대한 미표시 AI 재연
- 프로필 해시 변경 후 과거 승인 재사용
- M2 합성 실패 후 다른 보이스 자동 대체
- 게시물 삭제를 claim 철회로 자동 판정
- 서로 다른 플랫폼의 동일 원글을 독립 신호로 가산
- provider 권한 부재 시 scraper fallback
- 비공개 계정·Reddit Pro 화면·타인 게시물 직접 인용
- 정정이 제목·자막·파생 Shorts에 전파되지 않은 action manifest

### 22.3 테스트 계층

- strict profile schema unit test
- source role 및 corroboration group unit test
- event clustering·중복 제거 test
- topic score·expiry test
- claim gate·title escalation test
- narration persona·forbidden phrase test
- resolved profile bundle hash cascade test
- rights·AI disclosure test
- correction lifecycle test
- source state와 claim status 분리 test
- provider capability 및 retention compliance test
- format별 delivery·timing gate test
- accessibility·thumbnail scope-match test
- 대표 3편 end-to-end dry run

## 23. 파일럿과 측정

첫 파일럿은 고위험 사생활 이슈를 피하고 최소 세 카테고리로 구성한다.

1. IT·테크: 공식 제품·정책 변화
2. 영화·드라마·연예: 공식 발표가 있고 스포일러를 통제할 수 있는 이슈
3. 스포츠: 공식 경기 결과, 규칙, 판정 또는 구단 발표

Offline/private dry run에서 측정할 운영 항목:

- critical fact error 수
- correction 발생 및 처리 시간
- source gate 실패율
- 후보 발견부터 release-ready까지 걸린 시간

수동 공개 파일럿 이후에만 측정할 플랫폼 항목:

- 15초·30초 유지율
- 평균 시청 지속 시간과 완주율
- 제목·썸네일 CTR
- 댓글에서 반복되는 이해 오류
- Shorts에서 long-form으로 이동한 비율

세 편의 private dry run은 기술 검증이며 플랫폼 성과를 증명하지 않는다. 별도 publication approval을 받은 세 편의 수동 공개 파일럿이 끝나기 전 “바이럴 효과”, “성과 개선”을 주장하지 않는다. 공개 baseline을 만든 뒤 카테고리별 목표를 정한다.

## 24. 인수 기준

다음 조건을 모두 만족하면 설계 구현을 완료한 것으로 본다.

1. `default_profile_id == doodle_seonbi_v1`이며 `nollam_file_v1.is_default == false`다.
2. 모든 profile 참조가 실제 존재하고 strict schema version 2를 통과한다.
3. `resolved_profile_bundle_v1`과 `profile_bundle_sha256`이 research부터 release까지 결속된다.
4. channel 또는 참조 policy 변경 시 downstream 승인과 산출물이 stale 처리된다.
5. 소셜 게시물 하나만으로 외부 사실 claim이 통과하지 못한다.
6. 신디케이트·보도자료 복제와 플랫폼 간 crosspost는 하나의 origin/corroboration group으로 계산된다.
7. 모든 signal은 URL 또는 provider ID, 관측 시각, source state, retention class를 가지며 evidence snapshot은 정책이 허용하는 integrity metadata와 freshness deadline을 가진다.
8. factual sentence, 제목, 썸네일 주장이 claim/source ID와 연결된다.
9. sentence type과 claim status가 화면 라벨 매핑표와 정확히 일치한다.
10. 실명 의혹, 사생활, 미성년자, 민감 사건, 권리 위험이 사람 승인 없이 release되지 않는다.
11. v1 활성 포맷 `놀람파일`은 12초 내 사건·질문, 15초 내 보상, 30초 내 기본 맥락을 제공한다. 숏폼·중간 포맷 타이밍은 v1.1 별도 인수 기준이다.
12. 전문용어는 첫 등장 직후 쉬운 설명을 갖고 독립 명료성 검수 평균이 4/5 이상이다.
13. 활성 포맷의 결말이 확정·미확정·다음 확인 포인트를 제공한다.
14. narrator 음성은 SuperTonic3 `M2 warm`, speed `0.95`, `total_step: 10`이며 fallback은 0건이다.
15. 절대 금지 제목 표현, 가짜 UI, 합성 반응, 무관 인물 사용이 0건이고 조건부 표현은 모두 scope/source ID를 가진다.
16. 320×180 축소 검수, 최대 2행·14자, 대비율, 색상 외 라벨·아이콘 기준을 통과한다.
17. 제목·썸네일만 본 독립 검수자가 대상과 중심 질문을 정확히 설명한다.
18. required provider capability가 없으면 `SOURCE_UNAVAILABLE`로 실패하고 optional provider 부재는 scraper fallback 없이 기록된다.
19. 삭제·수정·철회 상태가 분리되고 compliance purge와 tombstone test가 통과한다.
20. positive fixtures는 통과하고 negative fixtures는 모두 차단된다.
21. 서로 다른 세 카테고리의 end-to-end private dry run이 release-ready 상태까지 통과한다.
22. 뉴스·영화·연예·IT·스포츠 5주제 브랜드 일관성, 독립 검수자 3명 평가, 공개 CTR·유지율은 Phase 3 수동 공개 파일럿의 business validation 기준이며 v1 engineering acceptance의 필수 조건이 아니다.

## 25. Rollout

### Phase 0 — 계약 복구

- 현재 profile/delivery/test 불일치를 먼저 가시화하고 수정한다.
- legacy 기본 프로필 결과가 바뀌지 않는 회귀 테스트를 고정한다.

### Phase 1 — Offline dry run

- 저장된 fixture로 신호 수집 이후 모든 단계를 실행한다.
- 실제 게시나 외부 계정 변경은 하지 않는다.

### Phase 2 — 세 카테고리 private dry run

- IT·테크, 엔터테인먼트, 스포츠 각 1편을 비공개 release-ready 상태까지 제작한다.
- provider retention 정책 안에서 source, claim, correction manifest를 보존한다.
- 플랫폼 CTR·유지율 성과를 주장하지 않는다.

### Phase 3 — 수동 공개 파일럿

- 별도 publication approval을 받은 세 편을 사람 운영자가 공개한다.
- analytics snapshot 계약으로 CTR, 유지율, 완주율, 포맷 간 전환을 수집한다.
- 공개 후 6h/24h/72h 모니터 담당자와 정정 action workflow를 실제 검증한다.

### Phase 4 — 제한적 운영

- 1일 최대 1개 long-form research packet만 승인한다.
- 위험 주제는 계속 사람·법률 승인 대상으로 유지한다.

### Phase 5 — 조정

- 공개 파일럿 3편 이상 데이터로 topic score와 narration pacing을 조정한다.
- 정확성 게이트는 성과를 이유로 완화하지 않는다.

## 26. Non-goals와 변경 경계

이번 설계의 non-goal:

- 무인 자동 게시
- 모든 플랫폼의 전체 여론 측정
- 소셜 게시물 대량 보관·재배포
- 연예인 사생활 추적
- 속보 경쟁을 위한 검증 생략
- 영화·스포츠 클립 재편집 채널
- 정치·금융·의료 조언 채널
- 기존 쉽선비·Human Archive 프로필의 시각·대본 정책 변경

다음 변경은 별도 설계 승인이 필요하다.

- `nollam_file_v1`을 기본 프로필로 전환
- M2 warm 음성 잠금 변경
- 자동 게시 활성화
- 고위험 실명 의혹의 무인 승인
- 비공식 스크레이퍼 도입
- 역사 topic DB와 trend store의 통합 migration

## 27. 공식 참고 자료

## 27.1 참조 사례 감사 — 인류의서재 KWL8_AnSp2g

2026-08-31 공개된 `인류의서재` 영상 **「네팔 대홍수가 끝이 아닌 이유. 이제 시작일 뿐입니다. 다음은 20억 명입니다」**를 공개 메타데이터·자동 자막·스토리보드 샘플로 감사했다. 2026-09-01 확인 시점에 길이 30분 34초, 조회수 111,440, 좋아요 725, 댓글 47이었다. 이는 사용자가 말한 “하루 안에 10만 조회” 사례를 공개 수치로 재현한 것이다. 수치는 시간에 따라 변하므로 성과 보장이 아니라 당시 관측치로만 보존한다.

감사에서 놀람파일에 유효하다고 판정한 서사 패턴은 다음이다.

1. 첫 30초에 장소·시간·비정상 수치가 함께 나온다: 맑은 날, 30분 만에 수위 9m, 해발 5,000m에서 내려온 물처럼 시청자가 즉시 장면을 상상할 수 있는 구체성이 있다.
2. “왜 이런 일이 가능한가?”라는 기전 설명으로 첫 호기심을 회수한 뒤, 경고가 있었는데도 피해가 커진 역설을 제시한다.
3. 1963년 이탈리아, 2025년 스위스 등 과거 사례를 단순 나열하지 않고 현재 사건의 설명 변수로 연결한다.
4. 마지막에 네팔 밖의 사람·도시·인프라로 영향 범위를 확장해 개인적 중요성을 만든다.
5. 설명란의 연구자료 목록은 신뢰 보조 장치로 사용하되, 영상 본문은 논문 서지 낭독보다 현상·사람·선택의 흐름을 우선한다.

그대로 복제하면 안 되는 요소도 확인했다. 제목의 `20억 명` 같은 큰 수치는 출처·정의·범위를 확인하지 않으면 과장이고, 이 영상의 조회수 하나만으로 제목 공식이나 성과 인과를 확정할 수 없다. 따라서 Nollam은 `scale_claim`에 산정 범위·기준 시점·직접 출처를 요구하고, 대본보다 강한 제목·썸네일을 차단한다.

참조 사례를 반영한 추가 인수 기준은 다음과 같다.

- 첫 30초에 사건·중심 질문·시청 보상이 각각 한 문장과 한 시각 장치로 존재한다.
- 핵심 숫자는 숫자 카드만 띄우지 않고 장소·원인·비교 기준을 같은 장면에 결속한다.
- 설명 영상의 길이는 고정 8분을 강제하지 않고 evidence budget에 따라 8~30분 후보로 평가하되, v1 렌더 포맷은 계속 `nollam_file_long` 하나로 유지한다.
- 15초·30초·60초·3분·50% 지점의 유지율을 공개 파일럿에서 측정하지만, 단일 참조 영상의 조회수로 성공을 보장하지 않는다.

- [Google Trends Trending now](https://support.google.com/trends/answer/3076011?hl=en-GB)
- [Google Trends 데이터 FAQ](https://support.google.com/trends/answer/4365533?hl=en)
- [Google Trends API alpha 안내](https://developers.google.com/search/blog/2025/07/trends-api)
- [Google Trends API 문서](https://developers.google.com/search/apis/trends)
- [X Trends FAQ](https://help.x.com/en/using-x/x-trending-faqs)
- [X Search Posts](https://docs.x.com/x-api/posts/search/introduction)
- [X Developer Policy](https://docs.x.com/developer-terms/policy)
- [X Compliance Streams](https://docs.x.com/x-api/compliance/streams/introduction)
- [Reddit Pro Trends](https://support.reddithelp.com/hc/en-us/articles/47619216411284-Reddit-Pro-Feature-Trends)
- [Reddit Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy)
- [Reddit Data API Terms](https://redditinc.com/policies/data-api-terms)
- [Meta 공식 Threads API workspace](https://www.postman.com/meta/threads/overview)
- [Threads Keyword Search 요청](https://www.postman.com/meta/threads/request/m9j4i2x/search-for-threads-posts)
- [YouTube Data API videos.list](https://developers.google.com/youtube/v3/docs/videos/list)
- [YouTube API revision history](https://developers.google.com/youtube/v3/revision_history)
- [YouTube 채널 수익 창출 정책](https://support.google.com/youtube/answer/1311392?hl=en)
- [YouTube Fair Use 안내](https://support.google.com/youtube/answer/9783148?hl=en)
- [YouTube GenAI 공개 규칙](https://support.google.com/youtube/answer/14328491?hl=en)
- [YouTube Misinformation 정책](https://support.google.com/youtube/answer/10834785?hl=en)
- [YouTube 광고 친화성·민감 사건](https://support.google.com/youtube/answer/6162278?hl=en)
- [YouTube 괴롭힘·도싱 정책](https://support.google.com/youtube/answer/2802268?hl=en)
- [대한민국 형법 제307조](https://www.law.go.kr/lsLinkCommonInfo.do?chrClsCd=010202&lsJoLnkSeq=1032386799)
- [대한민국 형법 제310조 관련 조문·판례 체계](https://www.law.go.kr/joStmdInfoP.do?joBrNo=00&joNo=0310&lsiSeq=62388)
- [대한민국 민법](https://www.law.go.kr/lsInfoP.do?lsId=001706)
- [대한민국 개인정보 보호법](https://www.law.go.kr/법령/개인정보보호법)
- [대한민국 저작권법](https://www.law.go.kr/법령/저작권법)
- [대한민국 공직선거법](https://www.law.go.kr/법령/공직선거법)

## 28. 대본-영상 매치 우선 계약

놀람파일의 핵심 산출물은 대본과 이미지 목록이 따로 존재하는 것이 아니라, 모든 문장이 어떤 화면으로 어떻게 이해되는지를 고정한 `sentence_visual_alignment_v1`이다. 대본을 먼저 완성한 뒤 장식 이미지를 붙이는 방식은 금지한다.

각 sentence row는 `sentence_id`, 실제 오디오의 `audio_start_ms`/`audio_end_ms`, `semantic_intent`, `claim_ids`, `visual_role`, `asset_id`, `why_this_visual`, `source_basis`, `transition_type`, `coverage_score`를 가져야 한다. 오디오 구간은 예상 글자 수나 silent padding이 아니라 실제 SuperTonic3 산출물에서 측정한다.

| 문장 의도 | 우선 화면 역할 | 금지되는 매치 |
|---|---|---|
| `FACT` | 사건 장면·증거 카드·지도 | 무관한 분위기 풍경 |
| `CAUSAL` | 과정 도식·단면·애니메이션 | 원인 없는 인물 클로즈업 |
| `CONTEXT` | 과거 사례 타임라인·비교 지도 | 연도만 나열하는 슬라이드 |
| `REACTION` | 표본·기간이 표시된 집계 차트 | 가짜 댓글·합성 반응 얼굴 |
| `QUOTE` | 권리 허용 원문 카드 | 출처 없는 캡처 재현 |
| `QUESTION/BRIDGE` | 다음 질문·장소로 이동하는 화면 | 같은 stock image 반복 |

매치 QA는 semantic coverage 0.90 이상, claim-visual mismatch 0, unsupported visual 0, 연속 동일 asset 최대 2회, 숫자·지명 overlay의 source ID 결속을 요구한다. 실행 순서는 `sentence segmentation → M2 TTS → measured audio timeline → alignment rows → visual brief/asset generation → overlay → motion/render → alignment QA`다.
