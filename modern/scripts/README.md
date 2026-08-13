# modern/scripts — Hermes 브리지 CLI

다른 LLM/에이전트는 **`../HANDOFF.md`를 먼저** 읽으세요.

## 명령 순서 (Preview)

```powershell
cd C:\Users\amd\module\modern

# 0) 경로 확인
python scripts\paths.py

# 1) shot_plan.json 생성
python scripts\build_shot_plan_json.py --run smoke_g1

# 2) job 패키징 (Ch1 16씬)
python scripts\pack_hermes_job.py --run smoke_g1 --mode preview

# 3) 검증 (exit 0=pass, 1=block, 2=warn)
python scripts\validate_job.py --job runs\smoke_g1\hermes_jobs\preview

# 4) 보이스 미리듣기 (나레이션/캐릭터 각각)
python scripts\tts_multi_voice.py --job runs\smoke_g1\hermes_jobs\preview --preview-only
# → runs/smoke_g1/hermes_jobs/preview/voice_previews/*.wav
# 귀 검수 후 voice_map.json 에 "preview_approved": true

# 5) 전체 multi-voice TTS
python scripts\tts_multi_voice.py --job runs\smoke_g1\hermes_jobs\preview

# 6) Hermes lock (단일 보이스 TTS 재호출 방지 — 필수)
python scripts\lock_audio_manifest.py --job runs\smoke_g1\hermes_jobs\preview --backup

# 7) Hermes 렌더
cd C:\Users\amd\hermes
$env:HERMES_YOUTUBE_FINAL_NAME = "final-preview-multivoice.mp4"
node scripts\render-youtube-with-tts.mjs C:\Users\amd\module\modern\runs\smoke_g1\hermes_jobs\preview

# 8) 인트로 프리롤
cd C:\Users\amd\module\modern
python scripts\pre_roll_intro.py --job runs\smoke_g1\hermes_jobs\preview --body runs\smoke_g1\hermes_jobs\preview\final-preview-multivoice.mp4
```

## 파일

| 스크립트 | 설명 |
|---|---|
| paths.py | 경로 단일 소스 |
| build_shot_plan_json.py | 이미지+챕터 → shot_plan.json / segments |
| pack_hermes_job.py | Hermes jobDir 생성 |
| validate_job.py | BLOCK/WARN |
| tts_multi_voice.py | **화자별** SuperTonic + scene wav concat |
| lock_audio_manifest.py | multi-voice → Hermes `measured-and-locked` |
| pre_roll_intro.py | intro.mp4 + body → final_with_intro.mp4 |

## Full 40씬 (축약 스모크)

```powershell
python scripts\pack_hermes_job.py --run smoke_g1 --mode full
python scripts\validate_job.py --job runs\smoke_g1\hermes_jobs\full
python scripts\tts_multi_voice.py --job runs\smoke_g1\hermes_jobs\full
```

## Upload fulltext (본선 · 전문 대본)

```powershell
python scripts\build_shot_plan_json.py --run smoke_g1 --profile fulltext
python scripts\pack_hermes_job.py --run smoke_g1 --mode upload
python scripts\validate_job.py --job runs\smoke_g1\hermes_jobs\upload
# SuperTonic venv 권장 — 233씬 TTS ~25분, 렌더 ~1.5–2시간
& "C:\Users\amd\supertonic3-local-tts-20260517-r4\supertonic3-local-tts\.venv-win\Scripts\python.exe" `
  scripts\tts_multi_voice.py --job runs\smoke_g1\hermes_jobs\upload
python scripts\lock_audio_manifest.py --job runs\smoke_g1\hermes_jobs\upload --backup
cd C:\Users\amd\hermes
$env:HERMES_YOUTUBE_FINAL_NAME = "final-upload-fulltext.mp4"
node scripts\render-youtube-with-tts.mjs C:\Users\amd\module\modern\runs\smoke_g1\hermes_jobs\upload
```

## 주의

- 단일 보이스 `make-scenes-tts.py` 만 돌리면 나레이션=대사 동일 톤 → **제품 금지**
- 렌더 전 **반드시** `lock_audio_manifest.py` (없으면 Hermes가 단일 보이스로 덮음)
- CapCut Export 자동화 없음
