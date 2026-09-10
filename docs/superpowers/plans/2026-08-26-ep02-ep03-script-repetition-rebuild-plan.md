# EP02·EP03 반복 대본 제거 및 전체 재구축 계획

> 상태: 진단 완료, 구현 전 계획
>
> 대상: `human_archive/runs/ep02_jang_huibin`, `human_archive/runs/ep03_maecheon`
>
> 원칙: 현재 영상·자막에서 반복 문장만 지우지 않는다. 승인 대본을 새로 만들고, 그 대본에서 파생된 음성·자막·장면·이미지 요청·렌더 타임라인을 새 build ID로 전부 재생성한다.

## 1. 결론

반복은 렌더러나 자막 분할기가 만든 문제가 아니다. EP02·EP03의 대본 생성기가 목표 문장 수를 채우기 위해 작은 문장 묶음을 순환시키며, 그 결과가 검증 없이 TTS와 ASS 자막으로 전달됐다.

- EP02: 180문장 중 고유 문장 33개, 중복 발생 147회(81.7%).
- EP03: 180문장 중 고유 문장 51개, 중복 발생 129회(71.7%).
- EP03의 핵심 템플릿 3문장은 각각 44회 반복된다.
- 현행 검증은 sentence ID의 존재와 순서 위주라, ID가 다르지만 본문이 같은 반복을 차단하지 못한다.
- 이미지 프롬프트도 대본과 독립된 preset 순환 구조여서, 대본을 고쳐도 기존 이미지 계약을 그대로 쓰면 의미 불일치가 남는다.

따라서 해결 단위는 문장 교체가 아니라 `verified_script → audio/subtitle → visual contract → image request → render plan` 전체 해시 연쇄다.

## 2. 직접 원인

### EP02

- `human_archive/scripts/generate_ep02_full_docu.py`가 제한된 문장 pool을 문장 번호에 modulo로 배치한다.
- 목표 180문장을 “새 논지 180개”가 아니라 “pool 반복 180칸”으로 채운다.
- 챕터별 논증 진전, 이미 말한 내용, 다음 문장과의 정보 증가량을 검사하지 않는다.
- 반복 문장마다 새 sentence ID가 붙어 ID coverage 검사는 통과한다.

### EP03

- `human_archive/scripts/generate_ep03_full_docu.py`가 챕터별 템플릿 문장을 반복한다.
- 같은 3문장이 각각 44회 재사용되지만 서로 다른 sentence ID를 가진다.
- 장편 길이를 문장 수로 맞추고 실제 정보량·논증 진행률·TTS 예상 시간을 gate로 사용하지 않는다.

### 공통 전파 경로

1. 반복 대본이 `script_seonbi_v2/v3.json`에 저장된다.
2. TTS가 sentence ID별로 정상 합성한다.
3. 자막 생성기가 합성 타이밍을 정상 ASS로 변환한다.
4. 영상은 정상 25fps로 렌더된다.
5. 기술 후검증은 PASS하지만 내용 반복은 검사항목에 없어 품질본으로 오인된다.

## 3. 해결하지 못하는 접근

- 최종 ASS에서 중복 자막만 삭제: 음성에는 반복이 남고 A/V sync가 무너진다.
- TTS 파일만 교체: 자막·장면·렌더 타임라인 hash가 stale이 된다.
- 동일 문장에 표현만 바꾸기: semantic repetition과 논증 정체가 남는다.
- 기존 180문장 수를 유지한 채 빈칸 채우기: 같은 생성 압력이 재발한다.
- 기존 45개 이미지와 장면 순서를 무조건 유지: 새 대본의 의미 단위와 맞지 않는다.

## 4. 목표 구조

```text
source/claims
  → outline_contract
  → script_candidate
  → script_quality_report
  → fact/persona/editorial approval
  → verified_script (immutable)
  → audio + caption timing
  → episode_visual_contract
  → image_request_manifest + asset_manifest
  → frame-exact render_plan
  → candidate + content/motion/release QA
```

