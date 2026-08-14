# 구약 힐링 영상 프로젝트 작업 규칙

이 문서는 `C:\Users\amd\module` 프로젝트 전용 지침이다. 상위·외부 프로젝트인 `C:\Users\amd\hermes\CLAUDE.md`의 규칙을 이 프로젝트에 자동으로 상속하지 않는다.

## 작업 전 필수 확인

1. `bible_healing/config/media_rules_lock.json`
2. `manual.md`
3. `research.md`
4. `bible_healing/config/final_render_policy.json`
5. `bible_healing/scripts/media_rules_preflight.py` (본편 full-job 게이트)
6. `bible_healing/scripts/final_background_preflight.py`
7. `bible_healing/scripts/final_render_preflight.py` (first3min/preview 전용; 본편 아님)

문서 규칙과 실행 정책이 다르면 `media_rules_lock.json`을 기준으로 삼되, 반드시 문서도 함께 수정한다.

## 본편 게이트

- **본편(full) preflight:** `python bible_healing/scripts/media_rules_preflight.py --job <full>`
- **본편 postflight:** `python bible_healing/scripts/media_rules_postflight.py <mp4> --job <full>`
- `final_render_preflight.py`는 `actual_first3min_pause_split` 등 프리뷰 경로용이다. 본편 배포 게이트로 쓰지 않는다.

## 배경영상 규칙

- 최종영상 배경은 반드시 `bible_healing/assets/movie-sample/pingpong-1min/*.mp4`에서 선택한다.
- 각 배경은 1분 길이의 앰비언트 영상이며 정방향·역방향 핑퐁 루프가 적용된 파일이다.
- `scene_*_flow.jpg`, `bg_*.jpg`, 정지 이미지, 단색 plate를 최종 배경으로 사용하지 않는다.
- 최종 렌더 전에 다음 검사를 실행한다.

```powershell
python bible_healing/scripts/final_background_preflight.py
# 본편 full job:
python bible_healing/scripts/media_rules_preflight.py --job bible_healing/runs/ep01_anxious_night/hermes_jobs/full
# first3min/preview only:
python bible_healing/scripts/final_render_preflight.py --job <preview_job>
```

검사 실패 시 렌더를 시작하지 않는다.

## 음성 규칙 (lock과 동일해야 함)

- 허용 화자는 `narrator`와 `scripture`뿐이다. F3/M2/M3/M5 금지.
- **여성 narrator:** F5, speed **0.95**, total_step 8, silence 0.24, 필터 없음.
- **남성 scripture:** M4, speed **0.88**, total_step **10**, silence **0.25**, pitch **-14%** (`asetrate=24000*0.86,aresample=24000`, **atempo 없음**). 체감 속도 약 0.76.
- 성경은 절 하나 = TTS 1회. `max_chunk` 90. 자막 시간은 필터 후 WAV 길이.
- 성경 본문에서 괄호·표제·셀라·느낌표·물음표를 제거한다.

## 자막 규칙

- 롱폼 균형형 자막을 사용한다.
- 최대 2줄, 한 줄 목표 14~18자, hard 최대 20자다.
- 본문 96px, 성경 100px(1080p), outline 6, shadow 3, marginV 90.
- 자막은 실제 오디오 세그먼트 시작·종료 시각을 따른다.
- 장면 전체 시각을 여러 자막에 재사용하지 않는다.
- 자막 크기와 위치를 영상 전체에서 고정한다.

## 챕터 표시 규칙

- 우측 상단에 현재 주제 확인용으로 표시한다.
- 최대 한 줄, 최대 12자, 1080p 기준 36px 이하로 한다.
- 자막보다 작게 표시한다.
- 영상에서 사라지지 않고 주제가 바뀔 때 문구만 교체한다.

## 결과물 보호

- 기존 영상·원본 에셋·설정·매뉴얼을 덮어쓰지 않는다.
- 새 렌더는 별도 파일명으로 만든다.
- 불완전한 렌더 파일은 검증 전에 배포본으로 보고하지 않는다.
- 최종 보고에는 배경 MP4 경로, 영상 길이, 코덱, 자막 검사 결과를 기록한다.

## 전체 배포영상 필수 검사 규칙

- 배경은 반드시 `bible_healing/assets/movie-sample/pingpong-1min/*.mp4`의 1분 앰비언트 샘플을 사용한다.
- 12개 샘플을 순환 사용하며 단일 촛불 영상만 반복하지 않는다.
- 배경은 `setpts=3*PTS`로 0.333배속 재생한다.
- 최종 배포본에는 `subtitles-full-audio-aligned.ass` 본문 자막을 반드시 번인한다.
- 챕터 오버레이만 있고 본문 자막이 없으면 배포 불가다.
- 최종 렌더 전 `final_background_preflight.py`와 **본편** `media_rules_preflight.py --job <full>`을 모두 통과한다.
- first3min/preview는 `final_render_preflight.py`를 사용한다 (본편 경로 아님).

## 음성·자막 전체 파이프라인 검사 규칙

- 자막은 장면 번호만으로 만들지 않고 실제 오디오 manifest의 `startSeconds`와 `endSeconds`를 기준으로 생성한다.
- 최종 음성 길이와 자막 마지막 타임코드는 반드시 일치해야 한다. 허용 오차는 0.5초 이내다.
- 자막 마지막 타임코드가 음성보다 짧으면 배포를 중단한다.
- 기존 자막 파일을 다른 전체 영상에 복사하지 않는다. 음성·자막·영상이 동일 작업의 산출물인지 확인한다.
- 장면 manifest에 없는 추가 음성 구간이 발견되면 배포하지 않고 원본 오디오와 장면 대본을 먼저 대조한다.
- 최종 검사 항목: 음성 길이, 자막 마지막 타임코드, 자막 이벤트 수, 시작·종료 시각의 오름차순, 빈 구간 없음.
