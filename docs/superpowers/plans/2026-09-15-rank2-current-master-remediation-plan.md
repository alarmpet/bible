# Rank 2 현재 마스터 시각 품질 정상화 실행 계획

## 목표

`NOLLAM-HUMAN-LIBRARY-RANK2-EXACT-MASTER.mp4`의 컨테이너만 통과하는 상태를 종료하고, 대본·큐·주장·샷·이미지·모션·전환·자막이 실제 encoded frames에서 일치하는 clean candidate를 만든다. BGM, 채널 로고, HUD는 clean-scope에서 계속 제외한다.

## 절대 원칙

- 현재 output master와 기존 release manifest는 보존하며 새 candidate만 렌더한다.
- 물리 Gate PASS를 시각 품질 PASS로 해석하지 않는다.
- 모든 컷은 `sentence_id`, `cue_id`, `claim_ids`, `shot_id`, `plate_id`, `visual_beat`, `motion_profile`, `transition_in/out`을 가져야 한다.
- `A-B-A`/`B-A-B`뿐 아니라 같은 의미·같은 구도·같은 plate의 반복도 fail-closed한다.
- provider watermark, 생성 텍스트, baked-in subtitle band가 있으면 clean export 또는 재생성 전에는 승격하지 않는다.
- 모션 효과 이름만 기록하지 말고 실제 encoded frame에서 효과와 경계를 검증한다.

## V3 재설계 결정 — semantic match + calm pacing

- [x] 기존 V2의 600개 visible cut 전부를 빠른 컷으로 사용하지 않고 V3 목표를 420~480 visible hard cuts로 낮춘다.
- [x] 첫 10초 최대 4컷, 첫 30초 최대 10컷, cut당 dominant transform 1개를 적용한다.
- [x] 455컷/1,440초의 평균이 약 3.16초이므로 본문 visible cut은 3~5초를 기본으로 하고 긴 설명은 내부 reframe/hold로 처리한다.
- [x] 각 cut에 `semantic_anchors`와 `semantic_match_status`를 추가한다. ID lineage는 실제 이미지 의미 일치의 증명이 아니므로 pixel/human review를 별도 요구한다.

### V3 후보 실행 결과 (2026-09-15)

- [x] `NOLLAM-HUMAN-LIBRARY-RANK2-EXACT-MASTER-V3-CANDIDATE.mp4`를 별도 경로에 렌더하고 SHA-256 체인을 동결했다.
- [x] 물리 결과: 1,440.000초, 43,200 frames, AV delta 0.0000초, 전체 decode PASS, Gate 0~5 PASS.
- [x] 실제 encoded-frame 결과: boundary diff median 28.152, internal diff median 0.708, internal diff<1.0 75.30%, direction reversal 132건.
- [x] V3 의미 결과: 455/455 metadata anchor audit PASS이지만 `pixel_semantic_verification_required=true`를 유지한다.
- [ ] hard boundary 450건의 encoded transition 품질을 shot boundary/same-shot cut별로 분리 검수한다.
- [ ] source↔candidate 동시각 이미지 의미 검수와 preview 승인 전에는 기존 output을 교체하지 않는다.

## Task 1 — SSOT와 데이터 계보 재결합

**대상:** `master_script_clean.json`, canonical cue manifest, `shot_composition_plan.json`, `master_plates_composition_plan.json`, `subcut_montage_plan.json`

- [ ] source duration 1,439.800초와 canonical target 1,440.000초의 채택 근거를 결정한다.
- [x] 507 cues → 274 sentences → 64 shots 계보를 candidate plan의 source bundle/script/canonical manifest 참조로 연결한다. 단, source 1,439.800초 대 target 1,440.000초 채택은 미결정이다.
- [x] 각 shot을 sentence span과 claim ID에 연결하고, shot-local cut timing을 canonical timeline에서 계산한다.
- [x] 각 A/B plate와 cut에 `visual_beat`, focal/evidence role 및 motion metadata를 기록한다.
- [x] subcut마다 sentence/cue/claim/beat lineage를 저장하고, 누락 시 렌더 전 fail-closed한다.

## Task 2 — A/B가 아닌 실제 보완형 plate 재설계

**대상:** 128개 Flow plate prompt와 `images_2d_master/`

- [ ] A=상황·전경·공간, B=증거·인물 행동·유물 디테일처럼 의미가 분리된 prompt를 작성한다. V3 현재 후보는 기존 master plate 파생본이므로 이 항목은 아직 완료로 보지 않는다.
- [ ] 단순 `angle A`/`angle B` 차이를 금지하고, 두 prompt의 semantic anchor가 실제로 달라지는지 검사한다.
- [x] provider watermark, generated text, logo, persistent band를 candidate plate audit로 탐지한다.
- [ ] 문제가 있는 plate는 라이선스가 허용하는 clean export 또는 Flow 재생성으로 교체한다. 제거 권한이 없는 표식은 inpaint로 숨기지 않는다.
- [ ] 하단 18% safe area의 실제 luminance/edge occupancy를 검사하고, 자막이 들어갈 공간을 plate 단계에서 비워 둔다.

## Task 3 — Rank 2 렌더러를 beat-aware edit graph로 교체

**대상:** `subcut_montage_engine.py`, `cinematic_effect_planner.py`, `cinematic_editing_director.py`

