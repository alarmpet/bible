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

## Task 1 — SSOT와 데이터 계보 재결합

**대상:** `master_script_clean.json`, canonical cue manifest, `shot_composition_plan.json`, `master_plates_composition_plan.json`, `subcut_montage_plan.json`

- [ ] source duration 1,439.800초와 canonical target 1,440.000초의 채택 근거를 결정한다.
- [ ] 507 cues → 274 sentences → 64 shots를 명시적으로 매핑한다.
- [ ] 각 shot을 sentence span과 claim ID에 연결하고, shot duration이 해당 음성 구간에서 계산됐는지 검증한다.
- [ ] 각 A/B plate에 `visual_beat`, semantic anchors, focal subject, place, era, action, evidence role을 기록한다.
- [ ] subcut마다 sentence/cue/claim/beat lineage를 저장한다. 누락된 lineage는 렌더 전에 중단한다.

## Task 2 — A/B가 아닌 실제 보완형 plate 재설계

**대상:** 128개 Flow plate prompt와 `images_2d_master/`

- [ ] A=상황·전경·공간, B=증거·인물 행동·유물 디테일처럼 의미가 분리된 prompt를 작성한다.
- [ ] 단순 `angle A`/`angle B` 차이를 금지하고, 두 prompt의 semantic anchor가 실제로 달라지는지 검사한다.
- [ ] provider watermark, generated text, logo, persistent band를 OCR/시각 검사로 탐지한다.
- [ ] 문제가 있는 plate는 라이선스가 허용하는 clean export 또는 Flow 재생성으로 교체한다. 제거 권한이 없는 표식은 inpaint로 숨기지 않는다.
- [ ] 하단 18% safe area의 실제 luminance/edge occupancy를 검사하고, 자막이 들어갈 공간을 plate 단계에서 비워 둔다.

## Task 3 — Rank 2 렌더러를 beat-aware edit graph로 교체

**대상:** `subcut_montage_engine.py`, `cinematic_effect_planner.py`, `cinematic_editing_director.py`

- [ ] Rank 2 pipeline이 현재의 전역 modulo profile을 직접 사용하지 않고 `CinematicEffectPlanner`의 beat-aware profile을 소비하도록 연결한다.
- [ ] `motion_profile`을 `family`, `axis`, `focal_anchor`, `zoom_start/end`, `pan_start/end`, `tilt_start/end`, `easing`, `duration`으로 확장한다.
- [ ] 컷마다 좌표를 새로 리셋하지 말고, 동일 shot 안에서는 이전 컷의 종료 상태와 다음 컷의 시작 상태를 연결한다.
- [ ] 실제 tilt/rotate/flip은 필요할 때만 구현하고, metadata에만 존재하는 효과 이름은 허용하지 않는다.
- [ ] 같은 axis/direction의 기계적 연속과 in/out 방향의 무근거 역전을 제한한다. 현재 367건인 방향 역전은 beat 근거가 없으면 제거한다.
- [ ] 0.333초 strobe는 전체 템포 규칙이 아니라 script beat가 있는 한정 구간으로 격리한다.

## Task 4 — 진짜 transition layer 도입

**대상:** montage renderer와 final assembly filtergraph

- [ ] 각 경계에 `hard_cut`, `match_cut`, `dissolve`, `whip_pan` 중 하나와 길이를 명시한다.
- [ ] hard cut은 시맨틱 충돌이 없고 피사체 축이 안정된 경계에만 사용한다.
- [ ] dissolve/xfade는 모든 컷에 일괄 적용하지 말고 장면 전환·시간 점프·회상에만 제한한다.
- [ ] match/whip은 이전·다음 프레임의 방향/색/초점이 일치할 때만 사용한다.
- [ ] 실제 encoded output에서 각 transition의 시작·끝 프레임을 독립 검출하고, 선언만 있고 사용되지 않은 transition은 FAIL 처리한다.

## Task 5 — 자막 가독성과 clean visual layer 정상화

**대상:** `build_rank2_clean_subtitles.py`, ASS, plate/raw montage

- [ ] 원본의 실제 glyph 높이·stroke·box 폭을 기준으로 52pt 고정값을 재보정한다. 현재 샘플 결과 glyph 약 36px, 원본 약 52px 차이를 해소한다.
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

- [ ] 계획 경계와 encoded frame boundary의 1:1 일치를 검사한다.
- [ ] 각 비-strobe 컷의 실제 내부 motion, motion axis, direction, focal anchor를 측정한다.
- [ ] 경계 diff가 내부 motion을 압도하는 경우 transition 또는 motion profile을 재검토한다.
- [ ] A/B 반복 0뿐 아니라 semantic novelty, 동일 구도 반복, 무근거 방향 역전도 검사한다.
- [ ] subtitle glyph/box와 provider/band/OCR 검사를 통과한 candidate만 manifest에 기록한다.
- [ ] 전체 decode, frame count, AV parity, SHA chain은 마지막에 다시 실행한다.
- [ ] 모든 Gate PASS와 시청용 preview 승인 전에는 `output` mirror를 교체하지 않는다.

## 완료 기준

- [ ] source/canonical timing SSOT가 문서로 고정됨
- [ ] 100% cut lineage: sentence/cue/claim → shot → plate → subcut
- [ ] 실제 transition layer가 encoded output에 반영됨
- [ ] beat-aware motion이 global modulo cycle을 대체함
- [ ] subtitle glyph 크기·box·contrast가 승인 기준을 충족함
- [ ] provider mark, generated text, baked-in band 0건
- [ ] A/B loop, semantic repeat, 무근거 방향 reversal 0건
- [ ] 물리·시각 독립 Gate 및 preview review PASS
- [ ] 새 candidate SHA-256을 PROGRESS/manifest에 기록한 뒤에만 원자 승격
