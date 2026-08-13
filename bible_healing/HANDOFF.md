# HANDOFF — bible_healing

> **구 보이스 문서.** 보이스·자막·배경·저장 경로는 `config/media_rules_lock.json`이 우선한다. 이 파일과 충돌하면 lock을 따른다.
>
> 마지막 갱신: 2026-08-13  
> 설계 문서: `../계획서_구약_힐링_낭독_파이프라인.md`  
> **품질 진단(재작업 필수):** `../계획서_구약힐링_ep01_품질진단_재작업.md`  
> **미디어 잠금:** `config/media_rules_lock.json` (version 2)

## ⛔ 구 100분본 배포 금지

| 문제 | 구 산출 |
|------|---------|
| 느린 음성 | 0.78/0.72 + 31s 무음 패드 |
| 이미지 없음 | 그라데이션 더미 |
| 자막 없음 | SRT만, MP4 미합성 |

## 재작업 진행

| 항목 | 상태 |
|------|------|
| 품질 진단 | `../계획서_구약힐링_ep01_품질진단_재작업.md` |
| **Hermes 규약 업그레이드 계획 (최신)** | **`../계획서_구약힐링_Hermes규약_업그레이드.md`** |
| 음성 재캘리브 | ✅ 1.00 / 0.96 (스모크) |
| 자막 계약 | ✅ `config/healing_caption_policy.json` (줄당 **20자**, min **0.75s**, 96px) |
| Hermes 분할 | ✅ `scripts/caption_split_hermes.py` (알고리즘 포팅) |
| 타임드 큐 | ✅ `build_cues_from_manifest.py` → cues + ASS |
| 렌더 v3 | ✅ 이미지 무텍스트 + ASS burn-in |
| 실이미지 | ✅ Imagine 3종 시작 (`assets/generated/ep01/`) — 대량 생성은 후속 |
| **기본 보이스** | **F5@0.95 / M4@0.72 pitch -8** — `config/media_rules_lock.json` 고정 |
| 면책 문구 | 낭독 **제외** → 설명란만 (`licenses.yaml`) |
| 엠비언트 영상 계획 | `../계획서_구약힐링_엠비언트영상_매칭.md` v1.1 |
| 플레이트 파이프 | ✅ yaml + timeline + assign + qa |
| 엠비언트 스모크 | `smoke_review/final-sample5-ambient-smoke.mp4` (~6.5분, 플레이트 1) |
| **최종 본편** | **`hermes_jobs/full/final-ep01-full.mp4` (~50분 14초)** |
| 업로드 복사본 | `upload_package/final-ep01-full.mp4` |
| 권장 청취 샘플 | `voice_casting/sample5_F10_M10_stable.mp3` |

### 플레이트 스모크 재실행
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

### v3 재빌드 (스모크)
```powershell
cd C:\Users\amd\module\bible_healing
python scripts\prepare_plain_backgrounds.py --job runs\ep01_anxious_night\hermes_jobs\preview  # or real bg map
python scripts\build_cues_from_manifest.py --job runs\ep01_anxious_night\hermes_jobs\preview
python scripts\build_ass_from_cues.py --job runs\ep01_anxious_night\hermes_jobs\preview
python scripts\qa_healing_render.py --job runs\ep01_anxious_night\hermes_jobs\preview
python scripts\render_healing_v3.py --job runs\ep01_anxious_night\hermes_jobs\preview --final-name final-smoke10-v3.mp4
```

### 업로드할 파일 (여기)

```
C:\Users\amd\module\bible_healing\runs\ep01_anxious_night\upload_package\
  final-bible-healing-ep01-100m.mp4   ← 본편
  TITLE.txt
  DESCRIPTION.txt                     ← 챕터 포함
  TAGS.txt
  subtitles-ko.srt                    ← 선택
  CHECKLIST.md
```

원본 작업 디렉터리:
`runs/ep01_anxious_night/hermes_jobs/full/final-bible-healing-ep01-100m.mp4`

### 분량 설명

| 버전 | 길이 | 파일 |
|------|------|------|
| 순수 낭독 | 1:25:47 | `final-bible-healing-ep01.mp4` |
| **+ 유닛 쉼 (권장)** | **1:40:00 (100분)** | `final-bible-healing-ep01-100m.mp4` |

## 보이스

- narrator **F5** @ 0.95 / scripture **M4** @ 0.72, pitch -8  
- 단일 기준: `config/media_rules_lock.json`  
- yaml 참고: `config/voice_healing.yaml` (lock과 다르면 lock 우선)

## 파이프 요약

```
download → parse OSIS → build_episode → QA → pack_to_hermes
→ prepare_job_media → tts_multi_voice → lock_audio_manifest
→ render_simple_longform → extend_to_target_duration (100m)
→ build_chapter_timestamps_padded → build_upload_package
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
