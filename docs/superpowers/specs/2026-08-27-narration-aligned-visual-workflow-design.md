# 내레이션 정렬형 시각 워크플로우 설계

> 작성일: 2026-08-27
>
> 상태: 사용자 승인 완료
>
> 근거: `docs/superpowers/specs/2026-08-27-human-library-top30-script-visual-benchmark.md`
>
> 대체 범위: `docs/superpowers/specs/2026-08-27-doodle-seonbi-channel-pipeline-design.md`의 장면 밀도·호스트 할당 규칙과 `docs/superpowers/plans/2026-08-27-ep02-doodle-visual-role-and-text-qa-rebuild.md`의 15~25% 호스트 및 분산 8장 단독 파일럿 규칙을 이 문서가 대체한다. 팩트 승인, 해시 계보, OCR, canonical host overlay, 릴리스 게이트는 유지한다.

## 1. 결정

Human Archive의 기본 장편 시각 프로필을 `narration_aligned_hybrid_v1`로 추가한다. 이 프로필은 실제 문장별 TTS 시간을 정본으로 사용해 9~12초 단위 샷을 만들고, 각 샷의 주장·인물·행동·장소를 구조화한 뒤 이미지를 생성한다.

쉽선비는 전체 화면의 주인공이 아니라 채널 브랜드 진행자다. 전체 샷의 8~12%에서 인트로, 장 전환, 핵심 종합에만 deterministic overlay로 등장한다. 역사 재현, 장소, 지도, 메커니즘, 증거 장면은 내레이션이 말하는 대상을 화면의 주인공으로 삼는다.

EP02는 기존 `full-v4-001`과 `full-v4-002`를 수정하거나 덮어쓰지 않고 `full-v5-001`에서 새 계약으로 재구축한다.

## 2. 목표와 비목표

### 목표

- 18~20분 대본에서 고정 45장 또는 문자 수 기반 63장이 아니라 실제 TTS 길이에 맞춰 약 95~120장을 계획한다.
- 한 샷의 내레이션과 이미지 사이에 검증 가능한 `semantic_anchors`를 둔다.
- 프롬프트 컴파일러가 인물·행동·장소를 일반 책상·책·두루마리로 덮어쓰지 못하게 한다.
- 정책 차단 재시도에서도 장면의 핵심 의미를 유지한다.
- 연속적인 시각 붕괴와 전체 분포 문제를 전체 생성 전에 발견한다.
- 이미지 유형과 내레이션에 맞는 모션을 선택하고 자막·렌더 계보를 유지한다.
- 동일한 명령으로 다른 에피소드에도 적용할 수 있게 episode-neutral 경로와 계약을 사용한다.

### 비목표

- 인류의서재의 그림을 복제하거나 특정 작가의 고유 화풍을 모사하지 않는다.
- 인기 영상의 자동 자막을 역사적 사실의 출처로 사용하지 않는다.
- 생성 모델이 정확한 연도·한글·지도 라벨을 그리도록 요구하지 않는다.
- 정책 차단을 우회하거나 계정을 자동 전환하지 않는다.
- 기존 승인·팩트·출고 게이트를 자동 승인하지 않는다.

## 3. 기본 프로필의 불변 조건

`human_archive/config/visual_pacing_profiles.yaml`에 다음 값을 정본으로 저장한다.

```yaml
narration_aligned_hybrid_v1:
  min_shot_sec: 9.0
  target_shot_sec: 10.5
  max_shot_sec: 12.0
  hard_max_shot_sec: 15.0
  max_sentences_per_shot: 2
  host_ratio_min: 0.08
  host_ratio_max: 0.12
  host_min_non_host_gap: 7
  max_same_mode_streak: 2
  max_evidence_streak: 1
  motif_window_shots: 10
  max_motif_occurrences_per_window: 2
  cold_open_pilot_shots: 12
  cold_open_pilot_max_sec: 120.0
  coverage_pilot_shots: 8
  max_policy_auto_retries: 2
```

화면은 1920x1080, 16:9, 25 CFR이며 base image에는 읽을 수 있는 글자·숫자·연도·캡션·간판·워터마크·서비스 마크를 허용하지 않는다. 필요한 글자와 지도 라벨은 `overlay_event_manifest.json`을 통해 렌더러가 합성한다.

