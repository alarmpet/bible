# 계획서: Module 대본·이미지 → Hermes 최종 영상 (v1.2)

> **작성:** 2026-08-07  
> **갱신:** 2026-08-07 — 리뷰 반영(v1.1) + **다중 보이스(나레이션≠캐릭터) 정책(v1.2)**  
> **목적:** `module` 산출물(대본·이미지·인트로)을 Hermes job으로 포장해 SuperTonic3 TTS → 동기 MP4 → (선택) CapCut editable draft까지 연결.  
> **기준 자산:** `modern/runs/smoke_g1/`

### ★ v1.2 핵심 정정 (사용자 질의)

| 질문 | 답 |
|---|---|
| 나레이션·캐릭터 음성을 **따로** 쓰도록 이미 업데이트했나? | **아니오.** v1.1까지는 job당 **단일 voice**(기본 M1) 전제였다. |
| 지금 문서 기준 | **반드시 분리 생성**한다. 나레이션 vs 인물 대사는 **프리셋·속도·필터가 확연히 다르게**. |

SuperTonic3 엔진 지원 보이스: **`M1`–`M5`, `F1`–`F5`** (+ 커스텀 `voice_style_path`).  
현재 Hermes `make-scenes-tts.py`는 **씬 전체 한 보이스**만 돌림 → **다중 보이스는 신규 파이프(세그먼트 TTS + concat)** 가 필요하다.

---

## 리뷰 반영 요약 (v1.1) + v1.2

| 판정 | 내용 |
|---|---|
| ✅ | 큰 방향 유지: Module → jobDir → TTS → MP4 → CapCut(선택), Preview 우선 |
| ✅ | **구현된 사실 / 계획 / Hermes capability** 상태 분리 |
| ✅ | 정식 **Job 계약** (`scenes.json`·`shot_plan.json` 원본, `draft.json` 파생) |
| ✅ | 나레이션 분할 = 문장·발화·사건 경계 우선 (등분 금지) |
| ✅ | **70자(씬)** vs **130자(TTS 엔진 chunk)** 정책 분리 |
| ✅ | TTS/미디어 preflight · manifest `ok` 신뢰 조건 |
| ✅ | **intro_mode 단일 enum** 고정 (`PRE_ROLL_VIDEO`) |
| ✅ | CapCut: scene_count ≠ duration, 덮어쓰기 금지, Export 수동 |
| ✅ | 구현 순서: 계약·validator → 패커 → Preview → Full → CapCut |
| ✅ **v1.2** | **다중 보이스:** 나레이션 / 캐릭터 대사 분리 생성·확연한 음색 차이 |
| 완화 | Hermes 내부 단일보이스 스크립트 확장 = **의존 구현** (Module 래퍼 또는 Hermes PR) |
| 완화 | checks.py 전면 통일 스키마 = Module 검증 진화 과제 |

---

## 0. 상태 분리 (혼동 방지)

| 층 | 현재 상태 | 문서에서 하는 말 |
|---|---|---|
| **A. 구현됨 (Module)** | smoke_g1 대본·ch1–5 이미지·캐릭터 S0·intro.mp4·shot_plan.**md** | 자산 준비됨 |
| **B. 미구현 (어댑터)** | pack 스크립트, shot_plan.**json**, draft/scenes.json, job validator | **계획** |
| **C. 구현됨 (Hermes)** | make-scenes-tts.py, render-youtube-with-tts.mjs, reassemble_draft, CapCut 런북 | 도구 존재 |
| **D. Hermes capability** | 구조적 10초 드래프트 등 일부 증거; 60m/90m/120m·일부 캡션 셀은 **미검증/대기** | 과장 금지 |

**지금 당장 “한 명령으로 최종 영상”은 불가.** 먼저 B 계층(계약·패커·validator)이 필요.

---

## 1. 한 줄 아키텍처