대본 합격 전에는 TTS·자막·이미지 생성·렌더를 시작하지 않는다.

## 5. 대본 계약 변경

### 5.1 문장 수 대신 정보 구조를 권위로 사용

- `180문장` 하드코딩을 제거한다.
- 목표 길이는 예상 TTS 시간과 한국어 음절/어절 수로 계산한다.
- 각 챕터에 다음 필드를 요구한다.
  - `chapter_question`
  - `new_claim_ids[]`
  - `evidence_span_ids[]`
  - `counterpoint`
  - `chapter_takeaway`
  - 이전 챕터 대비 새 정보 요약
- 같은 claim/evidence를 다시 설명할 때는 `recap_reason`을 명시하고 짧은 요약만 허용한다.

### 5.2 문장별 progression metadata

각 문장은 최소한 다음을 가진다.

- `sentence_id`
- `chapter`, `beat`
- `display_text`, `tts_text`
- `claim_ids[]` 또는 비사실 문장의 `function`
- `new_information`
- `depends_on_sentence_ids[]`
- `intentional_repetition: false|true`
- true일 때 `repetition_reason`

### 5.3 허용 반복

다음만 allowlist로 허용한다.

- 오프닝/엔딩의 고정 채널 문구
- 직접 인용문을 다시 분석하는 경우
- 챕터 전환에서 1회 사용하는 짧은 recap

허용 반복도 별도 metadata와 reviewer 승인이 필요하다.

## 6. 품질 gate

### 6.1 결정론 검사

`human_archive/scripts/audit_episode_quality.py`를 확장해 다음을 계산한다.

- exact duplicate
- 공백·문장부호·숫자를 정규화한 duplicate
- 숫자·고유명사만 바꾼 template duplicate
- 동일 3~8gram 반복
- 챕터별 새 claim/evidence 비율
- 연속 문장 lexical overlap
- 예상 TTS 시간과 목표 시간 차이

Fail 기준:

- allowlist 밖 exact/normalized duplicate 1건 이상
- 동일 template 3회 이상
- 한 챕터에서 새 claim/evidence 없는 연속 3문장 이상
- 동일 결론을 새로운 근거 없이 2회 초과 설명

### 6.2 의미 반복 검사

`ScriptSemanticEvaluator` 인터페이스를 추가한다.

```python
evaluate(sentences, chapter_contract) -> ScriptSemanticReport
```

- 모델을 사용할 수 없거나 실패하면 자동 PASS가 아니라 `REVIEW_REQUIRED`.
- 의미 유사도만으로 삭제하지 않고 `claim/evidence/function` metadata와 함께 판정한다.
- 높은 유사도 문장 쌍은 사람이 유지·통합·삭제 중 하나를 기록한다.

### 6.3 사람 승인

검토자는 다음 순서로 본다.

1. 챕터별 한 문단 요약
2. claim/evidence progression 표
3. exact/template/semantic 반복 목록
4. 전체 대본
5. 예상 TTS 길이

승인 파일에는 대본 SHA-256과 quality report SHA-256을 함께 기록한다.

## 7. 구현 작업

### Task 1 — 현행 결함을 회귀 fixture로 고정

Create:

- `human_archive/tests/fixtures/ep02_repetitive_script.json`
- `human_archive/tests/fixtures/ep03_repetitive_script.json`
- `human_archive/tests/test_script_repetition_gate.py`

작업:

- 현재 EP02의 33/180, EP03의 51/180 수치를 fixture에 고정한다.
- EP03 3문장×44회 패턴이 지정 오류 코드로 실패하는 테스트를 먼저 작성한다.
- ID가 모두 달라도 본문이 같으면 실패하는 테스트를 추가한다.

완료 기준: 현행 대본이 `DUPLICATE_TEXT`, `TEMPLATE_LOOP`, `NO_INFORMATION_GAIN`으로 실패한다.

### Task 2 — 반복 생성기 production 차단

Modify:

