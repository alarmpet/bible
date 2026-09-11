# Rank1 Exact Master 산출물 검증·검수 보고서

- 검수일: 2026-09-11 (KST)
- 대상 릴리스: `HL-RANK1-EXACT-CLONE-V1`
- 대상 영상: `tPBVrfcU85g`
- 검수 범위: 최종 MP4, 외부 WAV, 릴리스 매니페스트, canonical timeline, subcut plan, master plate plan, ASS 자막, exact pipeline 코드
- 제외 범위: BGM, 채널 로고/워터마크, HUD 카드의 품질 판정

## 1. 최종 판정

**기술 컨테이너는 조건부 통과이나, `1:1 완전 복제 마스터`로의 릴리스 승인은 보류한다.**

파일 존재성, 제시된 SHA-256, MP4의 30fps/29,195프레임, 전체 디코딩은 확인됐다. 그러나 다음 사유로 콘텐츠와 감사 추적성 기준을 충족하지 않는다.

1. 실제 canonical timeline은 406개가 아니라 346개 cue이다.
2. ASS 자막 600개 이벤트 중 85개가 `\\N`을 포함해 1줄 조건을 위반한다.
3. 실제 마스터 이미지 콘텐츠는 40개뿐이며, 모두 1920×1080 포토리얼 이미지다. 계획상의 80개 2304×1296 2D 마스터 플레이트가 아니다.
4. WAV는 주장된 46,711,584 샘플이 아니라 RIFF PCM 데이터 기준 46,711,609 샘플이다.
5. “3-Track WAV”는 실제로 1개 오디오 스트림·2채널 stereo이며, 3개 stem/track 구조가 없다.
6. 매니페스트는 파일별 SHA 목록일 뿐, source-to-release SHA 체인·Gate 0~5 결과·검증 도구 버전을 포함하지 않는다.
7. exact pipeline의 postflight는 실제 프레임 손상, 자산 차원, 1줄 자막, 2D 스타일을 검사하지 않는다.

## 2. 산출물 대조 결과

| 항목 | 주장값 | 실측값 | 판정 |
|---|---:|---:|---|
| MP4 파일 크기 | 265,379,922 bytes | 265,379,922 bytes | PASS |
| MP4 SHA-256 | `4E45C619...5D9131F` | 동일 | PASS |
| MP4 영상 | H.264 High, 1920×1080 | H.264 High, 1920×1080, progressive, yuv420p | PASS |
| 영상 프레임레이트 | 30.00 fps CFR | `r_frame_rate=30/1`, `avg_frame_rate=30/1` | PASS |
| 영상 프레임 수 | 29,195 | `nb_frames=29,195`, `nb_read_frames=29,195` | PASS |
| 영상 런타임 | 973.166667 s | 973.166667 s | PASS |
| MP4 오디오 | AAC-LC, 48kHz, stereo, 320kbps | AAC-LC, 48kHz, 2ch stereo, 측정 bitrate 약 273.705kbps | CONDITIONAL |
| WAV 파일 크기 | 186,846,514 bytes | 186,846,514 bytes | PASS |
| WAV SHA-256 | `E9993714...B6CFC30` | 동일 | PASS |
| WAV PCM | 46,711,584 samples | RIFF `data` 기준 46,711,609 sample frames | FAIL |
| WAV 런타임 | 973.158000 s | 973.158521 s | CONDITIONAL |
| 매니페스트 릴리스 ID | `HL-RANK1-EXACT-CLONE-V1` | 동일 | PASS |
| 매니페스트 파일별 hash/size | 6개 artifact | 6개 모두 존재·size/hash 일치 | PASS |
| SHA chain freeze | 체인 동결 | chain root/order/source hash 없음 | FAIL |

MP4 영상과 MP4 AAC 스트림의 실측 parity는 `0.008667초`, MP4 영상과 외부 WAV의 parity는 `0.008146초`로 모두 `0.033초` 이내다. 다만 외부 WAV와 MP4 AAC 사이에는 `0.000521초`, 즉 25 sample frame 차이가 있으므로 어떤 샘플 경계를 SSOT로 삼는지 매니페스트에 고정해야 한다.