시각 스타일 ID는 `doodle_seonbi_narrative_v2`다. 손으로 그린 검은 잉크 윤곽, 절제된 따뜻한 파스텔 색, 은은한 미색 종이 바탕을 사용하되 장면은 전경·중경·배경으로 화면을 채운다. 사진, 3D, anime, 사실적 얼굴, 포스터·카탈로그·분할 패널, 불필요한 넓은 빈 공간은 금지한다. 넓은 빈 공간은 `host_chapter_hinge`의 canonical overlay 안전 영역에만 허용한다. 이 스타일은 벤치마크 채널의 고유 그림을 복제하지 않고 정보 밀도와 편집 문법만 반영한다.

## 4. 권위 데이터 흐름

```text
승인 대본 + claim inventory
        │
        ▼
문장별 TTS 생성 ──────────────► sentence_audio_manifest.json
        │                                  │
        │                                  ▼
        │                      실측 시간 기반 샷 분할
        │                                  │
        │                                  ▼
        │                         shot_timing_manifest.json
        │                                  │
        │                    Codex CLI 구조화 시각 브리프
        │                                  │
        │                                  ▼
        └──────────────────────► visual_brief_manifest.json
                                           │
                                           ▼
                              shot_alignment_manifest.json
                                           │
                       ┌───────────────────┴───────────────────┐
                       ▼                                       ▼
          image_request_manifest.json            scene_audio_manifest.json
                       │                                       │
                       ▼                                       ├─► subtitles.ass
             이중 파일럿→Flow 전체 생성                       │
                       │                                       ▼
                       └────────────► 모션 클립 ─────────► 최종 렌더
```

대본 해시는 문장 TTS, 샷 타이밍, 시각 브리프, 이미지 요청, 자막, 렌더까지 전 단계에 전파한다. 어느 단계든 상위 해시가 달라지면 기존 승인과 하위 자산은 stale로 처리한다.

## 5. TTS 우선 타임라인

현재 `build_audio_master_v2.py`는 샷 계약을 먼저 읽고 샷별 TTS를 만든다. 새 프로필에서는 순서를 뒤집는다.

1. 승인된 `script_candidate.json`의 문장을 순서대로 합성한다.
2. 각 문장의 실제 WAV 길이와 0.35초 간격을 기록한다.
3. 전체 master audio를 만든다.
4. 샷이 확정되면 문장 타임라인을 샷 단위 `scene_audio_manifest.json`으로 투영하되 음성을 다시 합성하지 않는다.

`sentence_audio_manifest.json`의 필수 구조는 다음과 같다.

```json
{
  "schema_version": 1,
  "episode_id": "HA002",
  "script_sha256": "SCRIPT_SHA256",
  "master_audio": "master_audio_48k.wav",
  "total_duration_sec": 1080.0,
  "gap_sec": 0.35,
  "sentences": [
    {
      "sentence_id": "S001",
      "order": 1,
      "chapter": 1,
      "beat": "hook",
      "tts_text": "승인된 첫 문장",
      "start_sec": 0.0,
      "end_sec": 8.7,
      "duration_sec": 8.7,
      "audio_file": "S001.wav",
      "provenance": {}
    }
  ]
}
```

문장 누락, 순서 중복, 음수 시간, 겹치는 시간, 대본 해시 불일치는 실패다.

## 6. 실측 시간 기반 샷 분할

샷 분할은 deterministic 단계다. 모델이 샷 수나 시간을 임의로 바꾸지 못한다.

1. 장 경계는 항상 강제 분할한다.
2. claim ID 변경, `그런데/하지만/그렇다면/결국/문제는` 같은 반전·전환, beat 변경을 선호 분할점으로 둔다.
3. 한 문장을 기본 샷으로 시작하고 9초 미만일 때만 다음 문장을 합친다.
4. 합친 결과가 12초를 넘거나 2문장을 넘으면 합치지 않는다.
5. 단일 문장이 12초를 넘으면 `segments[]` 또는 쉼표·접속어 절 경계에서 시간 비례로 나눈다.
6. 의미 있는 절 경계가 없으면 최대 15초까지 허용하고 `duration_exception`을 기록한다. 15초 초과는 실패다.
7. 샷 ID는 에피소드와 순서에만 의존하는 안정된 형식 `ha002_v5_shot_001`을 사용한다.

`shot_timing_manifest.json`에는 `shot_id`, `order`, `chapter`, `start_sec`, `end_sec`, `duration_sec`, `sentence_spans`, `claim_ids`, `boundary_reason`을 저장한다. `sentence_spans`는 문장 전체 또는 문장 내부 절의 `char_start`, `char_end`, `start_sec`, `end_sec`를 포함한다.

