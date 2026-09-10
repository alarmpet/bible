# 폼페이 EP01 마지막 영상 품질 감사 및 재구축 설계

날짜: 2026-08-21

상태: 배포 보류(BLOCK) / 재구축 설계 승인 대기

감사 대상: `human_archive/runs/ep01_pompeii_18hours/final_pompeii_ep01.mp4`

SHA-256: `DA91A7F62549B24434D9EDE94E55EEEE9E3287D871815E3618A7DDD649455BC9`

## 1. 결론

현재 최종본은 업로드하거나 납품하면 안 된다. 파일 자체는 끝까지 디코드되고 68개 구간의 병합 순서도 정상이나, 작품의 핵심인 **문장·내레이션과 실제 화면의 의미 정합성**이 전편에서 무너져 있다.

수동 전수 이미지 감사에서는 68개 중 의도한 샷을 정확히 충족한 이미지가 0개였고, 부분 관련 5개, 높은 불일치 18개, 치명적 불일치 45개로 판정됐다. 별도의 완성본 30초 표본 검사에서도 23개 지점 중 최소 17개가 현재 내레이션과 직접 충돌했다. 이 결과는 단순한 취향 문제가 아니라 잘못된 이미지가 다음 `shot_id`로 저장되는 자동화 경쟁 조건, 실제 픽셀을 보지 않는 검증기, 하드코딩된 성공 로그가 합쳐진 구조적 결함이다.

또한 대본의 중심 명제인 “폼페이 시민 대다수가 약 18시간 남아 있었고 정상화 편향과 재산 집착 때문에 탈출하지 못했다”는 사료와 연구로 입증되지 않는다. 많은 사람, 아마 대다수가 초기 단계에 탈출했을 가능성이 더 강하다. 따라서 기존 JPG를 파일명만 바꾸거나 일부 샷만 교체하는 방식은 채택하지 않는다. 제목·훅·사실 장부·대본·이미지 전체를 새 빌드 경로에서 다시 만들어야 한다.

## 2. 감사 범위와 방법

이번 감사에서는 원본 영상과 제작 파일을 수정하지 않았다. 다음을 서로 대조했다.

- 최종 MP4의 컨테이너·코덱·프레임·색·SAR·오디오 음량·무음·정지·검은 프레임
- 20초/30초 간격 표본 프레임, 장면 전환 프레임, 68개 원본 JPG와 68개 모션 MP4
- `full_script_68shots.json`, `scene_audio_manifest.json`, `subtitles.ass`, concat 목록
- 이미지 생성·재생성·TTS·자막·모션·렌더·검증 스크립트
- `narration_policy.yaml`, `documentary_contract.yaml`, 작업 로그의 성공 주장
- 폼페이 분출 날짜·지속시간·탈출자·온도·희생자·발굴사에 관한 공식기관·동료평가 자료

점검용 contact sheet와 분석 산출물은 `.audit_root`, `.audit_semantic`, `.audit_av`에 분리했다. 이 파일들은 진단 근거이며 재구축 입력으로 사용하지 않는다.

근거 파일 경로·hash·대표 타임스탬프는 [`2026-08-21-pompeii-video-audit-evidence.json`](2026-08-21-pompeii-video-audit-evidence.json)에 고정했다. 단, 이번 수동 전수 감사의 0/5/18/45 분류와 23개 표본 중 최소 17개 불일치 tally는 당시 reviewer가 row 단위 JSON을 남기지 않아 독립적으로 자동 재집계할 수 없다. 따라서 이 수치는 참고용으로 보존하고 v2의 공식 합격 지표로 사용하지 않는다. 재구축 판단은 별도로 확인 가능한 연쇄 오매핑, 누락·중복, 서비스 표식, 입력 계보 부재, 사실 계약 변경만으로도 유지된다. v2에서는 반드시 image hash와 reviewer를 포함한 per-shot 구조화 보고서를 만든다.

## 3. 실제 생성 과정

### 3.1 관찰된 타임라인

| 시각(2026-08-20) | 단계 | 확인 결과 |
|---|---|---|
| 02:09–02:28 | `ch1_11`–`ch4_15` 이미지 저장 | Flow 화면의 결과를 `shot_id.jpg`로 다운로드했으나 결과 카드와 샷의 불변 연결 정보가 없음 |
| 02:45–02:49 | `ch1_01`–`ch1_10` 재생성 | 고정 18초 대기와 최신 URL fallback으로 이전 결과 저장 가능 |
| 04:06 | `full_script_68shots.json` 수정 | 이미지 생성 후 수정됐으므로 현재 JSON이 당시 실제 입력이었다는 증거가 없음 |
| 04:07–04:10 | 68개 TTS WAV 및 오디오 매니페스트 생성 | JSON의 ID·순서·문장과 WAV 길이는 현재 매니페스트와 일치 |
| 04:11 | 139개 ASS 자막 이벤트 생성 | 샷 경계는 연속이나 단어 타이밍은 발화 측정이 아니라 글자 수 비례 |
| 04:11–04:14 | 68개 모션 MP4 생성 | 실제 생성형 비디오가 아니라 잘못 저장된 JPG에 2.5D pan/zoom/tilt 적용 |
| 04:14–04:17 | 세그먼트 병합·자막 번인·최종 렌더 | concat 순서는 정상, 실제 의미 검증 없이 성공 로그 출력 |

