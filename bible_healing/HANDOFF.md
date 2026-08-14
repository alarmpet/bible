# HANDOFF — bible_healing

> **구 보이스 문서.** 보이스·자막·배경·저장 경로는 `config/media_rules_lock.json`이 우선한다. 이 파일과 충돌하면 lock을 따른다.
>
> 마지막 갱신: 2026-08-14  
> 설계 문서: `../계획서_구약_힐링_낭독_파이프라인.md`  
> **품질 진단(재작업 필수):** `../계획서_구약힐링_ep01_품질진단_재작업.md`  
> **미디어 잠금:** `config/media_rules_lock.json` (version 2)

## 본편 실행 (유일한 진입점)

```powershell
cd C:\Users\amd\module
python bible_healing/scripts/run_full_media_pipeline.py --job bible_healing/runs/ep01_anxious_night/hermes_jobs/full
```

- 단계 리포트: `D:\bible_healing_ep01\work\pipeline\`
- 최종 MP4: `D:\bible_healing_ep01\final\deploy-ep01-authoritative-audio-aligned.mp4`
- TTS에 `--skip-existing` 를 넘기지 않는다. 중간 실패 시 중단.

## ⛔ 구 본편 / 100분본 배포 금지

| 문제 | 구 산출 |
|------|---------|
| 느린 음성 | 0.78/0.72 + 31s 무음 패드 |
| 이미지 없음 | 그라데이션 더미 |
| 자막 없음 | SRT만, MP4 미합성 |

**배포 금지 (legacy):** `hermes_jobs/full/final-ep01-full.mp4`,
`upload_package/final-ep01-full.mp4`,
`upload_package/final-bible-healing-ep01-100m.mp4`,
`hermes_jobs/full/final-bible-healing-ep01-100m.mp4`.
Live 본편은 D: final + 오케스트레이터만.

## 재작업 진행

| 항목 | 상태 |
|------|------|
| 품질 진단 | `../계획서_구약힐링_ep01_품질진단_재작업.md` |
| **Hermes 규약 업그레이드 계획 (최신)** | **`../계획서_구약힐링_Hermes규약_업그레이드.md`** |
| 음성 재캘리브 | ✅ 1.00 / 0.96 (스모크) |
| 자막 계약 | lock captions (14~18/20, 96/100px) |
| **본편 자막** | **`build_full_audio_aligned_ass.py` → `subtitles-full-audio-aligned.ass`** |
| Hermes 분할 | preview/smoke only — `caption_split_hermes.py` (**본편 아님**) |
| 타임드 큐 | preview/smoke only — `build_cues_from_manifest.py` → `subtitles-timed-ko.ass` (**본편 아님**) |
| 렌더 v3 | ✅ 이미지 무텍스트 + ASS burn-in |
| 실이미지 | ✅ Imagine 3종 시작 (`assets/generated/ep01/`) — 대량 생성은 후속 |
| **기본 보이스** | **F5@0.95 / M4@0.95 pitch -14 (atempo 없음)** — `config/media_rules_lock.json` |
| 면책 문구 | 낭독 **제외** → 설명란만 (`licenses.yaml`) |
| 엠비언트 영상 계획 | `../계획서_구약힐링_엠비언트영상_매칭.md` v1.1 |
| 플레이트 파이프 | ✅ yaml + timeline + assign + qa |
| 엠비언트 스모크 | `smoke_review/final-sample5-ambient-smoke.mp4` (~6.5분, 플레이트 1) |
| **최종 본편 (live)** | **`D:\bible_healing_ep01\final\deploy-ep01-authoritative-audio-aligned.mp4`** — `run_full_media_pipeline.py` 만 |
| ~~구 본편~~ | ~~`hermes_jobs/full/final-ep01-full.mp4`~~ — **legacy, do not deploy** |
| ~~업로드 복사본~~ | ~~`upload_package/final-ep01-full.mp4`~~ — **legacy** |
| 권장 청취 샘플 | `voice_casting/sample5_F10_M10_stable.mp3` |

### 플레이트 스모크 재실행 (preview/smoke — 본편 아님)
본편 자막은 `subtitles-full-audio-aligned.ass`다. 아래 cues/`subtitles-timed-ko.ass` 경로는 스모크 전용.
```powershell
cd C:\Users\amd\module\bible_healing
python scripts\build_plate_timeline.py --job runs\ep01_anxious_night\hermes_jobs\sample5_F10_M10
python scripts\assign_plates_to_scenes.py --job runs\ep01_anxious_night\hermes_jobs\sample5_F10_M10
python scripts\qa_ambient_plates.py --job runs\ep01_anxious_night\hermes_jobs\sample5_F10_M10
python scripts\build_cues_from_manifest.py --job runs\ep01_anxious_night\hermes_jobs\sample5_F10_M10
python scripts\build_ass_from_cues.py --job runs\ep01_anxious_night\hermes_jobs\sample5_F10_M10
python scripts\render_healing_v3.py --job runs\ep01_anxious_night\hermes_jobs\sample5_F10_M10 --final-name final-sample5-ambient-smoke.mp4
```
| Full 재합성 | ⬜ 스모크 승인 후 |

### 지금 열어볼 파일
```
bible_healing/runs/ep01_anxious_night/smoke_review/final-smoke10-v3-realbg.mp4
```

### v3 재빌드 (스모크 — 본편 아님)
```powershell
cd C:\Users\amd\module\bible_healing
python scripts\prepare_plain_backgrounds.py --job runs\ep01_anxious_night\hermes_jobs\preview  # or real bg map
python scripts\build_cues_from_manifest.py --job runs\ep01_anxious_night\hermes_jobs\preview
python scripts\build_ass_from_cues.py --job runs\ep01_anxious_night\hermes_jobs\preview
python scripts\qa_healing_render.py --job runs\ep01_anxious_night\hermes_jobs\preview
python scripts\render_healing_v3.py --job runs\ep01_anxious_night\hermes_jobs\preview --final-name final-smoke10-v3.mp4
```

### 업로드 / 배포 (live only)

- **본편 진입점:** `run_full_media_pipeline.py` (위 절)
- **배포 MP4:** `D:\bible_healing_ep01\final\deploy-ep01-authoritative-audio-aligned.mp4`
- 메타(TITLE/DESCRIPTION/TAGS)는 새 렌더 기준으로 다시 패키징한다.

### ⛔ Legacy artifacts — do not deploy

| 파일 | 상태 |
|------|------|
| `hermes_jobs/full/final-ep01-full.mp4` | legacy 구 본편 |
| `upload_package/final-ep01-full.mp4` | legacy 복사본 |
| `upload_package/final-bible-healing-ep01-100m.mp4` | 구 100분본, 배포 금지 |
| `hermes_jobs/full/final-bible-healing-ep01-100m.mp4` | 구 100분본, 배포 금지 |
| `final-bible-healing-ep01.mp4` | 구 순수 낭독 경로 |

### 분량 설명 (역사 기록)

| 버전 | 길이 | 파일 | 비고 |
|------|------|------|------|
| 순수 낭독 | 1:25:47 | `final-bible-healing-ep01.mp4` | legacy |
| + 유닛 쉼 | 1:40:00 (100분) | `final-bible-healing-ep01-100m.mp4` | legacy, 배포 금지 |
| **authoritative 본편** | (pipeline 산출) | `D:\bible_healing_ep01\final\deploy-ep01-authoritative-audio-aligned.mp4` | **live** |

## 보이스 (2026-08-14)

| | narrator (여) | scripture (남) |
|---|---|---|
| ID | F5 | M4 |
| 엔진 속도 | 0.95 | 0.95 |
| total_step | 8 | 10 |
| 쉼 | 0.24s | 0.25s |
| 피치 | 없음 | -14% (`asetrate=24000*0.86`, atempo 없음) |
| 체감 속도 | 0.95 | ≈0.82 |
| 합성 | 장면 단위 | 절(마침표) 1회, max_chunk 90 |

- 단일 기준: `config/media_rules_lock.json`
- yaml: `config/voice_healing.yaml` (다르면 lock 우선)

## 파이프 요약

```
download → parse OSIS → build_episode → QA → pack_to_hermes
→ run_full_media_pipeline.py (유일한 본편 경로)
   1 media_rules_preflight
   2 build_full_job
   3 tts_multi_voice  (no --skip-existing)
   4 verify_voice_provenance
   5 rebuild_authoritative_full_audio
   6 verify_authoritative_audio
   7 build_full_audio_aligned_ass
   8 ASS qa_ass
   9 render_authoritative_full → D:\bible_healing_ep01\final\...
  10 media_rules_postflight
```

## ep02

- 테마 등록됨: `ep02_weary_day` (지친 하루)  
- 진행: `runs/ep02_weary_day/PROGRESS.md`  
- 나레이션 뱅크 작성 후 ep01과 동일 파이프

## 업로드 전 체크

1. `upload_package/CHECKLIST.md` 재생 검수  
2. TITLE / DESCRIPTION / TAGS 붙여넣기  
3. 개역한글·의료 면책 문구 확인  

## 선택 후속

- [ ] ep02 나레이션 뱅크 + 본편  
- [ ] 사진/일러스트 배경으로 flow 교체  
- [ ] 아주 낮은 BGM 덕킹  