```
module/smoke_g1 자산
  → [B] pack + validate (신규)
  → hermes jobDir (정식 계약 파일 세트)
  → 대본 파싱: 나레이션 세그먼트 + 캐릭터 대사 세그먼트 (화자별)
  → SuperTonic3 TTS **화자별 보이스** (seg_*.wav → scene_N.wav concat)
  → render-youtube-with-tts.mjs (MP4, 씬 단위 최종 wav 사용)
  → [선택][D 통과 셀만] PyCapCut draft → CapCut 수동 Export
```

Module = 창작·에셋. Hermes = TTS·타임라인·드래프트.  
**TTS는 단일 톤 금지:** 나레이터 ≠ 유진 ≠ 기철 ≠ 경호 ≠ 시우.

---

## 1-A. 다중 보이스 TTS (v1.2 필수) ★

### 1-A-1. 현황 (사실)

| 항목 | 상태 |
|---|---|
| SuperTonic3 프리셋 | `M1`–`M5` (남), `F1`–`F5` (여) |
| 엔진 API | `synthesize_to_file(..., voice="M1", speed=..., silence_duration=...)` |
| Hermes `make-scenes-tts.py` | **job 전체 1 voice** — 씬 `narration` 문자열 통짜 합성 |
| 캐릭터별 분리 | **미구현** |

→ “나레이션만 깔고 대사는 다른 목소리”는 **현재 한 줄 호출로는 불가능**. 세그먼트 단위 합성이 필요.

### 1-A-2. 목표 체감

| 트랙 | 요구 |
|---|---|
| **나레이션** | 설명체, 비교적 안정·중저/중성, 속도 일정 (다큐·낭독) |
| **캐릭터 대사** | 인물마다 **성별·연령·기질**이 바로 구분될 것 |
| 대비 | 같은 씬 안에서 나레이션→대사 전환 시 **청취 1초 안에 화자 전환 인지** |

같은 성별 2인이면 **다른 번호 프리셋 + speed 차이**로 벌린다 (예: M1 vs M4, speed 1.0 vs 1.12).

### 1-A-3. smoke_g1 보이스 맵 (기본안 · 미리듣기로 확정)

| speaker_id | 역할 | 성별·톤 | SuperTonic | speed | silence(세그먼트 뒤) | 비고 |
|---|---|---|---|---|---|---|
| `narrator` | 3인칭 나레이션 | 남·차분 낭독 | **M2** | 1.05 | 0.20 | 기본 설명 목소리 (M1과 겹치지 않게) |
| `youjin` | 한유진 | 여·담담·짧음 | **F2** | 1.08 | 0.12 | 주인공 |
| `gicheol` | 송기철 | 남·낮고 차갑 | **M5** | 0.95 | 0.15 | 악역 — **나레이터와 확연히 다른 M** |
| `gyeongho` | 박경호 | 남·낮고 느림 | **M3** | 0.98 | 0.15 | 조력 회색 |
| `siwoo` | 이시우 | 남·빠르고 날카 | **M1** | 1.15 | 0.10 | 과장 — 속사포 |

- 확정 전: 각 보이스로 **동일 샘플 문장** 3초 미리듣기 → `voice_map.json`에 lock.  
- `F*` / `M*` 가 기대와 다르면 번호만 교체 (맵 파일만 수정).  
- 커스텀 스타일 JSON이 있으면 `voice_style_path`로 더 벌릴 수 있음 (선택).

파일: `job/voice_map.json`

```json
{
  "schema_version": "1.0",
  "engine": "supertonic3",
  "speakers": {
    "narrator": { "voice": "M2", "speed": 1.05, "pitch": null, "audio_filter": "" },
    "youjin":   { "voice": "F2", "speed": 1.08, "pitch": null, "audio_filter": "" },
    "gicheol":  { "voice": "M5", "speed": 0.95, "pitch": null, "audio_filter": "highpass=f=80" },
    "gyeongho": { "voice": "M3", "speed": 0.98, "pitch": null, "audio_filter": "" },
    "siwoo":    { "voice": "M1", "speed": 1.15, "pitch": null, "audio_filter": "" }
  },
  "rules": {
    "narration_default_speaker": "narrator",
    "quoted_dialogue_requires_character": true,
    "min_voice_distance": "narrator must not share voice id with any character"
  }
}
```