## 7. 구조화 시각 브리프

문자열 키워드 규칙만으로 역사적 주체와 행동을 안정적으로 추출하기 어렵다. 샷 시간은 deterministic하게 고정한 뒤 Codex CLI를 JSON Schema 출력 모드로 사용해 시각 브리프만 작성한다.

실행기는 shell 문자열을 만들지 않고 인수 배열과 표준입력을 사용한다.

```text
codex exec
  --ephemeral
  --sandbox read-only
  --output-schema human_archive/schemas/visual_brief_manifest.schema.json
  --output-last-message C:\Temp\visual-brief-output.json
  --cd D:\module\bible
  -
```

테스트와 오프라인 재현을 위해 `json-file` provider도 제공한다. Antigravity CLI는 조사 시점에 실행 파일이 설치되어 있지 않으므로 정식 provider로 넣지 않는다. OmniRoute는 선택 확장점으로 남기되 이 설계의 성공 조건에는 포함하지 않는다.

시각 브리프의 필수 필드는 다음과 같다.

- `shot_id`
- `narration_digest`: 내레이션을 바꾸지 않는 한 문장 요약
- `visual_mode`
- `semantic_anchors[]`: `anchor_id`, `kind`, `source_text`, `visual_token`, `required`
- `focal_subject`
- `action`
- `place`
- `era`
- `shot_scale`: `wide`, `medium`, `close`, `top_down`, `diagram`
- `camera`
- `foreground`, `midground`, `background`
- `continuity_group`
- `reference_asset_ids[]`
- `prop_motifs[]`
- `text_overlay_policy`
- `overlay_items[]`: `overlay_id`, `kind`, `text`, `source_anchor_id`, `anchor`, `start_offset_sec`, `end_offset_sec`
- `motion_profile`
- `safety_treatment`

모델은 내레이션의 사실을 추가하거나 인물·장소를 바꿀 수 없다. 모든 `required` 앵커는 승인 대본 또는 claim inventory의 source span에 연결돼야 한다. `overlay_items[].text`도 승인 대본 또는 승인된 고유명사 표기의 부분 문자열이어야 하며, 이미지 프롬프트에는 들어가지 않고 renderer manifest로만 전달된다. `reference_asset_ids`는 승인된 character/reference asset manifest에 존재하는 ID만 허용한다.

## 8. 시각 모드와 선택 기준

| `visual_mode` | 선택 조건 | 화면의 중심 | 금지되는 기본 대체 |
|---|---|---|---|
| `event_reconstruction` | 인물의 행동·결정·충돌 | 역사 인물과 구체적 행동 | 빈 방, 일반 책상 |
| `place_establishing` | 장소·환경·규모가 주장 핵심 | 장소와 그곳의 생활 흔적 | 고립된 상징 아이콘 |
| `route_map` | 이동·거리·분포·영역 | 라벨 없는 지도와 경로 | 문서 더미 |
| `mechanism_diagram` | 유전·정치 구조·인과 과정 | 단계·관계가 보이는 도식 | 장식용 콜라주 |
| `evidence_artifact` | 증거·연구 방법 자체가 핵심 | 서술된 특정 유물·문서와 맥락 | 일반 책·두루마리 순환 |
| `modern_analogy` | 추상 개념을 현대 비유로 설명 | 하나의 구체적 비유 상황 | 서로 무관한 아이콘 모음 |
| `atmosphere_transition` | 장·시간·정서 전환 | 장소·날씨·시간 변화 | 빈 종이 카드 |
| `host_chapter_hinge` | 인트로·장 전환·핵심 종합 | base vignette + canonical host overlay | 생성된 쉽선비 |

기존 `visual_role`은 다음처럼 파생한다.

```text
host_chapter_hinge                              -> host_explainer
event_reconstruction, place_establishing       -> historical_reconstruction
evidence_artifact                              -> evidence_object
route_map, mechanism_diagram, modern_analogy   -> diagram_metaphor
atmosphere_transition                          -> atmosphere
```

## 9. 시퀀스 제약과 쉽선비

시각 브리프 생성 후 `validate_visual_sequence()`가 전체 배열을 검사한다.

