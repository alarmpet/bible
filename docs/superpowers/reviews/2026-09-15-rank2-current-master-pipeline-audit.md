# Rank 2 현재 마스터 영상·코드베이스·워크플로우 포렌식 감사

- **감사일**: 2026-09-15
- **대상 영상**: `D:\module\output\NOLLAM-HUMAN-LIBRARY-RANK2-EXACT-MASTER.mp4`
- **대상 제목**: 잊혀진 문명, 세계 최강이 사라진 이유
- **판정**: 컨테이너·프레임·해시·기본 테스트는 PASS이지만, 시각 연출·자막 가독성·대본-이미지 매칭·모션 연속성은 FAIL/보류
- **범위**: BGM, 채널 로고, HUD는 기존 clean-scope와 동일하게 평가 제외한다. 단, Google Flow provider 표식과 이미지에 baked-in된 하단 밴드는 채널 브랜딩이 아니므로 결함으로 평가한다.

## 1. 물리 산출물 재확인

현재 output mirror는 1,007,822,336 bytes, SHA-256 `590FFC0CE988F8A43FF822EBDEB5CA6AE306725735B600D8C0836E0846AB00CA`이다. ffprobe상 1920×1080 H.264 High, 30/1 CFR, 43,200 frames, 1,440.000초와 AAC-LC 48kHz stereo는 정상이다. 전체 video/audio null decode도 성공했고, `test_human_library_rank2_exact_physical_release.py`는 7/7 PASS(69.21초), 관련 Python 문법 검사도 PASS했다.

이 결과는 “파일이 재생된다”는 뜻이지, 시청각 품질이 원본과 맞거나 편집 문법이 정상이라는 뜻은 아니다. 현재 테스트가 검증하는 것은 주로 메타데이터·파일 존재·해시·계획 JSON이다.

## 2. 사용자가 지적한 연출 결함의 직접 증거

### 2.1 전환 효과가 없는 하드 컷 연속

실제 렌더 경로는 `run_human_library_rank2_exact_clone_pipeline.py` → `render_subcut_montage_stream()`이다. 이 함수는 각 컷의 PIL crop/resize 프레임을 하나의 rawvideo stdin으로 차례로 밀어 넣는다. 컷 사이에 `xfade`, `blend`, `dissolve`, `match cut`, `whip pan` 또는 transition duration을 적용하는 코드가 없다. 최종 filtergraph도 사실상 `[0:v]ass=...,fps=30,format=yuv420p`뿐이다.

따라서 `transformation`이라는 이름은 컷 내부 crop trajectory를 의미할 뿐, 컷과 컷을 연결하는 전환 효과를 의미하지 않는다. 836개 컷 경계는 전부 즉시 새 이미지로 교체된다.

### 2.2 컷 내부 모션보다 컷 경계 충격이 훨씬 큼

현재 raw montage를 96×54 grayscale로 전 프레임 스캔해 계획상의 836개 경계와 컷 내부 프레임 차이를 분리했다.

| 측정 | 결과 | 해석 |
|---|---:|---|
| 계획 컷 | 837 | 메타데이터상 숫자 |
| 실제 경계 | 836 | 각 컷 사이의 즉시 교체 |
| 경계 mean-abs diff 중앙값 | 35.17 | 이미지 교체 충격 |
| 컷 내부 mean-abs diff 중앙값 | 1.79 | 대부분 매우 약한 이동 |
| 컷 내부 diff < 1.0 비율 | 31.22% | 모션이 거의 감지되지 않는 프레임 쌍 |
| 경계 diff p95 | 65.34 | 일부 경계는 큰 플래시성 점프 |
| 컷 내부 diff p95 | 7.42 | 내부 모션보다 경계가 압도적으로 큼 |

즉 “정지화면은 아니므로 PASS”인 상태지만, 실제 체감은 **약한 Ken Burns + 매 1.7초 강제 점프**다. 이것이 전환 효과가 허접하고 영상이 덜컹거리는 근본 원인이다.

### 2.3 줌·팬 방향이 시맨틱이 아니라 전역 modulo 순환

