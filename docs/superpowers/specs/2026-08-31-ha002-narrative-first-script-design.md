# HA002 내러티브 우선 대본 파이프라인 설계

> 작성일: 2026-08-31 (Asia/Seoul)
>
> 대상: Human Archive EP02 장희빈 3분 샘플 및 후속 에피소드 대본 파이프라인
>
> 설계 결정: `사약 난동`은 기록 범위를 벗어나지 않는 콜드오픈 반전으로 짧게 처리한다. 본편은 근거가 동기를 직접 지지할 때만 **“숙종은 왜 세자의 어머니에게 죽음을 명령했는가?”**를 사용하고, 그렇지 않으면 **“어떤 사건과 정치적 판단이 세자 생모의 죽음 명령으로 이어졌는가?”**로 약속을 낮춘다.
>
> 상태: 방향 승인 완료, 교차 검토 반영본, 사용자 문서 검토 대기

## 1. 목적

현재 파이프라인은 사실 연결, 파일 무결성, 페르소나 표현, 시청각 규격은 검사하지만 사건 진행과 호기심 회수는 검사하지 않는다. 그 결과 정확성 절차가 내레이션의 전면에 나오고, 시청자가 기대한 인물·선택·갈등·결과가 사라졌다.

이 설계의 목적은 팩트 검증을 약화하는 것이 아니다. 팩트 검증은 제작 단계의 강한 안전장치로 유지하되, 시청자에게 들리는 대본에서는 증거가 **이야기를 멈추는 강의가 아니라 다음 반전을 여는 장치**로 기능하게 한다.

핵심 원칙은 다음과 같다.

> 사료를 설명하는 채널이 아니라, 사료 때문에 우리가 알던 이야기가 계속 뒤집히는 채널을 만든다.

## 2. 범위

### 2.1 포함 범위

- 중심 질문, 사건 spine, 열린 질문과 payoff, 인과관계, 새 정보 단위를 표현하는 내러티브 계약
- outline 생성과 문장 대본 생성을 분리하는 2단계 생성 흐름
- 사건 진행, 질문 회수, 추상 해설 비중, 의미 반복을 검사하는 내러티브 QA
- 전체본의 앞 문장을 자르는 방식이 아닌 독립적인 3분 sample arc 생성
- 샘플 전용 fact, persona, narrative 보고서 및 승인 해시 결속
- HA002 신규 3분 대본을 소비하는 `sample-3m-v4-001` 빌드 계약
- 현재 문제를 다시 만들지 못하게 하는 회귀 테스트

### 2.2 제외 범위

- `sample-3m-v3-001` MP4 또는 그 내부 자산의 패치
- 인류의서재 고유 문체, 문장 또는 시각 화풍의 복제
- 확정되지 않은 역사 해석을 흥미를 이유로 단정하는 것
- 사용자가 이미 만족한 이미지 화질, M4 음성, 대본-이미지 의미 매칭 방식의 전면 재설계
- 이번 3분 검증 전에 정규 18분 EP02 전체 영상을 다시 생성하는 것

신규 샘플은 기존 이미지와 오디오를 재사용하지 않는다. 최종 승인 대본에서 M4 TTS, 자막, 이미지, 모션을 새로 파생한다. 샷 수는 고정하지 않고 실제 TTS 시간으로 계산한다.

## 3. 감사 결과

### 3.1 현재 샘플의 이야기 단절

감사 대상:

- `human_archive/runs/ep02_jang_huibin/sample-3m-v3-001/source/script_candidate.json`
- `human_archive/runs/ep02_jang_huibin/sample-3m-v3-001/sentence_audio_manifest.json`

| 시점 | 내용 | 판정 |
|---:|---|---|
| 20.98초 | 정사에 사약 난동 기록이 없다고 첫 반전 공개 | 제목의 첫 약속을 이미 회수 |
| 59.22초 | 같은 결론을 다시 설명 | 새 정보 없는 반복 |
| 101.56초 | 숙종이 왜 세자의 어머니를 죽였는지 질문 | 본편이 되어야 할 중심 질문 |
| 108.27초 | 비극이 장옥정의 입궐에서 시작된다고 예고 | 사건 진입 약속 |
| 115.74~167.23초 | 사료의 거리, 기록의 성격, 사료 비판을 11문장 연속 설명 | 51.49초 동안 사건 진행 중단 |
| 167.53초 | 범용 아웃트로 | 중심 질문 미회수 |

현재 영상은 171.565초다. 11문장 방법론 블록만 약 30%를 차지한다. claim이 연결된 네 문장도 모두 `CLM-JH-001`의 난동 기록 부재를 반복하고, `CLM-JH-002`부터 `CLM-JH-007`까지는 샘플의 인과 서사에 사용되지 않았다.

현재 구조는 다음과 같다.

```text
답 공개
→ 같은 답 반복
→ 더 큰 질문
→ 사건 시작을 한 문장으로 예고
→ 사료 방법론 11문장
→ 질문을 풀지 않고 종료
```

### 3.2 인류의서재 벤치마크에서 확인된 문법

근거 문서는 `docs/superpowers/specs/2026-08-27-human-library-top30-script-visual-benchmark.md`다. 공개 장편 상위 30편의 첫 60초에서는 질문 73.3%, 시간·숫자 앵커 76.7%, 상식 뒤집기 63.3%가 관찰되었다. 그러나 질문을 계속 던지는 방식은 아니었다. 대표 흐름은 다음과 같다.

```text
관찰 가능한 사실 또는 통념
→ 시청자가 예상할 설명
→ 그런데/하지만 반전
→ 원인·증거·메커니즘
→ 결과 또는 다음 질문
```

폼페이 영상은 도망칠 시간이 있었다는 모순에서 출발해 빵집 주인의 행동과 발굴된 탄 빵으로 들어간다. 조선 여행 영상은 산길의 공포에서 여러 켤레의 집신과 여행 허가증으로 이동한다. 이스터섬 영상은 자멸 통설을 위성 자료로 흔든 뒤 최초 정착민의 생활로 들어간다. 문서, 유물, 연구 결과는 별도 방법론 강의가 아니라 현재 질문을 바꾸는 구체적 증거다.

### 3.3 프로그램의 구조적 원인

1. `human_archive/config/seonbi_narration_policy.yaml`과 `human_archive/templates/seonbi_script_prompt.j2`는 본문 중심을 “실록/사료 팩트폭격”과 `source_commentary`로 정의한다. 사건 연쇄, 열린 질문, payoff, 인과 결과의 계약은 없다.
2. HA002 v6 확장 계약은 7개 블록에 각각 13문장을 강제하고, 비claim 문장에서 새 사건·행동·연대기를 추가하지 못하게 한다. 분량을 늘릴 수 있는 안전한 선택지가 추상적인 사료 일반론밖에 남지 않는다.
3. 첫 확장 블록은 원래 `HA002-S018`의 입궐 예고와 `HA002-S019`의 장옥정 소개 사이에 삽입되어 자연스러운 인접 사건을 끊는다.
4. `human_archive/schemas/verified_script_v2.schema.json`은 beat, text, fact binding만 표현한다. 중심 질문, 새 정보, 의존 문장, 열린 질문, 회수 지점, 사건 상태 변화는 표현할 수 없다.
5. `human_archive/scripts/compile_context_sample_script.py`는 `audio_rows[:N]`으로 앞 문장을 자르고 아웃트로를 붙인다. 3분 안에 어떤 질문을 열고 어떤 결말까지 갈지는 고려하지 않는다.
6. 현 QA는 시그니처 문구, 문장 길이, claim 연결, exact/normalized 중복과 파일 규격을 주로 검사한다. 고유한 문장 217개가 모두 사건을 진행하지 않아도 통과할 수 있다.
7. 샘플 컴파일러는 전체본의 fact/persona 보고서와 승인을 복사한다. 현재 30문장 샘플에 217문장 평가 보고서가 붙어 있고, 승인 내부의 script SHA도 현재 전체본과 샘플 어느 쪽에도 일치하지 않는다.
8. 기존 `2026-08-27-doodle-seonbi-channel-pipeline-design.md`에는 `hook_contract`, `outline`, `new_information`, `depends_on_sentence_ids`, `opening_echo`가 이미 제안되었지만 스키마와 실행 게이트에는 구현되지 않았다.

### 3.4 사실·출처 무결성 감사

