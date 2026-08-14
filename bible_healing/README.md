# bible_healing — 구약 공개 성경 · 이중 보이스 힐링 낭독

약 100분(±20%) 유튜브형 콘텐츠 파이프라인.

## 본편 (유일한 진입점)

```powershell
cd C:\Users\amd\module
python bible_healing/scripts/run_full_media_pipeline.py --job bible_healing/runs/ep01_anxious_night/hermes_jobs/full
```

오케스트레이터가 preflight → job 재빌드 → TTS(skip-existing 없음) → provenance →
authoritative audio → ASS+QA → D: 렌더 → postflight 를 순서대로 실행한다.
중간 실패 시 다음 단계를 돌리지 않는다. 단계 리포트: `D:\bible_healing_ep01\work\pipeline\`.

## 빠른 시작 (준비 단계)

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

# 4) Hermes job 패킹 (scenes + voice_map) — 본편은 오케스트레이터가 build_full_job 재실행
python scripts\pack_to_hermes.py --episode ep01_anxious_night --mode full

# 5) 보이스 프리뷰만 (본편 TTS는 오케스트레이터)
& "C:\Users\amd\supertonic3-local-tts-20260517-r4\supertonic3-local-tts\.venv-win\Scripts\python.exe" `
  ..\modern\scripts\tts_multi_voice.py --job runs\ep01_anxious_night\hermes_jobs\full --preview-only
```

## 현재 산출 (ep01)

- 최종 배포 경로: `D:\bible_healing_ep01\final\deploy-ep01-authoritative-audio-aligned.mp4`
- 운영 메모: `HANDOFF.md`

## 고정 보이스

| | 여성 narrator | 남성 scripture |
|---|---|---|
| ID | F5 | M4 |
| 엔진 속도 | 0.95 | 0.88 |
| 피치 | 없음 | -14% (asetrate 0.86, atempo 없음) |
| 쉼 / step | 0.24s / 8 | 0.25s / 10 |

값은 `config/media_rules_lock.json`이 원본이다.


## 본문 라이선스

- 한국어: **개역한글(KRV)** 계열 공개 텍스트 (저작권 만료)
- 소스: [seven1m/open-bibles](https://github.com/seven1m/open-bibles) `kor-korean.osis.xml`
- 현대 해설·나레이션: 채널 오리지널 (의료 치료 대체 아님)

자세한 설계: `../계획서_구약_힐링_낭독_파이프라인.md`
