# modern/ — 현대 드라마 파이프라인 (v12 + 품질계약 v2)

야담(조선) 레거시(`대본 sonnet/`)를 **덮어쓰지 않은** 작업 트리입니다.  
설계 근거: `../계획서_현대화_대본품질_보강.md` (v1.1 리뷰 반영).

## 빠른 시작

1. `config/content_lanes.yaml`에서 콘텐츠 레인과 `truth_mode`를 확정
2. `templates/project_contract.yaml`을 작품 폴더에 복제하고 분량 티어 지정
3. 메인 프롬프트 `v12_modern_main_SONNET.md`와 필요한 slim 참고문서 로드
4. 주제 카드 8개 → 상위 3개 비교 → 1개 승인 후 Story/Execution DNA 설계
5. 작품 폴더 `runs/<슬러그>/`에 bible·clue ledger·챕터·QA 보고서 저장
6. 합본 감사: `python modern/scripts/audit_story_quality.py --text <final.txt> --contract <project_contract.yaml>`

경로 표: 루트 `../PATHS.md`

## 파일 목록

| 파일 | 역할 |
|---|---|
| `v12_modern_main_SONNET.md` | 메인 생성 프롬프트 |
| `motif_bank.md` | 현대 엔진 모티프 |
| `name_bank.md` | 현대 이름 풀 |
| `name_picker.py` | 작명 코드 추출 |
| `부록_양식.md` | 계약·매트릭스·증거·검증 양식 |
| `scripts.md` | era_leak·허구고지·증거 회수 등 |
| `story_quality.py` | 반복·실화성·분량·주제카드·포트폴리오 하드 게이트 |
| `config/` | 5개 레인, 5개 truth mode, 분량, QA 기준 |
| `templates/` | project contract, source packet, topic card, story bible, clue ledger |
| `scripts/audit_story_quality.py` | UTF-8 JSON QA CLI, BLOCK 시 종료코드 2 |
| `참고_*_slim.md` | 비트·말투·인트로·장르 |
| `smoke_checklist.md` | 1·2차 스모크 절차 |
| `runs/` | 작품별 런타임 (gitignore 권장) |

## 레거시와의 관계

| | 레거시 | modern v12 |
|---|---|---|
| 위치 | `대본 sonnet/` | `modern/` |
| 배경 | 조선 야담 | 2015~2026 한국 합성 드라마 |
| 상태 | 읽기 전용 보관 | **활성 작업** |
| archive | 스모크 통과 후 검토 | — |

## 시각·썸네일

| 파일 | 역할 |
|---|---|
| **`참고_이미지컷_밀도_규칙.md`** | **챕터1 고밀도(문장·훅) / 2+ 사건 밀도** — 초반 이탈 방지 |
| **`참고_캐릭터_일관성_시트.md`** | **A0→정면·측면·후면·S0 턴어라운드·표정** — 얼굴 흔들림 방지 |
| `prompt_v6_modern_flow.md` | Google Flow 본편 (총 N 기본 40, 고정 아님) |
| `썸네일_프롬프트_현대.md` | 썸네일 카피·이미지 |
| `시스템프롬프트_인트로_현대.txt` | 인트로 훅 영상 |

총 컷 40은 **기본값**. 스토리 챕터와 1:1 아님. 챕터1에 전체의 35~45% 배분 권장.

## 스모크 완료

| 런 | 결과 |
|---|---|
| `runs/smoke_g1/final.txt` | 장르1 약자 통쾌 ~21k ✅ |
| `runs/smoke_g4/final.txt` | 반복 패딩 회귀 표본 — `FILLER_REPEAT_BLOCK` ❌ |

`smoke_g4` 기존 파일은 회귀 표본으로 보존한다. 생성 스크립트는 짧은 원고를 반복 확장하지 않고 `INSUFFICIENT_STORY_MATERIAL`로 중단한다.