현재 claim inventory를 그대로 새 대본의 승인 근거로 사용할 수 없다.

- `CLM-JH-001`은 “검토한 공식 기록에 난동 장면이 보이지 않는다”는 **범위가 정해진 부정 증거**와 “후대 서사에 그 장면이 등장한다”는 두 명제로 분리해야 한다. 기록 부재만으로 사건이 절대 없었다고 증명하거나 허구라고 단정하지 않는다.
- `CLM-JH-003`, `CLM-JH-006`의 근거 `SRC-AKS-STUDY`는 현재 snapshot에서 저자와 정확한 논문 식별자가 없고, 한 span의 `snapshot_sha256`이 `1B2C3D4E5F6A...` 형태의 placeholder다. 실제 원문과 정상 hash를 확보하기 전에는 두 claim을 **BLOCKED**로 둔다.
- `CLM-JH-007`은 번역문이 `최석항`이라 쓰지만 함께 보관된 한문 `領議政崔錫鼎等力爭`은 `최석정(崔錫鼎)`을 가리킨다. 인물 식별을 정정하고 원문 범위를 재검토하기 전에는 **BLOCKED**다.
- `CLM-JH-004`의 “죽음이 법을 바꿨다”는 표현은 명령 시점, 조문 성격, 직접 인과를 별도로 확인해야 한다. 확인 전에는 “뒤이어 어떤 왕실 규칙이 기록되었는가” 이상으로 말하지 않는다.
- 현재 full-v6, sample script, approval에 서로 다른 script SHA가 묶여 있다. 기존 PASS와 사람 승인은 모두 stale로 취급한다.

재검증 후보로는 실록의 1701년 9월 25일 첫 명령, 9월 27일 신료 반대, 10월 8일 최종 논의 기사를 우선한다. 이 순서는 **연구 가설**일 뿐 아직 승인된 대본 사실이 아니다. source snapshot에 원문·번역·기사 식별자·정상 hash를 새로 고정하고 fact reviewer가 승인한 뒤에만 사용한다.

## 4. 선택한 서사 접근

검토한 선택지는 세 가지였다.

| 접근 | 중심 약속 | 장점 | 한계 |
|---|---|---|---|
| 권력 미스터리 | 숙종은 왜 세자의 어머니를 죽였는가 | 인물의 선택과 결과가 끊기지 않고 기존 claim을 인과적으로 사용할 수 있음 | 정치적 동기와 책임 표현을 재검증해야 함 |
| 악녀 이미지 추적 | 사약 난동 장면은 누가 만들었는가 | 통념 반박이 선명함 | 매체사·사료론 설명으로 다시 이탈할 가능성이 큼 |
| 상승과 추락 전기 | 궁녀에서 중전, 죽음까지 | 이해하기 쉬운 시간 순서 | 백과사전식 생애 요약이 되기 쉬움 |

선택은 **권력 미스터리를 본편으로 하고 악녀 이미지 추적을 콜드오픈과 마지막 echo에만 사용하는 혼합형**이다.

콜드오픈의 정확한 질문은 `정사에서 그 난동 장면이 확인되는가?`다. 답도 “검토한 공식 기록에는 그 장면이 보이지 않는다”까지만 말한다. `사실이 아니었다`, `후대가 완전히 지어냈다`, `실제 최후는 조용했다`로 확대하지 않는다.

그 뒤의 중심 질문은 outline 생성 전에 `promise_answerability` 검사를 거친다.

- 동시대 기록이 행위자의 동기를 직접 말하면 `왜 명령했는가?`를 쓸 수 있다.
- 기록된 정당화나 사건 연쇄만 확인되면 `어떤 사건과 정치적 판단이 명령으로 이어졌는가?`를 쓴다.
- 학술적 해석만 있으면 그 해석을 귀속해 소개하되 중심 질문의 유일한 정답으로 만들지 않는다.
- 어느 수준도 뒷받침하지 못하면 권력 미스터리 구조를 포기하고 검증 가능한 다른 질문을 선택한다.

HA002 pilot은 장옥정의 상승을 1~2문장으로 압축하고, 현재 근거가 약한 숙빈 최씨·영조 곁가지는 제외한다. 재검증을 통과할 경우 `첫 처분 명령 → 신료의 반대와 변화 → 최종 명령 → 기록된 정당화와 결과`가 중심 질문을 좁히는 사건 spine이 된다. 단순 연대기 목록은 허용하지 않는다.

## 5. HA002 3분 story contract

목표 최종 길이는 180초이며 허용 범위는 기존 `quick_3m` 계약의 170~190초다. 문장 수나 글자 수가 아니라 실제 M4 TTS 실측 시간이 권위다.

| 시간 예산 | 기능 | 사건·정보 | 목표 반응 | 후보 claim |
|---:|---|---|---|---|
| 0~15초 | 익숙한 장면 소환 | 사극 속 난동 장면을 `dramatic_reference`로 소환 | “그 장면 알지” | 사실 주장 아님; 화면에도 재연 표기 |
| 15~25초 | 범위가 정해진 첫 반전 | 검토한 공식 기록과 후대 장면의 차이 | “기록에는 그 장면이 없다고?” | 분리·재검증한 `CLM-JH-001` |
| 25~38초 | 중심 질문 | 답변 가능성에 맞춰 `왜` 또는 `무엇이 이어졌는가`를 약속 | “그럼 실제 결정은 어떻게 나왔지?” | `core_answer_contract`로 후속 회수 |
| 38~58초 | 이해관계 압축 | 장옥정의 상승과 세자 생모라는 위치를 1~2문장으로 제시 | “이 결정이 왕실 전체와 연결되는구나” | 신규 또는 재검증된 배경 claim |
| 58~80초 | 구체 사건 | 취선당·통명전 관련 기록에서 확인된 행동만 제시 | “실제 기록의 사건은 이거였구나” | 재검증한 `CLM-JH-005` |
| 80~105초 | 결정의 첫 굴곡 | 첫 명령과 신료의 반대, 명령 변화 | “왕도 한 번에 밀어붙인 게 아니었어?” | 신규 primary claim 필요 |
| 105~132초 | 판단의 압력 | 최종 논의와 contemporaneous statement로 기록된 정당화 | “질투극보다 왕실·세자 문제가 핵심이었나?” | 신규 primary claim 필요 |
| 132~158초 | 중심 질문 회수 | 최종 명령과 근거가 허용하는 범위의 답 | “결정까지의 흐름이 보인다” | 재검증한 `CLM-JH-002` 및 신규 claim |
| 158~180초 | 결과와 opening echo | 뒤이은 왕실 규칙의 정확한 관계와 난동 장면 대비 | “기억된 장면과 기록된 결정은 달랐구나” | 재검증한 `CLM-JH-004`, 의도적 echo |

이 표는 **HA002 pilot의 편집 가설**이지 사실 승인표가 아니다. 특히 `CLM-JH-003`, `CLM-JH-006`, `CLM-JH-007`은 현재 상태로 사용하지 않는다. 각 주장은 최신 source snapshot으로 다시 검증하고, 현재 문구에 대한 fact approval을 얻은 것만 대본에 들어간다. 자료가 “동기”가 아니라 “기록된 정당화”만 지지하면 대본도 그 수준에 머문다. 배경 claim이 부족하면 beat를 축소하며 흥미를 위해 빈칸을 추정으로 채우지 않는다.

### 5.1 공용 계약과 pilot profile의 분리

`quick_3m_common`은 길이, loop 완결, 실제 TTS 기반 비율, artifact 결속처럼 장르와 무관한 불변식만 가진다. 중심 결정, 처분, 법적 결과와 같은 구조는 `power_mystery_v1`에 둔다. 위 시간표와 수치 임계값은 `HA002_power_mystery_pilot_v1`에만 적용한다. 다른 역사 소재로 일반화하기 전, 서로 다른 구조의 최소 두 소재에 대한 이식성 테스트와 threshold 보정을 거친다.

## 6. 데이터 계약

### 6.1 사실 계약과 서사 계약의 분리

팩트 시스템과 서사 시스템은 서로 다른 질문에 답한다.

- `claim_inventory`: 이 말을 해도 되는가.
- `narrative_outline`: 왜 이 정보를 지금 말하는가.
- `script_candidate`: 실제로 무엇을 어떻게 들려주는가.
- `fact_report`: 각 사실 표현이 근거 범위 안에 있는가.
- `narrative_quality_report`: 질문, 사건, 인과, payoff가 작동하는가.