- 쉽선비 8~12%; 에피소드가 짧아 정수 반올림 오차가 생기면 범위에 가장 가까운 수를 사용한다.
- 쉽선비 연속 최대 1장.
- 쉽선비 사이 최소 7개 비호스트 샷.
- `evidence_artifact` 연속 최대 1장.
- 같은 모드 연속 최대 2장.
- 같은 `prop_motif`는 10장 창에서 최대 2회.
- 같은 `novelty_signature`는 0회 중복.
- 필수 semantic anchor coverage 100%.

쉽선비 장면은 생성 모델에 인물을 요청하지 않는다. 배경 base에는 왼쪽 또는 중앙의 맥락 장면과 overlay 안전 영역을 만들고 `human_archive/assets/doodle_seonbi_v1.png`를 합성한다. costume, anchor, asset SHA가 canonical manifest와 다르면 실패한다.

역사적 주요 인물은 `continuity_group`과 reference asset SHA를 공유한다. 동일 인물이 장면마다 한복 색·관모·성별·연령이 바뀌면 `character_continuity` 축에서 실패한다.

## 10. 프롬프트 컴파일 계약

프롬프트 컴파일러는 브리프의 내용을 번역·정리할 수 있지만 의미를 대체할 수 없다.

```text
style prefix
+ era/place
+ required semantic anchors
+ focal subject and concrete action
+ foreground/midground/background
+ shot scale and camera
+ mode-specific composition
+ no-text instruction
```

현재 `_HOST_BASE_VIGNETTES`와 `_EVIDENCE_OBJECT_VIGNETTES` 순환 배열은 제거한다. `evidence_artifact`도 브리프에 특정 유물이 없으면 컴파일을 거부한다. 모든 request에는 다음 메타데이터를 보존한다.

- `visual_mode`
- `semantic_anchors`
- `continuity_group`
- `reference_asset_ids`
- `motion_profile`
- `novelty_signature`
- `source_sentence_spans`
- `alignment_sha256`

`prompt_alignment_report.json`은 요청마다 필수 앵커 보존 여부와 시퀀스 제약 결과를 기록한다. `overlay_items`는 `overlay_event_manifest.json`으로 분리하고 현재 alignment SHA에 결속한다. 이 보고서가 PASS가 아니면 Flow 브라우저를 열지 않는다.

## 11. 정책 차단 처리

정책 차단은 장면 하나의 상태 변화이며 전체 시각 문법을 사물 카드로 바꾸는 신호가 아니다.

자동 재시도 사다리는 두 단계다.

1. `safe_rephrase`: 같은 인물·장소·행동을 유지하면서 비그래픽, 비폭력적, 교육용 역사 일러스트로 표현한다. 상처·시신·직접 위해는 결과가 드러나지 않는 직전·직후·원거리 장면으로 바꾼다.
2. `safe_abstraction`: 같은 주장과 장소를 유지하면서 실루엣, 원거리 군중, 지도, 관계 도식, 상징적 환경 중 원래 모드에 가장 가까운 표현으로 바꾼다.

두 번 모두 다음 값은 바꿀 수 없다.

- `required` semantic anchor의 ID와 source span
- claim IDs
- era와 place
- 장면이 전달해야 하는 인과관계

두 번 실패하면 해당 샷을 `REVIEW_REQUIRED`로 두고 배치를 중단한다. 계정 변경, 모델 강제 전환, 무한 재시도, 다른 장면의 최신 URL 재사용은 금지한다. 모든 실패 자산과 요청은 `rejected_policy_variants/{shot_id}/`에 보존한다.

## 12. 이중 파일럿과 전체 생성

`--pilot`은 다음 두 집합의 합집합만 생성한다.

- `cold_open`: 처음 12장 또는 시작 후 120초까지
- `coverage`: 장·모드·주요 continuity group을 최대한 포괄하는 8장

파일럿 승인에는 `pilot_sets`, current contract SHA, request manifest SHA, 각 자산 SHA, 각 샷의 평가축이 포함된다. 전체 생성 중 새 행이 추가되어 manifest 전체 해시가 바뀌어도 승인한 파일럿 자산 fingerprint가 같으면 승인을 유지한다.

콘택트시트는 이미지 아래에 다음 정보를 표시한다.

```text
shot_id | 00:42.1-00:52.4 | event_reconstruction
내레이션 요약
anchors: 숙종 / 대신 / 조정 회의
```

콜드오픈 시트와 커버리지 시트는 별도 파일로 생성한다. 두 시트가 모두 승인되지 않으면 `--all`은 실패한다.

## 13. QA 게이트

### 생성 전