**강제:** `narrator.voice` ∈ character voices → **BLOCK** (동일 프리셋 공유 금지).

### 1-A-4. 대본 → 세그먼트 파싱

한 씬(이미지 1장) 안에도 화자가 섞일 수 있다.

```text
나레이션 문장.
"대사입니다."          ← 직전/호칭/프로필로 speaker 추정
나레이션 문장.
```

| 패턴 | speaker |
|---|---|
| 큰따옴표·대화 인용 | 캐릭터 (`character_matrix` 호칭·말버릇·문맥) |
| 그 외 | `narrator` |
| 애매 | WARN → 기본 narrator, 리포트에 표시 |

출력: `scenes.json` 확장

```json
{
  "scene_id": "ch1_s09",
  "order": 9,
  "segments": [
    { "seg_id": "ch1_s09_01", "speaker": "narrator", "text": "박경호 대리가 조끼 주머니에 손을 넣고 물었습니다." },
    { "seg_id": "ch1_s09_02", "speaker": "gyeongho", "text": "한 씨, 오늘도 남아요?" },
    { "seg_id": "ch1_s09_03", "speaker": "youjin", "text": "네. 전표 조금만 더 보고 갈게요." }
  ]
}
```

Hermes 레거시 호환: 렌더러가 단일 `narration`만 보면  
`narration` = segments 텍스트 join (표시/검수용), **실제 청취 오디오는 multi-voice concat wav**.

### 1-A-5. 생성 파이프 (권장 구현)

```
1) segments[] 확정 + voice_map
2) 각 seg → SuperTonic synthesize (voice/speed/filter per speaker)
     audio/seg/{seg_id}_{speaker}.wav
3) 씬 단위 concat (ffmpeg)
     세그먼트 사이: 화자 전환 시 0.08~0.15s, 동일 화자 연속 시 0.05s
     → audio/scene_{order}.wav  (렌더러 기존 계약 유지)
4) scene_audio_manifest에 speaker timeline 기록
```

**신규 스크립트 (택1):**

- `module/modern/scripts/tts_multi_voice.py` — SuperTonic 엔진 직접 호출 후 concat  
- 또는 Hermes `make-scenes-tts-multivoice.py` (upstream 기여)

기존 `make-scenes-tts.py` **단일 보이스 경로는 Preview 디버그 전용**으로 강등.  
**제품 기본 경로 = multi-voice.**

### 1-A-6. 검증 (음성 차이)

| 코드 | 내용 |
|---|---|
| `VOICE_MAP_DISTINCT` | narrator voice ∉ character voice set |
| `SEGMENT_SPEAKER_REQUIRED` | 인용 대사에 character speaker 있음 |
| `MULTI_VOICE_FILES` | 씬에 2+ speaker면 seg wav ≥2 존재 |
| `SCENE_WAV_FROM_CONCAT` | scene_N.wav duration ≈ sum(seg)+gaps |
| `VOICE_PREVIEW_LOCK` | voice_map에 preview_approved: true (사람 체크 후) |

사람 검수 체크리스트 (Preview 필수):

- [ ] 눈 감고 들어도 나레이션 vs 대사 구분  
- [ ] 기철 vs 시우 vs 경호 구분  
- [ ] 유진(여) vs 나레이터(남) 혼동 없음  

### 1-A-7. CapCut

- 이상적: voice 레인 분리(나레이션/대사) — PyCapCut 지원 범위 확인 후  
- 최소: **씬 단위 혼합 wav 1트랙** + 편집 시 볼륨만 조정  
- 다중 레인 미지원이어도 **청취 분리는 concat 단계에서 이미 달성**

### 1-A-8. DoD 추가 (Preview)