두 보고서가 모두 유효해야 다음 단계로 진행한다. 하나의 PASS가 다른 하나를 대신할 수 없다.

### 6.2 `narrative_outline_v1`

새 outline은 질문 태그만 저장하지 않고 **어떤 수준의 답을 할 수 있는지**, **무엇을 답해야 하는지**, **각 beat가 그 답을 어떻게 좁히는지**를 저장한다. 아래 값은 schema를 설명하기 위한 **재검증 전 후보**다. 실제 artifact는 빈칸이나 일반어를 허용하지 않으며, 정확한 한국어 명제와 claim binding이 채워지고 fact approval을 받아야 `SUPPORTED`가 된다.

```json
{
  "episode_id": "HA002",
  "format_profile": "HA002_power_mystery_pilot_v1",
  "target_duration_sec": 180,
  "fact_contract_sha256": "...",
  "promise_answerability": {
    "status": "PENDING_FACT_REVIEW",
    "answer_mode": "recorded_justification",
    "supported_claim_ids": [],
    "rejected_question": "숙종의 내면적 진짜 동기는 무엇이었는가?",
    "selected_promise": "어떤 사건과 정치적 판단이 세자 생모의 죽음 명령으로 이어졌는가?"
  },
  "core_answer_contract": {
    "required_propositions": [
      {
        "proposition_id": "PROP-CORE-TRIGGER",
        "answer_slot": "trigger_event",
        "meaning": "취선당·통명전 관련 행위가 처분 논의의 기록상 배경으로 등장한다",
        "claim_ids": ["CLM-JH-005"],
        "certainty": "recorded_allegation",
        "attribution_required": true
      },
      {
        "proposition_id": "PROP-CORE-DELIBERATION",
        "answer_slot": "decision_change",
        "meaning": "첫 처분 명령 뒤 신료 반대와 명령 변화가 기록된다",
        "claim_ids": ["CLM-PRIMARY-FIRST-ORDER"],
        "certainty": "documented_order",
        "attribution_required": false
      },
      {
        "proposition_id": "PROP-CORE-JUSTIFICATION",
        "answer_slot": "recorded_justification_content",
        "meaning": "최종 논의의 귀속 발언은 훗날의 당파와 국가·세자 위험을 정당화로 제시한다",
        "claim_ids": ["CLM-PRIMARY-STATEMENT"],
        "certainty": "attributed_statement",
        "attribution_required": true
      },
      {
        "proposition_id": "PROP-CORE-ORDER",
        "answer_slot": "final_order",
        "meaning": "재논의 뒤 최종 처분 명령이 기록된다",
        "claim_ids": ["CLM-JH-002"],
        "certainty": "documented_order",
        "attribution_required": false
      }
    ],
    "typed_edges": [
      {
        "from": "PROP-CORE-TRIGGER",
        "to": "PROP-CORE-DELIBERATION",
        "relation": "recorded_sequence",
        "claim_ids": ["CLM-JH-005", "CLM-PRIMARY-FIRST-ORDER"]
      },
      {
        "from": "PROP-CORE-DELIBERATION",
        "to": "PROP-CORE-JUSTIFICATION",
        "relation": "deliberation_changes_decision_state",
        "claim_ids": ["CLM-PRIMARY-FIRST-ORDER", "CLM-PRIMARY-STATEMENT"]
      },
      {
        "from": "PROP-CORE-JUSTIFICATION",
        "to": "PROP-CORE-ORDER",
        "relation": "recorded_as_justification_for_decision",
        "claim_ids": ["CLM-PRIMARY-STATEMENT", "CLM-JH-002"]
      }
    ],
    "forbidden_shortcuts": ["질투 때문에", "정치 때문", "난동했기 때문에"]
  },
  "hook_answer_contract": {
    "required_propositions": [
      {
        "proposition_id": "PROP-HOOK-OFFICIAL",
        "meaning": "명시한 공식 기록 검토 범위에서는 사약 난동 장면이 확인되지 않는다",
        "epistemic_class": "negative_evidence",
        "claim_ids": ["CLM-JH-001-OFFICIAL"]
      },
      {
        "proposition_id": "PROP-HOOK-LATER",
        "meaning": "그 난동 장면은 귀속을 밝힌 후대 서사에 등장한다",
        "epistemic_class": "later_narrative",
        "claim_ids": ["CLM-JH-001-LATER"]
      }
    ]
  },
  "entity_ledger": [
    {
      "entity_id": "ENT-JANG-OKJEONG",
      "canonical_spoken_name": "장희빈",
      "aliases": ["장옥정"],
      "first_intro_role": "세자의 생모",
      "first_beat_id": "BEAT-03"
    },
    {
      "entity_id": "ENT-SUKJONG",
      "canonical_spoken_name": "숙종",
      "aliases": [],
      "first_intro_role": "처분을 결정한 왕",
      "first_beat_id": "BEAT-03"
    },
    {
      "entity_id": "ENT-MINISTERS",
      "canonical_spoken_name": "대신들",
      "aliases": [],
      "first_intro_role": "첫 처분 명령에 반대한 신료들",
      "first_beat_id": "BEAT-06"
    }
  ],
  "loops": [
    {
      "loop_id": "LOOP-HOOK",
      "question_text": "정사에서 그 난동 장면이 확인되는가?",
      "required": true,
      "open_beat_id": "BEAT-01",
      "resolve_beat_id": "BEAT-02",
      "resolve_deadline_sec": 25,
      "answer_criteria": ["PROP-HOOK-OFFICIAL", "PROP-HOOK-LATER"]
    },
    {
      "loop_id": "LOOP-CORE",
      "question_text": "어떤 사건과 정치적 판단이 죽음 명령으로 이어졌는가?",
      "required": true,
      "open_beat_id": "BEAT-03",
      "resolve_beat_id": "BEAT-08",
      "resolve_deadline_sec": 158,
      "answer_criteria": [
        "PROP-CORE-TRIGGER",
        "PROP-CORE-DELIBERATION",
        "PROP-CORE-JUSTIFICATION",
        "PROP-CORE-ORDER"
      ]
    }
  ],
  "beats": [
    {
      "beat_id": "BEAT-06",
      "order": 6,
      "function": "opposition",
      "duration_budget_sec": 25,
      "entity_ids": ["ENT-SUKJONG", "ENT-MINISTERS"],
      "documented_event": "재검증된 기사에 기록된 신료 반대와 명령 변화",
      "narrative_inference": null,
      "epistemic_class": "documented_order",
      "attribution_required": false,
      "evidence_role": "complicate",
      "progress_type": "pressure_increase",
      "contribution_target": "core_answer",
      "semantic_pattern": "cause_decision_consequence",
      "causal_link_to_core": "최종 명령이 즉흥적 단일 행동이라는 가설을 복잡하게 만든다",
      "state_before": "처분이 한 번에 결정된 것으로 보임",
      "state_after": "반대와 재논의를 거친 결정으로 좁혀짐",
      "new_information": "첫 명령 뒤 반대와 변화가 있었다",
      "claim_ids": ["CLM-PRIMARY-ORDER"],
      "opens_loop_ids": [],
      "resolves_loop_ids": [],
      "depends_on_beat_ids": ["BEAT-05"],
      "spoken_source_reason": null,
      "visual_anchor": "명령문과 반대 상소의 대조",
      "visualization_mode": "symbolic"
    }
  ]
}
```

`answer_mode`는 `explicit_motive`, `recorded_justification`, `attributed_inference`, `multi_causal` 중 하나다. `explicit_motive`가 아니면 내면을 단정하는 `진짜 이유` 표현을 금지한다. production artifact의 네 core answer slot은 모두 구체적인 명제와 승인 claim을 가져야 하며 하나라도 pending이면 중심 loop를 열 수 없다. typed edge도 귀속 claim이 지지하는 관계 이상으로 강해질 수 없다. 단순 선후 관계를 원인으로 바꾸지 않는다.

`function`은 `hook_scene`, `reversal`, `core_question`, `rise`, `event`, `decision`, `opposition`, `payoff`, `consequence`, `closing_echo`처럼 사건 기능을 표현한다. `contribution_target`은 `core_answer`, `hook_loop`, `framing` 중 하나다. `core_answer` beat만 `causal_link_to_core`와 인과 삭제 검사를 요구하고, hook·echo는 `evidence_observation_reframe` 패턴으로 별도 loop 또는 framing에 기여할 수 있다. 기존 `source_commentary`는 필수 beat에서 제거한다.