- `human_archive/scripts/generate_ep02_full_docu.py`
- `human_archive/scripts/generate_ep03_full_docu.py`
- `human_archive/scripts/build_episode_v2.py`

작업:

- modulo/template fill 경로를 `legacy_only`로 격리한다.
- 해당 경로 결과에 `release_eligible: false`를 강제한다.
- production orchestrator가 legacy generator를 호출하면 즉시 실패한다.

완료 기준: 기존 생성기로는 candidate/final build를 만들 수 없다.

### Task 3 — outline-first 대본 생성

Create/Modify:

- `human_archive/scripts/plan_script_outline.py`
- `human_archive/scripts/generate_verified_script.py`
- `human_archive/scripts/lib/script_generation.py`
- `human_archive/templates/seonbi_script_prompt.j2`
- `human_archive/schemas/script_outline.schema.json`

작업:

- EP02·EP03의 claim inventory와 evidence span으로 챕터 outline을 먼저 만든다.
- outline 승인 후 한 챕터씩 생성한다.
- 생성 시 이전 챕터 요약과 이미 사용한 claim/핵심 문구 목록을 함께 전달한다.
- retry는 전체 대본이 아니라 실패 챕터만 다시 생성한다.
- 새 대본을 합칠 때 전역 repetition gate를 다시 실행한다.

완료 기준: 모든 챕터가 새로운 claim·evidence·분석 기능 중 하나를 추가한다.

### Task 4 — EP02 대본 재작성

새 build ID 예시: `script-v4-001`, `full-v4-001`.

챕터 방향:

1. 대중 서사와 기록의 차이
2. 장옥정의 신분 상승과 정치적 조건
3. 기사환국·갑술환국의 인과
4. 인현왕후 사후 기록과 처분 명령
5. 실록·승정원일기에 기록된 것과 기록되지 않은 것
6. 후대 소설·드라마가 만든 악녀 이미지
7. 사료로 말할 수 있는 결론과 불확실성

기존 반복 문장을 표현만 바꿔 재사용하지 않고, claim/evidence/function 단위로 다시 쓴다.

### Task 5 — EP03 대본 재작성

새 build ID 예시: `script-v4-001`, `full-v4-001`.

챕터 방향:

1. 황현과 『매천야록』의 성격
2. 편찬 시기·기록 방식·사료 한계
3. 구한말 정치와 민생에 대한 구체 기록
4. 동학농민전쟁·외세·개혁의 관찰
5. 을사늑약과 지식인의 반응
6. 1910년 절명과 절명시의 맥락
7. 야사·개인 기록을 읽는 방법

현재 44회 반복된 “특급 내부 고발서/실록이 못 적은 진실/선비의 결기” 프레임을 폐기하고, 구체 사건·기록·한계를 균형 있게 배치한다.

### Task 6 — 하위 산출물 전면 무효화

새 verified script가 승인되면 다음 기존 artifact를 새 build에서 재사용하지 않는다.

- scene audio manifest
- TTS audio clips와 master audio
- subtitles.ass
- shot/visual contract
- image request manifest
- asset manifest의 request binding
- render plan
- build/release report

이미지는 semantic QA를 다시 통과하고 새 scene/request hash에 명시적으로 재결속될 때만 재사용할 수 있다.

### Task 7 — EP02·EP03 새 오디오와 자막

- 새 대본으로 TTS 전체 재합성.
- 자막은 phrase timing에서 다시 생성.
- 1080p 기준 기본 72px, outline 5px를 profile에 고정.
- 대본의 모든 text span coverage 100%, gap/overlap 0.
- 음성 내용과 자막 normalized text가 100% 일치해야 한다.

### Task 8 — 새 visual contract와 이미지 재매칭

- TTS block과 visual event를 분리한다.
- caption span마다 scene을 연결한다.
- 대본 반복 제거 뒤 기존 45-shot 고정을 폐기하고 약 120~180 visual event 범위에서 계산한다.
- 새 대본의 subject/action/place/era와 맞지 않는 기존 이미지는 재생성한다.
- 같은 이미지 재사용은 `reuse_group_id`와 의미상 이유가 있을 때만 허용한다.

