# HANDOFF — 다음 에이전트/LLM용 (막힘 없이 이어가기)

> **마지막 갱신:** 2026-08-09 (upload 품질 진단 — **배포 금지**, 개선 계획서 작성)  
> **이 파일을 먼저 읽고** 작업을 시작하세요.  
> 워크스페이스: `C:\Users\amd\module`  
> 최종 영상 연동 대상: `C:\Users\amd\hermes` + SuperTonic3

---

## 1. 지금 상태 (한 장)

| 영역 | 상태 | 위치 |
|---|---|---|
| 현대 대본 파이프 | ✅ 문서+스모크 | `modern/v12_*`, banks, 참고_* |
| smoke_g1 대본 | ✅ | `runs/smoke_g1/final.txt`, chapter_*.txt |
| 캐릭터 S0 다각도 | ✅ | `runs/smoke_g1/images/characters/` |
| 본편 이미지 40체계 | ✅ | `images/ch1`…`ch5/` |
| 인트로 영상 | ✅ 슬라이드 mp4 | `runs/smoke_g1/videos/intro.mp4` |
| 컷 밀도 규칙 | ✅ 문서 | `참고_이미지컷_밀도_규칙.md` |
| 캐릭터 일관성 규칙 | ✅ 문서 | `참고_캐릭터_일관성_시트.md` |
| Hermes 최종영상 계획 | ✅ v1.2 | `../계획서_HERMES_최종영상_파이프라인.md` |
| **Job 패커/validator/다중TTS** | ✅ 동작 | `modern/scripts/` |
| **Preview job** | ✅ | `hermes_jobs/preview/` — 16씬 / ~84s with intro |
| **Full job pack** | ✅ | `hermes_jobs/full/` — 40씬 |
| **Full multi-voice TTS** | ✅ | `scene_1.wav`…`scene_40.wav` (~464s) |
| **Full audio lock** | ✅ | `measured-and-locked` |
| **Full MP4 렌더** | ✅ 축약본 | `hermes_jobs/full/final-full-multivoice.mp4` (~7:45) |
| **Full intro pre-roll** | ✅ 축약본 | `hermes_jobs/full/final_with_intro.mp4` (~7:51) |
| **Upload fulltext plan** | ✅ | `shot_plan_upload.json` — 전문 대본 233씬 (텍스트 드롭 없음) |
| **Upload job** | ✅ | `hermes_jobs/upload/` multi-voice TTS ~50.4분 |
| **Upload MP4** | ⚠️ **배포 금지** | ~50분 생성됨 — 이미지/화자/보이스 품질 실패 (아래 계획서) |
| **품질 진단 계획** | ✅ | `계획서_업로드영상_품질진단_개선.md` |
| **주제·대본 다양성 계획** | ✅ | `../계획서_주제_대본_다양성_품질_강화.md` (2026-08-10) |

**막히기 쉬운 점:** Hermes 렌더는 `scene_N_flow.jpg` + `draft.json` 이 필요. module 이미지는 `ch1_01_….jpg` 형식 → **반드시 pack**.

---

## 2. 필수 문서 읽기 순서

1. 이 파일 (`modern/HANDOFF.md`)  
2. `../PATHS.md`  
3. `../계획서_HERMES_최종영상_파이프라인.md` (**v1.2 — 다중 보이스 §1-A**)  
4. `../README_파이프라인.md`  
5. 작업 대상 run: `runs/smoke_g1/shot_plan.md`, `character_sheet.md`, `images/INDEX.md`  

Hermes 쪽 참고 (읽기 전용 이해):

- `C:\Users\amd\hermes\scripts\make-scenes-tts.py` — **단일 보이스** (제품 기본으로 쓰지 말 것)  
- `C:\Users\amd\hermes\scripts\render-youtube-with-tts.mjs` — 최종 렌더  
- `C:\Users\amd\hermes\docs\capcut-editable-handoff-runbook.md`  
- SuperTonic: `C:\Users\amd\supertonic3-local-tts-20260517-r4\supertonic3-local-tts`  
  - 보이스: **M1–M5, F1–F5**

---

## 3. 절대 규칙 (어기면 재작업)

1. **허구 고지** 유지. SEO `실화` 기본 금지.  
2. **나레이션 ≠ 캐릭터 음성** — `voice_map.json`에서 narrator voice를 인물과 **공유 금지**.  
3. **챕터1 이미지 고밀도 / 2+ 사건 밀도** — `참고_이미지컷_밀도_규칙.md`.  
4. 본편 이미지 재생성 시 **S0 턴어라운드 레프 edit** — text-only gen 남발 금지.  
5. CapCut **Export 자동화 없음**. draft 덮어쓰기 금지. CapCut 경로 길이 **20분(1200s)** 자격 주의.  
5-b. **분량 매트릭스:** 기본 `standard` 25~45분. `quick` 15~25, `deep` 45~70, `special/anthology` 80~120분 — `duration_default.md`.  