loop는 ID의 존재만으로 통과하지 않는다. `answer_criteria`의 필수 명제가 실제 payoff 문장 의미에 나타나야 하며, `정치 때문이었다`처럼 `forbidden_shortcuts`만 말한 문장은 resolve 태그가 있어도 실패한다. `resolve_deadline_sec`는 resolve beat의 시작이 아니라 **마지막 필수 answer proposition이 들어 있는 문장의 실제 TTS 종료 시각**이다.

target별 요구 필드는 다음처럼 다르다.

- `core_answer`: `progress_type`, `causal_link_to_core`, factual claim/epistemic binding이 필수이며 삭제 후 core 인과 그래프가 약해져야 한다.
- `hook_loop`: hook proposition과 `evidence_observation_reframe` 연결이 필수다. 최초 극화 장면은 `fact_status: non_factual_reference`, 빈 `claim_ids`, `visualization_mode: dramatic_reference`로 명시하면 claim binding 없이 허용한다.
- `framing`: `framing_purpose`와 연결 loop 또는 closing echo가 필수이며 core 인과 삭제 검사는 적용하지 않는다.

`entity_ledger`는 첫 등장 때 관계와 역할을 한 번 설명하고 이후 하나의 `canonical_spoken_name`을 쓰게 한다. 별칭 변경은 의도와 대상 ID를 명시한다. HA002 pilot은 한 beat의 신규 named entity를 원칙적으로 1명, 최대 2명으로 제한한다.

### 6.3 `verified_script_v3` 문장 계약

기존 `verified_script_v2`에 선택 필드를 덧붙이는 방식은 사용하지 않는다. 선택 필드는 누락돼도 schema validation을 통과해 같은 문제가 반복될 수 있기 때문이다. 다만 HA002 검증 전에 모든 downstream 소비자를 한꺼번에 v3로 바꾸지도 않는다.

- `verified_script_v3.schema.json`은 `sample-3m-v4-001` 신규 경로에만 적용한다.
- 레거시 v2 빌드는 읽기 전용 재현 경로로 유지하고 v3로 자동 승격하지 않는다.
- 기존 TTS·자막·시각 소비자에는 공통 필드만 내보내는 `script_common_projection_v1` adapter 하나를 둔다.
- v4 인수를 통과한 뒤에만 전체 에피소드와 다른 포맷으로 일반화한다.

각 문장은 기존 fact segment 외에 다음 서사 필드를 가진다.

- `narrative_beat_id`
- `sentence_function`: `scene`, `action`, `fact_reveal`, `cause`, `decision`, `consequence`, `bridge`, `payoff`, `echo`
- `content_mode`: `story_progress`, `evidence_reveal`, `methodology`, `reflection`
- `normalized_proposition_id`: 같은 뜻의 문구 변형을 하나로 세기 위한 ID
- `entity_ids`: `entity_ledger`의 대상만 참조
- `intentional_repetition`: 원문 proposition ID와 echo 목적, 또는 `null`

loop, beat dependency, answer criteria는 pilot에서 outline의 beat 수준에 유지한다. sentence schema에 같은 상태 기계를 중복 구현하지 않는다. `additionalProperties: false`와 필수 enum을 사용하며 compiler가 누락 필드를 기본값으로 메우지 않는다. schema validation과 별도로 ID 유일성·순서, 참조 존재, dependency cycle, loop open/resolve 순서, proposition 반복을 semantic validator가 검사한다.

`fact_report`, `persona_report`, `narrative_quality_report`에는 모두 중복 없는 순서 보존 `evaluated_sentence_ids`, `verified_script_sha256`, `narrative_outline_sha256`, `policy_sha256`를 필수로 저장한다. `narrative_quality_report`는 provisional TTS 뒤 생성하며 `tts_manifest_sha256`, 문장별 start/end, content-mode별 실제 발화 시간을 추가로 저장한다. ID 집합만 같고 문장이 바뀐 stale report는 hash mismatch로 실패한다. 사료명은 fact metadata에 존재한다고 자동 낭독하지 않는다. `spoken_source_reason`이 `contradiction_reveal`, `artifact_reveal`, `dispute_qualification` 중 하나일 때만 짧게 말할 수 있다.

### 6.4 사실·해석·연출의 층위

claim과 beat에는 다음 `epistemic_class` 중 하나를 둔다.

- `documented_order`: 문서에 기록된 명령이나 처분
- `contemporaneous_statement`: 당대 인물에게 귀속된 발언·정당화
- `recorded_allegation`: 기록에 실렸지만 진실 여부와 별개인 고발
- `negative_evidence`: 명시한 corpus와 검색 범위에서 찾지 못함
- `later_narrative`: 후대 기록·극화에 등장
- `scholarly_interpretation`: 연구자의 인과 해석

`contemporaneous_statement`, `recorded_allegation`, `later_narrative`, `scholarly_interpretation`은 기본적으로 `attribution_required: true`다. `negative_evidence`는 검토 corpus와 범위를 말해야 하며 비존재 증명으로 승격할 수 없다.

연출도 `literal`, `reconstruction`, `symbolic`, `dramatic_reference`로 구분한다. 기록되지 않은 대면·표정·전달 순간을 사실적인 literal 화면으로 만들지 않는다. 재구성은 화면이나 asset metadata에서 재연임을 드러낸다.

## 7. 생성 흐름

```text
source snapshot + claim inventory
→ story evidence packet
→ narrative_outline_v1 생성
→ deterministic outline QA
→ 문장 대본 생성
→ fact QA + persona QA + pre-TTS narrative structure preflight
→ 사람의 fact 승인
→ projection + provisional M4 문장 TTS 및 실측 시간
→ authoritative narrative quality/timing report
→ audio-first cold-listen
→ 대본 읽기 editorial review + narrative 승인
→ 시간 초과/부족 또는 review 실패 시 새 script revision으로 beat 단위 수정
→ 시각 브리프와 신규 이미지
→ 모션·자막·렌더·postflight
```

### 7.1 Story evidence packet

LLM에 원문 자료 전체와 claim 목록만 던지지 않는다. 먼저 다음을 가진 story packet을 만든다.

- 사건 타임라인
- 인물과 당시 이해관계
- 확인된 행동과 결과
- 행위자가 직접 말한 동기와 기록자가 남긴 정당화의 구분
- 해석이 갈리는 지점
- `epistemic_class`, 귀속 의무, 사용할 수 있는 정확한 표현
- 말할 수 없는 과장과 금지 표현
- 각 사실을 시각화할 수 있는 사람·행동·장소·물건

팩트 검토자는 이 packet의 근거 범위를 판단한다. 그 결과로 `promise_answerability`를 먼저 확정하고, 대본 생성기는 승인 범위 안에서만 질문과 정보 공개 순서를 설계한다. 질문을 먼저 정한 뒤 자료를 억지로 답처럼 붙이지 않는다.

### 7.2 Outline 우선 생성

문장 생성 전에 모든 beat가 중심 질문을 전진시키는지 검사한다. exact 문장 수를 강제하지 않는다. 각 beat는 최소 하나의 상태 변화를 가져야 한다.

- 새로운 사건이 발생한다.
- 새로운 인물이 행동한다.
- 원인이 드러난다.
- 예상이 뒤집힌다.
- 앞 질문이 회수된다.
- 결과가 다음 질문을 만든다.

위 항목이 하나도 없으면 outline 단계에서 제거한다.

상태 변화만으로는 부족하다. `core_answer` beat는 `core_answer_contract`의 어느 명제를 좁히는지 연결해야 한다. 새 날짜나 새 인물을 추가했어도 그 core beat를 삭제한 뒤 인과 그래프와 답이 그대로라면 filler다. `hook_loop` beat는 hook answer를 열거나 좁히거나 회수해야 하고, `framing` beat는 명시한 echo 목적에 기여해야 한다. 증거 역할은 `confirm`, `narrow`, `complicate`, `reverse` 중 하나로 다양화하고, 모든 자료를 억지 반전으로 만들지 않는다.

### 7.3 문장 생성

쉽선비 말투는 양념으로 취급한다. `에헴`, `천만의 말씀`, 현대적 비유, 직접 호명은 필수 개수로 강제하지 않는다. 정보 없는 시그니처 문장이 사건 진입을 늦추면 삭제한다.

