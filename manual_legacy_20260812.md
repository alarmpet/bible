# Bible Healing 공용 운영 매뉴얼

이 문서는 특정 LLM, IDE, 에이전트, 대화 세션에 종속되지 않는 프로젝트 운영 기준이다. 어떤 LLM이 이어받아도 이 문서와 실행 로그를 읽으면 현재 상태를 파악하고, 같은 산출물 계약에 맞춰 작업을 재개할 수 있어야 한다.

## 1. 프로젝트 기준 경로

작업 루트:

```text
C:\Users\amd\module
```

프로젝트 루트:

```text
C:\Users\amd\module\bible_healing
```

핵심 문서:

- `계획서_구약힐링_첫1분훅_진성엠비언트.md` — 목표와 설계
- `계획서_구약힐링_첫1분훅_진성엠비언트_실행로그.md` — 문제, 수정, 검증, 보류 작업의 누적 기록
- `research.md` — 웹 조사와 출처
- `bible_healing/README.md` — 기존 파이프라인 명령
- `bible_healing/HANDOFF.md` — 기존 인수인계 기록

작업을 시작하는 LLM은 위 문서를 먼저 읽고, 실행 후에는 반드시 실행 로그에 결과를 추가한다.

## 2. 현재 상태 확인 순서

PowerShell에서:

```powershell
cd C:\Users\amd\module
Get-Content -Raw manual.md
Get-Content -Raw 계획서_구약힐링_첫1분훅_진성엠비언트_실행로그.md
Get-Content -Raw research.md
Get-ChildItem bible_healing\runs\ep01_anxious_night\hermes_jobs -Directory
```

현재 첫 1분 검증 산출물:

```text
bible_healing\runs\ep01_anxious_night\hermes_jobs\hook_smoke_v2
```

현재 full job은 새 대본과 scene 구조만 준비된 상태다. 유효한 full `scene_audio_manifest.json`이 없으면 본편 render나 업로드 패키지 생성을 진행하지 않는다.

## 3. 표준 작업 순서

### A. 대본 생성

```powershell
cd C:\Users\amd\module\bible_healing
python scripts\build_episode.py --episode ep01_anxious_night
```

첫 훅은 본문 뱅크가 아니라 아래 오버라이드에서 관리한다.

```text
config\opening_hooks\ep01_anxious_night.yaml
```

훅 단계는 다음 순서를 유지한다.

```text
hook → mirror → validate → permission_bridge → scripture
```

대본 변경 후:

```powershell
python scripts\qa_healing_script.py --episode ep01_anxious_night
python scripts\estimate_duration.py --episode ep01_anxious_night
```

### B. Hermes job 생성

```powershell
python scripts\build_full_job.py
python scripts\prepare_job_media.py --job runs\ep01_anxious_night\hermes_jobs\full
```

preview 또는 별도 smoke job을 만들 때는 원본 full job을 직접 덮어쓰지 않는다.

### C. 첫 1분 음성 smoke

첫 6개 scene만으로 검증 job을 만들 수 있다.

```powershell
python scripts\build_hook_smoke_job.py `
  --source runs\ep01_anxious_night\hermes_jobs\full `
  --destination runs\ep01_anxious_night\hermes_jobs\hook_smoke_next
```

SuperTonic 경로는 환경마다 다를 수 있다. 기본 환경은 다음과 같다.

```powershell
$ttsPython = "C:\Users\amd\supertonic3-local-tts-20260517-r4\supertonic3-local-tts\.venv-win\Scripts\python.exe"
& $ttsPython ..\modern\scripts\tts_multi_voice.py `
  --job runs\ep01_anxious_night\hermes_jobs\hook_smoke_next
```

TTS가 중단된 경우 이미 생성된 scene을 재사용할 수 있다.

```powershell
& $ttsPython ..\modern\scripts\tts_multi_voice.py `
  --job runs\ep01_anxious_night\hermes_jobs\hook_smoke_next `
  --skip-existing
```

첫 1분 QA:

```powershell
python scripts\qa_first_minute.py `
  --job runs\ep01_anxious_night\hermes_jobs\hook_smoke_next
```

통과 기준:

- 첫 음성 시작 ≤ 0.5초
- 첫 성경 구절 시작 45–55초
- 훅 단계 4개가 metadata에 존재
- 보장성 표현 없음
- 호흡 지시가 있다면 선택형 표현 포함

운영 TTS manifest는 `items`/`duration` 형식일 수 있고, lock된 manifest는 `scenes`/`startSeconds` 형식일 수 있다. QA는 두 형식을 모두 지원해야 한다.

### D. full 음성 생성 및 lock

첫 1분 smoke가 통과한 뒤에만 full 음성을 생성한다.