### Task 9 — candidate 및 내용 QA

- 기술 postflight와 별도로 content QA를 필수화한다.
- 무작위가 아니라 opening/body/outro와 모든 chapter boundary를 검토한다.
- 음성으로 동일 문장이 반복되는지 ASR transcript로 재검사한다.
- 최종 ASR transcript도 script repetition gate를 통과해야 한다.
- 사람이 본 candidate SHA-256을 승인 파일에 기록한다.

## 8. EP02·EP03 재구축 순서

1. 기존 final과 candidate SHA-256을 baseline에 보존한다.
2. 현행 대본을 실패 fixture로 고정한다.
3. legacy 생성기를 production에서 차단한다.
4. EP02 outline → 대본 → quality/fact/persona 승인.
5. EP02 TTS·자막 → visual contract → 이미지 → render → QA.
6. EP02에서 gate를 보정한 뒤 EP03에 동일 pipeline을 적용한다.
7. EP03 outline → 대본 → 승인 → 전체 하위 artifact 재생성.
8. 새 final은 `full-v4-*`로만 만들고 v2/v3는 비교용 read-only로 보존한다.

## 9. 테스트 실행 계획

```powershell
python -m pytest human_archive/tests/test_script_repetition_gate.py human_archive/tests/test_script_quality.py -q
python -m pytest human_archive/tests/test_verified_script_generation.py human_archive/tests/test_script_approval_binding.py -q
python -m pytest human_archive/tests/test_visual_contract.py human_archive/tests/test_prompt_compiler.py -q
python -m pytest human_archive/tests/test_audio_timeline_v2.py human_archive/tests/test_subtitles_v2.py -q
python -m pytest human_archive/tests/test_postflight_release.py human_archive/tests/test_release_gate_v2.py -q
```

RED 증거:

- 현재 EP02·EP03 fixture가 정확한 반복 오류로 실패한다.
- legacy generator로 release를 시도하면 실패한다.
- 대본 hash를 바꾸고 기존 audio/subtitle/visual artifact를 쓰면 stale hash로 실패한다.

GREEN 증거:

- 새 EP02·EP03 대본이 반복 gate를 통과한다.
- ASR transcript와 approved script가 일치한다.
- 모든 하위 artifact hash가 새 verified script에 연결된다.

## 10. 최종 합격 기준

### 대본

- allowlist 밖 exact/normalized duplicate 0건.
- 숫자·고유명사만 바꾼 template loop 0건.
- reviewer 미승인 semantic duplicate 0건.
- 모든 챕터에 새로운 claim/evidence/analysis 기능 존재.
- claim/evidence coverage와 fact approval 100%.
- 목표 duration 오차 ±5% 이내.

### 음성·자막

- 승인 대본과 TTS 입력 hash 일치.
- ASR transcript에서 반복 gate PASS.
- caption span coverage 100%, gap/overlap/orphan 0건.
- 음성·자막 normalized text 불일치 0건.
- 1080p 자막 72px/outline 5px profile 적용.

### 이미지·영상

- 모든 caption이 유효한 scene을 참조.
- scene과 narration 의미 충돌 0건.
- 승인 없는 image reuse 0건.
- 25fps CFR, BT.709, loudness/true peak postflight PASS.
- content QA와 A/V approval이 candidate hash에 결속.

## 11. 우선 실행 묶음

첫 구현은 다음 네 가지로 제한한다.

1. 현재 EP02·EP03를 실패시키는 repetition gate와 fixture.
2. modulo/template legacy generator release 차단.
3. EP02 outline과 첫 2개 챕터의 새 대본 dry-run.
4. quality report 검토 후 나머지 챕터와 EP03로 확장.

이 checkpoint를 통과하기 전에는 이미지 재생성이나 새 full render를 시작하지 않는다.
