# 「계획서_HERMES_최종영상_파이프라인」 리뷰

작성일: 2026-08-07  
대상: `C:\Users\amd\module\계획서_HERMES_최종영상_파이프라인.md`  
검토 범위: Module 산출물, `modern/checks.py`, smoke 실행 스크립트, Hermes TTS·렌더·CapCut 런북

## 결론

계획서의 큰 방향은 좋다. `Module → jobDir → TTS → MP4 → CapCut editable draft`라는 경계가 명확하고, Preview를 먼저 통과시킨 뒤 Full/CapCut으로 확장하는 순서도 안전하다. 특히 CapCut 20분 제한, 수동 Export, 캡션·미디어의 사람 검수 필요성을 문서에 명시한 점은 현실적이다.

그러나 현재 문서는 “구현된 사실”, “계획”, “외부 Hermes 런북의 검증된 capability”를 한 흐름으로 서술한다. 이 상태에서 바로 실행하면 다음 문제가 생긴다.

- Module 쪽에는 `draft.json`, `scenes.json`, `shot_plan.json`이 없고, 계획서에 적힌 `pack-modern-smoke-job.mjs`도 현재 존재하지 않는다.
- 씬 분할의 핵심 규칙인 70자 제한이 Module 어댑터에서 실제로 강제되지 않는다. Hermes TTS는 `max_chunk_length=130`을 사용하므로 음성 내부 분할과 이미지 씬 분할의 계약이 다르다.
- TTS 후처리 실패가 manifest의 `ok: true`와 함께 남을 수 있어, 렌더 단계가 불완전한 WAV를 정상 입력으로 받을 위험이 있다.
- 렌더러·CapCut 재조립 스크립트에 사용자 PC 절대경로가 중복 하드코딩되어 `PATHS.md`만 고쳐서는 경로가 바뀌지 않는다.
- 인트로를 프리롤로 붙일지 Hermes 씬으로 넣을지 결정되지 않아, 영상·대사·자막이 중복되거나 첫 씬 싱크가 어긋날 수 있다.

따라서 먼저 데이터 계약과 검증기를 구현하고, Preview 16씬을 “재현 가능한 한 명령”으로 통과시킨 뒤 Full과 CapCut으로 확장해야 한다.

## 확인된 구현-계획 불일치

| 항목 | 계획서의 상태 | 실제 확인 | 개선 방향 |
|---|---|---|---|
| Job 패커 | Phase 1에서 구현 예정 | `module/modern/scripts/pack_hermes_job.mjs`, `C:\Users\amd\hermes\scripts\pack-modern-smoke-job.mjs` 모두 없음 | Module 안에 단일 패커를 만들고, 입력·출력 manifest를 명시 |
| Hermes 입력 | `draft.json`과 `scenes`가 준비된 것처럼 설명 | smoke run에는 `draft.json`, `scenes.json`, `shot_plan.json`이 없음 | `shot_plan.md`를 수동 파싱하지 말고 JSON을 정식 원본으로 생성 |
| 씬 글자 제한 | 약 70자 권장 | TTS 엔진은 `max_chunk_length=130`; 이미지 씬 단위 70자 검사는 없음 | `narration` 길이·문장 경계·TTS chunk를 각각 검증 |
| 오디오 성공 판정 | WAV 생성 후 렌더 | `make-scenes-tts.py`는 후처리 예외를 출력만 하고 계속 진행 | 후처리 실패 시 non-zero 종료, manifest `ok:false` |
| 경로 설정 | env 확장 권장 | 렌더러 `ROOT`, `TTS_ROOT`, `PY_TTS`가 절대경로 고정; 재조립에도 동일 경로 존재 | `PATHS.json` 또는 환경변수 단일 해석기로 통합 |
| CapCut 장기 길이 | 60/90/120분 계획 언급 | 런북상 현재 Hermes 경로는 1,200초까지만 자격 인정, 60/90/120분은 별도 검증 필요 | 지원/미지원/검증 대기 상태를 분리하고 자동 라우팅 금지 |

## P0 개선사항

### 1. 정식 Job 계약을 먼저 고정

현재 최소 `draft.json`만으로는 이미지 파일, 인트로, 오디오 정책, 캡션 정책, 해시, 렌더 버전을 재현하기 어렵다. 다음 계약을 권장한다.