### 3.2 실제 데이터 흐름과 결함 전파

```text
대본 생성기
  -> 편집 가능한 JSON
  -> Flow 프롬프트 제출
  -> 고정 시간 대기 + DOM의 최신/미확인 URL 선택
  -> 잘못된 결과를 다음 shot_id.jpg로 저장
  -> 실제 픽셀을 보지 않는 "싱크" 검사
  -> JPG에 반복 2.5D 모션 적용
  -> 글자 수 비례 카라오케 자막
  -> exact SHA 중복 검사만 실행
  -> "68/68 PASS" 하드코딩 출력
  -> 최종 MP4
```

오디오와 자막의 샷 순서는 현재 JSON과 비교적 잘 연결됐지만, 이미지가 `shot_id`에 잘못 붙는 순간 이후 단계는 그 오류를 충실히 확대했다. 렌더러가 틀린 파일명을 신뢰했기 때문에 화면은 틀리고 자막·내레이션은 서로 맞는 상태가 됐다.

## 4. P0: 문장·이미지·영상 의미 불일치

### 4.1 전수 이미지 감사 요약(참고용 수동 tally)

| 판정 | 수량 | 의미 |
|---|---:|---|
| 정확 일치 | 0 | 인물·장소·시대·행동·결과가 현재 샷 의도를 모두 만족한 파일 없음 |
| 부분 관련 | 5 | 폼페이/화산이라는 넓은 주제만 관련되거나 핵심 행동이 다름 |
| 높은 불일치 | 18 | 다른 샷의 화면이거나 핵심 인물·행동·시점이 다름 |
| 치명적 불일치 | 45 | 서사 의미를 반대로 만들거나 현대물·복싱·황제 알현·엉뚱한 유물 등이 등장 |

현재 68개 JPG는 모두 재사용 불가로 본다. 의미 불일치 외에도 거의 전편의 오른쪽 아래에 동일한 생성 서비스 표식이 있고, 일부 파일에는 금지된 영어 라벨과 가짜 문자가 포함돼 있기 때문이다.

### 4.2 관찰된 오매핑 계열

| 현재 파일 범위 | 실제로 보이는 계열 | 판정 |
|---|---|---|
| `ch1_01` | 고대 아치 너머 현대 도시. 후반 현대적 질문 계열로 보임 | 첫 프레임부터 시대·문맥 치명적 충돌 |
| `ch1_02`–`ch1_10` | 대체로 `ch1_01`–`ch1_09` 화면이 한 샷씩 늦게 저장됨 | 고정 대기보다 생성이 늦었을 때 생기는 전형적 1-shot lag |
| `ch1_11`–`ch1_18` | 현재 내레이션과 다른 구형/선행 프롬프트 계열 | 현 JSON과 생성 당시 입력의 계보 불명 |
| `ch2_01`–`ch2_08` | `ch1_11`–`ch1_18` 계열 | 장 전체가 이전 장면 묶음으로 밀림 |
| `ch2_09`–`ch2_17` | `ch2_01`–`ch2_09` 계열 | 약 8샷 지연 |
| `ch3_01`–`ch3_08` | `ch2_09`, `ch2_11`–`ch2_17` 계열 | `ch2_10` 화면은 누락 |
| `ch3_09`–`ch3_18` | `ch3_01`–`ch3_09` 계열, 불타는 지하실 중복 | 누락·중복 동시 발생 |
| `ch4_01`–`ch4_07` | `ch3_10`, `ch3_13`–`ch3_18` 계열 | `ch3_11`·`ch3_12` 화면 누락 |
| `ch4_08` | 직전 청동 두상과 지각적으로 매우 유사 | byte hash는 달라도 의미 중복 |
| `ch4_09`–`ch4_15` | `ch4_01`–`ch4_04`, 중복 `ch4_04`, `ch4_06`–`ch4_07` 계열 | 결말 이미지들이 앞 샷으로 밀리고 의도한 도서관 결말 누락 |

파일명을 재배열해도 해결되지 않는다. 필요한 장면 자체가 빠졌고, 중복·서비스 표식·영문 라벨이 존재하며, 대본도 사실관계 수정 후 달라져야 한다.

