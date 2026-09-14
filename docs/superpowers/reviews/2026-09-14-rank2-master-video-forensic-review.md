# Rank 2 Exact Master 비디오 포렌식 분석 보고서

## 판정

대상 파일 `D:\module\output\NOLLAM-HUMAN-LIBRARY-RANK2-EXACT-MASTER.mp4`는 컨테이너·프레임·오디오 디코드 무결성은 통과한다. 그러나 현재 `PROMOTED_MASTER` 표시는 콘텐츠/시각 품질 기준까지 통과했다는 뜻으로 사용할 수 없다. 원본과의 시각적 1:1 대응, 자막 박스 계약, provider overlay 제거/허용 정책, 무음 의미 분류가 미해결이므로 **조건부 기술 산출물 / 릴리스 승인 보류**로 판정한다.

## 검증 대상과 재현 증적

| 항목 | 실측값 |
|---|---|
| 결과 영상 | `D:\module\output\NOLLAM-HUMAN-LIBRARY-RANK2-EXACT-MASTER.mp4` |
| 파일 크기 / SHA-256 | 1,074,273,648 bytes / `0C14AEB0ECCB64137C8DF37E0093D2BC066E2DAC2DFF5F40845EEE7D2868060B` |
| 비디오 | H.264 High, 1920×1080, 30/1 CFR, 43,200 frames, 1,440.000s |
| 오디오 | AAC-LC, 48,000Hz, stereo, 1,440.000s, 약 275kbps |
| 원본 비교 파일 | `D:\module\scratch\human_library_top3\original_rank2.mp4`, 1,439.800s, 1920×1080, 30fps |
| Flow plate 실물 | 128개, 모두 2304×1296, SHA-256 unique 128/128 |
| 전체 디코드 | `ffmpeg -err_detect explode` 비디오/오디오 모두 Exit Code 0 |
| 출력 미러 parity | production master와 output mirror SHA-256 일치 |

## 핵심 문제

### P0 — 시각적 1:1 복제 실패

원본 0.5초 프레임은 클레오파트라와 피라미드, 우측 상단 채널 엠블럼, 하단 중앙의 작은 둥근 자막 박스로 시작한다. 결과 영상 0.5초 프레임은 나일강 항공 지도이며, 우측 상단 채널 엠블럼은 없고, 하단 전체 폭에 어두운 고정 밴드와 우측 하단의 4점형 Flow provider 표식이 보인다. 채널 로고/HUD를 제외하는 현재 clean-scope는 의도된 범위지만, 장면·구도·자막 박스·provider 표식은 별개의 exactness 문제다.

하단 밴드와 provider 표식은 최종 자막 합성 단계가 아니라 `images_2d_master/SHOT_001_A.jpg` 및 raw montage 프레임에도 존재한다. 따라서 최종 MP4의 ASS만 고쳐서는 제거되지 않는다. Flow 무표식 합법 export가 없으면 해당 자산은 exact release에 승격할 수 없고, 사용 조건을 확인하지 않은 watermark 제거/인페인팅은 수행하지 않는다.

### P0 — 자막 스타일 계약과 실제 산출물 불일치

`rank2_exact_master_subtitles.ass`의 `DocuNarrator_Exact` 스타일은 다음과 같다.

```text
BorderStyle=1, Outline=3.5, Shadow=2.0, Alignment=2, MarginV=55
```

계획/문서가 요구한 반투명 둥근 박스는 `BorderStyle=3`이어야 한다. 현재 영상의 검은 하단 밴드는 자막별 둥근 박스가 아니라 plate/raw video에 baked-in된 영역으로 확인된다. 이벤트 수는 현재 ASS와 release manifest 기준 **542개**이며, 과거 진행 문서의 **958개** 표기는 이 산출물과 불일치한다. 현재 ASS 자체는 542 events, zero-start 0, overlap 0, multiline 0, yellow keyword tags 86건이다.

### P1 — 타임라인 SSOT 결정 미완료

원본 파일 probe는 1,439.800초, 결과 영상은 1,440.000초로 **0.200초 차이**가 있다. Rank 2 canonical manifest는 1,440.000초를 목표로 하므로 어느 값을 SSOT로 채택할지 먼저 결정해야 한다. 이 결정을 하지 않은 상태에서 `parity_delta=0.0`만으로 “원본 exact”를 주장하면 목표와 원본의 차이를 숨기게 된다.

### P1 — 오디오의 측정 가능한 무음 구간