- [ ] `voice_map.json` 존재, 미리듣기 승인  
- [ ] 나레이션·주요 캐릭터 **서로 다른 voice id**  
- [ ] 대사 있는 씬에 character seg wav 존재  
- [ ] 귀로 확인한 화자 구분 체크리스트 통과

---

## 2. Hermes 인벤토리 (사실)

### 2-1. 경로

| 역할 | 경로 |
|---|---|
| Hermes 루트 | `C:\Users\amd\hermes` |
| SuperTonic3 | `C:\Users\amd\supertonic3-local-tts-20260517-r4\supertonic3-local-tts` |
| TTS Python | `…\supertonic3-local-tts\.venv-win\Scripts\python.exe` |
| TTS 호출 | `hermes/scripts/make-scenes-tts.py <job_dir> <scenes.json>` |
| 렌더 | `hermes/scripts/render-youtube-with-tts.mjs <jobDir>` |
| 이미지 파일명 계약 | `scene_{order}_flow.jpg` 또는 `_grok.jpg` |
| PyCapCut venv | `C:\Users\amd\AppData\Roaming\hermes\runtimes\pycapcut\.venv` |
| CapCut | `…\CapCut\Apps\8.9.1.3802\CapCut.exe` |
| Drafts | `…\CapCut\User Data\Projects\com.lveditor.draft` |
| 드래프트 재조립 | `hermes/.agents/skills/yadam-capcut-builder/scripts/reassemble_draft.mjs` |
| 런북 | `hermes/docs/capcut-editable-handoff-runbook.md` |

### 2-2. TTS 계약 (엔진 vs 씬)

| 정책 | 값 | 의미 |
|---|---|---|
| 엔진 `max_chunk_length` | **130** | SuperTonic **내부** 텍스트 청크 (영상 씬 단위 아님) |
| 이미지 씬 나레이션 | **권장 45–70자**, WARN 71–110, **BLOCK ≥111** (한 문장 강제 절단 금지) | 시청·자막·호흡 |
| silence_duration | 기본 0.25s/씬 (Hermes) | **전체 duration 예산에 포함** 계산; 정책별 조정 가능 |
| voice 기본 | M1 | 고정 강요 금지 — 미리듣기로 확정 |
| speechSpeed 기본 | 1.08 | 샘플 평가 후 job에 기록 |

### 2-3. CapCut 제약 (과장 금지)

| 항목 | 상태 |
|---|---|
| Export 자동화 | **없음** (수동) |
| 현재 Hermes 자격 상한 | **1,200초 (20분)** — 초과 시 자동 성공 처리 금지 |
| 60m / 90m / 120m | **별도 검증 필요 / 대기** — 계획에 “지원됨”으로 쓰지 않음 |
| 기존 draft 덮어쓰기 | **금지** — 매 실행 고유 draft ID |
| capability 판정 | JSON 구조 감사만으로 통과 금지 — 사람 검수 셀 구분 |

### 2-4. 경로 하드코딩 (리스크)

`render-youtube-with-tts.mjs`, `reassemble_draft.mjs` 등에 **amd 절대경로 중복**.  
`module/PATHS.md`만 고쳐서는 Hermes 내부가 안 바뀜.

**계획:** Module 패커는 **현재 PC 경로 전제**로 동작 + `job/provenance.json`에 실제 사용 경로 기록.  
Hermes 쪽 env resolver 통합은 **Hermes PR**로 분리 추적 (`HERMES_PATH_RESOLVER` 이슈).

---

## 3. Module 자산 vs 갭

### 3-1. 있음

| 자산 | 경로 |
|---|---|
| 대본 | `final.txt`, `chapter_1..5.txt` |
| 샷 플랜 (md) | `shot_plan.md` (Ch1=16 고밀도, Ch2–5=24) |
| 이미지 40 체계 | `images/ch1`…`ch5`, `INDEX.md` |
| 캐릭터 S0 | `images/characters/*_S0_turnaround.jpg` |
| 인트로 | `videos/intro.mp4` |

### 3-2. 없음 (B 계층)