6. intro: **`PRE_ROLL_VIDEO`** — intro.mp4는 final 앞 프리롤, 본편 TTS와 대사 중복 금지.  
7. 레거시 `대본 sonnet/` 덮어쓰지 말 것. 작업은 `modern/` 만.

---

## 4. 다음이 할 일 (우선순위 고정)

### Step A–F — 이미 완료됨 (2026-08-07)

**Preview (16씬 / Ch1)**  
- pack / multi-voice TTS / lock / 렌더 / intro ✅  
- `hermes_jobs/preview/final_with_intro.mp4` (~84s)

**Full (40씬)**  
- `build_shot_plan_json.py` event-density 버그 수정 (챕터 잔여 대본이 마지막 샷에 3k+자 몰림 방지)  
- pack full / validate BLOCK 0 ✅  
- multi-voice TTS 40씬 ✅ (~464s 오디오)  
- lock + Hermes 렌더 ✅  
- intro pre-roll ✅  
- 본편 **~7:45** → CapCut **20분 게이트 통과**

귀 검수 후: `voice_map.json` 에 `"preview_approved": true` 설정.

### Full 재실행 레시피

```powershell
cd C:\Users\amd\module\modern
python scripts\build_shot_plan_json.py --run smoke_g1
python scripts\pack_hermes_job.py --run smoke_g1 --mode full
python scripts\validate_job.py --job runs\smoke_g1\hermes_jobs\full
# SuperTonic venv 권장
& "C:\Users\amd\supertonic3-local-tts-20260517-r4\supertonic3-local-tts\.venv-win\Scripts\python.exe" `
  scripts\tts_multi_voice.py --job runs\smoke_g1\hermes_jobs\full
python scripts\lock_audio_manifest.py --job runs\smoke_g1\hermes_jobs\full --backup
cd C:\Users\amd\hermes
$env:HERMES_YOUTUBE_FINAL_NAME = "final-full-multivoice.mp4"
node scripts\render-youtube-with-tts.mjs C:\Users\amd\module\modern\runs\smoke_g1\hermes_jobs\full
cd C:\Users\amd\module\modern
python scripts\pre_roll_intro.py --job runs\smoke_g1\hermes_jobs\full --body runs\smoke_g1\hermes_jobs\full\final-full-multivoice.mp4
```

**위험:** lock 없이 렌더하면 Hermes 단일 보이스 TTS가 multi-voice WAV를 덮음.  
백업: `hermes_jobs/full/audio_multivoice_backup/`

### Step G — Upload fulltext (본선 · 2026-08-08)

**목표:** 챕터 1–5 **전문 대본** + multi-voice + 전체 이미지(챕터 내 재사용) → 유튜브 업로드용 MP4.

```powershell
cd C:\Users\amd\module\modern
python scripts\build_shot_plan_json.py --run smoke_g1 --profile fulltext
python scripts\pack_hermes_job.py --run smoke_g1 --mode upload
# SuperTonic venv
& "C:\Users\amd\supertonic3-local-tts-20260517-r4\supertonic3-local-tts\.venv-win\Scripts\python.exe" `
  scripts\tts_multi_voice.py --job runs\smoke_g1\hermes_jobs\upload
python scripts\lock_audio_manifest.py --job runs\smoke_g1\hermes_jobs\upload --backup
cd C:\Users\amd\hermes
$env:HERMES_YOUTUBE_FINAL_NAME = "final-upload-fulltext.mp4"
node scripts\render-youtube-with-tts.mjs C:\Users\amd\module\modern\runs\smoke_g1\hermes_jobs\upload
cd C:\Users\amd\module\modern
python scripts\pre_roll_intro.py --job runs\smoke_g1\hermes_jobs\upload --body runs\smoke_g1\hermes_jobs\upload\final-upload-fulltext.mp4
```

| 항목 | 값 |
|---|---|
| 씬 수 | **233** (`shot_plan_upload.json`) |
| 오디오 | multi-voice ~**50.4분** (전문 유지) |
| 이미지 | ch1–5 기존 컷 라운드로빈 재사용 |
| 본선 경로 | `hermes_jobs/upload/final-upload-fulltext.mp4` |
| intro 포함 | `hermes_jobs/upload/final_with_intro.mp4` |
| CapCut | 본편 ~50분 → **20분 게이트 초과** (Hermes MP4 직업로드 권장) |