## 3. 타임라인 SSOT 검수

실제 파일 대조 결과는 다음과 같다.

| 소스/산출물 | 실측 개수 | 비고 |
|---|---:|---|
| `scratch/human_library_top3/rank1_tPBVrfcU85g_cues.json` | 346 | 사용자가 제시한 406과 불일치 |
| `canonical_timeline_manifest.json`의 `cues` | 346 | `target_duration_sec=973.167`, 마지막 cue end `973.167` |
| 원본 JSON3 `events` | 694 | JSON3 이벤트 단위 |
| VTT timestamp line | 693 | 별도 포맷의 timestamp 단위 |
| `rank1_exact_master_subtitles.ass` Dialogue | 600 | cue의 자막 표시 분할 단위 |

따라서 406을 절대 SSOT라고 선언할 증거가 없고, 현재 릴리스는 346-cue canonical bundle에서 만들어진 것으로 보인다. 406이 실제 요구사항이면 Gate 0에서 중단하고 원본 cue 파일을 먼저 재확정해야 한다. 346이 올바른 원본이면 모든 문서와 테스트의 `406` 표기를 346 기준으로 정정해야 한다.

canonical cue 자체는 첫 시작 `2.79초`, 마지막 종료 `973.167초`, 0초 시작 0건, cue 간 overlap 0건으로 확인됐다. 이는 cue 배열의 물리적 정합성은 보여주지만, 406개 요구사항을 충족한다는 뜻은 아니다.

## 4. 자막 검수

`rank1_exact_master_subtitles.ass`는 다음을 만족한다.

- Dialogue: 600개
- 0초 시작: 0건
- 이벤트 overlap: 0건
- malformed Dialogue: 0건
- `DocuNarrator_Exact`: 600개
- `BorderStyle=3`: 확인
- 반투명 배경 `BackColour=&H80000000&`: 확인
- 노란색 강조 태그 `\\c&H003BEBFF&`: 89개 이벤트에서 확인

하지만 다음은 실패다.

- `\\N` 포함 multi-line 이벤트: 85개
- ASS 헤더의 `WrapStyle: 0`은 자동 줄바꿈을 허용하므로, “엄격한 1줄” 보장 장치가 아니다.
- 매니페스트에는 cue 수와 ASS 이벤트 수의 변환 규칙, 1줄 위반 수, 강조 태그 검증 결과가 없다.

첫 자막은 `0:00:02.79`에 시작하고 마지막은 `0:16:13.17`에 끝난다. 따라서 0초 도배 버그는 실측상 확인되지 않았지만, 1줄 조건은 현재 승인할 수 없다.

## 5. 서브컷·페이싱 검수

`subcut_montage_plan.json` 실측값:

- 총 컷: 570개 — 요구 범위 550~600 PASS
- parent shot: 40개 — PASS
- frame_count 합계: 29,195 — PASS
- 구간 overlap: 0건
- 잘못된 interval: 0건
- 첫 300초 cut 시작: 185개, 실제 전환 경계는 184개 — `>=150` PASS
- 전체 목표 기준 평균: `973.1667 / 570 = 1.70731초/cut`
- 실제 duration 범위: 0.3333~1.8000초
- 첫 40~46초 구간에 0.3333초 strobe cut이 존재

따라서 “550~600개”와 첫 300초 전환 수는 통과하지만, “평균 1.62초/cut”이라는 표현은 실측 평균과 맞지 않는다. 1.62초를 강제하려면 목표 컷 수를 약 601개로 조정하거나, 현재의 570개를 유지하고 문구를 `평균 1.707초/cut, 0.3333초 burst 포함`으로 바꿔야 한다.