- `shot_plan.json`, `scenes.json`, `draft.json`
- `pack_*.mjs` / `pack_*.py`
- jobDir, TTS wav, final MP4, CapCut handoff report
- Hermes 입력 validator

---

## 4. 정식 Job 계약 (P0 고정)

### 4-1. 디렉터리

```text
job/
  job.json                      # schema_version, job_id, title, aspect, intro_mode, policies
  shot_plan.json                # 시각·챕터·소스 경로 (사람 검토 원본)
  scenes.json                   # 씬별 narration 원본 (사람 검토)
  draft.json                    # Hermes 렌더용 파생
  scene-media-manifest.json     # media 경로, sha256, w/h
  scene_audio_manifest.json     # WAV 검증 결과 (ok는 전원 성공 시에만 true)
  render-options.json
  provenance.json               # 소스 해시, 툴 버전, 타임스탬프
  validation-report.json
  media/                        # scene_N_flow.jpg 정규화 사본
  audio/                        # 또는 job 루트 scene_N.wav (Hermes 관례 맞출 것)
  captions/                     # srt 등
  reports/
    pack_report.json
    tts_report.json
    render_report.json
    capcut_handoff_report.json | capcut_not_run.json
```

### 4-2. 식별자

- 모든 씬: 안정 **`scene_id`** (예: `ch1_s03`, 서브씬 `ch1_s03_a`)  
- **`order`**: 렌더 정렬용 정수 (재정렬 가능)  
- 연결은 `scene_id` 우선 — order만으로 장기 연결 금지  

### 4-3. job.json 필수 필드 (발췌)

```json
{
  "schema_version": "1.0",
  "job_id": "smoke_g1_preview_20260807_001",
  "title": "...",
  "aspect": "16:9",
  "intro_mode": "PRE_ROLL_VIDEO",
  "caption_policy": "DETERMINISTIC_FROM_NARRATION",
  "source_run_dir": "C:/Users/amd/module/modern/runs/smoke_g1",
  "scene_count": 16,
  "duration_budget_seconds": null
}
```

`intro_mode`는 enum 하나만. **혼용 BLOCK.**

### 4-4. intro_mode 고정: `PRE_ROLL_VIDEO` (기본)

| 규칙 | 내용 |
|---|---|
| 영상 | `intro.mp4`는 **final 프리롤**로만 붙임 |
| 음성 | 인트로 **무음 훅** (기본). 대사는 본편 scene_1부터 |
| 자막 | 인트로 구간 자막 없음 (또는 별도 정책 명시 시만) |
| 본편 | `scene_1` = 첫 본문 대사부터 (인트로 문구 중복 TTS 금지) |
| 기록 | concat 후 총 duration, 본편 cue offset |

`HERMES_OPENING_SCENE` 모드는 **후순위 옵션** — job에 명시하기 전 사용 금지.

### 4-5. 자막 정책 고정: `DETERMINISTIC_FROM_NARRATION`

| 정식 원본 | TTS 입력 `narration` → 문장·호흡 단위 SRT |
|---|---|
| Whisper | **검수용** 차이 리포트 (정식 타임코드 아님, Preview 기본) |
| cue 필드 | `scene_id`, `cue_id`, `start`, `end`, `text` |
| 화면비 | 16:9 / 9:16 안전영역 검증 결과 **별도** 보존 |

---

## 5. 나레이션 분할 규칙 (등분 폐기)

### 5-1. 우선순위

1. 문장 끝 + 인용부호 닫힘  
2. 화자 발화 단위  
3. 사건/샷 카드 시작·종료  
4. 그다음 목표 글자 수·목표 장면 길이  

**금지:** “Ch1을 16등분” 기계 분할.  
**허용:** Ch1에 **약 16샷**을 목표로 하되, 경계는 위 우선순위로 스냅. 샷 수는 14–18 범위로 조정 가능.

### 5-2. 길이 티어 (씬 narration)