**참고:** `hermes_jobs/full/` 은 예전 **40컷 축약** 스모크용. 업로드 본선은 **`upload/`**.

### Step H — 완료 + 다음

- [x] upload fulltext 렌더 (~50:26, 233씬, multi-voice, 자막)  
- [x] intro pre-roll (`final_with_intro.mp4` ~50:33)  
- [ ] **재생 검수** 후 업로드 (허구 고지·보이스·엔딩)  
- [ ] (선택) 이미지 재사용 구간 추가 컷 생성  

**업로드 권장 파일**

`C:\Users\amd\module\modern\runs\smoke_g1\hermes_jobs\upload\final_with_intro.mp4`

---

## 5. 스크립트 목록 (`modern/scripts/`)

| 파일 | 역할 |
|---|---|
| `paths.py` | 경로 단일 해석 |
| `build_shot_plan_json.py` | shot_plan.md/이미지 → `shot_plan.json` |
| `pack_hermes_job.py` | run → jobDir (media, scenes, draft, manifests) |
| `validate_job.py` | BLOCK/WARN 리포트 |
| `tts_multi_voice.py` | 화자별 SuperTonic + concat |
| `lock_audio_manifest.py` | multi-voice → Hermes `measured-and-locked` manifest |
| `pre_roll_intro.py` | intro.mp4 + body → `final_with_intro.mp4` |
| `slice_narration.py` | 대본→segments (화자 추정) |

---

## 6. smoke_g1 보이스 맵 (기본 · 확정 전)

| speaker | voice | speed | 역할 |
|---|---|---|---|
| narrator | M2 | 1.05 | 나레이션 |
| youjin | F2 | 1.08 | 주인공 |
| gicheol | M5 | 0.95 | 악역 |
| gyeongho | M3 | 0.98 | 조력 |
| siwoo | M1 | 1.15 | 과장 |

파일: `runs/smoke_g1/hermes_bridge/voice_map.json`

---

## 7. 하지 말 것

- `대본 sonnet/` 야담 파이프를 modern 결과로 덮기  
- 계획서에 “이미 최종 영상 됨”으로 쓰기  
- CapCut 60/90/120분을 지원 완료로 단정  
- 나레이션·대사 동일 voice  
- shot_plan.md만 수동 파싱에 의존 (json 원본 유지)

---

## 8. 완료 정의

### Preview
- [x] validation / multi-voice / lock / MP4 / intro  
- [ ] 귀 검수 `preview_approved: true`

### Full
- [x] `hermes_jobs/full` validation BLOCK 0  
- [x] multi-voice wav 40씬  
- [x] lock + MP4 렌더 (`final-full-multivoice.mp4` ~7:45)  
- [x] intro pre-roll (`final_with_intro.mp4` ~7:51)  
- [ ] 전체 재생 검수  
- [ ] CapCut editable draft (선택)

## 9. 산출물 경로

| 파일 | 설명 |
|---|---|
| `hermes_jobs/preview/final_with_intro.mp4` | Ch1 미리보기 ~84s |
| `hermes_jobs/full/final-full-multivoice.mp4` | 본편 40씬 ~7:45, 1920×1080 |
| `hermes_jobs/full/final_with_intro.mp4` | **최종 권장 재생** ~7:51 |
| `hermes_jobs/full/subtitles-ko-v2.srt` | 자막 |
| `hermes_jobs/full/scene_audio_manifest.json` | locked multi-voice |
| `hermes_jobs/full/audio_multivoice_backup/` | WAV 백업 |

## 10. 알려진 이슈

1. ~~Hermes 렌더 TTS 재호출~~ — lock 필수.  
2. ~~event-density last-shot dump~~ — `build_shot_plan_json.assign_narration` 수정 완료.  
3. 화자 추정 휴리스틱 단순 — 대사 화자 오분류 가능  
4. CapCut `job-request.json` 아직 pack 미생성  
5. ch2–5 나레이션은 타임라인 샘플링(~100자/씬). 전문 대본 대비 축약됨  
6. Hermes stub: `electron/services/video-operation-dependencies.mjs` (verify only)

---

## 9. 연락/맥락

- 사용자 목표: 현대 합성 드라마 롱폼 → 로컬 TTS + CapCut 가능 최종물  
- 초반 이탈 방지: Ch1 이미지 촘촘  
- 캐릭터 얼굴: S0 일관성  
- 음성: **차이가 확 나게** 다중 보이스  

질문 없이 막히면: 이 HANDOFF §4 Step부터 재개하고, 실패 로그를 `hermes_jobs/.../reports/` 에 저장.
