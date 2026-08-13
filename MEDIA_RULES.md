# 최종 영상 단일 규칙

모든 생성기는 `bible_healing/config/media_rules_lock.json`을 단일 기준으로 사용한다. `manual.md`, `CLAUDE.md`, `bible_healing/HANDOFF.md`, 연구·계획 문서와 런타임 설정이 다르면 렌더를 중단하고 이 잠금 파일을 기준으로 동기화한다.

## 음성

- 화자 종류는 `narrator`와 `scripture` 두 개만 허용한다.
- narrator는 F5 (speed 0.95, total_step 8, silence 0.24), scripture는 승인된 남성 M4만 사용한다.
- scripture는 속도 0.72, pitch -8%, 문장 종결 뒤 0.65초 쉼, `max_chunk_length` 90을 사용한다.
- scripture `total_step`은 A/B 전까지 `pending_ab`이며 후보는 8·10·12다. 24는 금지한다.
- TTS 입력에서 `! ！ !? ❗ ? ？`는 마침표로 바꾸고, `<laugh> <breath> <sigh>`는 금지한다.
- `--skip-existing`로 예전 WAV를 재사용하지 않는다.
- F3, M2, M3, M5, 이전 MP4 오디오, 임의 voice loop는 최종 음성으로 금지한다.

## 자막

- 실제 authoritative 음성의 장면별 시작·종료 시각에서 만든다.
- 최대 2줄, 한 줄 목표 14~18자, 최대 20자. 조사·어미·어절 중간 분할 금지.
- 본문 96px, 성경 100px, outline 6, shadow 3, marginV 90 (Malgun Gothic).
- 표제·셀라·느낌표가 ASS에 남아 있으면 배포하지 않는다.
- 음성과 자막의 시작·종료 차이는 0.5초 이내여야 한다.

## 영상·배경·저장

- 배경은 `pingpong-1min`의 12개 1분 MP4를 순환 사용하고 0.333배속으로 재생한다.
- 정지 이미지와 과거 MP4의 오디오 트랙을 최종 입력으로 사용하지 않는다.
- 최종 산출물은 `D:\bible_healing_ep01\final`, 임시 파일은 `D:\bible_healing_ep01\work`에 저장한다.
- `media_rules_preflight.py`가 실패하면 렌더하지 않고, `media_rules_postflight.py`가 통과하지 않으면 배포하지 않는다.