### 4.3 완성본에서 확인된 대표 충돌

| 시각 | 내레이션/자막 의미 | 실제 화면 | 영향 |
|---:|---|---|---|
| 00:00 | 서기 79년 베수비오 분연주 | 고대 아치 너머 현대 대도시 | 작품의 시대와 신뢰를 첫 프레임에서 파괴 |
| 01:20.84 | 바닥에 떨어진 청동 와인잔 | 검투사/군인이 있는 거리 | 사물 중심 복선이 전혀 전달되지 않음 |
| 03:22.72 | 기와지붕 붕괴 | 웃으며 대화하는 귀족 | 재난 강도가 반대로 표현됨 |
| 05:01.40 | 어머니가 아이를 안음 | 번개를 동반한 화산 | 인간 장면과 자연재해 장면 불일치 |
| 09:11.92 | 인간의 거푸집·피오렐리 | 황제 알현 | 발굴사와 로마 정치 장면 혼동 |
| 10:15.64 | 오늘날 우리에게 던지는 질문 | 발굴 현장 | 철학적 전환의 영상 문법 실패 |
| `ch3_13` | 해변에서 쓰러진 대 플리니우스 | 불타는 지하실 문 | 사건·장소·인물 모두 불일치 |
| `ch3_15` | 포도밭·올리브밭의 회복 | 현대 복싱 실루엣 | 시대·행동·서사 모두 치명적 불일치 |
| `ch4_06` | 희생자가 손에 쥔 유물 | 영어 라벨이 붙은 발굴 단면도 | 프롬프트 금지 텍스트 노출과 의미 충돌 |
| `ch4_15` | 고대 도서관과 결말 | 열쇠를 쥔 석고 손 | 마지막 메시지가 앞 유물 샷으로 대체됨 |

## 5. P0: 자동화와 QA가 오류를 만든 이유

### 5.1 Flow 결과를 샷과 결속하지 않음

[`batch_generate_flow_images.py`](../../../human_archive/scripts/batch_generate_flow_images.py)는 실행 시 `seen_media_urls`를 빈 집합으로 시작한다. 기존 화면에 이미 있던 결과를 baseline으로 제외하지 않은 채 16초만 기다리고, DOM 전체에서 역순으로 처음 만나는 “아직 보지 않은 URL”을 저장한다. 새 결과가 없으면 최신 URL로 fallback한다.

[`regenerate_clean_synced_images.py`](../../../human_archive/scripts/regenerate_clean_synced_images.py)도 18초 뒤 새 URL이 없으면 `post_urls[-1]`을 현재 `shot_id`로 저장한다. 생성 완료 이벤트가 아니라 시간과 화면 순서에 의존하므로, 느린 응답 한 번이 이후 파일을 연쇄적으로 한 칸씩 밀어낸다.

필수였지만 없었던 연결 정보는 다음과 같다.

- `shot_id`, 배열 순서, canonical script hash
- 제출한 prompt의 정규화본과 SHA-256
- provider job/card ID와 완료 상태
- 결과 asset ID/URL, 모델, seed, 생성시각
- 다운로드된 원본 SHA-256과 픽셀 규격

### 5.2 “싱크 검증”이 실제 이미지를 열지 않음

[`verify_sync_matching.py`](../../../human_archive/scripts/verify_sync_matching.py)는 JPG 픽셀을 읽지 않는다. 같은 JSON 안의 내레이션과 영어 prompt 문자열을 비교하고, 기대 키워드 중 하나가 prompt에 있으면 통과한다. 한국어 핵심어는 판정에 쓰지 않으며 실패해도 CLI 종료코드 1을 보장하지 않는다. 이 검사를 현재 파일에 실행하면 실제 화면이 틀렸는데도 68/68 PASS가 나온다.

[`verify_zero_image_reuse.py`](../../../human_archive/scripts/verify_zero_image_reuse.py)는 파일 byte SHA-256만 비교한다. 재압축·크롭·색 변경·같은 구도의 다른 출력은 통과하면서 결과 메시지는 “Unique Semantic Image Mapping Verified”라고 과장한다.

[`render_docu_episode.py`](../../../human_archive/scripts/render_docu_episode.py)는 zero-reuse 검사만 호출하고 sync 검사는 호출하지 않는다. 그럼에도 마지막에 `Sync Verification: 68/68 PASS`를 고정 문자열로 출력한다. 현재 `human_archive/tests`에는 수집되는 테스트가 0개다.

### 5.3 입력과 생성기 원본이 갈라짐

