# Rank 2 V3 후보 영상 재설계·렌더 검수 보고서

## 판정

V3 후보는 기존 A/B 왕복과 초단기 컷 과밀 문제를 구조적으로 완화한 물리 검증본이다. 기존 output을 덮어쓰지 않고 별도 후보로 보존한다. 물리 Gate 0~5는 PASS이지만, 이미지 픽셀 의미 매칭과 시청용 최종 승인은 아직 보류한다.

이번 범위에서는 BGM, 채널 로고, HUD를 포함하지 않았다.

## 산출물

- 영상: `D:\module\output\NOLLAM-HUMAN-LIBRARY-RANK2-EXACT-MASTER-V3-CANDIDATE.mp4`
- 크기: 710,963,703 bytes
- SHA-256: `532097B7FD6BF89B824BD998E3E0C82445AFBD1F8FD5A0FE40665105E91C8162`
- 매니페스트: `D:\module\bible\human_archive\runs\human_library_replica\rank2_forgotten_civilization\metadata\rank2_candidate_v3_release_manifest.json`
- release ID: `HL-RANK2-EXACT-CANDIDATE-V3`
- status: `CANDIDATE`
- 계획: 455 visible cuts, 43,200 frames, 30fps CFR, 1,440.000s

## 렌더·컨테이너 검증

- Video: H.264 High, 1920×1080, 30/1, 43,200 frames, 1,440.000s
- Audio: AAC-LC, 48kHz, 2ch, 1,440.000s
- AV parity delta: 0.0000s
- 전체 decode: video/audio 모두 PASS
- SHA-256 체인: PASS
- 코드 검증: 관련 `py_compile` PASS, 대상 테스트 25 passed, 전체 테스트 613 passed/1 warning/Exit Code 0
- 자막: 542 events, zero-start 0, overlap 0, multiline 0
- plate: 128/128 unique, provider mark 및 bottom band 탐지 0

## V3 페이싱 검증

- visible cut: 455개 — 목표 420~480 범위
- 첫 10초: 3개 — 상한 4
- 첫 30초: 9개 — 상한 10
- visible cut duration: 2.5~4.5초, median 3.1667초
- cut당 다중 변환: 0건
- transition declaration: hard cut 450개, 6-frame dissolve 5개
- A/B 2-back 반복: 0건
- 역할 역전: 0건

기존의 모든 컷을 1.6초 안팎으로 강제하지 않고, 본문은 3~5초 hold를 기본으로 했다. 긴 설명은 컷 수를 늘리는 대신 컷 내부의 완만한 crop/reframe으로 처리하는 구조다.

## 실제 encoded-frame 모션 측정

최종 MP4를 43,200프레임 직접 디코드하여 계획값과 분리 측정했다.

- cut boundary diff: median 28.152, p95 74.060, max 96.756
- cut internal diff: median 0.708, p95 1.830, max 2.340
- internal diff < 1.0 비율: 75.30%
- direction reversal: 132건

V2의 경계 median 35.17, 내부 median 1.79, direction reversal 190건보다 개선되었다. 그러나 hard cut 비중이 높아 경계 차분이 내부 모션보다 큰 현상은 남아 있다. 따라서 “전환 효과가 완전히 해결됐다”고 판정하지 않고, 다음 검수에서 shot boundary별 dissolve/match-cut 필요성을 선별한다.

## 대본-이미지 의미 매칭 판정

각 cut에는 `sentence_ids`, `cue_ids`, `claim_ids`, `semantic_anchors(place/subject/action/era/evidence_role)`가 연결되어 있고 455/455 레코드가 누락 없이 감사됐다. 이것은 계보와 메타데이터 정렬을 증명한다.

하지만 현재 V3 plate는 기존 master plate에서 파생된 clean layer이며, 자동 검증이 이미지의 실제 픽셀 내용이 대본과 일치하는지까지 증명하지는 않는다. 매니페스트도 이 한계를 명시하여 `pixel_semantic_verification_required=true`, `METADATA_ALIGNED_REVIEW_REQUIRED` 455건으로 고정했다.

따라서 동일 시각 source frame과 candidate frame의 contact sheet, OCR/CLIP 또는 사람 검수 결과가 추가되기 전에는 정식 `PROMOTED_MASTER`로 승격하지 않는다. 불일치 plate는 inpaint로 숨기지 않고 권리와 provenance가 확인된 clean export 또는 Google Flow 재생성 대상으로 보낸다.

## 결론 및 다음 게이트

V3 후보는 재생성 가능한 새 페이싱·모션·계보 계약을 구현했고, 기존 output/V2를 보존한 상태로 물리 렌더까지 완료했다. 현재 결론은 `CANDIDATE / PHYSICAL PASS / SEMANTIC PIXEL REVIEW REQUIRED`다.

정식 승격 전 잔여 작업은 다음 세 가지다.

1. source 1,439.800초와 canonical target 1,440.000초의 SSOT 선택 근거를 문서화한다.
2. 60/120/300/600/900/1200초의 source↔candidate 동시각 contact sheet를 검수하고 의미 불일치 plate를 교체한다.
3. hard boundary 450건을 shot boundary와 same-shot cut으로 분리해 필요한 경계만 실제 dissolve/match 처리하고 encoded boundary QA를 통과시킨다.