- 스키마와 해시
- 모든 문장/절 span의 정확한 1회 커버리지
- 9~12초 분포와 15초 hard max
- semantic anchor coverage
- host/mode streak
- motif window
- prompt/novelty signature 중복
- base prompt의 글자·숫자 금지

### 생성 후 자동 검사

- 파일 존재, 1920x1080, SHA
- stale request hash
- OCR 및 서비스 마크
- 전체·인접 pHash 중복
- canonical host overlay SHA
- reference asset과 continuity group 계보

### 생성 후 의미 검사

Codex CLI vision 평가와 사람 승인을 구분해 기록한다. 기계 평가는 `semantic_match`, `required_anchor_presence`, `visual_mode_match`, `character_continuity`, `composition_density`, `embedded_text`, `style_profile`, `dignity`, `service_mark`를 평가한다. 기계 평가가 PASS여도 사람의 현재 해시 승인 없이 렌더하지 않는다.

## 14. 모션·자막·렌더

`motion_profile`은 브리프에서 파생한다.

| 시각 모드 | 기본 모션 |
|---|---|
| 사건 재현 | 느린 push-in 또는 행동 방향 pan |
| 장소 전경 | 넓은 sweep 또는 미세 pull-out |
| 지도 | 경로 방향 pan; 라벨은 renderer reveal |
| 메커니즘 도식 | 단계별 overlay reveal + 짧은 push |
| 증거·유물 | 제한된 parallax 또는 close push |
| 현대 비유 | focal subject를 향한 pan |
| 분위기 전환 | 느린 drift |
| 쉽선비 | base의 미세 drift, host overlay는 고정 또는 제한된 pose event |

한 이미지가 12초를 넘는 예외 샷은 동일 이미지를 그대로 정지하지 않고 두 crop state로 나누되 새 의미 샷으로 집계하지 않는다. 모션은 내레이션 시간과 정확히 같은 프레임 수를 사용한다.

자막은 `sentence_audio_manifest.json`의 문장 시간을 정본으로 만들고, 샷 타임라인과 독립적으로 유지한다. 최종 렌더는 `shot_alignment_manifest.json`, `scene_audio_manifest.json`, `asset_manifest.json`, `subtitles.ass`의 현재 해시를 기록한다.

## 15. 버전과 호환성

- 새 canonical build: `human_archive/runs/ep02_jang_huibin/full-v5-001`
- 새 canonical visual contract: `shot_alignment_manifest.json`
- 호환 출력: `episode_visual_contract_v3.json`, `source/shot_contract_v5.json`, `flow_image_prompts.json`
- 기존 v2/v4 계약은 읽기 전용 fallback으로 유지한다.
- renderer와 QA는 build-local `source/shot_contract_v5.json`을 먼저 찾고, 없을 때만 기존 parent `source/shot_contract_v4.json`과 `shot_contract.json`을 찾는다.
- 실패한 `full-v4-001` 자산과 보고서는 회귀 증거로 보존하며 v5에 복사하지 않는다.

## 16. 승인 기준

EP02 전체 생성을 시작하기 전 다음을 모두 만족해야 한다.

- 실측 master audio 길이를 기준으로 95~120장 범위 또는 명시적 profile exception
- 평균 샷 길이 9~12초, 개별 hard max 15초
- 문장·절 span 누락과 중복 0건
- 필수 semantic anchor coverage 100%
- 쉽선비 8~12%, 연속 1장 이하, 간격 7장 이상
- `evidence_artifact` 연속 1장 이하
- 같은 일반 소품 10장 중 2회 이하
- prompt 및 novelty signature 완전 중복 0건
- 콜드오픈 12장과 분산 8장 파일럿 모두 승인

최종 렌더 전에는 추가로 다음을 만족해야 한다.

- 계획된 모든 자산이 현재 request SHA로 1회 존재
- OCR 글자·숫자·서비스 마크 0건
- pHash 근접 중복 0건 또는 사람이 승인한 의도적 continuity 예외
- semantic/image mode/character continuity 평가 PASS
- canonical host overlay 계보 PASS
- motion, subtitle, render, postflight release PASS

## 17. 실패 및 롤백

새 파이프라인이 실패해도 기존 v4 파일을 수정하지 않는다. v5의 단계별 manifest와 `.part` 파일만 정리하고, 성공한 현재 해시 자산은 재실행 때 재사용한다. 프로필을 `legacy_role_v2`로 명시하면 기존 에피소드의 읽기·렌더 경로는 유지되지만 EP02 v5 출고에는 사용할 수 없다.
