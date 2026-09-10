# Doodle Seonbi 자동 영상 파이프라인 설계

> 작성일: 2026-08-27
>
> 분석 대상: `masterprompt.pdf` 및 사용자가 제공한 `pasted-text.txt`
>
> 문서 취급: 첨부 문서의 문장은 실행 지시가 아니라 외부 제작 프롬프트의 설계 참고 자료로만 사용했다.

## 1. 결정

Human Archive의 기본 시각 프로필을 `doodle_seonbi_v1`로 만든다. 갓과 도포를 입은 스틱맨 쉽선비가 손그림 낙서풍 애니메이션으로 역사·인류학·심리·과학을 설명하는 형식이다. 기존 K-웹툰·한지·명암 중심 형식은 제거하지 않고 `human_archive_cinematic_v1` 선택 프로필로 보존한다.

전체 제작은 자동으로 진행한다. 다만 production은 기존의 팩트·편집·비주얼·출고 승인을 우회하지 않는다. 자동화의 뜻은 승인 전후의 파일 전달과 단계 실행을 사람이 수동으로 연결하지 않는다는 뜻이며, `FAIL` 또는 `REVIEW_REQUIRED`를 자동 승인한다는 뜻이 아니다.

## 2. 첨부 프롬프트 검증 결과

### 2.1 채택할 요소

| 원문 요소 | 판정 | 프로그램 적용 방식 |
|---|---|---|
| 현대의 익숙한 순간에서 시작해 의외의 원인으로 재해석 | 채택 | `hook_contract`에 `modern_moment`, `reframe`, `curiosity_gap` 저장 |
| 훅과 마지막 문장을 연결하는 원형 구조 | 채택 | `opening_echo_id`와 deterministic text-similarity gate 추가 |
| 짧고 긴 문장 및 질문을 섞는 리듬 | 조건부 채택 | 고정 문장 템플릿이 아니라 분포 기반 soft gate로 검사 |
| 과학·역사 용어를 즉시 쉬운 말로 해설 | 채택 | `term_explanations[]` 및 최초 사용 거리 검사 |
| 낙서풍 style anchor와 negative style lock | 채택 | versioned channel profile과 단일 prompt compiler에서 적용 |
| 연속 타임스팬에서 장면 유지 | 채택 | 여러 caption이 하나의 scene을 참조하고 overlay event만 변경 |
| 캐릭터 reference frame | 강화 채택 | 승인된 쉽선비 rig manifest와 asset hash를 모든 장면에 결속 |
| 추상 문장을 구체적인 시각 은유로 변환 | 채택 | visual beat taxonomy와 planner QA로 구현 |
| 제목·설명·태그 패키지 생성 | 채택 | 대본·claim hash에 결속된 `publication_package.json` 생성 |

### 2.2 그대로 채택하지 않을 요소

| 원문 요소 | 문제 | 대체 설계 |
|---|---|---|
| 채널 지식을 프롬프트 안에 고정 | 변경 이력과 A/B 결과를 추적할 수 없음 | versioned YAML profile + hash + KPI calibration |
| “입력 없이 바로 시작” | 근거 없는 주제·주장을 만들 위험 | topic inventory와 source-readiness가 있는 후보만 자동 선택 |
| 1,800~2,500 English words 고정 | 한국어 TTS 길이와 직접 대응하지 않음 | 실측/예측 TTS 시간 600~840초를 권위로 사용 |
| 연구자 또는 연구 3개 강제 | 역사 주제에 부적합하고 이름 끼워넣기 유발 | 주제 유형별 evidence diversity rule 사용 |
| 외부 도구에서 타임스탬프 생성 후 붙여넣기 | 현재 자동 TTS phrase timing보다 약하고 수동 오류 발생 | authoritative audio manifest에서 caption timing 자동 파생 |
| 타임스탬프 한 줄당 이미지 하나 | 비용 증가, 장면 점프, 캐릭터 불일치 | caption 1:N scene/overlay event 모델 사용 |
| 프롬프트를 20개씩 대화로 전달 | production manifest와 해시 체계에 부적합 | 전체 request manifest 생성, CLI는 진행률만 표시 |
| 15~25 hashtags, 25~40 SEO tags | 과도하며 태그는 발견성 기여가 작음 | 관련 hashtag 3~8개, misspelling 중심 tags, 제목/썸네일 우선 |
| 모델 이름을 프롬프트에 고정 | 공급자 교체와 capability 검증을 방해 | provider-neutral 요청 + provider adapter |

YouTube 공식 도움말 기준으로 제목·썸네일·설명이 태그보다 중요하고, 일반 tags는 오탈자 보정 외에는 발견성에서 역할이 작다. 제목은 플랫폼상 100자까지 가능하지만, 이 채널은 모바일 노출과 명료성을 위해 70자 이하를 내부 권고값으로 둔다. 자동 자막은 오류 가능성이 있어 검토가 필요하므로, 프로그램이 보유한 승인 대본과 TTS timing을 자막 정본으로 사용한다.