문장은 한 문장에 한 주장 또는 한 반전을 원칙으로 한다. 실제 M4 발화의 **중앙값**은 4.5~6초를 pilot 지침으로 삼되 모든 문장을 같은 길이로 맞추지 않는다. 짧은 충격문과 더 긴 맥락문을 섞고, 같은 주어·어미·반전 접속사가 세 문장 이상 반복되면 editorial 경고를 낸다. 최종 길이는 합성 전 추정치가 아니라 실제 TTS로 판정한다.

### 7.4 증거 노출

다음 순서를 기본으로 한다.

```text
사람·행동·상황
→ 질문을 확인·좁힘·복잡화·반전하는 구체적 사실
→ 필요할 때만 짧은 근거 출처
→ 그 사실이 바꾼 선택 또는 다음 질문
```

자세한 사료 비교, 연구 방법, 출처 한계는 description 또는 source card로 이동한다. 단, 불확실성이 결론의 의미를 바꾸는 경우에는 한 문장으로 자격을 명시한다.

## 8. 내러티브 QA

### 8.1 결정적 hard gate와 의미 review gate

v4 pilot에서 재현 가능한 자동 검증과 아직 보정이 필요한 의미 평가를 구분한다. 결정적 hard gate와 사람의 의미 승인을 모두 통과해야 한다.

자동 hard gate:

1. `promise_answerability.status`는 `SUPPORTED`이고 관련 claim과 정확한 질문 문구가 유효한 fact approval에 결속되어야 한다.
2. 모든 required loop에 open/resolve beat, deadline, answer criteria가 있고 참조·순서·기한이 구조적으로 유효해야 한다.
3. 모든 필수 beat는 `contribution_target`을 가지며 target별 필수 필드를 만족해야 한다. `core_answer`에는 `progress_type`, `causal_link_to_core`, factual claim/epistemic binding을 요구한다. `hook_loop`에는 hook proposition과 evidence pattern을, `framing`에는 framing purpose를 요구한다. 명시적 `non_factual_reference` hook만 빈 claim binding을 허용한다.
4. 질문 beat 다음 1~2문장 안에 같은 downstream beat로 연결된 story/evidence 문장이 시작되어야 한다.
5. 동일 `normalized_proposition_id`는 최초 한 번만 허용한다. 명시된 opening/closing echo 한 번은 예외다.
6. script와 fact, persona, narrative report의 `evaluated_sentence_ids`는 중복 없이 순서까지 정확히 같고 모든 입력·보고서 hash가 현재 파일과 일치해야 한다.
7. schema 오류, 누락 필드, unknown version, extra property, stale 또는 cross-scope parent는 fail-closed다.

`HA002_power_mystery_pilot_v1` 자동 hard gate:

1. 콜드오픈의 마지막 필수 hook proposition은 실제 TTS 종료 시각 25초 안에 끝나고, 중심 질문은 38초 안에 나온다.
2. `core_answer_contract`의 마지막 필수 proposition은 실제 TTS 종료 시각 158초 안에 끝나고, 다음 beat는 결과 또는 opening echo다. 답을 마지막 30초에 다시 반복하도록 강제하지 않는다.
3. 선언된 새 정보 경계의 간격 목표는 10~12초, hard max는 15초다.
4. `methodology`는 총 8초 이하이고, `methodology + reflection`은 총 20초 이하이다. 추상 문장은 연속 최대 2개다.
5. `story_progress + evidence_reveal`은 M4 TTS 실측 발화 시간의 85% 이상이다.
6. 한 beat의 신규 named entity는 원칙적으로 1명, 최대 2명이며 첫 등장 역할 소개와 canonical name을 지킨다.

위 시간·비율 gate의 권위 자료는 provisional TTS를 parent로 가진 `narrative_quality_report`다. pre-TTS 구조 검사는 비용을 아끼기 위한 preflight일 뿐 timing PASS를 발행하지 않는다.

다음은 v4 pilot에서 semantic evaluator가 검사하되 자동 PASS/FAIL로 확정하지 않는다.

- payoff 문장이 `answer_criteria`의 의미를 실제로 답하는가.
- story/evidence beat의 텍스트에 실제 `actor-action-change` 또는 `cause-decision-consequence`가 있는가.
- `core_answer` beat를 삭제했을 때 core answer의 인과 그래프가 실제로 약해지는가.
- 서로 다른 ID를 쓴 문장들이 같은 명제를 바꿔 말한 의미 반복인가.
- 질문 다음 문장이 실제로 질문을 좁히는가.
- metadata가 긴 추상문, 무관한 resolve, 새 인물 나열을 story progress로 세탁했는가.

semantic finding이 하나라도 있으면 결과는 `REVIEW_REQUIRED`다. 독립 editorial reviewer가 근거와 함께 해소 또는 허용 결정을 서명해야만 narrative approval이 생기며, 그 전에는 이미지 생성으로 진행하지 않는다. 현재 v3 실패본, 새 v4 후보, 벤치마크의 주석된 좋은/나쁜 대본으로 false-pass·false-reject와 평가 일치도를 보정한 뒤에만 항목별 자동 hard gate 승격을 검토한다.

문장 수, 질문 부호 수, `그런데` 횟수는 soft metric이다. 위 10~12초, 15초, 8초, 20초, 85%는 **HA002 실험 profile 값**이다. 벤치마크의 표면 숫자를 영구 템플릿으로 복제하지 않는다.

### 8.2 범용 문장 탐지

다음과 같이 어느 역사 영상에도 붙일 수 있는 문장은 자동 경고한다.

- “사료는 모두 같은 거리에서 사건을 바라보지 않습니다.”
- “역사는 후대의 자극적인 이야기에 가려집니다.”
- “대중은 차분한 기록보다 자극적인 이야기를 좋아합니다.”

최종 editorial review는 각 문장에 다음 질문을 적용한다.

> 이 문장을 빼도 장희빈 사건의 이해와 다음 궁금증이 그대로인가?

답이 `예`라면 삭제하거나 description으로 이동한다.

semantic evaluator는 `new_information`, `sentence_function`, `content_mode` 같은 자기신고 필드를 그대로 신뢰하지 않는다. 실제 문장에서 주체, 행동·판단, 바뀐 상태 또는 질문을 좁힌 구체적 증거를 찾아 outline과 비교한다. 긴 추상문 사이에 짧은 행동문을 끼워 85%를 세탁하거나, 무관한 문장에 resolve 태그를 붙이거나, 새 인물만 계속 추가한 의심이 있으면 `REVIEW_REQUIRED`를 낸다.

### 8.3 사람 평가

기계 PASS와 fact approval 뒤 provisional M4 TTS를 만든다. 시각 작업 전 최소 한 명의 지정된 사람 editorial reviewer가 **대본과 자료를 보지 않은 상태에서 오디오를 먼저** 듣고 cold-listen 회상 답변을 제출한다. 그 뒤에만 대본을 읽고 아래 일곱 항목을 평가한다. reviewer ID, `audio_first: true`, 각 노출 시각을 기록한다. editorial reviewer는 대본 생성자와 달라야 하며 fact reviewer와 editorial reviewer 역할은 별도 승인으로 남긴다.

다음 일곱 항목을 5점 척도로 평가하며 어느 하나도 4점 미만이면 수정한다.

- 놀라움: 새 사실이 기존 이해를 실제로 바꾸는가.
- 이해: 인물과 인과관계를 한 번에 따라갈 수 있는가.
- 전진감: 다음 문장을 계속 듣고 싶은가.
- 회수감: 처음 약속한 질문에 근거 범위 안의 답과 결과가 있는가.
- 구체성: 이름·행동·물건·결정이 추상 해설보다 먼저 떠오르는가.
- 생동감: 사실을 왜곡하지 않으면서 장면과 선택을 머릿속에 그릴 수 있는가.
- 리듬: 짧고 긴 문장, 질문과 서술이 단조롭지 않게 변하는가.

점수 anchor는 공통으로 고정한다. `1`은 이해 또는 흥미를 방해하고 전면 재작성 필요, `3`은 핵심은 전달되지만 혼동·정체가 있어 수정 필요, `5`는 사전 설명 없이도 명확하고 기억 가능하며 군더더기가 없는 상태다. `2`와 `4`는 인접 anchor 사이 수준이다.