현재 `subcut_montage_plan.json`의 837개 컷을 분석하면 다음과 같다.

- 첫 300초에 197컷이 배치됨
- 컷 내부 `zoom` 변화량이 0인 컷 234개
- 평균 zoom 변화량 0.078, 최대 0.14
- 평균 중심점 이동량 0.0628, 최대 0.12
- 인접 컷의 in/out 또는 좌/우 방향 역전 367건
- 씬당 컷 수가 10개 이상인 샷 52/64개
- 40~46초에 0.333초짜리 18컷 strobe 구간 존재

`build_rank2_semantic_subcut_plan.py`는 `MOTION_PROFILES[(cut_idx - 1) % len(MOTION_PROFILES)]`로 전역 순환 프로필을 선택한다. 그 결과 같은 의미 단위 안에서도 `pan_left → macro_detail → wide_establishing`, `pull_out → pan_left → macro_detail`처럼 방향·스케일이 자동으로 충돌한다. 367건의 방향 역전은 연출 의도나 대본 비트에서 나온 것이 아니라 이 순환의 부산물이다.

또한 `SubcutPlan` 주석에는 `horizontal_flip`이 있으나 Rank 2 실제 렌더러에는 flip/tilt/rotate 처리가 없다. 실제 구현은 crop box를 계산해 resize하는 한 가지 방식이다.

### 2.4 A/B 토글만 제거됐을 뿐, A/B가 실제로 다른 서브컷이 아님

709건의 `A-B-A` 왕복은 현재 plan에서 0건으로 줄었지만, 64개 A/B 프롬프트를 비교하면 평균 토큰 차이가 약 5.56%이며 핵심 차이는 `angle A composition` 대 `angle B alternate dynamic framing`이다. 즉 A/B가 대본의 서로 다른 정보 역할을 가진 샷이라기보다 같은 콘셉트에 각도 문구만 바꾼 변형에 가깝다.

현재 계획의 단조 배치는 “A를 먼저, B를 나중에”라는 순서만 보장한다. 그것이 곧 A에서 B로 정보가 진행된다는 뜻은 아니다. 따라서 `aba_repeats=0`은 필요한 조건이지만 충분조건이 아니다.

## 3. 대본·이미지 매칭 구조의 결함

### 3.1 최종 Rank 2 파이프라인이 대본을 직접 소비하지 않음

`run_human_library_rank2_exact_clone_pipeline.py`에는 `SCRIPT_PATH`가 선언되어 있지만 실행 중 읽히지 않는다. 실제 서브컷 플랜 생성기 `build_rank2_semantic_subcut_plan.py`도 `master_script_clean.json`, canonical cue, claim ID를 읽지 않고 `shot_composition_plan.json`의 64개 시간 구간만 읽는다.

따라서 최종 `subcut_montage_plan.json`의 각 컷에는 `sentence_id`, `cue_id`, `claim_id`, `visual_beat`가 없다. 결과적으로 “이 컷이 지금 읽히는 문장을 설명하는가”를 자동 검증할 수 없다. 기존 문서의 “대본 기반 시맨틱 바인딩 100%”는 shot time range 바인딩을 의미할 뿐, 문장·큐·주장 단위의 실제 의미 매칭을 의미하지 않는다.

### 3.2 동일 시각의 원본과 결과 장면이 다름

원본 `D:\module\scratch\human_library_top3\original_rank2.mp4`와 결과를 같은 60초 지점에서 비교했다. 두 영상의 자막 문구는 같은 “글자까지 통째로 읽으면서” 구간이지만, 원본은 무너진 고대 신전/유물 장면이고 결과는 나일강·사막 농경 지도 장면이다. 이는 단순한 스타일 차이가 아니라 source-to-target visual correspondence가 검증되지 않았다는 직접 증거다.

또한 원본 probe는 1,439.800초, 결과는 1,440.000초로 0.200초 차이가 있다. 현재 manifest는 1,440초 목표와 AV parity만 검증하므로 원본 시각 타임라인과의 exact correspondence를 보장하지 않는다.