- [ ] Rank 2 pipeline이 `CinematicEffectPlanner` 자체의 profile을 소비하도록 연결한다. 현재는 전역 modulo를 제거하고 shot-local profile을 도입한 중간 단계다.
- [x] `motion_profile`에 motion family, zoom/pan center, rotation, easing, visual beat, duration metadata를 기록한다.
- [ ] 컷마다 좌표를 새로 리셋하지 말고, 동일 shot 안에서는 이전 컷의 종료 상태와 다음 컷의 시작 상태를 연결한다.
- [ ] 실제 tilt/rotate/flip은 필요할 때만 구현하고, metadata에만 존재하는 효과 이름은 허용하지 않는다.
- [ ] 같은 axis/direction의 기계적 연속과 in/out 방향의 무근거 역전을 제한한다. 현재 367건인 방향 역전은 beat 근거가 없으면 제거한다.
- [x] 0.333초 전역 strobe burst를 제거하고, candidate는 shot-local cadence를 사용한다.

## Task 4 — 진짜 transition layer 도입

**대상:** montage renderer와 final assembly filtergraph

- [ ] 각 경계에 `hard_cut`, `match_cut`, `dissolve`, `whip_pan` 중 하나와 길이를 명시한다.
- [ ] hard cut은 시맨틱 충돌이 없고 피사체 축이 안정된 경계에만 사용한다.
- [ ] dissolve/xfade는 모든 컷에 일괄 적용하지 말고 장면 전환·시간 점프·회상에만 제한한다.
- [ ] match/whip은 이전·다음 프레임의 방향/색/초점이 일치할 때만 사용한다.
- [ ] 실제 encoded output에서 각 transition의 시작·끝 프레임을 독립 검출하고, 선언만 있고 사용되지 않은 transition은 FAIL 처리한다. candidate는 53개 non-zero transition boundary와 pixel interpolation test를 통과했지만 full boundary QA는 남아 있다.

## Task 5 — 자막 가독성과 clean visual layer 정상화

**대상:** `build_rank2_clean_subtitles.py`, ASS, plate/raw montage

- [x] 원본 대비 작은 52pt 고정값을 폐기하고 candidate를 72pt `BorderStyle=3` 반투명 박스로 재보정했다. 실제 원본 glyph parity는 human preview에서 추가 승인한다.
- [ ] 한 줄 우선, 불가피한 경우만 의미 단위 2줄로 분할하며, 텍스트 폭에 따른 adaptive font size를 적용한다.
- [ ] 자막 box는 per-event bounded box로 유지하고, 영상 전체에 깔린 baked-in bottom band는 제거/재생성한다.
- [ ] 숫자·지명·핵심어 yellow tag는 보존하되, 글자 대비와 safe area를 프레임으로 검증한다.
- [ ] 0초·overlap·multiline뿐 아니라 실제 burn-in glyph bbox, 대비, 하단 band 면적, provider mark 존재를 Gate에 추가한다.

## Task 6 — 대본-이미지-컷 매칭 검증

**대상:** 새 edit graph와 독립 QA script

- [ ] 각 sentence/cue의 핵심 명사·동작·장소·시점을 visual anchor와 비교한다.
- [ ] 같은 시각의 source frame과 candidate frame을 샘플링해 scene correspondence를 검토한다.
- [ ] OCR/CLIP 또는 승인된 시맨틱 검사로 생성 이미지가 narration과 무관한 장면으로 drift하지 않는지 검사한다.
- [ ] 매칭 불명확한 plate는 자동 승격하지 않고 reviewer queue로 보낸다.
- [ ] 60초, 120초, 300초, 600초, 900초, 1200초 구간의 human review contact sheet를 보존한다.

## Task 7 — 독립 시각 Gate와 재렌더링

**대상:** `exact_release_verifier.py`, Rank 2 physical release tests, 새 candidate MP4

- [ ] 계획 경계와 encoded frame boundary의 1:1 일치를 검사한다. 현재 전체 decode는 PASS이나 hard boundary 품질의 독립 검수는 남아 있다.
- [ ] 각 비-strobe 컷의 실제 내부 motion, motion axis, direction, focal anchor를 측정한다.
- [ ] 경계 diff가 내부 motion을 압도하는 경우 transition 또는 motion profile을 재검토한다.
- [ ] A/B 반복 0뿐 아니라 semantic novelty, 동일 구도 반복, 무근거 방향 역전도 검사한다.
- [x] subtitle glyph/box와 provider/band 기본 검사를 통과한 V3 candidate를 manifest에 기록했다. OCR/시청용 glyph parity는 추가 승인 대상이다.
- [x] 전체 decode, frame count, AV parity, SHA chain을 V3 candidate에서 다시 실행했다.
- [ ] 모든 Gate PASS와 시청용 preview 승인 전에는 `output` mirror를 교체하지 않는다.

## 완료 기준

- [ ] source/canonical timing SSOT가 문서로 고정됨
- [ ] 100% cut lineage: sentence/cue/claim → shot → plate → subcut
- [ ] 실제 transition layer가 encoded output에 반영됨
- [ ] shot-local beat motion이 global modulo cycle을 대체함 (candidate 구현 완료; `CinematicEffectPlanner` 직접 연동과 방향 근거 QA는 잔여)
- [ ] subtitle glyph 크기·box·contrast가 승인 기준을 충족함
- [x] candidate derived plate layer에서 provider mark, generated text, baked-in band 0건 audit PASS (provider clean export provenance는 별도 보류)
- [ ] A/B loop, semantic repeat, 무근거 방향 reversal 0건
- [ ] 물리·시각 독립 Gate 및 preview review PASS
- [ ] 새 candidate SHA-256을 PROGRESS/manifest에 기록한 뒤에만 원자 승격