cold-listen 직후 검토자는 사전 자료 없이 다음을 적는다.

1. 누가 어떤 결정을 했는가.
2. 어떤 사건과 판단이 그 결정으로 이어졌는가.
3. 기록된 정당화와 제작진의 추론을 구분할 수 있는가.
4. 결정의 결과는 무엇인가.

네 문항 중 최소 세 문항이 정확해야 하고 **2번과 3번은 모두 필수 통과**다. 점수, 코멘트, 회상 답변, 노출 순서, reviewer ID, 현재 script/report/TTS digest는 `approvals/narrative_editorial_approval_v1.json`에 저장한다. LLM 평가는 보조 의견이며 자동 승인이 아니다.

## 9. 3분 샘플 컴파일과 provenance

### 9.1 Prefix slicing 폐기

`audio_rows[:N]`과 `append_sentence_ids`로 샘플을 만드는 경로는 신규 production에서 금지한다. 3분 샘플은 두 방식 중 하나만 허용한다.

1. 독립적으로 작성·승인된 `quick_3m` 대본
2. 승인된 `sample_arc_manifest`가 명시한 beat와 sentence ID 순서

이번 HA002는 첫 번째 방식을 사용한다. 새 sentence ID namespace를 사용해 이전 전체본의 같은 ID와 텍스트가 충돌하지 않게 한다.

### 9.2 Sample-local 보고서

전체본의 보고서와 승인을 복사하지 않는다. 다음 산출물을 샘플 대본에서 다시 계산한다.

- `narrative_outline.json`
- `script_candidate.json`
- `claim_inventory_v2.json`
- `source_snapshot_manifest_v2.json`
- `fact_check_report_v2.json`
- `persona_report_v2.json`
- `narrative_quality_report.json`
- `approvals/fact_review_approval_v2.json`
- `approvals/narrative_editorial_approval_v1.json`

fact 승인은 source, claim, script, fact report만 승인한다. narrative 승인은 outline, script, persona report, narrative report, provisional TTS manifest/audio inventory, audio-first cold-listen과 text review를 승인한다. 한 파일에 두 책임을 합치지 않는다. 두 승인 모두 현재 입력과 자신이 승인한 report의 digest를 묶는다. 대본 한 글자, claim, source, outline, 보고서, 정책 profile, TTS 중 하나가 바뀌면 관련 승인은 stale이다.

### 9.3 Downstream 무효화

모든 산출물은 명시된 parent digest를 가진다. stale 계산은 파일명 목록이 아니라 parent graph를 따라 전이한다.

```text
source/claim/policy → outline → script
script → fact/persona reports
fact report + source/claim/script → fact approval
script → script_common_projection_v1
projection + fact approval + voice profile → provisional sentence manifest/TTS
outline/script/policy + TTS → narrative quality/timing report
outline/script/persona/narrative reports + TTS → narrative editorial approval
narrative approval + projection/TTS → subtitle + visual brief
visual brief → image request → image assets/approval
TTS/subtitle/approved assets → motion → candidate video → final QA/COMPLETE
```

시간 또는 cold-listen 실패로 대본을 바꾸는 것은 graph 안의 순환이 아니다. 새 script revision과 새 run을 만들고 fact report부터 descendant를 다시 계산한다.

어느 parent digest든 바뀌면 해당 node와 모든 descendant를 무효화한다. 최종 승인 대본이 바뀌면 TTS, 자막, 시각 brief, image request, asset approval, motion, candidate video를 모두 다시 만든다. 기존 자산을 새 대본에 이름만 바꿔 연결하지 않는다.

### 9.4 `artifact_envelope_v1`

v4 pilot에서 모든 기존 JSON 형식을 한꺼번에 바꾸지 않는다.

- 신규 `narrative_outline_v1`, `verified_script_v3`, `narrative_quality_report_v1`, 두 approval, `COMPLETE`는 공통 envelope와 payload 형식을 쓴다.
- `script_common_projection_v1`은 기존 소비자가 그대로 읽을 수 있는 공통 payload shape를 내고 `.artifact-meta.json` sidecar로 v3 parent와 adapter version을 결속한다.
- 기존 shape를 유지해야 하는 source/claim/fact/persona/TTS·subtitle artifact에는 같은 basename의 `.artifact-meta.json` sidecar로 envelope를 둔다. legacy file 자체는 변경하지 않는다.
- sidecar payload는 `target_relative_path`, 정확한 legacy `artifact_file_sha256`, `scope_kind`, `scope_id`, `run_id`를 필수로 묶는다. 따라서 경로만 같거나 원본 또는 sidecar 하나만 복사한 artifact는 통과하지 않는다.
- 모든 legacy consumer의 native envelope migration과 전 artifact RFC 8785 전환은 v4 인수 뒤 별도 설계로 일반화한다.

```json
{
  "envelope": {
    "artifact_id": "HA002-V4-NARRATIVE-REPORT",
    "artifact_type": "narrative_quality_report",
    "schema_version": "narrative_quality_report_v1",
    "scope_kind": "quick_3m",
    "scope_id": "HA002-sample-3m-v4-001",
    "run_id": "sample-3m-v4-001",
    "payload_sha256": "...",
    "parents": [
      {
        "role": "verified_script",
        "artifact_id": "HA002-V4-SCRIPT",
        "payload_sha256": "...",
        "envelope_core_sha256": "..."
      },
      {
        "role": "narrative_outline",
        "artifact_id": "HA002-V4-OUTLINE",
        "payload_sha256": "...",
        "envelope_core_sha256": "..."
      },
      {
        "role": "tts_manifest",
        "artifact_id": "HA002-V4-TTS",
        "payload_sha256": "...",
        "envelope_core_sha256": "..."
      }
    ],
    "generator": {
      "name": "validate_narrative_quality",
      "version": "1.0.0",
      "git_commit": "..."
    },
    "policy_sha256": "...",
    "created_at": "2026-08-31T00:00:00+09:00"
  },
  "payload": {}
}
```

hash 계산은 다음처럼 고정한다.

- native envelope JSON의 `payload_sha256`은 RFC 8785 JSON Canonicalization Scheme으로 canonicalize한 payload의 UTF-8, BOM 없음 bytes에 SHA-256을 계산한다.
- legacy sidecar의 `payload_sha256`은 sidecar가 설명하는 원본 file의 정확한 bytes에 SHA-256을 계산하고 `payload_hash_method: file_bytes_sha256`을 기록한다.
- 이미지, 오디오, 영상, 원문 snapshot 같은 binary/file artifact는 저장된 정확한 bytes에 SHA-256을 계산한다.
- JSON 파일 전체의 `artifact_file_sha256`은 실제 직렬화된 file bytes에 계산해 approval과 `COMPLETE` manifest에 별도로 기록한다.
- `envelope_core_sha256`은 `created_at`과 `envelope_core_sha256` 자기 필드를 제외한 envelope를 RFC 8785로 canonicalize해 계산한다. 따라서 scope, parents, generator, policy의 변조도 탐지한다.
- `created_at`은 envelope에만 있고 결정적 payload/envelope core hash에는 포함하지 않는다. 같은 input, policy, generator version이면 같은 core digest가 나와야 한다.
- consumer는 approval 내부의 자기주장 hash를 믿지 않고 실제 파일을 다시 읽어 payload와 file hash를 모두 계산한다.
- parent edge는 `payload_sha256`와 `envelope_core_sha256`를 모두 참조한다. approval은 parent file hash를 묶지만 자기 자신의 file hash는 포함하지 않는다. approval file hash는 `COMPLETE`가 묶고, `COMPLETE`는 자기 자신을 inventory에서 제외해 순환 hash를 만들지 않는다.

scope는 경로명이 아니라 envelope로 증명한다. `scope_kind`는 `episode_source`, `full`, `quick_3m`, `sample_arc` 중 하나다. `episode_source`는 episode ID와 content digest로 주소화한 immutable snapshot이며 수정 대신 새 artifact ID를 만든다. `quick_3m` report와 approval은 같은 `scope_id`·`run_id`의 outline/script/report만 parent로 받을 수 있고, immutable `episode_source`만 공유 parent로 받을 수 있다. full script/report/approval은 받을 수 없다.

