# SuperTonic3 자연 낭독 업그레이드 (옵션 B)

날짜: 2026-08-15  
상태: 승인된 방향. CosyVoice3 등 새 TTS 설치는 하지 않는다.

## 목적

이 PC 사양으로는 새 엔진 설치가 멈춘다. 본편 엔진은 SuperTonic3를 유지하고,
`Downloads/supertonic3-natural-narration-guide.md`에서 측정된 레버만 올린다.

잠금 유지: narrator F5 / scripture M4, speed 0.95, total_step 8·10.
`total_step`을 16으로 올리지 않는다. 전량 재합성은 이번 범위가 아니다.

## 범위

1. TTS 텍스트만 숫자를 한글로 바꾼다. 자막 `display`는 아라비아 숫자를 유지한다.
2. 합성 후 엔진 패딩을 `silenceremove`(-45dB / 30ms)로 자른다.
3. 페이싱은 조립 단계가 소유한다. 같은 화자 0.05초, 화자·장면 전환 0.6초.
   lock의 `silence_seconds` 0.24·0.25는 바꾸지 않는다.
4. SuperTonic HTTP 서버(`:3093`)가 켜져 있으면 그쪽으로 합성한다. 꺼져 있으면
   기존 in-process CLI 엔진으로 폴백한다. 새 TTS가 아니다.

## 비범위

- CosyVoice3 설치·모델 다운로드·본편 엔진 전환
- F5/M4 재선정
- `total_step` 16 이상
- lock `silence_seconds`를 0.05로 내리는 전량 재합성(옵션 C)

## 구성

- `korean_number_reading.py`: TTS 숫자 읽기
- `sanitize_script()`: `tts`에만 숫자 변환, `display`는 숫자 유지
- `trim_tts_padding.py`: 클립 앞뒤 정적 제거
- `tts_assembly.py`: 간격 계산
- `supertonic3_http.py`: `/health`, `/api/tts`, 로컬 wav 복사
- `start_supertonic3_server.ps1`: 기존 SuperTonic venv로 서버만 기동

## 성공 기준

- 단위 테스트: 숫자 변환, 자막 숫자 유지, 트림, 조립 간격, HTTP URL/폴백
- lock 화자·속도·step 불변
- 새 TTS 패키지/모델을 받지 않음