또한 `frame_count`는 정확히 맞지만, JSON의 초 단위 값은 4자리 반올림이다. 최종 승인용으로는 cut마다 정수 `start_frame`, `end_frame_exclusive`를 저장하고 시간은 파생값으로 취급하는 편이 안전하다.

## 6. 마스터 플레이트·최종 영상 시각 검수

계획 파일은 `total_plates=80`을 선언하고 `main_narrative` 40개와 `contrast_detail` 40개 prompt를 보유한다. 그러나 각 plate 항목에는 `path`, `sha256`, `width`, `height`가 없다. 따라서 계획만으로 실제 80개 이미지 확보를 증명할 수 없다.

실제 run 디렉터리의 이미지 파일은 다음과 같다.

- 이미지 파일 수: 80개
- 고유 파일명 수: 40개 (`SHOT_001.jpg`~`SHOT_040.jpg`)
- 고유 콘텐츠 hash 수: 40개
- 각 파일명은 `generation/downloads/approved`와 `images`에 2벌 존재하지만 동일 hash
- 전체 해상도: 1920×1080
- 2304×1296 이미지: 0개

즉 80개는 서로 다른 80장이라기보다 40장의 중복 사본이다. 코드의 `get_plate_image()`도 `SHOT_xxx_A/B`를 찾지 못하면 `SHOT_xxx.jpg` 부모 이미지로 fallback하므로, 계획의 A/B plate 분리가 실제 렌더에 반영되지 않는다.

추출한 최종 영상 샘플 프레임(`0초`, `3초`, `300초`, `600초`, `972.8초`)을 육안 검수한 결과:

- 2D graphic novel / bold black ink / ligne claire / flat cel-shaded가 아니라 포토리얼 사진·사진풍 생성 이미지다.
- `300초`와 `972.8초` 샘플에는 2줄 자막이 실제로 보인다.
- 최종 영상에는 상단 우측 엠블럼 및 기타 그래픽 오버레이가 보인다. 이는 이번 판정의 제외 범위지만, “제외”를 의미하는 clean profile이 실제 렌더에 사용된 것은 아니다.

따라서 Art Style Gate는 현재 FAIL이다. prompt가 2D라고 쓰여 있는 것과 최종 픽셀의 스타일은 별도 검증 대상이며, prompt 문자열만으로 통과 처리하면 안 된다.

## 7. 오디오 구조 검수

외부 WAV의 RIFF 구조는 다음과 같다.

- chunk: `fmt ` 16 bytes, `LIST` 26 bytes, `data` 186,846,436 bytes
- codec: PCM signed 16-bit little-endian
- sample rate: 48,000Hz
- channels: 2
- bytes per sample frame: 4
- `data` sample frames: `186,846,436 / 4 = 46,711,609`
- WAV duration: `46,711,609 / 48,000 = 973.158520833초`

파일은 정상 디코딩되지만, “3-Track”이라는 명칭은 물리 구조와 맞지 않는다. 실제로는 하나의 stereo interleaved PCM stream이다. 3개 트랙을 의미하는 경우 다음 중 하나로 명세를 바꿔야 한다.

1. voice/BGM/SFX를 3개의 별도 stem WAV로 배포한다.
2. 한 파일 안의 6채널 또는 명시적인 multichannel layout으로 제공한다.
3. BGM 및 HUD/브랜딩을 제외한 현재 범위에서는 `voice_stereo_master_48k.wav`처럼 이름을 바꾼다.

또한 MP4 AAC stream의 probe bitrate는 약 273.705kbps다. `-b:a 320k`가 인코더 목표값일 수는 있지만, 320kbps를 릴리스 조건으로 주장하려면 측정 bitrate 허용오차를 정의하고 검증해야 한다.

## 8. 매니페스트와 Gate 감사성

매니페스트는 다음 6개 artifact의 path, size, SHA-256을 기록하고 있으며, 이번 검수에서 6개 모두 실제 파일과 일치했다.

- master MP4
- master WAV
- ASS subtitles
- canonical timeline manifest
- subcut montage plan
- master plates plan

