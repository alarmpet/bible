# 최종 영상 단일 규칙

모든 생성기는 `bible_healing/config/media_rules_lock.json`을 단일 기준으로 사용한다. `manual.md`, `CLAUDE.md`, `bible_healing/HANDOFF.md`, 연구·계획 문서와 런타임 설정이 다르면 렌더를 중단하고 이 잠금 파일을 기준으로 동기화한다.

## 음성 (2026-08-14 고정)

| | 여성 narrator | 남성 scripture |
|---|---|---|
| 보이스 | **F5** | **M4** |
| 엔진 속도 | **0.95** | **0.88** |
| total_step | 8 | **10** (24 금지) |
| 조각 사이 쉼 | 0.24초 | **0.25초** |
| 피치 | 없음 | **-14%** (`asetrate=24000*0.86,aresample=24000`, **atempo 없음**) |
| 체감 속도 | 0.95 | 약 **0.76** (0.88×0.86) |
| 필터 | 없음 | highpass 60Hz, lowpass 7000Hz, EQ 180Hz +2.5dB |
| 합성 단위 | 장면 문장 | **절(마침표) 하나 = TTS 1회**, `max_chunk_length` 90, 어절 중간 절단 금지 |

- 화자는 `narrator`와 `scripture`만 허용한다. F3/M2/M3/M5 금지.
- TTS 입력에서 `! ！ !? ❗ ? ？`는 마침표, `<laugh> <breath> <sigh>`·표제·셀라 금지.
- 자막 시간은 필터 **후** 실제 WAV 길이를 쓴다. `--skip-existing` 금지.

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