```text
job/
  job.json                    # schema_version, job_id, title, aspect, policy
  draft.json                  # Hermes 렌더 입력
  scenes.json                 # 씬별 narration의 정식 입력
  shot_plan.json              # 시각·챕터·비트·소스 경로
  scene-media-manifest.json   # 정규화된 media 경로, sha256, width, height
  scene_audio_manifest.json   # WAV 경로, duration, sample rate, loudness, sha256
  render-options.json
  provenance.json             # source files/hash, tool versions, timestamps
  validation-report.json
  media/
  audio/
  captions/
```

`draft.json`은 파생 산출물로 취급하고, `scenes.json`과 `shot_plan.json`을 사람이 검토 가능한 원본으로 둔다. 모든 씬은 `scene_id`를 가져야 하며 단순 `order`만으로 연결하지 않는다. 재정렬·서브씬 분할 시 `scene_id=ch1_s03_a`처럼 안정적인 ID가 필요하다.

### 2. 텍스트 분할을 비율이 아니라 사건 경계 중심으로 구현

계획서의 “Ch1 16등분, Ch2~5 6등분”은 첫 smoke에는 편하지만 대사가 잘리는 위험이 크다. 다음 우선순위로 분할해야 한다.

1. 문장 끝과 인용부호 닫힘
2. 화자 발화 단위
3. 사건 카드의 시작·종료 경계
4. 목표 글자 수와 장면 길이

70자는 고정 하드 리밋보다 `권장 45~70자`, `경고 71~110자`, `분할 BLOCK 111자 이상`처럼 운영한다. 단, 한 문장을 억지로 자르면 TTS와 자막 모두 깨지므로 `서브씬`을 만들고 `parent_scene_id`를 보존해야 한다.

또한 TTS 엔진의 `max_chunk_length=130`은 음성 엔진 내부 chunk일 뿐, 영상 씬의 나레이션 상한이 아니다. 두 정책을 문서와 validator에서 분리해야 한다.

### 3. TTS manifest를 신뢰 가능한 증거로 변경

현재 `make-scenes-tts.py`는 `voice_audio_filter`나 peak normalize가 실패해도 예외를 출력하고 다음 단계로 진행한다. 이 동작은 “파일은 있으나 실제 정책이 적용되지 않은” 상태를 성공으로 오인하게 한다.

다음 검사를 추가한다.

- 입력 씬 수와 출력 WAV 수가 정확히 일치
- WAV 존재, 파일 크기, 재생 가능한 duration > 0
- sample rate/channel/bit depth 기록
- peak와 loudness를 함께 기록; peak normalize만으로 음량 일관성을 주장하지 않기
- 후처리 실패는 `ok:false`, `exit code != 0`
- 엔진 voice, speed, filter, TTS 버전, Python 경로를 manifest에 기록
- 동일 job 재실행 시 기존 WAV를 덮어쓰기 전에 job fingerprint 비교

`scene_audio_manifest.json`의 `ok:true`는 “모든 씬 생성·후처리·검증 성공”일 때만 허용해야 한다.

### 4. 렌더 전 media preflight를 추가

현재 계획은 파일명 매핑을 패커가 정규화한다고 되어 있지만, 렌더 전에 다음을 모두 검사하는 단계가 없다.

- 기대 scene 수와 실제 scene 수
- 모든 `scene_id`에 이미지 또는 영상이 정확히 하나씩 연결되는지
- 이미지 확장자·읽기 가능 여부·해상도·색상 모드
- 첫 프레임이 검은 이미지가 아닌지
- `scene_N_flow.jpg` 파일명과 manifest ID가 일치하는지
- 인트로가 별도 프리롤인지 씬 0인지
- 누락·고아 media·중복 order가 없는지

실패 시 렌더를 시작하지 말고, 누락 파일 목록과 예상 경로를 JSON/터미널 양쪽에 출력해야 한다.

### 5. 인트로 모드를 하나의 계약으로 고정

현재 A/B가 모두 남아 있고 P0는 A를 권장한다. 실제 구현에서는 아래 중 하나를 기본 정책으로 고정해야 한다.

`PRE_ROLL_VIDEO`:

- `intro.mp4`는 final 앞에만 존재
- intro의 음성·자막은 별도 정책으로 명시
- 본편 `scene_1`은 첫 본문 대사부터 시작
- concat 후 총 duration과 첫 본문 cue offset을 기록

또는 `HERMES_OPENING_SCENE`:

- intro를 `scene_id=intro_01`로 등록
- source audio keep/mute, caption 시작 시점, 영상 duration을 manifest에 기록
- CapCut draft에서도 intro가 첫 번째 video lane인지 확인

두 모드를 동시에 허용하면 첫 3~5씬이 반복될 가능성이 높으므로, job.json에 `intro_mode`를 필수 enum으로 두고 혼용을 BLOCK해야 한다.

## 오디오·자막 품질 개선

### 오디오

- 씬 사이 0.25초 silence가 모든 씬에 적용되면 긴 영상에서 누적 지연이 커진다. silence는 문장/장면 정책별로 적용하고, 전체 duration 예산에 포함해야 한다.
- peak normalize만으로는 씬 간 체감 음량이 일정하지 않을 수 있다. 최종 오디오 기준 LUFS와 true peak를 측정해 리포트한다.
- `speechSpeed=1.08`을 기본값으로 고정하기보다 TTS 미리듣기 샘플에서 말끝, 숫자, 고유명사 발음, 대사 구분을 평가한다.
- WAV 생성 후 MP4에 들어간 오디오 stream의 실제 duration을 다시 probe해야 한다. manifest 값만 신뢰하면 mux·concat 오류를 놓친다.

### 자막

계획서에는 Whisper 보정 또는 렌더 SRT가 있으나, 자막의 정식 원본이 무엇인지 없다. 다음 중 하나를 정한다.

- TTS 입력 텍스트에서 deterministic SRT 생성 후 Whisper는 검수용
- Whisper 타임코드를 정식 SRT로 사용하고, 원문과 차이를 리포트

긴 나레이션 한 덩어리를 한 자막으로 넣지 말고, 문장·호흡 단위로 분할한다. `scene_id`, `cue_id`, `start`, `end`, `text`를 보존하면 MP4와 CapCut 양쪽을 대조할 수 있다. 16:9와 9:16은 자막 안전영역·줄바꿈 검증을 별도 결과로 남겨야 한다.

## CapCut 경로의 개선사항

Hermes 런북의 보수적인 원칙을 계획서에 더 강하게 가져와야 한다.

- 기존 draft를 절대 덮어쓰지 않고 매 실행마다 고유 job/draft ID 사용
- CapCut 열기 전 job·media·draft 해시 검증
- `draft JSON inspection`만으로 capability를 통과시키지 않기
- 첫·중간·마지막 자막과 음성 싱크를 사람 눈으로 확인
- 저장·닫기·재열기 검증이 필요한 셀과 필요 없는 셀을 구분
- CapCut Export는 자동화 완료로 표현하지 말고 수동 단계로 표시

계획서의 “Full 40씬 + CapCut”은 영상 길이와 독립적이다. 40씬이라도 TTS 길이가 20분을 넘으면 현재 CapCut 경로의 자격 범위를 벗어날 수 있다. `scene_count`와 `duration_seconds`를 별도 축으로 관리해야 한다.

## 현재 검증 코드에 대한 구체 리뷰

### `modern/checks.py`

- `check_era_leak`는 허용 블록을 지원하는 점은 좋지만, 허용 블록이 실제 최종 대본까지 남아도 되는지 정책이 없다. 원문용 주석과 최종 낭독용 텍스트를 분리해야 한다.
- `check_modern_anchor`는 장소·직업 존재를 확인하지만, 첫 900자에서 앵커가 서사적으로 쓰였는지까지 판단하지 못한다. “검출”과 “분산/기능” 검사를 분리한다.
- 함수의 `tuple` 결과가 `(bool, list, level)` 또는 `(bool, list)`로 서로 다르다. 모든 검사 결과를 `{status, severity, code, details}` 구조로 통일하는 편이 패커·CI 연동에 안전하다.
- 대본 검증에는 현재 Hermes 입력에서 가장 중요한 `scene_count`, `narration_length`, `media_mapping`, `audio_duration`, `subtitle_coverage` 검사가 없다.

권장 결과 형식:

```json
{
  "status": "pass",
  "checks": [
    {"code": "SCENE_COUNT_MATCH", "severity": "block", "status": "pass"},
    {"code": "NARRATION_LENGTH", "severity": "warn", "status": "pass", "details": {}}
  ]
}
```

### Smoke 스크립트