그러나 root key는 파일별 artifact 목록뿐이며 다음이 없다.

- 원본 cue JSON의 path/size/SHA-256
- 원본 reference MP4의 path/size/SHA-256
- source → canonical → subtitles → subcut → plates → raw montage → final mux 순서의 ordered hash chain
- chain root digest 또는 서명
- Gate 0~5별 pass/fail, 실제 측정값, verifier 버전
- WAV의 실제 `data` sample frames
- ASS Dialogue 수, multi-line 수, overlap 수
- plate별 path, dimensions, SHA-256 및 fallback 사용 여부
- FFmpeg/FFprobe/Python 버전과 인코딩 command digest
- 전체 null-decode exit code 및 검사 시각

또한 코드의 `step_5_generate_release_manifest()`는 “Atomic Release Manifest”라고 출력하지만 Python `open(..., "w")`로 최종 경로에 직접 기록한다. 프로세스 중단 시 부분 매니페스트가 남을 수 있으므로 임시 파일 작성 후 `os.replace()`하는 원자적 교체가 필요하다.

현재 `status: PROMOTED_MASTER`와 `postflight_metrics.status: PASS`는 coarse probe 결과를 의미할 뿐, 실제 Gate 0~5 전체 통과를 증명하지 않는다.

## 9. 코드·워크플로우 검수 결과

`human_archive/scripts/run_human_library_exact_clone_pipeline.py`에서 확인된 위험:

- audio step은 “3-Track”이라고 출력하지만 원본 MP4에서 오디오를 추출해 하나의 stereo WAV를 만든다. SuperTonic3 voice와 3개 stem 생성은 코드상 입증되지 않는다.
- montage step은 `IMAGES_DIR`에서 A/B plate를 찾고, 없으면 parent shot 이미지로 fallback한다.
- assembly step은 `build_branding_overlay_filtergraph()`를 항상 호출한다. 이번 범위에서 로고/HUD를 제외하려면 overlay profile을 끌 수 있어야 한다.
- postflight는 duration, parity, fps, sample rate, frame count의 coarse assertion만 수행한다. exact frame count가 아니라 `[29194, 29195, 29196]`을 허용한다.
- postflight에는 전체 decode, ASS 1줄, 실제 이미지 차원, 실제 style, WAV RIFF sample count, source chain 검사가 없다.
- release manifest 생성은 per-file hash 목록이며 chain root가 아니다.

기존 테스트도 해석에 주의해야 한다.

- exact clone gate/pacing/pipeline/audio 테스트: 12 passed. 주로 plan·계약 데이터 검증이며 실제 2D 픽셀 스타일과 최종 MP4 손상 여부를 독립 검증하지 않는다.
- timeline/replica/subtitle 테스트: 9 passed. 346-cue canonical 및 기존 subtitle 계약을 대상으로 한다.
- full master physical release 테스트: 7 passed. 이 테스트는 주석과 assertion상 별도의 legacy `rank1_master_documentary.mp4` 1091.280초 artifact를 검증하므로, 새 exact master의 증거로 사용하면 안 된다.
- py_compile: 관련 3개 Python 파일 통과.

## 10. 수정 우선순위

### P0 — 재릴리스 전 필수

1. **Gate 0 SSOT 재확정**: 406과 실제 346 중 하나를 원본 파일 hash와 함께 선택한다. 선택 전에는 `PROMOTED_MASTER`를 유지하지 않는다.
2. **실제 2D plate 재생성**: `SHOT_xxx_A/B` 각각의 파일 path·hash·dimensions를 생성하고, 누락 시 fallback 대신 hard fail한다. 출력은 2304×1296 이상 원본을 보존하고 1920×1080은 렌더 단계에서만 downsample한다.
3. **1줄 ASS 재생성**: `\\N` 0건을 강제하고, 폭 초과 시 cue를 더 잘게 나누되 start/end frame 기반으로 재계산한다.
4. **최종 시각 검증 추가**: 샘플링이 아니라 모든 cut의 대표 frame에서 photoreal/placeholder/duplicate plate를 검사하고, style gate를 실제 픽셀 기준으로 판정한다.