현재 JSON은 이미지 저장 뒤에 수정됐다. `ch1_03`, `ch3_11`, duration tier 등은 현재 JSON과 [`generate_18min_deep_script.py`](../../../human_archive/scripts/generate_18min_deep_script.py)가 서로 다르다. 재실행하면 이미 고친 내용이 되돌아가며, 어떤 버전의 prompt가 어떤 JPG를 만들었는지 증명할 수 없다.

## 6. P0: 대본의 사실·서사 문제

### 6.1 중심 전제 판정

| 현재 주장 | 판정 | 재작성 원칙 |
|---|---|---|
| 79년 8월 24일 | 논쟁적 | “서기 79년 가을, 10월 24일설이 유력하지만 논쟁 중”으로 처리 |
| 최후의 18시간 | 부분 사실/과장 | 약 18–19시간의 분출 단계로 설명하고 전 구간을 안전한 탈출창으로 부르지 않음 |
| 인구 2만 명 | 확정 불가 | 추정 범위를 설명하고 단일 숫자를 사실처럼 사용하지 않음 |
| 대다수 시민 잔류 | 반증 우세 | 많은 사람, 아마 대다수가 초기 탈출했음을 중심 전제로 반영 |
| 도시 전체의 정상화 편향 | 과잉 일반화 | 미세눔에서의 플리니우스 기록과 폼페이 주민 전체를 분리 |
| 재산 집착이 탈출을 막음 | 인과 근거 없음 | 휴대품은 도피·새 삶의 자원일 수도 있음을 병기하고 피해자 비난 제거 |
| 폼페이 화쇄류 500°C | 지역 혼동/논쟁 | 헤르쿨라네움 수치를 전용하지 않고 폼페이 연구의 온도·사망기전 논쟁 병기 |
| 대 플리니우스 유독가스 질식 | 확정 불가 | 짙은 연기 속에서 쓰러졌고 정확한 사인은 불명이라고 서술 |
| 1748년 운하 공사 중 발견 | 오류 | 16세기 말 폰타나 운하와 1748년 부르봉 발굴을 분리 |
| 수많은 석고상 손의 열쇠·금화 | 근거 없음 | 발굴번호와 출처가 있는 개별 사례만 사용 |