`_merge_and_validate.py`와 `_validate_ch1.py`는 텍스트 품질을 보는 데 유용하지만 Hermes job 검증기가 아니다. smoke_g1/g4에 각각 다음 실행물을 추가해야 한다.

- `pack_report.json`
- `tts_report.json`
- `render_report.json`
- `capcut_handoff_report.json` 또는 `capcut_not_run.json`

그리고 `final.txt`를 다시 만드는 스크립트의 파일명·챕터 수·목표 길이·허구 고지 여부를 CLI 인자로 받아, 특정 폴더에만 맞춘 하드코딩을 줄여야 한다.

## 권장 구현 순서

### Phase 0: 계약·경로·검증

1. `PATHS.json` 또는 환경변수 resolver 하나로 Hermes root, TTS root, Python, ffmpeg, CapCut drafts를 해석
2. `job.schema.json`, `shot_plan.schema.json`, `scene_audio_manifest.schema.json` 작성
3. validator가 입력 파일과 media를 검사하고 report를 출력
4. 기존 smoke 산출물로 pack 없이 dry-run 검증

### Phase 1: 패커

1. `shot_plan.json`을 정식 입력으로 확정
2. 이미지 복사/hardlink와 SHA-256 manifest 생성
3. `scenes.json`, `draft.json`, `render-options.json` 생성
4. intro mode와 caption policy를 job contract에 기록
5. 패키징 후 validator가 BLOCK 0인지 확인

### Phase 2: Preview

1. Ch1 16씬만 TTS
2. 각 WAV probe 및 오디오 manifest 생성
3. 렌더 후 MP4의 duration, stream, 첫·중간·끝 frame을 검사
4. 자막은 별도 SRT로 생성하고 첫·중간·끝 싱크를 검수
5. Preview 성공 로그와 tool version을 보존

### Phase 3: Full MP4

Preview가 재현된 뒤에만 40씬으로 확장한다. Full은 CapCut 성공을 전제로 하지 않고 MP4-only와 CapCut-ready를 별도 결과로 낸다.

### Phase 4: CapCut

CapCut은 렌더러의 하위 단계가 아니라 별도 acceptance cell로 다룬다. 16:9/9:16, full-video/audio-first, native-image 여부는 각각 검증된 capability를 가질 때만 통과시킨다.

## 보완된 Definition of Done

### Preview MP4

- 고유 job ID와 provenance 기록
- 16씬 수와 16개 WAV/이미지 매핑 일치
- 모든 WAV 재생 가능, duration > 0, 후처리 성공
- MP4의 실제 duration과 scene audio 합계가 정책 오차 안에 있음
- 첫·중간·끝 장면의 자막과 음성 대조 완료
- black frame, missing media, orphan process 없음
- intro mode가 한 가지로 고정되고 중복 없음

### Full MP4

- 40씬 또는 실제 입력 씬 수가 manifest와 일치
- 총 길이와 chunk 정책이 명시됨
- 20분 초과 시 CapCut을 자동으로 성공 처리하지 않음
- 재실행 시 기존 job/draft를 덮어쓰지 않음

### CapCut editable draft

- Hermes 런북의 해당 capability cell이 사전에 통과되어 있음
- 고유 draft 생성, staging→promotion, 해시 검증 완료
- voice/SFX/caption/visual lane의 편집 가능성을 사람 검수
- 저장·닫기·재열기 요건을 해당 셀 기준으로 충족
- Export는 수동 후속 작업으로 남김

## 최종 판단

HERMES 계획서는 실행 순서와 위험 인식은 잘 잡혀 있지만, 아직 “최종 영상 파이프라인”이라기보다 “구현 계획 + 운영 런북 요약”에 가깝다. 가장 먼저 수정할 것은 기능 추가가 아니라 신뢰 가능한 경계다.

우선순위는 다음과 같다.

1. 절대경로 resolver와 job schema
2. `shot_plan.json → scenes.json/draft.json` 패커
3. TTS/미디어/씬 수/duration validator
4. PRE_ROLL_VIDEO 또는 HERMES_OPENING_SCENE 중 하나 고정
5. Preview 16씬의 재현 가능한 성공 로그
6. Full MP4와 CapCut acceptance를 별도 단계로 확장

이 순서를 지키면 현재 Module의 텍스트·이미지 자산을 안전하게 재사용하면서도, 실패한 렌더를 성공으로 오인하거나 CapCut 검증 상태를 과장하는 문제를 크게 줄일 수 있다.