```powershell
& $ttsPython ..\modern\scripts\tts_multi_voice.py `
  --job runs\ep01_anxious_night\hermes_jobs\full
```

완료 후:

```powershell
& $ttsPython ..\modern\scripts\lock_audio_manifest.py `
  --job runs\ep01_anxious_night\hermes_jobs\full --backup
python scripts\qa_first_minute.py `
  --job runs\ep01_anxious_night\hermes_jobs\full
```

full TTS가 중단되면 오래된 음성과 새 음성을 같은 scene 번호로 섞지 않는다. 기존 파일은 삭제하지 말고 job 내부의 날짜가 붙은 백업 디렉터리로 이동한 뒤 재개한다.

### E. 자막·ambient·render

full manifest가 새로 lock되고 QA를 통과한 뒤에만 진행한다.

```powershell
python scripts\build_chapter_timestamps.py --job runs\ep01_anxious_night\hermes_jobs\full
python scripts\build_plate_timeline.py --job runs\ep01_anxious_night\hermes_jobs\full
python scripts\assign_plates_to_scenes.py --job runs\ep01_anxious_night\hermes_jobs\full
python scripts\qa_ambient_plates.py --job runs\ep01_anxious_night\hermes_jobs\full
python scripts\build_cues_from_manifest.py --job runs\ep01_anxious_night\hermes_jobs\full
python scripts\build_ass_from_cues.py --job runs\ep01_anxious_night\hermes_jobs\full
```

render 전에는 `qa_healing_render.py` 결과가 통과인지 확인한다. 실패한 render는 최종 파일로 이름을 바꾸지 않는다.

## 4. 파일 계약

대본 단계:

- `runs/<episode>/script_segments.json`
- `runs/<episode>/script_readable.md`
- `runs/<episode>/episode_manifest.json`

Hermes 단계:

- `hermes_jobs/<job>/scenes.json`
- `hermes_jobs/<job>/voice_map.json`
- `hermes_jobs/<job>/job.json`

음성 단계:

- `hermes_jobs/<job>/scene_*.wav`
- `hermes_jobs/<job>/segments/*.wav`
- `hermes_jobs/<job>/scene_audio_manifest.json`

검증 단계:

- `hermes_jobs/<job>/reports/qa_first_minute.json`
- `hermes_jobs/<job>/reports/qa_ambient_plates.json`
- `hermes_jobs/<job>/reports/qa_healing_render.json`

`scene_audio_manifest.json`이 없거나 job의 scene 수와 일치하지 않으면 해당 job의 시간 데이터는 유효하지 않은 것으로 취급한다.

## 5. LLM 간 인수인계 규칙

다른 LLM이 작업을 이어받을 때 첫 응답 전에 다음을 확인한다.

1. 현재 작업 루트와 episode id를 확인한다.
2. 계획서, 실행 로그, research, 이 문서를 읽는다.
3. `git` 사용 가능 여부와 현재 변경 상태를 확인한다. git 저장소가 아니면 파일 백업으로 변경 이력을 남긴다.
4. 마지막 실행 로그의 “남은 작업” 중 하나만 선택해 진행한다.
5. 기존 산출물을 덮어쓰기 전 job 수, manifest 상태, scene 번호를 확인한다.
6. 실패하면 원인·명령·출력·복구 조치를 실행 로그에 기록한다.
7. 성공을 주장하기 전에 테스트 또는 실제 QA 출력으로 증명한다.

LLM이 바뀌어도 다음 상태를 파일로 공유한다.

- 설계: 계획서
- 근거: `research.md`
- 진행 이력: 실행 로그
- 실행 절차: `manual.md`
- 실제 시간 권위: `scene_audio_manifest.json`
- 검증 결과: `reports/*.json`
- 복구 가능한 이전 산출물: 날짜별 backup 디렉터리

## 6. 변경 기록 양식

실행 로그에 아래 형식으로 추가한다.

```markdown
### YYYY-MM-DD — 작업 제목

- 목표:
- 변경 파일:
- 실행 명령:
- 발견한 문제:
- 원인:
- 수정:
- 검증 결과:
- 산출물 경로:
- 남은 위험:
- 다음 작업:
```

## 7. 절대 규칙

- 근거 없는 완료 선언을 하지 않는다.
- full job의 오래된 manifest를 새 대본의 시간 데이터로 사용하지 않는다.
- scene 번호가 바뀐 상태에서 기존 wav를 `--skip-existing`으로 재사용하지 않는다.
- 사용자 확인 없이 원본 대본·본문 DB·최종 영상 파일을 삭제하지 않는다.
- 연구 자료의 커뮤니티 반응을 임상적 효과나 시청 성과의 증거로 표현하지 않는다.
- 첫 1분 통과와 전체 영상 길이 통과를 별도 QA로 관리한다.