공식 INGV 연표는 10월 24일과 약 25km 분연주를 제시하고, 이탈리아 문화부 자료는 분연주 약 18–19시간, 높이 약 26→32km, 사망 비율 약 15–20%를 설명한다. [INGV/Osservatorio Vesuviano](https://www.ov.ingv.it/index.php/storia-vesuvio/pompei), [이탈리아 문화부](https://cultura.gov.it/comunicato/24630)

폼페이의 온도와 사망기전은 단일 결론이 아니다. 2021년 연구는 약 115°C 흐름과 약 17분 노출·질식을 모델링했고, 2010년 연구는 250°C 이상의 열충격을 주장한다. 500°C는 헤르쿨라네움 연구 수치를 폼페이에 옮겨 쓴 것이다. [Scientific Reports 2021](https://www.nature.com/articles/s41598-021-84456-7), [PLOS ONE 2010](https://pmc.ncbi.nlm.nih.gov/articles/PMC2886100/), [헤르쿨라네움 온도 연구](https://pmc.ncbi.nlm.nih.gov/articles/PMC10079856/)

### 6.2 샷별 필수 재작성 범위

| 범위 | 삭제·교정할 핵심 | 대체 방향 |
|---|---|---|
| `ch1_01`–`ch1_04` | 8월 24일·즉시 30km·인구 2만 단정 | 날짜 논쟁, 단계별 26→32km, 인구 추정 범위 |
| `ch1_05`–`ch1_10` | 시민의 무관심·귀족 연회·다음 주 검투사 경기 등 미확인 행동 | 평상시 도시 생활과 실제 플리니우스 기록을 분리하고 재연 표기 |
| `ch1_11`–`ch1_18` | 도시 전체 정상화 편향, 금화·문서 때문에 망설였다는 단일 인과 | 정보·이동성·가족·건물 붕괴·낙하물 등 복합 위험과 다수 탈출 |
| `ch2_01`–`ch2_05` | 불안정한 정확 시각, 수억 톤이 지붕에 얹혔다는 단위 혼동, 베개 사례의 장소 일반화 | 범위형 시각, 폼페이 부석층, 스타비아이 사례임을 명시 |
| `ch2_06`–`ch2_10` | 수천 명 항구 집결·해저 지진·삼각파도·선단 표류 단정 | 플리니우스가 기록한 불빛·거친 바다·해안 후퇴·항로 변경만 사용 |
| `ch2_11`–`ch2_17` | 모든 탈출로 완전 차단, 신전 집단 피신, 새벽 5시 정적, “가장 잔혹” | 실제 발굴 사례, 최신 연표, 선정적 비교 제거 |
| `ch3_01`–`ch3_06` | 06시·18시간 산술 모순, 폼페이 500°C, 1초·신경 마비·자세 고정 단정 | 07:30/08:00 계열 연표, 속도·온도·사망기전의 연구 범위 |
| `ch3_07`–`ch3_09` | 어머니·연인·충견 등 확인되지 않은 관계와 감정 | DNA/발굴로 확인된 범위만 말하고 익명성 유지 |
| `ch3_10`–`ch3_18` | 전 인구 소멸, 완전 망각, 누구도 손대지 않은 타임캡슐 | 생존자·재산 회수·약탈·부분 재사용·체계적 발굴까지의 시간 |
| `ch4_01`–`ch4_05` | 1748 운하 오류, 피오렐리 영웅화, 2,000년·완벽 부활 과장 | 16세기 운하와 1748 발굴 분리, 1863 인체 캐스트의 정확한 맥락 |
| `ch4_06`–`ch4_14` | 열쇠·금화→집착→족쇄라는 증거 없는 교훈의 반복 | 개별 유물 사례, 휴대품의 다중 해석, 피해자 비난 없는 현대적 성찰 |
| `ch4_15` | 역사적 결론과 채널 브랜드 문구 혼합 | 사실·해석·에필로그를 화면과 문장으로 구분 |

### 6.3 권장 제목과 오프닝 방향

기존 제목의 “18시간”은 분출 단계의 근사치로만 유지할 수 있고 “대다수가 떠나지 않았다”는 전제는 버려야 한다.

권장 작업 제목:

> **폼페이 최후의 밤 — 많은 이들은 떠났고, 누가 남았나**

권장 12초 내 훅 초안:

> 폼페이에서 발견된 희생자는 도시 전체가 아니었습니다. 많은 사람은 빠져나갔습니다. 그렇다면 남겨진 이들은 누구였고, 마지막 밤의 위험은 어떻게 바뀌었을까요?

첫 40초 안에는 질문, 반전 사실, 조사 범위를 모두 제시한다. “왜 그들은 재산 때문에 남았나”처럼 결론을 질문 속에 미리 넣지 않는다.

## 7. P1: 완성본의 AV·편집 품질

| 항목 | 실측 | 문제와 기준 |
|---|---:|---|
| 길이 | 677.761초(11:17.761) | 15분 계약보다 222.239초 짧음. 목표를 유지하면 900초 미만은 차단 |
| 프레임 | 16,938프레임, 평균 24.991fps | 80ms 프레임 5개가 있어 엄격한 25 CFR 아님 |
| 화면 비율 | SAR 129:128, DAR 43:24 | 1920×1080은 SAR 1:1, DAR 16:9여야 함 |
| 색 | `yuvj420p`, full range, `bt470bg`, primaries/TRC 미지정 | HD 납품은 `yuv420p(tv, bt709)`로 일관 태깅 |
| 검은 프레임 | 0건 | 합격 |
| 정지 | 19구간, 총 45.32초(6.69%) | 2.5D 모션이 약 6.64초 뒤 끝나 1.68–3.36초 정지. 샷당 비의도 정지 0.5초 이하 |
| 강한 장면전환 | scene>0.25에서 full-res 70회, 320px 선축소 72회 | detector 조건에 따라 수가 달라 단일 절대값으로 쓰지 않음. 두 조건 모두 40ms 이중 컷 2곳과 약 0.96초 짧은 삽입을 별도 확인 |
| 컷 누적 지연 | 후반 최대 약 +0.40초 | 영상·오디오·자막 경계 차이를 1프레임(40ms) 이하로 제한 |
| 오디오 | -24.6 LUFS, LRA 3.2LU, -7.1dBTP | 웹 목표 -16±1 LUFS, true peak ≤ -1dBTP. 현재 약 8–10LU 작음 |
| 무음 | 69구간, 총 71.537초(10.56%) | 거의 모든 TTS 말미에 0.536–1.199초 디지털 무음. 의도한 호흡 0.2–0.5초만 허용 |
| 자막 | 139 cue, gap/overlap 0, 안전영역 통과 | 물리 동기는 양호하나 글자 수 비례 karaoke와 의미 없는 절단, 최대 8.29초 cue 개선 필요 |
| A/V 종단 | audio와 video 차 41ms | 컨테이너 종단은 양호. ASS가 마지막 audio보다 약 0.39초 먼저 끝나지만 선언된 outro 계약이 없어 의도 여부는 판정할 수 없음 |
| 파일 | 180,143,618 bytes | 작업 로그의 72.8MB 주장은 실제와 불일치 |

자막의 대표 잘못된 분절은 “청년 학자 소 / 플리니우스는”, “열릴 대규모 / 검투사 시합”, “생사를 가를 / 결정”처럼 명사구·관형구를 중간에서 끊는 형태다. 자막 안전영역과 클리핑은 현재 방식에서 합격했으므로 위치는 유지할 수 있지만, 실제 발화 강제정렬과 의미 단위 분절이 필요하다.

배경음·환경음이 없는 mono 내레이션과 샷마다 반복되는 약 1초 무음은 기계적인 cadence를 만든다. 재구축 시 저작권·라이선스가 확인된 절제된 ambience를 선택 사항으로 두되, 음성 명료도와 사실 전달을 우선한다.

## 8. P1: 계약과 페이싱 불일치

현재 파일들은 서로 다른 목표를 선언한다.

- `documentary_contract.yaml`: 최소 15분 `standard_docu`
- 생성기 파일명과 코드: `18min`
- 현재 JSON: `longform_11min`
- 실제 완성본: 11분 17.761초

`narration_policy.yaml`은 첫 장면군을 4–8초, 최대 10초, 전체 샷 예산의 45%로 규정하지만 실제 Chapter 1은 18/68=26.47%이며 18개 모두 8초를 넘고 7개는 10초를 넘는다. Chapter 2 이후 50개 중 12초 이상은 1개뿐이라 12–20초 목표와도 맞지 않는다. 첫 40초에 계약상 필수인 역설 질문도 없다.

재구축 권장 계약은 다음과 같다.

- 최종 길이: 15:00–16:30
- 첫 12초: 반전 사실과 핵심 질문
- 첫 40초: 4–8초 단위의 고밀도 시각 전환
- 40초 이후: 의미 단위 10–18초를 기본으로 하되 정지 이미지는 시각 정보량에 따라 분할
- shot 수는 68로 고정하지 않고 대본 컴파일 결과로 결정
- 기존 “Chapter 1이 전체 샷의 45%” 규칙은 “첫 40초 고밀도”로 명시적으로 개정하거나, 유지하려면 실제 샷 수를 그 비율에 맞춤

## 9. 재구축 아키텍처

```text
공식·동료평가 출처
       |
       v
source snapshots + source_ledger.json
       |
       v
claim inventory ---> 자동 근거·범위·수치·모순 검사 ---> 사람 fact approval
       |
       v
canonical shot_contract.json (script + visual anchors + duration + disclosure)
       |                                  |
       |                                  +--> measured phrase WAV timeline --> ASS
       v
provider job/card ID + prompt hash
       |
       v
asset_manifest.json + original image
       |
       v
decode/OCR/logo/pHash/semantic score + 100% human contact-sheet approval
       |
       v
safe 2.5D motion or licensed footage
       |                                  |
       +------------------+---------------+
                          v
                  build-isolated renderer
                          |
                          v
             final MP4 + machine postflight + release_report.json
```

핵심 원칙은 파일명이 아니라 **불변 ID와 hash chain**이 모든 단계를 연결하는 것이다. `script hash → prompt hash → provider asset ID → image hash → WAV hash → alignment hash → motion hash → ASS hash → final hash` 중 하나라도 끊기거나 stale이면 렌더하지 않는다.

## 10. 필수 품질 게이트

### 10.1 Fact gate

- 대본 생성기는 자유 문장부터 쓰지 않는다. 먼저 `claim_inventory.json`을 만들고 승인된 claim만 문장에 사용할 수 있다.
- 모든 검증 가능 문장에 `sentence_id`, `claim_id`, 출처 URL/DOI, 페이지 또는 섹션, 장소·시대 범위, 신뢰도, 표현 강도를 기록한다.
- 각 문장은 `verified_fact`, `contested_fact`, `inference`, `reconstruction`, `editorial` 중 하나로 분류한다. 분류가 없거나 근거 없는 사실 문장은 컴파일하지 않는다.
- 출처는 공식기관·1차 사료·동료평가 연구를 우선하고, 검색 요약이나 출처 위치가 없는 2차 문장은 증거로 인정하지 않는다. 단, “공식/논문”이라는 명칭만으로 강한 근거로 취급하지 않고 claim에 대한 직접성, 목격 범위, 장소·시대 범위, 연구 방법, 데이터 독립성, 상반 연구 존재를 별도 등급화한다.
- source page/PDF의 URL, 조회시각, 제목, 저자·기관, 발행일, locator와 content hash를 snapshot manifest에 남긴다. 긴 원문 전체를 복제하지 않고 검증에 필요한 짧은 근거 메모와 정확한 위치만 저장한다.
- 자동 검사는 claim과 근거의 entailment, 숫자·단위·시간 산술, 인물·장소·시대 scope, 샷 간 모순을 확인한다. `13:00→다음 날 06:00=17시간`, 헤르쿨라네움 500°C를 폼페이에 적용하는 사례는 반드시 실패해야 한다.
- 상반되거나 측정 대상·방법이 다른 연구가 있으면 `contested_fact`로 분류하고 각 연구의 대상·방법·한계와 허용 표현을 요구한다. 논쟁성은 곧 낮은 품질을 뜻하지 않으며, 한 연구만 전체 사실처럼 단정할 수 없다.
- 생성된 문장은 다시 sentence-to-claim 역검증을 거친다. claim에 없던 인과·수식어·최상급·심리 추정이 추가되면 `unsupported_addition`으로 실패한다.
- 논쟁적 사실은 화면과 내레이션에서 불확실성을 명시한다.
- 재연 행동·관계·대화는 `AI 재현 / 기록에 없는 장면 재구성`으로 표시한다.
- 근거 없는 집단 심리·피해자 동기·가족관계는 차단한다.
- 최종 산출물은 `source_snapshot_manifest.json`, `claim_inventory.json`, `script_draft.json`, `fact_check_report.json`, `fact_approval.json`이다. 다섯 hash가 현재 shot contract와 연결되지 않으면 다음 단계로 진행하지 않는다.
- 자동 점수만으로 승인하지 않는다. 사실 담당자가 모든 역사 문장을 확인하고, high-impact claim과 모든 `contested_fact`는 출처 원문 위치까지 다시 대조한 뒤 현재 script hash에 서명해야 한다.
- shot의 visual anchor와 생성 prompt는 승인된 `sentence_id`/`claim_id`를 참조해야 한다. 기록에 없는 행동을 재현하면 별도 `reconstruction_id`, 허용 범위, 화면 고지와 사람 승인이 필요하다. visual 계획의 hash가 바뀌면 fact 승인이 stale이다.
- `display`, TTS 발음용 텍스트, 자막은 승인된 문장의 파생물이다. 숫자 읽기 같은 의미 보존 변환만 허용하고, 정규화해 이어 붙인 자막과 TTS 문장이 승인된 display 문장과 의미·문구 면에서 일치해야 한다.

### 10.2 Asset lineage gate

- provider 완료 상태와 제출 card/job ID가 없으면 다운로드하지 않는다.
- timeout은 실패이며 이전 URL이나 최신 카드로 fallback하지 않는다.
- 다운로드는 `.part`에 저장한 뒤 decode·hash 검증 후 atomic rename한다.
- 원본 run과 다른 `ep01_pompeii_rebuild_v2/{build_id}` 아래에만 쓴다.

### 10.3 실제 픽셀 QA gate

각 이미지에 다음 여섯 축을 판정한다.

1. subject: 필요한 인물·사물
2. place: 폼페이/미세눔/스타비아이/발굴 현장 등 정확한 장소
3. era: 고대 로마, 18–19세기 발굴, 현대의 구분
4. action: 붕괴·탈출·관찰·발굴 등 핵심 동작
5. emotion/tone: 공포·정적·성찰 등 내레이션과 충돌하지 않는 정조
6. result: 문장이 말한 원인과 결과가 화면에 뒤집히지 않는지

subject·place·era·action 중 하나라도 치명적으로 다르면 자동/수동 승인 불가다. OCR text, provider 표식, 가짜 로고, 해부학 오류, pHash 근접 중복, 낮은 해상도도 실패다. 모델 점수만으로 합격시키지 않고 승인자가 전체 contact sheet와 개별 원본을 100% 확인한다.

생성 서비스 표식을 무단 크롭하거나 약관을 우회하지 않는다. 깨끗한 export 권한이 없으면 정식 사용이 가능한 스톡·공식 자료·다른 생성 제공자로 바꾸고, AI 재현 장면은 고지한다.

### 10.4 Pilot gate

전체 이미지를 만들기 전에 60–90초 파일럿을 새 아키텍처로 만든다. 사실 장부, 6축 시각 점수, 자막 강제정렬, 색·SAR·음량·컷 동기를 사람이 승인한 뒤 나머지 샷을 생성한다.

### 10.5 Render/postflight gate

- 1920×1080, SAR 1:1, DAR 16:9, progressive, strict 25 CFR
- `yuv420p`, limited/tv range, BT.709 primaries/TRC/matrix
- 48kHz mono, EBU R128 통합 음량 -16±1 LUFS, 4× oversampled true peak ≤ -1dBTP, clipping 0. clean narration의 미선언 0.5초 이상 무음 0건
- phrase short-term loudness 중앙값 편차 ±3 LU 이내, join click 0. LRA는 수치만 보고하고 사람 청취 승인으로 평탄한 TTS를 차단
- canonical visual event의 계획 frame index와 decoded video PTS 차이 ≤1프레임; phrase WAV의 master sample offset 오차 ≤1 sample; 자막 cue와 대응 phrase 차이 ≤20ms
- visual/audio/caption을 서로 맞추는 검사는 contract에서 `linked_boundary=true`로 지정한 이벤트에만 적용하고 차이 ≤1프레임. 독립 B-roll 컷을 음성 pause에 강제로 맞추지 않음
- A/V stream 종료 차이 ≤1프레임. 마지막 자막은 마지막 발화 phrase와 ≤20ms로 맞추며 contract에 선언된 0.2–1.0초 outro hold/ambience는 허용
- 자막 전 clean visual track을 320×180 area downscale한 고정 조건에서 `freezedetect=n=-50dB:d=0.5`, `blackdetect=d=0.10:pix_th=0.10:pic_th=0.98`, scene threshold 0.25로 검사. motion plan allowlist 밖의 freeze/black/0.12초 미만 double cut 0건
- decoded best-effort PTS가 40ms 간격이고 계획 정수 frame 합과 일치하며 `avg_frame_rate=r_frame_rate=25/1`. 80ms cadence hitch 0건
- 자막 hard max 2줄·줄당 25자, 권장 14–22자. cue 노출은 `max(0.7초, 한글 표시문자 수/11 CPS)` 이상·6초 이하, 형태소·문장 성분 중간 절단과 고아 어절 0건
- 렌더 후 자막 bbox가 좌우 5%, 상하/하단 10% 안전영역 안에 있고 clipping 0건
- delivery encode는 contract의 x264 High@4.1, CRF18, preset slow, keyint50, AAC-LC 48kHz mono 160kb/s를 따르고 자막 전 mezzanine 대비 visual SSIM ≥0.98 및 사람 압축 아티팩트 승인
- 자막 시각은 실제 phrase WAV 경계 또는 검증된 forced alignment에서만 생성하고, 글자 수 비례 karaoke는 사용하지 않음
- watermark/서비스 마크/OCR 금지 텍스트 0건
- 실제 픽셀 의미 불일치 0건, 사람의 전수 승인 누락 0건
- 실패한 게이트가 하나라도 있으면 exit nonzero이고 final 파일을 publish 경로에 쓰지 않음

## 11. 권위 출처 묶음

- 분출 연표·날짜·높이: [INGV/Osservatorio Vesuviano](https://www.ov.ingv.it/index.php/storia-vesuvio/pompei), [Earth-Science Reviews 2022](https://doi.org/10.1016/j.earscirev.2022.104072)
- 10월 목탄 낙서: [폼페이 유적청](https://pompeiisites.org/wp-content/uploads/Cartella-stampa-visita-Ministro-ENG.pdf)
- 플리니우스 서한: [Epistles 6.16·6.20](https://www.attalus.org/pliny/ep6.html)
- 분출 18–20시간과 초기 탈출: [Sigurdsson et al., AJA 1982](https://www.journals.uchicago.edu/doi/10.2307/504292)
- 폼페이 PDC 온도·사망기전 논쟁: [Scientific Reports 2021](https://www.nature.com/articles/s41598-021-84456-7), [PLOS ONE 2010](https://pmc.ncbi.nlm.nih.gov/articles/PMC2886100/)
- 캐스트 관계 통념을 반박한 DNA 연구: [Current Biology 2024](https://www.sciencedirect.com/science/article/pii/S0960982224013617)
- 피오렐리와 캐스트: [폼페이 유적청](https://pompeiisites.org/pompei-map/approfondimenti/i-calchi/)
- 분출 뒤 재산 회수·약탈·운하·발굴: [폼페이 유적청](https://pompeiisites.org/en/pompeii-map/analysis/pompeii-after-the-eruption/)
- 도피자가 휴대한 동전: [폼페이 유적청](https://pompeiisites.org/en/press-kit-en/with-a-sack-of-20-silver-and-bronze-coins/)

## 12. 최종 의사결정

1. 기존 final MP4, JPG, WAV, ASS, 작업 로그는 증거 보존용으로 그대로 둔다.
2. 현 영상을 공개·업로드·납품하지 않는다.
3. 기존 68개 JPG는 파일명 재배열이나 부분 교체로 구제하지 않는다.
4. 제목과 중심 질문을 “대다수 잔류/재산 집착”에서 “다수 탈출 이후 남은 사람과 변화하는 위험”으로 바꾼다.
5. 새 run에서 사실 장부와 canonical shot contract를 먼저 승인한다.
6. 60–90초 파일럿을 승인한 뒤에만 전체 자산 생성과 최종 렌더를 진행한다.
7. 상세 실행 순서는 대응 구현 계획서 `2026-08-21-pompeii-video-context-rebuild.md`를 따른다.

이 문서는 감사와 설계만 기록한다. 제작 코드·기존 영상·기존 자산은 변경하지 않았다.