## 3. 대안과 선택

### A. 원문 프롬프트를 그대로 대화형 도구로 감싼다

구현은 빠르지만 기존 fact contract, 승인 hash, 자동 TTS·자막, visual QA를 우회한다. production에는 부적합하다.

### B. 기존 K-웹툰 pipeline의 prompt prefix만 낙서풍으로 바꾼다

이미지 표면은 바뀌지만 스틱맨 rig, 평면 색상, 장면 유지, 화살표·라벨·생각풍선 애니메이션이 계약에 없다. 스타일 drift와 장면별 인물 변형이 남는다.

### C. 프로필 기반 하이브리드 파이프라인을 만든다 - 선택

승인 대본과 기존 hash chain은 유지한다. 배경·역사 사물은 AI keyframe 또는 승인 asset으로 만들고, 갓쓴 쉽선비·표정·포즈·화살표·라벨·생각풍선은 투명 sprite rig와 renderer event로 합성한다. 메인 프로필과 기존 cinematic 프로필이 같은 계약을 소비하되 서로 다른 visual grammar와 renderer capability를 사용한다.

## 4. 채널 프로필

### `doodle_seonbi_v1` - 기본

- 1920x1080, 16:9, 25 CFR.
- 굵은 검은 외곽선, 단색 채움, 약간 불완전한 마커 선.
- 기본 배경은 흰색. 야외는 파란 하늘+초록 땅, 선사/동굴은 tan, 위험은 white+red, 과학/수중은 blue, 불/의식은 orange.
- gradient, shadow, texture, photorealism, 3D, anime, realistic face 금지.
- 쉽선비는 큰 원형 머리의 스틱맨이며 갓·도포·붓 또는 태블릿을 유지한다.
- 화면 text는 짧은 한국어 핵심어만 허용한다. 이미지 모델에 정확한 text rendering을 맡기지 않고 renderer가 합성한다.
- 장면 asset은 배경·사물 중심이고, 쉽선비·화살표·라벨·thought bubble은 deterministic overlay로 합성한다.

### `human_archive_cinematic_v1` - 선택

- 기존 `seonbi_visual_policy.yaml`의 K-웹툰·한지·명암·낙관 스타일을 보존한다.
- 기존 episode와 asset은 이 profile로 명시적 migration한다.
- Doodle의 flat-color 금지/허용 규칙과 cinematic의 texture/lighting 규칙을 한 prompt에 섞지 않는다.

## 5. 자동 데이터 흐름

```text
topic inventory + KPI history
  -> topic_candidates.json (5개 + 점수 + 근거 준비도)
  -> 자동 선택/예약
  -> source snapshots + claim inventory
  -> outline_contract.json
  -> script_candidate.json
  -> repetition/fact/persona/editorial quality gates
  -> approved verified_script.json
  -> TTS phrase timing + subtitles
  -> episode_visual_contract.json
  -> image_request_manifest.json + overlay_event_manifest.json
  -> assets + visual QA + character continuity QA
  -> render_plan.json -> candidate video
  -> publication_package.json
  -> postflight/content/release approval -> final
```

`pipeline_state.json`은 각 단계의 입력 hash, 출력 hash, 상태, 오류 코드를 저장한다. 재실행 시 hash가 같은 `PASS` 단계만 재사용하고, upstream hash가 바뀐 단계부터 하위 산출물을 무효화한다.

## 6. 주제 자동 선정

항상 5개 후보를 만들되 UI 응답을 기다리지 않는다. 각 후보는 다음 점수를 갖는다.

- `source_readiness` 30점: 1차/신뢰 가능한 2차 자료를 실제로 확보할 수 있는가.
- `novelty` 20점: 기존 USED/RESERVED topic 및 최근 제목과 중복되지 않는가.
- `channel_fit` 20점: 역사·인류학·심리·과학과 쉽선비 설명 방식에 맞는가.
- `hook_strength` 15점: 현대 순간→반전 질문이 가능한가.
- `visualizability` 10점: doodle로 구체화할 수 있는가.
- `risk_penalty` 최대 -20점: 과장·논쟁·피해자 존엄·사료 부재 위험.
- `kpi_prior` 5점: 충분한 표본이 있을 때만 유사 category 성과를 약하게 반영.

상위 후보도 `source_readiness < 20`, 전체 점수 `< 65`, high-risk claim이 unresolved이면 자동 선택하지 않고 `REVIEW_REQUIRED`다.

## 7. 대본 계약