`silencedetect=noise=-50dB:d=0.50` 기준으로 0.5초 이상 무음 구간이 **42개, 누적 27.046초** 검출됐다. 가장 긴 구간은 약 0.793초다. 이는 자연스러운 문장 간 호흡일 수도 있으므로 전부 dead air로 단정하면 안 되지만, 현재 release manifest의 “dead-air 0” 또는 동일 취지의 무조건 PASS를 독립 검증한 것은 아니다. canonical cue/문장 경계와 대조해 허용된 pause와 실제 무음을 분리해야 한다.

오디오 레벨은 integrated loudness 약 **-14.1 LUFS**, mean volume **-17.2 dB**, max volume **-1.3 dB**로 측정됐다. 음성만 포함하는 clean-scope에서는 loudness 자체보다 발화 보존, pause 분류, AV parity가 우선이다.

### P1 — 컷 수 Gate가 실제 encoded behavior를 검증하지 않음

계획은 837 cuts를 선언하지만, 0.30 scene threshold의 encoded-frame scan에서는 1,670개의 scene-like transition이 검출됐다. 이 수치는 Ken Burns 내부 변화까지 포함하므로 실제 컷 수와 동일하지 않다. 반대로 1초 샘플에서는 1초 차이 평균 변화량 최솟값이 15.44로, 0.08 threshold의 exactish repeat는 0건이었다. 즉 “정지 영상 반복 0”은 확인되지만 “정확히 837개 컷”은 아직 검증되지 않았다. plan boundary와 encoded frame boundary를 직접 대조하는 별도 검사가 필요하다.

### P0/P1 — A/B 플레이트 토글 루프가 몽타주 다양성으로 오인됨

`subcut_montage_plan.json`의 실제 `plate_id` 순서를 직접 분석한 결과, 837개 컷 중 **773건**이 같은 `parent_shot_id` 내부의 인접 A/B 플레이트 전환이었다. 더 중요한 것은 `plate[i] == plate[i-2]`인 2-back 반복이 **709건**으로, `SHOT_003_A → SHOT_003_B → SHOT_003_A`, `SHOT_005_A → SHOT_005_B → SHOT_005_A`처럼 사용자가 지적한 **A → B → A → B** 패턴이 계획 데이터에 직접 인코딩되어 있다는 점이다. 이는 단순히 비디오 프레임이 픽셀 단위로 반복된다는 뜻은 아니다. Ken Burns 모션 때문에 매 반복의 픽셀은 달라질 수 있지만, 시청자가 인지하는 장면·구도·의미는 같은 두 플레이트 사이에서 왕복한다.

따라서 기존의 “1초 exactish repeat 0건”만으로는 이 결함을 통과시킬 수 없다. A/B를 상호 보완적인 역할(예: A=상황/전경, B=증거/디테일)로 배치하고, 즉시 역전하는 `A-B-A`/`B-A-B`는 명시적인 편집 비트가 아닌 한 거부하는 별도 시맨틱 반복 Gate가 필요하다. 현 상태는 컷 수가 많아 보이지만 실제 정보 진행이 정체되는 **perceptual stutter/semantic stagnation**으로 분류하며, clean candidate 재렌더링 전 해결해야 한다.

### P1 — 생성 이미지 내부 텍스트 및 시맨틱 drift

대표 프레임에서 `LOWER EGYPT` 등 생성된 영문 지도 텍스트와 의미가 불명확한 표기가 관찰됐다. 프롬프트의 `no text` 문장만으로 시각 QA PASS를 줄 수 없다. 128 plate 각각에 OCR/텍스트 흔적, 하단 안전영역, 역사적 장면·인물·지명 정합 검사를 추가해야 한다.

## 통과한 범위와 통과하지 않은 범위

통과한 것은 물리 컨테이너와 일부 intermediate integrity다. 30fps CFR, 43,200 frames, 48kHz stereo, output/prod hash parity, 전체 decode, 128개 plate의 해상도·파일 고유성은 확인됐다. 반면 원본 장면 대응, provider overlay, subtitle `BorderStyle=3`, 1,439.800/1,440.000 SSOT 결정, 42개 pause의 의미 분류, 837 encoded cut boundary, 생성 텍스트 제거는 미통과다.

## 결론

현재 파일은 재생 가능한 기술 마스터이지만 exact release로 승인할 수 없다. 다음 작업은 원본 장면을 무작정 다시 생성하는 것이 아니라, (1) timeline SSOT를 먼저 잠그고, (2) provider overlay가 없는 합법 plate 공급 여부를 결정하고, (3) 자막/하단 밴드를 분리된 합성 레이어로 재구축하며, (4) encoded video·오디오·자막을 독립 Gate로 재검증하는 순서로 진행해야 한다.