### P1 — 정합성과 재현성 개선

1. WAV를 `46,711,584` sample frames로 정확히 trim할지, 실제 `46,711,609`를 표준으로 채택할지 결정한 뒤 MP4/WAV/manifest를 동일 기준으로 재생성한다.
2. AAC bitrate를 목표값과 측정값으로 분리 기록하고, 320kbps를 요구하면 측정 허용오차를 정한다.
3. manifest에 source hash, intermediate hash, gate metrics, toolchain, command digest, verifier version을 추가한다.
4. manifest는 temp path에 쓴 뒤 `os.replace()`로 교체한다.
5. `start_frame`/`end_frame_exclusive`를 모든 cue·cut·audio boundary의 1차 값으로 저장한다.

### P2 — 범위 분리와 테스트 보강

1. BGM·로고·HUD 제외 범위를 pipeline profile로 명시하고, clean profile에서는 해당 입력과 filtergraph를 완전히 제거한다.
2. “3-Track”을 실제 stem 산출물과 연결하거나 `voice_stereo_master`로 이름을 정정한다.
3. 최종 MP4를 직접 대상으로 하는 독립 verifier를 추가한다. verifier는 파일 hash, ffprobe, frame count, null decode, ASS, plate manifest, WAV RIFF, parity를 한 번에 검사해야 한다.
4. 기존 legacy 1091.280초 테스트와 새 973.167초 exact release 테스트를 파일명·fixture·manifest schema로 분리한다.

## 11. 재검수 통과 기준

다음 조건을 모두 만족한 새 릴리스에서만 `PROMOTED_MASTER`를 허용한다.

- canonical source count와 요구 count가 일치하고 source SHA가 고정됨
- 영상 `29,195 frames`, `30/1 CFR`, runtime tolerance `<=0.033s`
- WAV sample frame count와 manifest sample count가 byte-level로 일치함
- ASS `0초 시작 0`, overlap 0, `\\N 0`, keyword tag 정책 통과
- subcut `550~600`, frame sum `29,195`, 첫 300초 transition `>=150`
- 실제 고유 2D plate 75~85장 또는 명시된 A/B 80장, 각 plate path/hash/dimension 검증
- 전체 MP4/WAV decode exit code 0
- MP4 AAC bitrate와 audio stream 구조가 명세와 일치
- source부터 final까지 ordered SHA chain 및 chain root 생성
- 독립 verifier가 모든 gate를 재실행하고 manifest status를 결정함

## 12. 검증 명령 및 결과

검수 환경: Windows, Python 3.13.5, pytest 9.0.3, FFmpeg/FFprobe 6.2 계열.

```text
SHA-256/size existence check                         PASS
manifest artifact size/hash cross-check              PASS (6/6)
ffprobe MP4/WAV                                      PASS
ffprobe frame count                                  PASS (29,195 / 29,195 read)
ffmpeg MP4 video null decode                         PASS (exit 0)
ffmpeg MP4 audio null decode                         PASS (exit 0)
ffmpeg WAV null decode                               PASS (exit 0)
pytest exact clone gate/pacing/pipeline/audio        PASS (12 passed)
pytest timeline/replica/subtitle                     PASS (9 passed)
pytest legacy full master physical release          PASS (7 passed; legacy artifact only)
python -m py_compile                                 PASS
```

검수 결론은 “파일이 손상되지 않았고 일부 컨테이너 수치가 정합하다”는 수준에서는 긍정적이다. 그러나 현재 산출물은 2D 스타일, 1줄 자막, 실제 80개 plate, 406-cue SSOT, 3-track WAV, Gate 0~5 감사 체인을 충족하지 않으므로 **조건부 기술 검증본**으로 보관하고, “1:1 완전 복제 최종 릴리스” 명칭과 `PROMOTED_MASTER` 상태는 수정 후 재검수까지 보류한다.
