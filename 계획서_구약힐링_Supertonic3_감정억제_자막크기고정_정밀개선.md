# SuperTonic3 감정 억제·자막 크기 고정 정밀 개선 계획

작성일: 2026-08-12

## 결론

남성 음성이 소리를 지르는 원인이 느낌표 하나 때문이라고 단정할 수는 없다. 현재는 강한 문장부호가 TTS 입력에 남아 있을 가능성, 전처리 경로 우회, 비공식 범위의 품질 단계, 후처리 미적용이 겹친 문제다.

## 공식 조사 결과

공식 Supertonic API는 `voice_style`, `total_steps`, `speed`, `silence_duration`, `max_chunk_length`를 핵심 제어값으로 사용한다. 공식 README는 `total_steps` 5~12, `speed` 0.7~2.0 예시를 제시하며 0.7은 느린 속도다. 현재 프로젝트의 `total_step: 24`는 로컬 래퍼에서는 실행되지만 공식 문서 범위를 벗어나므로 A/B 검증이 필요하다.

공식 Supertonic3는 `<laugh>`, `<breath>`, `<sigh>` 같은 표현 태그도 지원한다고 안내한다. 성경 낭독에는 이 태그를 금지해야 한다.

출처:

- [Supertonic 공식 GitHub README](https://github.com/supertone-inc/supertonic)
- [Supertonic Python Quick Start](https://supertone-inc.github.io/supertonic-py/quickstart/)
- [Supertonic Python API](https://supertone-inc.github.io/supertonic-py/api/)

## 현재 코드에서 확인된 원인

### 1. 느낌표 완화가 실제 실행 경로에 강제되지 않음

`bible_healing/scripts/scripture_tts_prep.py`에는 느낌표를 마침표로 바꾸는 `soften_for_speech()`가 있다. 그러나 실제 합성기 `modern/scripts/tts_multi_voice.py`는 `scenes.json`의 `segments[].text`를 직접 `engine.synthesize_to_file()`에 전달한다. 모든 장면이 `scripture_tts_prep.py`를 통과했는지 검증하지 않는다.

따라서 “대본에 !가 있어서 소리 지르는가?”에 대한 답은 “가능한 원인 중 하나지만, 현재는 전처리가 보장되지 않아 영향을 받을 수 있다”이다.

### 2. 현재 설정이 공식 범위와 후처리 실행을 분리함

현재 목표 설정은 `M4 / speed 0.72 / total_step 24 / silence 0.65 / pitch -8%`다. 하지만 `audio_filter`는 설정에 기록돼 있어도 `tts_multi_voice.py`가 자동으로 FFmpeg 후처리하지 않는다. 실제 피치 하향은 별도 스크립트에서만 수행됐다.

### 3. 자막 크기 변화

`config/healing_caption_policy.json`은 1080p 기준 96px, 성경 구절 100px을 정의한다. 반면 최근 수동 프리뷰 스크립트들은 ASS를 직접 만들며 42px 또는 48px을 사용했다. 즉, `build_ass_from_cues.py`의 정책 기반 경로와 수동 ASS 경로가 충돌해 자막 크기가 달라졌다.

## 수정 계획

### A. TTS 입력 정규화기를 필수 단계로 연결

새 정규화기를 만들고 `tts_multi_voice.py` 직전에 강제한다.

- `!`, `!!`, `!?`, `❗` → 마침표
- 반복 물음표·강조 기호 제거
- 괄호 헤더·Selah 제거
- `<laugh>`, `<breath>`, `<sigh>` 등 표현 태그 차단
- 연속 공백·문장부호 정리
- 화면 표시용 원문과 TTS 입력용 정규화 문장을 분리 저장
- 각 segment에 원문·TTS 입력 해시 기록

### B. 공식 범위 A/B/C 샘플

동일한 대본과 후처리로 다음을 비교한다.

| 후보 | voice | speed | total_steps | silence | 목적 |
|---|---|---:|---:|---:|---|
| A | M4 | 0.70 | 8 | 0.55 | 공식 느린 속도·기본 품질 |
| B | M4 | 0.70 | 10 | 0.65 | 안정성과 품질 균형 |
| C | M4 | 0.72 | 12 | 0.65 | 현재 속도·공식 상한 |

`total_step 24`는 공식 범위 밖이므로 A/B/C와 비교해 실제 청취상 이득이 확인될 때만 예외로 유지한다.

### C. 후처리 파이프라인 고정

모든 장면에 자동 적용한다.

- 피치 하향 `-8%`
- high-pass 65Hz
- low-mid +1.5dB
- low-pass 8500Hz
- 장면별 loudness 정규화
- peak ceiling 고정
- 후처리 전후 파일 해시와 메타데이터 manifest 기록

### D. 자막 단일 스타일 고정

수동 ASS 헤더 생성을 금지하고 `build_ass_from_cues.py`만 사용한다.

- 1920×1080 기준
- Malgun Gothic Bold
- 본문 108px 후보
- 성경 구절 112px 후보
- 최대 2줄, 한 줄 최대 24자
- `ScaledBorderAndShadow: yes`
- `marginV 90px`
- 길이가 길어도 글자 크기를 자동 축소하지 말고 2줄로 재분할

현재 정책의 96/100px보다 크게 설정해 “너무 작다”는 문제를 해결한다.

### E. QA 게이트

1. TTS 입력에 느낌표·표현 태그·강조 기호가 없는가
2. `voice_map`과 실제 segment manifest의 voice/speed/steps가 일치하는가
3. 모든 WAV에 동일한 피치·EQ·loudness 후처리가 적용됐는가
4. ASS 스타일이 하나의 정책 경로에서만 생성되는가
5. 1920×1080에서 자막 글자 크기가 기준값 이상인가
6. 자막과 음성 timeline drift가 150ms 이내인가
7. 음성 peak/LUFS 급등이 없는가
8. 10초·1분·초반 3분 샘플을 각각 청취·시각 검수했는가

## 구현 순서

1. TTS 입력 정규화기와 테스트 작성
2. `tts_multi_voice.py`에 정규화 단계 강제 연결
3. 공식 범위 A/B/C 음성 샘플 생성
4. 승인 후보를 config에 잠금
5. 피치·EQ·loudness 후처리를 실제 파이프라인에 연결
6. 수동 ASS 생성 경로 제거
7. 108/112px 자막 1분 샘플 렌더
8. 자막·음성 QA 통과 후 초반 3분 재생성
9. 통과 후 전체 본편 적용

## 완료 기준

- 남성 음성이 문장 시작과 끝에서 소리 지르는 느낌이 없음
- 느낌표가 원문에 있어도 TTS 입력에서는 감정 고조 기호가 제거됨
- 모든 장면에서 동일 음성 후보·속도·후처리 사용
- 영상 전체에서 자막 크기·글꼴·외곽선이 일정함
- 1920×1080에서 읽기 쉬운 큰 자막 유지
