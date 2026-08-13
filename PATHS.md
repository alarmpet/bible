# PATHS.md — 실행 경로 단일 관리

> Windows 워크스페이스 기준. Claude/Linux 절대경로는 매핑 참고용.

## 워크스페이스 루트

| 키 | 경로 |
|---|---|
| `WORKSPACE` | `C:\Users\amd\module` |
| `MODERN` | `C:\Users\amd\module\modern` |
| `LEGACY_YADAM` | `C:\Users\amd\module\대본 sonnet` |

## 현대 파이프라인 (v12) — 단일 원본

| 역할 | 상대경로 (WORKSPACE 기준) |
|---|---|
| 메인 프롬프트 | `modern/v12_modern_main_SONNET.md` |
| 모티프 뱅크 | `modern/motif_bank.md` |
| 이름 뱅크 | `modern/name_bank.md` |
| 작명 스크립트 | `modern/name_picker.py` |
| 검증 스크립트 | `modern/scripts.md` |
| 부록 양식 | `modern/부록_양식.md` |
| 비트 구조 | `modern/참고_비트구조_체크리스트_slim.md` |
| 말투·문체 | `modern/참고_캐릭터_말투_문체_slim.md` |
| 인트로·제목 | `modern/참고_인트로_제목_가이드_slim.md` |
| 장르 요소 | `modern/참고_장르별_요소풀_slim.md` |
| 스모크 체크 | `modern/smoke_checklist.md` |
| **기본 분량 (100분±20%)** | `modern/duration_default.md` |
| Flow v6 | `modern/prompt_v6_modern_flow.md` |
| 이미지 컷 밀도 규칙 | `modern/참고_이미지컷_밀도_규칙.md` |
| 캐릭터 일관성·다각도 | `modern/참고_캐릭터_일관성_시트.md` |
| 썸네일 현대 | `modern/썸네일_프롬프트_현대.md` |
| 인트로 영상 현대 | `modern/시스템프롬프트_인트로_현대.txt` |
| 파이프라인 맵 | `README_파이프라인.md` |
| 계획서 (현대 대본) | `계획서_현대화_대본품질_보강.md` |
| 계획서 (주제·대본 다양성·품질) | `계획서_주제_대본_다양성_품질_강화.md` |
| 계획서 (최종 영상·Hermes) | `계획서_HERMES_최종영상_파이프라인.md` |
| **다음 LLM 핸드오프** | `modern/HANDOFF.md` |
| Hermes 루트 | `C:\Users\amd\hermes` |
| SuperTonic3 TTS | `C:\Users\amd\supertonic3-local-tts-20260517-r4\supertonic3-local-tts` |
| SuperTonic Python | `…\supertonic3-local-tts\.venv-win\Scripts\python.exe` |
| 브리지 스크립트 | `modern/scripts/` |
| smoke_g1 job (preview) | `modern/runs/smoke_g1/hermes_jobs/preview/` |
| 스모크 g1 | `modern/runs/smoke_g1/final.txt` |
| 스모크 g4 | `modern/runs/smoke_g4/final.txt` |

## 작품 작업 디렉터리 (런타임)

작업마다 `MODERN/runs/<작품슬러그>/` 아래에 둔다.

| 파일 | 용도 |
|---|---|
| `story_contract.md` | 작품 계약 |
| `character_matrix.md` | 욕구·금기·전략 |
| `evidence_cards.md` | 증거 카드 |
| `beat_map.md` | 15비트 1줄 맵 |
| `story_facts.md` | 팩트시트 (파생) |
| `progress.md` | 챕터 재개 |
| `thumbnail_brief.md` | 썸네일 브리프 |
| `chapter_N.txt` | 챕터 본문 |
| `final.txt` | 합본 |

## 레거시 경로 매핑 (참고만 — 현대 작업에서 쓰지 않음)

| 레거시 (Linux/Claude) | 이 워크스페이스 |
|---|---|
| `/home/claude/v11/` | `modern/runs/<slug>/` |
| `/mnt/project/name_bank.md` | `modern/name_bank.md` |
| `/mnt/user-data/outputs/` | `modern/runs/<slug>/outputs/` |

## name_picker 호출 예 (Windows PowerShell)

```powershell
cd C:\Users\amd\module\modern
python name_picker.py 중산 여 --used 지훈 --n 6
python name_picker.py 권력 남 --used 지훈 서연 --n 6
```

## 규칙

1. **심볼릭 링크 사용 금지** (Windows/환경 차이). 원본은 `modern/` 하나.
2. 레거시 `대본 sonnet/`·루트 `name_bank.md`는 스모크 통과 전 **읽기 전용 보관**.
3. 프롬프트 안 하드코딩 경로는 이 파일 키(`MODERN`, `runs/...`)를 따른다.
