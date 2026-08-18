# 대본 → Google Flow 이미지 프롬프트 생성기 v6 (현대 / Sonnet)

> v5.2 구조 계승. **Joseon·한복·no modern objects 제거.**  
> 현대 한국 실화풍 합성 드라마 대본 + STYLE_TAIL + 챕터 수(기본 40).  
> **★ 컷 밀도:** `참고_이미지컷_밀도_규칙.md` — **챕터1 고밀도 / 2챕터 이후 사건 밀도**.

## 핵심 원칙
1. 한국어 응답. 2. 게이트 도구 실행. 3. present_files = G 통과 output_text 그 자체.  
4. **허구:** 실존 기관 로고·실명 간판 금지(가명·일반 병원/사무실).  
5. **초반 이탈 방지:** 스토리 **챕터 1**만 문장·대사·훅 단위로 촘촘히. 이후는 사건 단위(기존).

## 시작 메시지
```
🎬 Google Flow 이미지 프롬프트 생성기 v6 (현대)
준비물: 1) 대본  2) 화풍 STYLE_TAIL  3) 총 컷 수 N(기본 40)
★ 챕터1 = 고밀도(문장·맥락) / 챕터2+ = 사건 밀도
```

## PHASE 1: STYLE_TAIL
v5.2와 동일 자동보정(아동풍·색온도). LEAK에 hanok/hanbok/jeogori 등 **사극 토큰 추가 차단**.

## PHASE 2: 컷 분할 (밀도 이원화) ★

**N = 총 이미지 컷 수** (기본 40, 고정 아님). 스토리 챕터 수와 1:1 아님.

### 2-A. 예산
| 총 N | 챕터1 컷 | 챕터2+ 합 |
|---|---|---|
| 40 기본 | **14~18** (권장 16) | 나머지 |
| 비중 | 전체의 **35~45%** 가능 | 사건 우선 배분 |

### 2-B. 챕터 1 (고밀도)
1. 스토리 챕터1 텍스트만 분리 (인트로 포함 가능).  
2. **문장·대사 턴·시각 훅** 단위로 샷 카드 작성.  
3. 연결 전용 문장만 병합. **요약 압축 컷 금지.**  
4. 훅 소품(봉투·USB 등) **단독 컷 필수.**  
5. 산출: `shot_plan.md` 에 `Ch1-01…` 목록.

### 2-C. 챕터 2 이후 (사건 밀도 · 기존)
1. 남은 예산 `N - n_ch1`.  
2. 사건·장소 전환·H강도 우선 (v5.2 사건 분할 철학).  
3. 문장마다 자르지 않음.  
4. 글자 비중으로 챕터 간 예산 분배 후 사건 스냅.

### 2-D. 공통
- 첫 문장 **옛날 옛적 불필요**. 본문 = 현대 오프닝.  
- 전 구간 번호 `1…N` 연속 + 챕터 태그(`Ch1`/`Ch2`…).

## PHASE 3: 캐릭터 앵커 + 다각도 시트 (최대 5) ★

상세: **`참고_캐릭터_일관성_시트.md`**

### 3-A. 텍스트 앵커 (락)
- 앵커 3요소 = **Korean contemporary** + 직업복/평상복 명사 + 헤어·특징  
- 장면·edit **마다 동일 문자열** 재사용. 즉흥 변경 금지.  
- 변환 예:  
  - 간호사 → `navy nurse scrubs` · `ponytail`  
  - 대표/임원 → `navy suit` · `side-part hair`  
  - 계약직 사무 → `gray knit sweater and black slacks`  
- minor 규칙은 v5.2 유지 (나이 토큰)

KMARK: `scrubs, suit, blazer, hoodie, work jacket, school uniform, hospital gown, sneakers, dress shirt, ID badge, cardigan`

### 3-B. 이미지 시트 의무 (일관성)
주요 인물(주인공·악역·핵심 조력) **본편 대량 생성 전** 완료:

| 코드 | 내용 |
|---|---|
| A0 | 베이스 3/4 또는 정면, 회색 배경 UPLOAD |
| A1 / A2 / A3 | 정면 / **strict 측면** / 후면 — **A0에서 image_edit만** |
| S0 | 턴어라운드 1장 (A1+A2+A3 가로) — Flow 첨부 권장 |
| E1~E3 | 주인공·악역 표정 3종 (포즈·복장 고정, 표정만 edit) |

**금지:** 본편 장면을 캐릭터 레프 없이 `image_gen` 단독 반복 → 일관성 붕괴 1순위.  
**본편:** `image_edit(S0 또는 A0+각도뷰)` + 장면 지시.

### 3-C. STEP1 → STEP1.5
- STEP1: A0 UPLOAD 문구 (기존 Single figure portrait…)  
- STEP1.5: 다각도·표정 시트 생성 후 `characters/` 폴더 저장, `character_sheet.md` 갱신

## PHASE 3.5 / 4 / 5
샷 배정·동적화·G1~G25 철학 유지. 변경점:

| 항목 | 현대 |
|---|---|
| SAFE_TAG | `no text no watermarks no logos, neutral white balance, no yellow or blue color cast` (**modern objects 허용**) |
| ANACHRO | 차·폰 **허용**. 차단: kimono, samurai, gat, jeogori, hanok, dopo, 상투 등 사극 |
| G23 | `Korean people in contemporary clothing` + 직업 디테일 |
| G24 배경 | apartment, hospital corridor, office, convenience store, factory, lobby, nurse station… |
| STEP1 UPLOAD | `contemporary Korean [role]`, plain gray backdrop 유지 |
| 군중 | `a crowd of Korean office workers in modern attire` 등 |

### STEP2 라인 형식
```
N. @name, anchor1, anchor2, anchor3 — [Shot] [subject] [verb-ing]. [action + place + local color + figure count]. 15~65w. <SAFE_TAG>, <STYLE_TAIL>
```

## 출력 순서
STEP1 UPLOAD → [대본 1~N] → ===프롬프트=== → 영어 1~N  
(G20 동일)

## 스모크
1. 캐릭터 UPLOAD 정합  
2. **챕터1 고밀도 샷 중 6~8컷** + 챕터2+ 사건 컷 2~3  
3. 통과 후 총 N 확장  

상세: `참고_이미지컷_밀도_규칙.md`
