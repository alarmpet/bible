# Rank 2 V3 시맨틱 매칭·안정 페이싱 재설계

## 목적

현재 Rank 2 후보는 대본 ID 계보는 완성됐지만 이미지 내용의 실제 의미 대응은 검증되지 않았고, 짧은 컷과 강한 카메라 이동이 동시에 발생한다. V3는 `대본 의미 → visual anchor → plate role → visible cut/reframe → motion intensity`를 명시적으로 연결하고, 빠른 오프닝과 안정적인 본문 호흡을 분리한다. BGM, 채널 로고, HUD는 범위에서 제외한다.

## 설계 결정

### 1. 시맨틱 매칭 계약

각 shot은 `place`, `subject`, `action`, `era`, `evidence_role`, `must_show`, `must_not_show` 앵커를 가진다. 각 plate는 이 앵커를 참조하고, 실제 파일 존재·해상도·provider artifact 검사와 함께 매칭 상태를 `PASS`, `REVIEW_REQUIRED`, `FAIL`로 기록한다. lineage ID가 존재해도 앵커가 없거나 장면 대응이 불명확하면 자동 승격하지 않는다.

현재 자산에 대하여 OCR/파일 검사는 자동화하고, 실제 장면 의미가 불명확한 경우 reviewer queue로 보낸다. crop/inpaint로 의미 불일치를 숨기지 않으며, 교체가 필요하면 Google Flow CDP 재생성 후 새 prompt/file hash를 매니페스트에 바인딩한다.

### 2. 안정 페이싱

V3의 목표는 420~480개의 보이는 hard cut이다. 나머지 visual beat는 동일 clip 내부의 reframe으로 표현한다. 첫 10초는 최대 4 visible cuts, 첫 30초는 최대 10 visible cuts로 제한한다. 0~5초는 2~3컷의 훅으로 유지하되 컷마다 강한 transform 하나만 허용한다. 5~30초는 2.5~4.5초, 본문 visible cut은 3~5초를 기본으로 하며 긴 설명은 동일 화면 내부 reframe/hold로 처리한다. 455 visible cuts와 1,440초를 동시에 유지할 때 4~7초 고정은 수학적으로 불가능하므로 사용하지 않는다.

각 cut에는 줌·팬·회전 중 하나의 dominant motion만 허용한다. zoom delta는 기본 0.03~0.08, pan travel은 0.04~0.10 normalized 범위로 제한하고, 회전은 기본 0.2도 이하로 한다. 무근거 방향 반전과 기본 horizontal flip은 금지한다. dissolve/match/whip은 의미 있는 장면 경계에만 제한한다.

### 3. 검증

계획 검증은 semantic anchor 완전성, visible cut budget, multi-transform 금지, 무근거 방향 반전, cue/shot 시간 연속성을 검사한다. 렌더 후에는 encoded frame에서 visible boundary와 내부 motion을 재측정한다. 60/120/300/600/900/1200초 preview contact sheet를 보존하고, semantic 대응이 불명확하면 release 상태를 `CANDIDATE`로 유지한다.

## 산출물

- V3 plan: `rank2_candidate_v3_subcut_montage_plan.json`
- V3 clean plates: `images_2d_candidate_v3/`
- V3 subtitles: `rank2_candidate_v3_subtitles.ass`
- V3 raw montage/final MP4 및 독립 release manifest

기존 master와 V2 candidate는 변경하지 않는다.