`sample_arc`는 승인된 full script를 직접 플래그로만 가리키지 않는다. `selection_manifest_v1`이 full script의 payload/envelope/file digest와 선택한 ordered sentence IDs를 고정하고, sample artifact는 이 manifest를 필수 parent로 받는다. 그 경우에도 report와 approval은 sample sentence set에서 다시 계산한다. 이번 독립 `quick_3m` HA002 경로에는 `selection_manifest`와 `selected_from_full`을 모두 금지한다.

### 9.5 Artifact별 parent 계약

validator는 단순 DAG 모양이 아니라 artifact type별 required/allowed parent role, type, cardinality를 검사한다. 아래에 없는 extra parent는 기본 금지다.

| artifact type | required parent role → type (cardinality) |
|---|---|
| `narrative_outline_v1` | `episode_source` → source snapshot (1+), `claim_inventory` (1), `narrative_policy` (1) |
| `verified_script_v3` | `narrative_outline` (1), `claim_inventory` (1), `script_policy` (1) |
| `fact_report_v2` | `verified_script` (1), `claim_inventory` (1), `episode_source` (1+) |
| `persona_report_v2` | `verified_script` (1), `persona_policy` (1) |
| `narrative_quality_report_v1` | `verified_script` (1), `narrative_outline` (1), `narrative_policy` (1), `tts_manifest` (1) |
| `fact_review_approval_v2` | `verified_script` (1), `claim_inventory` (1), `episode_source` (1+), `fact_report` (1) |
| `script_common_projection_v1` | `verified_script` (1); adapter name/version/git commit은 generator 필드에 필수 |
| `sentence_tts_manifest` | `script_projection` (1), `fact_approval` (1), `voice_profile` (1) |
| `narrative_editorial_approval_v1` | `narrative_outline` (1), `verified_script` (1), `fact_approval` (1), `persona_report` (1), `narrative_report` (1), `tts_manifest` (1) |
| `subtitle_manifest` | `script_projection` (1), `tts_manifest` (1), `narrative_approval` (1) |
| `visual_brief` | `verified_script` (1), `narrative_outline` (1), `narrative_approval` (1) |
| `image_request` | `visual_brief` (1) |
| `asset_approval` | `image_request` (1), `image_asset` (1+) |
| `motion_manifest` | `tts_manifest` (1), `subtitle_manifest` (1), `asset_approval` (1) |
| `candidate_video` | `tts_manifest` (1), `subtitle_manifest` (1), `asset_approval` (1), `motion_manifest` (1), `narrative_approval` (1) |
| `final_qa_report` | `candidate_video` (1), `tts_manifest` (1), `subtitle_manifest` (1), `asset_approval` (1), `narrative_approval` (1) |
| `COMPLETE` | `final_qa_report` (1), `candidate_video` (1), `fact_approval` (1), `narrative_approval` (1) |

`sample_arc`에만 쓰는 `selection_manifest_v1`은 `full_script` (1), `full_outline` (1), `full_approval` (1)을 요구하고 payload에 ordered sentence IDs를 필수로 둔다. 독립 `quick_3m` graph에는 이 type이 존재하면 실패한다.

validator는 required edge 누락, 잘못된 type, cardinality 위반, 같은 role의 중복, 허용되지 않은 extra edge, 다른 scope/run, dependency cycle, `COMPLETE`에서 도달할 수 없는 disconnected artifact를 거부한다. projection을 건너뛰고 v3 script를 TTS에 직접 넣는 경로도 거부한다.

### 9.6 원자적 게시와 fail-closed

빌드는 최종 run 디렉터리에 파일을 하나씩 노출하지 않는다.

1. 동일 filesystem의 고유 staging 디렉터리에 모든 산출물을 쓴다.
2. schema, semantic, digest, lineage, media 검증을 끝낸다.
3. 검증된 파일 목록과 digest를 가진 `COMPLETE.json`을 마지막에 쓴다. inventory는 `COMPLETE.json` 자신을 제외하고 각 상대경로, artifact type, file hash를 기록한다. legacy 원본과 `.artifact-meta.json` sidecar는 각각 독립 entry로 들어가며 서로의 상대경로와 hash가 맞아야 한다.
4. final 경로가 존재하지 않을 때만 staging 디렉터리를 final로 옮기는 단일 원자 rename을 수행한다.

기존 완성 run을 덮어쓰지 않고 새 run ID를 사용한다. final 경로 선확인과 별개의 overwrite rename은 금지한다. rename의 `FileExists`는 단일 승자가 이미 publish한 것으로 보고 `CONCURRENT_PUBLISH`로 실패한다. staging과 final의 resolved path는 지정 run root 내부여야 하며 symlink·junction·reparse point와 staging 밖 상대경로를 거부한다.

compiler는 검증 뒤 입력을 다시 읽는 사이 바뀌는 TOCTOU를 막기 위해 content-addressed snapshot을 소비하거나, 자신이 읽은 bytes를 즉시 rehash하고 그 digest를 output lineage에 기록한다.

schema validation과 semantic validation은 별도 결과를 내며 다음 stable error code를 최소로 사용한다.

- `INVALID_JSON`
- `SCHEMA_MISMATCH`
- `HASH_MISMATCH`
- `CROSS_SCOPE_PARENT`
- `REPORT_STALE`
- `DEPENDENCY_INVALID`
- `LOOP_INVALID`
- `INCOMPLETE_PUBLISH`
- `CONCURRENT_PUBLISH`

오류에는 artifact ID와 JSON Pointer를 포함한다. report 기록 자체가 실패하면 이전 PASS report를 재사용하지 않고 운영 오류로 중단한다.

## 10. 실패 처리

| 실패 | 처리 |
|---|---|
| 선택 질문의 답변 가능성 부족 | 질문 강도를 낮추거나 다른 검증 가능 질문 선택; 동기를 추정하지 않음 |
| 중심 질문 미회수 | TTS 전에 차단하고 outline 수정 |
| 사건 없는 추상 구간 초과 | 해당 구간을 사건·행동·결과로 교체; filler 추가 금지 |
| 근거가 부족한 흥미로운 beat | 표현을 약화하거나 beat를 제거; 추정으로 보충 금지 |
| BLOCKED claim 참조 | outline 생성 전에 중단하고 정상 source snapshot과 fact 재승인 요구 |
| 목표 시간이 짧음 | 다음 인과 단계나 구체 사건을 추가; 사료 일반론으로 늘리지 않음 |
| 목표 시간이 김 | 반복 설명과 우회 비유부터 제거; 핵심 payoff는 보존 |
| fact와 narrative 평가 충돌 | fact 범위를 우선하고 다른 서사 경로를 선택 |
| metadata와 실제 문장 의미 불일치 | semantic failure; label 자동 수정 없이 문장 또는 outline 재작성 |
| report의 sentence ID 불일치 | stale artifact 오류로 실패하고 샘플 보고서 재생성 |
| 승인 SHA 불일치 | 모든 downstream 실행 차단 및 사람 재승인 요구 |
| narrative evaluator 불능 | `REVIEW_REQUIRED`; 자동 PASS 금지 |
| staging 중단 또는 `COMPLETE.json` 부재 | 미완성 run으로 격리하고 소비 금지 |

실패는 가능한 한 이미지 생성 전에 발생시켜 이미지 쿼터와 렌더 시간을 낭비하지 않게 한다.

## 11. 테스트 설계

구현은 회귀 테스트를 먼저 작성하는 방식으로 진행한다.

### 11.1 자동 차단되거나 `REVIEW_REQUIRED`여야 하는 fixture

- 현 `sample-3m-v3-001`의 19~29번 11문장 방법론 streak
- `HA002-S018`과 `HA002-S019` 사이의 무관한 사료 일반론 삽입
- 질문은 있지만 `resolves_loop_ids`가 없는 대본
- 모든 문장이 고유하지만 사건 상태 변화가 하나도 없는 217문장 대본
- 30문장 sample에 217문장 fact/persona report를 연결한 manifest
- 현재 script SHA와 다른 승인 artifact
- 배열 prefix와 outro만으로 만든 sample arc
- 동일 claim을 문구만 바꿔 세 번 반복한 대본
- 고유한 날짜와 사건은 많지만 core answer와 인과 연결이 없는 연대기 목록
- `정치 때문이었다`만 말하고 payoff로 태그한 대본
- 긴 추상문 사이에 짧은 행동문을 넣어 story 비율을 세탁한 대본
- 무관한 문장에 `resolve` 또는 `new information` metadata를 붙인 대본
- 모든 문장이 같은 길이·주어·어미인 단조로운 낭독문
- 상태 변화 대신 새 인물만 계속 추가하는 과밀 대본
- 범위가 정해진 negative evidence를 `그 사건은 없었다`로 확대하는 대본
- `recorded_allegation`과 `scholarly_interpretation`을 귀속 없이 사실로 말하는 대본
- 기록되지 않은 장면을 `literal` visualization으로 지정한 brief

