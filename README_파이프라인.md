# 파이프라인 의존 그래프

```
[활성] modern/  ── v12 현대 실화풍 합성 드라마
[보관] 대본 sonnet/ + 루트 야담 프롬프트  ── 레거시 (덮어쓰지 않음)
```

## 대본 생성 (현대)

```
v12_modern_main_SONNET.md
  ├─ motif_bank.md
  ├─ name_bank.md + name_picker.py
  ├─ 부록_양식.md
  ├─ 참고_비트구조 / 캐릭터 / 인트로 / 장르
  ├─ scripts.md + checks.py
  └─ runs/<slug>/
       contract · matrix · evidence · beat · facts · chapters · final
```

## 이미지·썸네일 (현대)

```
참고_캐릭터_일관성_시트.md   ← ★ 다각도 A0–A3·S0·표정, edit-chain
참고_이미지컷_밀도_규칙.md   ← ★ 챕터1 고밀도 / 2+ 사건 밀도
prompt_v6_modern_flow.md     ← 본편 Flow (총 N 기본 40, 고정 아님)
썸네일_프롬프트_현대.md
시스템프롬프트_인트로_현대.txt
runs/<slug>/shot_plan.md     ← 컷 리스트 (Ch1 촘촘)
```

**초반 이탈 방지:** 스토리 챕터1만 문장·맥락 단위로 촘촘히, 이후는 사건 단위.  
**캐릭터 일관성:** 본편 전 다각도 S0 완성 → 장면은 edit+레프 (text-only gen 남발 금지).

## 경로

`PATHS.md` 단일 관리.

## 스모크 완료

| 런 | 상태 |
|---|---|
| runs/smoke_g1 | 대본+캐릭터 S0+Ch1~5 이미지+인트로 mp4 ✅ |
| runs/smoke_g4 | 미스터리 5챕터 합본 ✅ |

## 최종 영상 (Hermes 연동)

| 문서 | 용도 |
|---|---|
| **`modern/HANDOFF.md`** | **다음 LLM 시작점** |
| `계획서_HERMES_최종영상_파이프라인.md` | 전체 설계 v1.2 |
| `modern/scripts/README.md` | CLI 순서 |

```
smoke_g1 → pack_hermes_job → tts_multi_voice (나레이션≠캐릭터)
  → hermes render-youtube-with-tts → (선택) CapCut draft
```

**현재:** pack + validate preview **통과**. TTS 미리듣기는 SuperTonic venv 필요.  
**미실행:** full TTS 16씬 → MP4 렌더 → CapCut.

## 후속

- Preview multi-voice TTS + Hermes 렌더
- g1/g4 25k 증량 / archive_yadam