| 구간 | 조치 |
|---|---|
| ≤44자 | OK (짧으면 인접 연결 검토) |
| **45–70** | **권장** |
| 71–110 | WARN + 리포트 |
| **≥111** | BLOCK — **서브씬** 분리, `parent_scene_id` 유지 (한 문장 강제 절단 금지) |

엔진 chunk 130 ≠ 씬 상한. validator에 **두 코드** 분리:

- `NARRATION_SCENE_LENGTH`  
- `TTS_ENGINE_CHUNK_HINT` (정보성)

### 5-3. silence

- 씬 말미 silence는 **duration 예산에 합산**  
- “모든 씬 무조건 0.25s”가 누적 지연을 키우면 정책 테이블로 조정 (문장 끝 vs 챕터 끝)

---

## 6. TTS · 미디어 신뢰 (manifest)

### 6-1. 오디오 (`scene_audio_manifest.json`)

`ok: true` **조건 (전부 만족 시에만):**

- 입력 씬 수 = 출력 WAV 수  
- 각 WAV 존재, size > 0, probe duration > 0  
- sample rate / channels 기록  
- peak + (가능하면) loudness 기록 — **peak만으로 음량 일관 주장 금지**  
- 후처리(normalize/filter) 실패 시 **해당 씬 fail**, 전체 `ok:false`, **exit ≠ 0**  
- voice, speed, filter, TTS/Python 경로, 버전 기록  
- 재실행 시 fingerprint 비교 후 덮어쓰기 정책 명시  

**Hermes 의존:** 현재 `make-scenes-tts.py`는 후처리 실패를 삼킬 수 있음 →  
Module 쪽은 (1) pack 후 TTS 래퍼가 probe 재검증 (2) Hermes에 fail-hard 패치 요청을 **의존 항목**으로 기록.

### 6-2. 미디어 preflight (렌더 전 BLOCK)

- 기대 scene_count vs 실제  
- 각 `scene_id`에 이미지/영상 **정확히 1**  
- 확장자·가독·해상도 기록  
- 검은 프레임 휴리스틱 (선택 WARN)  
- `scene_N_flow.jpg` ↔ manifest order/id 일치  
- intro_mode와 프리롤 파일 일치  
- 누락·고아·중복 order 목록 JSON+콘솔  

실패 시 **렌더 시작 금지**.

### 6-3. 렌더 후

- MP4 stream probe (audio duration 재측정 — manifest만 신뢰 금지)  
- scene audio 합 + silence ≈ MP4 duration (정책 오차)  
- 첫·중간·끝 프레임/자막 샘플 기록  

---

## 7. 오디오·자막 품질 (운영)

| 항목 | 정책 |
|---|---|
| speechSpeed / voice | Preview 미리듣기 후 job에 고정 기록 |
| 숫자·고유명사 | 샘플 검수 체크리스트 |
| 최종 LUFS / true peak | render_report에 기록 (주장 전 측정) |
| 자막 분할 | 문장·호흡; 한 화면에 장문 1덩어리 금지 |
| 16:9 vs 9:16 | 별도 caption 검증 결과 |

---

## 8. CapCut 경로 (별도 acceptance cell)

- Full MP4 성공 ≠ CapCut 성공  
- **`scene_count`와 `duration_seconds`는 별축**  
- 40씬이어도 TTS 합 > 1200s 이면 CapCut 자동 성공 **금지**  
- 매 실행 고유 job_id / draft 이름  
- 열기 전 해시 재검증  
- voice / visual / caption 레인 편집 가능성 **사람 검수**  
- Export = 수동 후속  
- capability cell 미검증 상태는 `capcut_not_run.json` 또는 `capability_pending`  

---

## 9. Module 검증 코드 방향 (분리)

| 범위 | 내용 |
|---|---|
| **본 계획 DoD** | job pack/tts/render report validator |
| **대본 era/anchor** | 기존 `checks.py` 유지; 결과 스키마 통일은 후속 |
| **금지** | smoke 전용 hardcode 검증기를 Hermes job 성공으로 오인 |