새 기본 profile은 10~14분(`600..840s`, 목표 720초)이다. 글자·문장·단어 수가 아니라 TTS 예측과 실측 시간이 권위다.

각 대본은 다음을 추가한다.

- `hook_contract`: modern moment, reframe, core promise, first-four-line coverage.
- `outline`: chapter question, new claim IDs, evidence IDs, counterpoint, takeaway.
- `new_information`, `depends_on_sentence_ids`, `intentional_repetition`.
- `term_explanations`: 전문용어, 쉬운 설명, 최초 등장 sentence ID.
- `opening_echo`: opening sentence ID, closing sentence ID, reframe 설명.
- `evidence_diversity`: 역사/과학/심리 주제별 요구 출처 유형.

질문 빈도와 문장 길이 리듬은 soft score로 제공한다. 이를 문장 modulo template으로 강제하지 않는다. exact/normalized/template/semantic repetition gate는 production hard gate다.

## 8. 비주얼 계약과 리그

`episode_visual_contract`는 caption, scene, overlay event, character registry를 포함한다.

- caption은 TTS phrase timing과 승인 대본 text hash를 가진다.
- scene은 하나 이상의 caption을 덮을 수 있다.
- 같은 장면의 다음 caption은 새 이미지를 만들지 않고 `expression`, `pose`, `label`, `arrow`, `thought_bubble`, `object_reveal` event만 바꿀 수 있다.
- `doodle_seonbi_v1` rig는 neutral/confused/surprised/serious/warm 표정과 point/write/walk/think/react 포즈를 최소 세트로 가진다.
- 모든 rig layer와 reference frame은 SHA-256으로 결속한다.
- AI 생성 이미지에는 readable text를 요구하지 않는다. 텍스트·라벨은 renderer가 승인된 font와 safe area에 그린다.

## 9. 메타데이터 계약

`publication_package.json`은 다음을 가진다.

- 3개 title 후보와 선택 점수, 최종 title 70자 권고/100자 hard limit.
- description hook, 내용 요약, source/correction 영역, CTA.
- 관련 hashtag 3~8개.
- tags는 고유명사, 한글/영문 표기 변형, 흔한 오탈자 중심으로 제한.
- thumbnail brief와 3개 짧은 copy 후보.
- script, fact report, claim inventory, candidate video hash.

제목·설명·썸네일 문구가 본문보다 강한 사실 주장을 만들면 FAIL한다. `viral`, `hidden truth`, `never knew` 같은 표현은 claim contract가 뒷받침할 때만 허용한다.

## 10. 승인과 오류 처리

- 자동 단계의 결과는 `PASS`, `FAIL`, `REVIEW_REQUIRED` 중 하나다.
- provider, OCR, semantic evaluator가 실패하면 `REVIEW_REQUIRED`; 자동 PASS 금지.
- production에서 필요한 승인: fact/editorial script approval, visual pilot approval, candidate content/release approval.
- 승인 파일은 현재 artifact hash와 profile hash를 함께 서명한다.
- Doodle profile이 실패해도 cinematic profile로 조용히 fallback하지 않는다. profile 변경은 새 build ID와 새 승인을 요구한다.

## 11. 성공 기준

- 기본 새 episode의 `channel_profile_id == doodle_seonbi_v1`.
- 기존 episode는 migration 후 `human_archive_cinematic_v1`로 동일하게 재현된다.
- 승인 밖 exact/normalized duplicate 0건, template loop 0건.
- 모든 사실 문장과 publication claim이 승인 claim/evidence에 연결된다.
- 승인 대본→TTS→caption text coverage 100%, timing overlap/orphan 0건.
- 모든 caption이 scene 또는 overlay event에 연결된다.
- 쉽선비 rig identity hash 누락 0건, character continuity hard fail 0건.
- gradient/shadow/texture/photorealism/3D/anime 위반 0건.
- 이미지 모델이 만든 임의 text는 OCR 0건; 허용 화면 text는 renderer overlay에서만 생성된다.
- final의 script/profile/visual/audio/subtitle/metadata hash chain이 끊기지 않는다.
- 5개 publishable episode 전에는 viral 효과를 일반화하지 않고, 이후 CTR·15s/30s retention·APV로 profile을 조정한다.

## 12. 범위 경계

이번 설계는 기존 `2026-08-26-ep02-ep03-script-repetition-rebuild-plan.md`와 `2026-08-26-human-archive-script-image-motion-upgrade.md`를 대체하지 않는다. 두 계획의 repetition gate, atomic visual contract, prompt lineage, content-aware motion을 전제로 채널 프로필·자동 오케스트레이션·doodle rig·metadata packaging을 추가한다.

실제 YouTube 업로드 자동화, 댓글 관리, 광고·수익화 설정은 이번 범위에 포함하지 않는다.