provenance 부정 fixture:

- sentence ID는 같지만 text만 바뀐 script와 오래된 report
- report ID의 순서 변경, 중복, 누락, extra ID
- 승인 뒤 report 파일 하나를 변조한 build
- 승인된 v3와 다른 text를 가진 projection 또는 projection을 건너뛴 TTS manifest
- required parent 누락·중복·잘못된 type·cardinality와 `COMPLETE`에서 끊긴 artifact
- 다른 run 또는 scope의 report·approval 교체
- full artifact를 quick 디렉터리에 복사하거나 full prefix를 독립 quick parent로 연결한 build
- CRLF/LF/BOM 차이에 대해 선언된 hash 규칙과 맞지 않는 artifact
- unknown schema/version, extra property, `null`과 빈 값의 잘못된 대체
- 없는 dependency, dependency cycle, loop 이중 resolve, required loop 미해결
- staging 중 쓰기 실패, 동시 compiler publish, `COMPLETE.json` 없는 run
- final 경로가 이미 존재하는데 overwrite rename을 시도한 run
- symlink·junction·reparse point 또는 run root 밖 상대경로가 inventory에 들어간 run
- script 변경 뒤 일부 descendant만 새로 만든 혼합 build
- gate 통과 직후 입력 bytes를 바꾼 TOCTOU fixture
- 새 report 기록 실패 뒤 이전 PASS report가 남은 run
- 대본을 먼저 본 reviewer가 cold-listen 승인을 제출하거나 노출 순서를 기록하지 않은 approval

### 11.2 통과해야 하는 fixture

- 하나의 core promise 아래 각 beat가 인과적으로 연결된 3분 outline
- 질문이 사건, 결정, 결과를 거쳐 시간 예산 안에 회수되는 대본
- 사료명이 한 번 등장하더라도 구체적 반전을 증명하고 즉시 사건으로 복귀하는 대본
- opening echo가 명시된 의도적 반복
- sample-local report의 sentence ID와 SHA가 모두 일치하는 build
- 근거가 동기를 지지하지 않아 질문을 `무엇이 명령으로 이어졌는가`로 낮추고 정확히 회수한 outline
- 같은 증거가 `confirm`, `narrow`, `complicate`, `reverse` 중 적합한 역할로 다양하게 진행되는 대본
- canonical payload가 같고 `created_at`만 다른 두 실행에서 payload SHA가 같은 artifact
- 모든 parent digest와 scope가 일치하고 원자적으로 게시된 `COMPLETE` run
- audio-first 노출 순서가 기록되고 회상 2번·3번을 모두 통과한 narrative approval

### 11.3 통합 검증

`sample-3m-v4-001`은 다음 순서로 검증한다.

```text
narrative outline schema
→ promise answerability + fact scope gate
→ pre-TTS narrative structure preflight
→ fact verification
→ persona validation
→ sample-local artifact binding
→ M4 TTS 실측 duration
→ authoritative narrative quality/timing report
→ audio-first cold-listen + text editorial approval
→ shot/visual contract
→ zero asset reuse
→ subtitle sync
→ content review
→ media postflight
```

## 12. 신규 샘플 인수 기준

### 12.1 대본

- 콜드오픈 마지막 필수 답 문장은 실제 TTS 종료 시각 25초 안, 중심 질문은 38초 안에 등장하고 core의 마지막 필수 답 문장은 종료 시각 158초 안에 끝난다.
- 선택 질문과 답이 `promise_answerability` 및 `core_answer_contract`의 근거 수준을 넘지 않는다.
- 새 정보 간격은 목표 10~12초, 최대 15초이며 모든 연속 15초 구간에 사건 진행 또는 증거 역할 변화가 있다.
- 추상적인 사료 방법론은 총 8초 이하, `methodology + reflection`은 총 20초 이하, 추상문은 연속 최대 2문장이다.
- `story_progress + evidence_reveal`은 실제 M4 TTS 발화 시간의 85% 이상이다.
- 동일 결론의 비의도적 의미 반복은 0건이다.
- payoff 다음 beat에 검증된 결과 또는 opening echo가 나오며 답을 재진술해 시간을 채우지 않는다.
- `CLM-JH-003`, `CLM-JH-006`, `CLM-JH-007`은 source·인물 오류를 해결하고 새 fact 승인을 받기 전까지 사용하지 않는다.
- negative evidence, 기록된 고발, 동시대 발언, 학술 해석의 귀속 규칙을 모두 지킨다.
- 사람 평가 일곱 항목이 모두 4/5 이상이고 cold-listen 회상 검사를 통과한다.
- cold-listen은 audio-first이고 회상 2번·3번을 반드시 통과하며 노출 순서가 승인에 남는다.

### 12.2 Provenance

- sample script와 fact/persona/narrative report의 sentence ID 배열이 중복 없이 순서까지 100% 일치한다.
- 현재 script, outline, claim, source, policy, report의 payload/file SHA와 승인 내부 digest가 모두 일치한다.
- full-v6의 오래된 fact/persona 보고서나 승인을 복사하지 않는다.
- `verified_script_v3 → script_common_projection_v1 → TTS` lineage와 adapter version이 결속되고 projection 우회는 0건이다.
- 대본 변경 뒤 stale TTS, 자막, 이미지, 승인 재사용은 0건이다.
- 모든 artifact의 scope/run/parent lineage가 유효하고 final run에는 검증된 `COMPLETE.json`이 존재한다.

### 12.3 시청각

- 새 빌드 ID는 `sample-3m-v4-001`이다.
- `sample-3m-v3-001`은 변경하지 않는다.
- 음성은 M4이며 실제 최종 길이는 170~190초다.
- 최종 대본에서 신규 이미지와 모션을 생성하며 기존 자산 재사용은 0건이다.
- 자막은 현재 샘플의 `Malgun Gothic` 108pt와 동등한 가독성 계약을 유지한다. 해상도나 safe area가 바뀌면 동일한 시각 크기를 기준으로 별도 승인한다.
- 대본-이미지 의미 매칭, 오디오, 자막, MP4 postflight가 모두 PASS여야 한다.

## 13. 변경 경계

구현은 다음 경계를 유지한다.

- `narrative_outline` 생성과 검증은 fact verifier와 독립된 작은 모듈로 만든다.
- sample compiler는 selection과 artifact 복사를 동시에 책임지지 않는다. arc 선택, 보고서 생성, 승인 검증을 분리한다.
- outline은 별도 `narrative_outline_v1` schema, 문장 대본은 필수 서사 필드를 가진 `verified_script_v3` schema로 도입한다. 레거시 v2는 읽기 전용 재현 경로에만 남긴다.
- v3는 먼저 HA002 `sample-3m-v4-001`에만 적용하고 공통 projection adapter로 기존 TTS·자막·시각 소비자에 연결한다. 인수 전 전체 파이프라인 migration은 하지 않는다.
- 시각 파이프라인은 승인된 script와 TTS manifest만 소비하며 내러티브 평가를 재구현하지 않는다.
- HA002에 특화된 인물·사건 데이터는 story packet에 두고 공용 validator에 하드코딩하지 않는다.

## 14. 성공의 정의

이번 설계가 성공했다는 것은 단순히 새 MP4가 만들어졌다는 뜻이 아니다.

1. 현 대본처럼 정확하지만 사건이 멈춘 대본이 이미지 생성 전에 자동으로 실패한다.
2. 시청자는 3분 동안 `공식 기록에서 난동 장면이 확인되는가`에서 `처분 명령으로 이어진 사건과 판단`, `기록에 남은 결정`, `검증된 결과`까지 하나의 질문으로 따라갈 수 있다.
3. 팩트 검증과 불확실성 표시는 유지되지만 시청자는 제작 방법론 강의를 듣지 않는다.
4. 새 대본은 자신의 sample-local 보고서와 승인에만 결속된다.
5. HA002에서 검증한 공용 불변식은 다른 역사 주제에서도 맞는 서사 profile을 선택하고 임계값을 보정한 뒤 재사용할 수 있다.