## 4. 자막이 작고 답답하게 보이는 원인

`build_rank2_clean_subtitles.py`가 `DocuNarrator_Exact`에 `Fontsize=52`, `MarginV=55`를 고정한다. 이는 원본 영상의 baked-in 자막을 측정해 역산한 값이 아니며, 길이·문자 폭·배경 대비에 따른 적응형 크기 조정도 없다.

같은 60초 자막을 기준으로 샘플 프레임의 주요 흰색 glyph component 세로 높이는 결과 약 36px, 원본 약 52px로 관측됐다. 결과 자막은 글자 자체가 상대적으로 작고, 하단에는 자막과 무관한 넓은 dark band가 함께 있어 화면을 더 답답하게 만든다.

특히 raw montage 단계부터 하단 band와 우측 하단의 회색 Flow provider diamond가 존재한다. 즉 이것들은 ASS 자막 필터가 만든 것이 아니다. 현재 `validate_plate_manifest()`는 파일 존재·SHA·해상도·고유성만 검사하므로 OCR, provider watermark, baked-in band, safe-area 침범을 전혀 거부하지 않는다.

## 5. 왜 기존 Gate가 문제를 잡지 못했는가

현재 release verifier가 확인하는 것은 다음과 같다.

1. MP4 codec, 해상도, CFR, frame count, duration
2. AAC sample rate/channel과 AV duration parity
3. ASS zero-start/overlap/multiline
4. plate count, dimensions, SHA, unique count
5. subcut JSON의 cut count/frame count/A-B 2-back/role reversal
6. 전체 decode 및 SHA-256 chain

빠진 검사는 다음과 같다.

- 실제 encoded frame boundary와 계획 경계의 일치
- transition type/length의 실사용 여부
- 컷 내부 모션량과 방향 연속성
- sentence/cue/claim-to-shot-to-plate 매칭
- 원본 동시각 장면 대응
- OCR·Flow 표식·baked-in band 검출
- 자막 glyph 크기와 원본 대비 가독성
- 컷당 semantic novelty 및 같은 콘셉트의 반복

그러므로 `31/31 PASS`, `aba_repeats=0`, `PROMOTED_MASTER`는 물리·구조 Gate의 결과일 뿐이며, 현재 영상의 시각 품질을 PASS로 해석하면 안 된다.

## 6. 근본 원인 요약

1. **렌더러 분리 실패**: 정교한 `CinematicEffectPlanner`/`CinematicEditingDirector`와 Rank 2 전용 `subcut_montage_engine`가 연결되지 않았다.
2. **전환 계층 부재**: cut-in/cut-out transition contract가 없고 raw frame concat만 수행한다.
3. **모션 파라미터의 전역 순환**: 대본 비트·초점 객체·이전 컷 상태가 아닌 `cut_idx % profile_count`로 연출을 결정한다.
4. **의미 매칭 부재**: 최종 렌더 플랜이 대본 문장·큐·claim ID를 보유하지 않는다.
5. **A/B 생성 차별성 부족**: A/B 프롬프트가 동일 장면의 각도 문구 변경 수준이다.
6. **QA가 선언값 중심**: 실제 영상 프레임과 시청자 체감 품질을 검증하지 않는다.
7. **자막/plate 전처리 미흡**: 52pt 고정 자막과 provider/band가 clean visual layer에 들어간 채 승격된다.

## 7. 결론

현재 MP4는 재생 가능한 기술 산출물이지, 사용자가 요구한 고품질 다큐멘터리 연출 마스터로 승인할 수 없다. A/B 왕복 709건은 해결됐지만, 그 수정이 영상의 핵심 문제인 하드 컷, 약한 모션, 전역 순환, 대본-이미지 불일치, 작은 자막, baked-in 오염을 해결하지 못했다.

다음 단계는 기존 output을 덮어쓰지 않고, 문장·큐·주장·샷·플레이트·모션·전환을 하나의 edit graph로 재구성한 clean candidate를 만든 뒤 실제 프레임 기반 독립 검수와 시청용 preview 승인 후에만 승격하는 것이다.