권장 check 결과 형식:

```json
{
  "status": "pass",
  "checks": [
    { "code": "SCENE_COUNT_MATCH", "severity": "block", "status": "pass" },
    { "code": "NARRATION_LENGTH", "severity": "warn", "status": "pass", "details": {} }
  ]
}
```

추가 코드 후보: `SCENE_COUNT_MATCH`, `NARRATION_LENGTH`, `MEDIA_MAPPING`, `AUDIO_DURATION`, `SUBTITLE_COVERAGE`, `INTRO_MODE_SINGLE`.

---

## 10. 구현 순서 (리뷰 권장 = 본 계획 공식)

### Phase 0 — 계약·경로·검증 (기능 추가 전)

1. Module `modern/scripts/paths.mjs` 또는 `PATHS.json` (Hermes root, TTS, python, 출력 job 루트)  
2. JSON Schema: job, shot_plan, scenes, media/audio manifest  
3. `validate_job.mjs` dry-run (pack 전후)  
4. smoke_g1 자산으로 **pack 없이** “누락 목록” dry-run  

### Phase 1 — 패커 + 화자 분리

1. `shot_plan.json` 정식 원본 생성 (md는 파생/문서)  
2. 나레이션 슬라이서 (문장·발화·사건 우선 + 길이 티어)  
3. **화자 태깅:** `segments[]` + `voice_map.json` (나레이터≠캐릭터 보이스)  
4. `scenes.json` (segments 포함) + 파생 `draft.json` (`narration` join 호환)  
5. 이미지 → `media/scene_N_flow.jpg` + sha256 manifest  
6. `intro_mode=PRE_ROLL_VIDEO`, caption_policy 기록  
7. `validation-report.json` BLOCK 0 (`VOICE_MAP_DISTINCT` 포함)  

**패커 위치:** `module/modern/scripts/pack_hermes_job.mjs` (단일 원본; hermes 쪽 복제 금지)

### Phase 1b — 다중 보이스 TTS 엔진 래퍼

1. `tts_multi_voice.py`: 세그먼트별 SuperTonic 호출 → concat → `scene_N.wav`  
2. 단일 `make-scenes-tts.py` 경로를 제품 기본에서 제외 (디버그 only)  
3. voice 미리듣기 샘플 생성 → 사람 승인 후 `preview_approved`  

### Phase 2 — Preview (재현 가능 한 줄)

- **씬 수 = Ch1 고밀도 샷 수** (목표 16, 범위 14–18)  
- **multi-voice TTS** → audio manifest 엄격 검증  
- **귀 검수:** 나레이션 vs 대사 구분, 인물 간 구분  
- render → MP4 + render_report  
- 자막 SRT deterministic (화자 표시 옵션)  
- 첫·중간·끝 싱크 사람 체크리스트  
- provenance + tool versions 보존  

예:

```text
node modern/scripts/pack_hermes_job.mjs --run smoke_g1 --mode preview
python modern/scripts/tts_multi_voice.py --job <jobDir>
node <hermes>/scripts/render-youtube-with-tts.mjs <jobDir>   # 기존 wav 재사용 모드 확인 필요
node modern/scripts/pre_roll_intro.mjs --job <jobDir> --intro <run>/videos/intro.mp4
```

### Phase 3 — Full MP4

- Preview 재현 후에만 40씬(또는 실제 N)  
- **CapCut 성공 전제 없음**  
- 결과: `full_mp4` / `capcut_ready` / `capcut_blocked_duration` 분리  

### Phase 4 — CapCut acceptance

- 별도 cell; 16:9 full-video 등 **검증된 capability만**  
- reassemble_draft + 사람 검수 + (필요 시) save/reopen  
- Export 수동  

---

## 11. Definition of Done (보완)

### Preview MP4

