# bible_healing — 구약 공개 성경 · 이중 보이스 힐링 낭독

약 100분(±20%) 유튜브형 콘텐츠 파이프라인.

## 빠른 시작

```powershell
cd C:\Users\amd\module\bible_healing

# 1) 공개 성경 다운로드 + 파싱
python scripts\download_bible.py
python scripts\parse_osis_to_json.py

# 2) 에피소드 대본 빌드 (구절 DB 기반 + 큐레이션)
python scripts\build_episode.py --episode ep01_anxious_night

# 3) QA + 분량 추정
python scripts\qa_healing_script.py --episode ep01_anxious_night
python scripts\estimate_duration.py --episode ep01_anxious_night

# 4) Hermes job 패킹 (scenes + voice_map)
python scripts\pack_to_hermes.py --episode ep01_anxious_night --mode full

# 5) 보이스 프리뷰 / 본편 TTS (SuperTonic venv)
& "C:\Users\amd\supertonic3-local-tts-20260517-r4\supertonic3-local-tts\.venv-win\Scripts\python.exe" `
  ..\modern\scripts\tts_multi_voice.py --job runs\ep01_anxious_night\hermes_jobs\full --preview-only

# 6) 미디어 준비 + TTS 본편 + lock + 빠른 렌더
python scripts\prepare_job_media.py --job runs\ep01_anxious_night\hermes_jobs\full
& "C:\Users\amd\supertonic3-local-tts-20260517-r4\supertonic3-local-tts\.venv-win\Scripts\python.exe" `
  ..\modern\scripts\tts_multi_voice.py --job runs\ep01_anxious_night\hermes_jobs\full
python ..\modern\scripts\lock_audio_manifest.py --job runs\ep01_anxious_night\hermes_jobs\full --backup
python scripts\build_chapter_timestamps.py --job runs\ep01_anxious_night\hermes_jobs\full
python scripts\render_simple_longform.py --job runs\ep01_anxious_night\hermes_jobs\full --workers 4
```

## 현재 산출 (ep01)

- 최종 영상: `runs/ep01_anxious_night/hermes_jobs/full/final-bible-healing-ep01.mp4` (~86분)
- 운영 메모: `HANDOFF.md`


## 본문 라이선스

- 한국어: **개역한글(KRV)** 계열 공개 텍스트 (저작권 만료)
- 소스: [seven1m/open-bibles](https://github.com/seven1m/open-bibles) `kor-korean.osis.xml`
- 현대 해설·나레이션: 채널 오리지널 (의료 치료 대체 아님)

자세한 설계: `../계획서_구약_힐링_낭독_파이프라인.md`