- [ ] 고유 `job_id` + provenance  
- [ ] 씬 수 = WAV 수 = 이미지 수  
- [ ] 모든 WAV probe 가능, duration>0, 후처리 정책 반영 또는 명시적 fail  
- [ ] MP4 duration ≈ audio 합 (정책 오차)  
- [ ] 첫·중·끝 자막↔음성 대조  
- [ ] black/missing/orphan 없음  
- [ ] **intro_mode 단일**, 대사 중복 없음  

### Full MP4

- [ ] scene_count manifest 일치  
- [ ] duration_seconds + chunk 정책 명시  
- [ ] >1200s 이면 CapCut 자동 성공 없음  
- [ ] job/draft 비덮어쓰기  

### CapCut draft

- [ ] 해당 capability 사전 상태 명시  
- [ ] 고유 draft, 해시 검증  
- [ ] 레인 편집 가능성 사람 확인  
- [ ] Export는 수동  

---

## 12. 리스크 (갱신)

| 리스크 | 대응 |
|---|---|
| 계획·구현 혼동 | §0 상태 표 |
| 등분으로 대사 절단 | §5 경계 우선 분할 |
| TTS 가짜 성공 | §6 manifest + 래퍼 probe |
| 경로 하드코딩 | provenance 기록 + Hermes PR 분리 |
| 인트로 중복 | PRE_ROLL_VIDEO 고정 |
| CapCut 과장 | duration 축 분리, capability 대기 표기 |
| 롱폼 | Preview → Full MP4 → 청크; CapCut은 20분 이내 하이라이트 가능 |

---

## 13. PR 분해 (v1.1)

| PR | 내용 |
|---|---|
| PR0 | schemas + validate_job dry-run |
| PR1 | shot_plan.json + narration slicer + **speaker segments** |
| PR2 | pack_hermes_job.mjs + media manifest + **voice_map.json** |
| PR3 | **tts_multi_voice.py** (화자별 합성·concat) + tts_report |
| PR4 | Preview one-command + 귀 검수 체크리스트 + pre_roll_intro |
| PR5 | Full pack/render + duration report |
| PR6 | CapCut job-request + reassemble + not_run 리포트 |

---

## 14. 치트시트

```
# TTS
C:\Users\amd\supertonic3-local-tts-20260517-r4\supertonic3-local-tts\.venv-win\Scripts\python.exe
C:\Users\amd\hermes\scripts\make-scenes-tts.py

# Render
C:\Users\amd\hermes\scripts\render-youtube-with-tts.mjs

# CapCut
C:\Users\amd\hermes\scripts\capcut\setup-capcut-runtime.ps1
C:\Users\amd\hermes\.agents\skills\yadam-capcut-builder\scripts\reassemble_draft.mjs

# Module 자산
C:\Users\amd\module\modern\runs\smoke_g1\
```

---

## 15. 리뷰 로그 (채택/완화)

| 리뷰 주장 | 판정 | 반영 |
|---|---|---|
| (사용자) 나레이션·캐릭터 음성 분리·확연한 차이 | **v1.2 필수 채택** | §1-A 전면 추가 |
| 방향·Preview 우선 | 채택 | 유지 |
| 사실/계획/capability 혼동 | 채택 | §0 |
| Job 계약 확장 | 채택 | §4 |
| 등분 분할 위험 | 채택 | §5 |
| 70 vs 130 분리 | 채택 | §2.2, §5.2 |
| TTS 후처리 가짜 성공 | 채택 | §6.1 (+ Hermes 의존) |
| media preflight | 채택 | §6.2 |
| intro 모드 고정 | 채택 | PRE_ROLL_VIDEO §4.4 |
| 경로 resolver | 채택(완화) | Module paths + Hermes PR |
| CapCut 보수 런북 | 채택 | §8 |
| checks.py 스키마 통일 | 채택(후속) | §9 |
| 구현 순서 재정렬 | 채택 | §10 |
| DoD 강화 | 채택 | §11 |

---

**문서 끝 (v1.1).**  
우선순위 확정: **resolver·schema → pack → TTS/미디어 validator → intro 고정 → Preview 16 재현 로그 → Full MP4 / CapCut 분리 확장.**
