# 계획서: 구약 힐링 파이프라인 — Hermes 규약 정합 · 전면 업그레이드

> **작성일:** 2026-08-10  
> **조사 범위:** `C:\Users\amd\hermes` (자막·폰트·싱크·렌더 계약) + `C:\Users\amd\module\bible_healing` (현재 실패/스모크 산출)  
> **결론:** 지금 bible_healing v1/v2 스모크는 **Hermes에 이미 있는 자막·싱크 규약을 무시**했고, **이미지는 AI/Flow 생성이 아니라 절차적 더미**다.  
> **목표:** Hermes 표준(줄당 글자·폰트·Whisper 싱크·장면 이미지)에 맞춰 **배포 가능한 힐링 롱폼**으로 재설계.

---

## 0. 사용자 질문에 대한 직답

| 질문 | 답 |
|------|-----|
| Hermes에 폰트크기·줄당 글자 정보가 있나? | **있다.** UI 프리셋, CapCut Reference-A, ASS, 단일행 분할 엔진에 명시. |
| 음성·자막 싱크가 안 맞는 이유? | 한 씬 오디오 전체 길이 동안 **잘린 고정 텍스트 1장**만 보여 줌. 시간에 따라 바뀌는 cue가 없음. |
| 이미지는 아직 생성 안 한 거지? | **맞다.** Flow/Grok Imagine 장면 이미지가 아니라 **Pillow로 그린 배경 + 글자 합성**이다. |

---

## 1. Hermes에 이미 있는 규약 (조사 결과)

### 1.1 자막 줄당 글자 · 줄 수 (UI 프리셋)

출처: `hermes/app.js`, `hermes/electron/renderer/app.js` — `subtitlePresetDefaults`

| 프리셋 ID | fontSize (UI) | outline | shadow | marginV | **maxLineChars** | **maxLines** |
|-----------|---------------|---------|--------|---------|------------------|--------------|
| `clean-news` | 20 | 4 | 2 | 36 | **12** | **2** |
| `bold-shorts` | 22 | 4 | 2 | 34 | **10** | **2** |
| `minimal` | 18 | 2 | 0 | 36 | **13** | **2** |
| 기본 fallback | — | — | — | 78 | **11** | **2** |

- 롱폼/뉴스형 기본 권장: **`clean-news` → 줄당 12자 · 최대 2줄**.  
- 쇼츠형: **`bold-shorts` → 줄당 10자 · 2줄**.

### 1.2 CapCut Reference-A (한글 단일행 정책)

| 항목 | 값 | 출처 |
|------|-----|------|
| **maxDisplayCharacters** | **16** | `capcut-single-line-caption.mjs`, `check-capcut-reference-caption-style-contract.mjs` |
| **minDisplaySeconds** | **0.65** | 동일 |
| 분할 함수 | `splitCaptionSrtForSingleLine` | 글자 가중치로 시간 배분 |
| 폰트 폴백 | **Malgun Gothic Bold** (`malgunbd.ttf`) | `caption-style-reference-a.v1.json` |
| 바 스타일 | 하단 반투명 검정 바, 흰 글자, 두꺼운 검정 테두리 | Reference-A design |
| textStyle.size (CapCut) | **15** (CapCut 단위, UI px와 다름) | reference JSON |
| border.width | **14** | reference JSON |
| background.alpha | v1 **0.76** / v2 **0.50** | design spec |
| clipSettings.transform_y | **-0.72** (하단 배치) | reference JSON |

**핵심:** Hermes 한글 자막의 “정답 경로”는  
**긴 문장 한 블록 고정이 아니라 → 16자 전후 단일 행(또는 UI 프리셋 2줄)으로 쪼개고 → 오디오 구간에 가중 배분**이다.

### 1.3 ASS / 로컬 스튜디오 폰트 스케일 (참고)

| 스타일 | fontSize (ASS/렌더) | marginV | 출처 |
|--------|---------------------|---------|------|
| bold_shorts | 54 | 150 | local-studio plan |
| clean_news | 42 | 130 | 동일 |
| caption_box | 40 | 120 | 동일 |
| installer preset bold | 24 | 78 | electron installer plan |
| installer clean | 18 | 60 | 동일 |

→ **“fontSize 숫자”는 레이어마다 단위가 다름** (UI CSS px ≠ CapCut size ≠ ASS).  
재구현 시 **한 계약 파일로 고정**해야 함 (아래 §4).

### 1.4 음성–자막 싱크 계약

| 계층 | Hermes 규약 | 비고 |
|------|-------------|------|
| 씬–오디오 | `scene_N.wav` duration = 씬 비주얼 길이 | `tts-sync-strategy.md`, render-youtube |
| 프로덕션 자막 | **Whisper word timestamps 필수** 옵션 | `render-youtube-with-tts.mjs` → `CAPTION_TIMING_ESTIMATED` |
| 정밀 자막 | `refine-subtitles-with-whisper.mjs` + `whisper_subtitle_refiner.py` | 단어 단위 큐 |
| 단일행 시간 배분 | 글자 수 weight + min 0.65s | `allocateTiming` |
| 허용 오차 (파생 쇼츠 리뷰) | **±100ms** 언급 | longform-to-short review |

### 1.5 이미지/장면

| Hermes 경로 | 역할 |
|-------------|------|
| Flow / Grok Imagine | `scene_N_flow.jpg` 등 **장면 스틸** 생성 |
| `imageSceneSource(order)` | 렌더 시 flow still 탐색 |
| 이미지 프롬프트 안전 | **이미지 안에 글자/자막/로고 넣지 말 것** (grok-imagine / gemini 쪽 공통) |
| modern 밀도 규칙 | 챕터1 고밀도 컷, 이후 사건 밀도 (`참고_이미지컷_밀도_규칙.md`) |

**중요 분리:**  
- **장면 이미지** = 글자 없는 비주얼  
- **자막** = 별도 레이어(ASS/CapCut/하드서브 타임라인)

bible_healing이 배경에 구절을 구워 넣은 방식은 **Hermes 이미지 정책(이미지에 텍스트 금지)과 충돌**하고, 싱크 엔진과도 충돌한다.

---

## 2. 현재 bible_healing 상태 (재진단)

### 2.1 무엇이 “있는 척”만 했는지

| 축 | 현재 | Hermes 대비 |
|----|------|-------------|
| 음성 | SuperTonic 이중 보이스, 속도 1.00/0.96 스모크 | TTS 엔진은 재사용 가능 |
| 이미지 | Pillow 밤하늘/숲 **프로시저 아트** | **Imagine/Flow 미사용 = “이미지 생성 안 함”이 맞음** |
| 자막 | 씬당 고정 프레임에 6줄·18자 wrap, 전 구간 동일 | **줄당 10–16자 단일/2줄 + 시간 분할 없음** |
| 싱크 | 오디오 46초에 화면 글자 108자 고정 | **구조적 디스싱크** (늦는 게 아니라 “안 바뀜”) |
| 100분본 | 무음 패드·저속 | 배포 금지 유지 |

### 2.2 싱크 불일치 수치 증거 (스모크 preview)

| order | speaker | 전체 글자 | 오디오(초) | 화면에 남는 대략 | 문제 |
|-------|---------|-----------|------------|------------------|------|
| 5 | scripture | **423** | **46.4** | ~108자(6×18) + `…` | 말 다 하는데 화면은 앞부분만 |
| 8 | narrator | 424 | 64.1 | ~108 | 동일 |
| 10 | scripture | 360 | 31.2 | ~108 | 동일 |

→ 사용자가 느끼는 “싱크 안 맞음” =  
**타이밍 오프셋 버그가 아니라, 타임드 자막 시스템이 아예 없음.**

### 2.3 이미지 “미생성” 판정 기준

| 단계 | 했는가 |
|------|--------|
| 테마·샷 플랜 | 부분 (유닛 구조만) |
| 장면 프롬프트 | ❌ |
| Grok Imagine / Flow 호출 | ❌ |
| `scene_N_flow.jpg` 의미 있는 컷 | ❌ (프로시저 배경) |
| 캐릭터/장소 일관성 시트 | ❌ (힐링이므로 장소 모티프 뱅크로 대체 가능) |

---

## 3. 목표 제품 정의 (업그레이드 후)

### 3.1 시청 경험

1. **음성:** 점잖은 여성 나레이션 + 온유한 말씀 보이스 (속도 귀 검수 확정).  
2. **화면:** 힐링 장소 이미지(밤 창·호수·촛불 등) — **글자 없음**.  
3. **자막:** 하단에 Hermes 규약 자막이 **말과 함께 넘어감**.  
4. **구절 구간:** 자막 스타일 강조(조금 더 큼/중앙 또는 Reference-A 바) + 참조 라벨(`시편 4:1`).  
5. **분량:** 80–120분, **무음 억지 패드 금지**.

### 3.2 품질 게이트 (DoD)

| ID | 조건 | 측정 |
|----|------|------|
| G1 | 줄당 글자 ≤ 정책값 | clean-news 12 또는 RA 16 |
| G2 | 동시 표시 줄 ≤ 2 (또는 RA 단일행) | 자동 검사 |
| G3 | 큐 최소 표시 0.65s | 자동 검사 |
| G4 | 자막 텍스트 ⊆ 해당 구간 발화 텍스트 | 샘플 + 가능하면 Whisper |
| G5 | 장면 이미지에 OCR 가능 본문 없음 | 스모크 OCR 또는 수동 |
| G6 | 이미지 출처 = Imagine/Flow 매니페스트 | provenance.json |
| G7 | 30s 이상 무음·무자막 고정화면 없음 | 자동 |
| G8 | 배포 전 10분 스모크 인간 승인 | checklist |

---

## 4. 단일 계약: `healing_caption_policy.json` (신설)

Hermes 분산 수치를 **bible_healing 한 파일로 고정**.

```json
{
  "policy_id": "healing-longform-v1",
  "inherits": {
    "line_split": "hermes-capcut-single-line-v3",
    "ui_preset": "clean-news",
    "font": "Malgun Gothic Bold"
  },
  "display": {
    "maxLineChars": 12,
    "maxLines": 2,
    "maxDisplayCharactersSingleLineAlt": 16,
    "minDisplaySeconds": 0.65,
    "mode": "two-line-weighted"
  },
  "typography_render": {
    "engine": "ass_or_pillow_timeline",
    "fontPath": "C:\\\\Windows\\\\Fonts\\\\malgunbd.ttf",
    "fontSizePx_1080p": 48,
    "outlinePx": 4,
    "shadowPx": 2,
    "marginV_px": 72,
    "boxAlpha": 0.50,
    "primaryColour": "#FFFFFF",
    "outlineColour": "#000000"
  },
  "scripture_emphasis": {
    "fontSizePx_1080p": 52,
    "refLabelSizePx": 32,
    "refLabelColor": "#E6D2A0"
  },
  "timing": {
    "prefer": "whisper-word-timestamps",
    "fallback": "char-weighted-splitCaptionSrtForSingleLine",
    "maxDriftMs": 150
  }
}
```

**권장 기본:** 롱폼 가독 → `maxLineChars=12`, `maxLines=2` (clean-news).  
CapCut 핸드오프 시에는 Hermes `splitCaptionSrtForSingleLine(..., { maxDisplayCharacters: 16 })` 재사용.

---

## 5. 목표 아키텍처 (업그레이드)

```
[1] verse DB + dual script          (유지, 개선)
        ↓
[2] shot plan (시각 비트)           ← NEW: 유닛당 3~6 비주얼 비트
        ↓
[3] image prompts (no text)         ← NEW: Grok Imagine / Flow
        ↓
[4] scene_N_flow.jpg                ← 실제 생성 이미지
        ↓
[5] TTS multi-voice                 (유지 SuperTonic)
        ↓
[6] lock audio manifest             (유지)
        ↓
[7] caption cues                    ← NEW: Hermes split + Whisper
        ↓
[8] render                          ← Hermes render 또는 v3 burn-in 타임라인
        ↓
[9] QA gates G1–G8
```

### 5.1 자막 파이프 (싱크 핵심)

```
script_segments + measured scene_audio_manifest
    → build_scene_srt.py          # 씬 단위 러프 SRT (전체 문장)
    → split via Hermes
         electron/services/capcut-single-line-caption.mjs
         또는 동등 Python 포트 (동일 알고리즘)
    → (권장) refine-subtitles-with-whisper.mjs
    → cues.json + subtitles-ko.srt
    → render: ASS softsub 또는 프레임 타임라인 하드서브
```

**금지:** 한 장의 `flow.jpg`에 구절 전문을 박고 오디오 전체와 맞춤.

### 5.2 이미지 파이프 (진짜 생성)

| 단계 | 내용 |
|------|------|
| 모티프 뱅크 | 밤창, 별밤, 호수, 촛불, 숲길, 새벽, 비창, 안식 방 등 12–20 |
| 샷 플랜 | 유닛당 최소 3컷: 훅 / 구절 분위기 / 해석 |
| 프롬프트 규칙 | **No text, no subtitles, no logos, no watermark** (Hermes grok-imagine 안전 문구 그대로) |
| 생성기 | 1순위: Hermes `automation/grok-imagine-media.mjs` / 기존 modern 이미지 경로 |
| 산출 | `assets/generated/ep01/shot_###.jpg` + provenance |
| 매핑 | `scene_visual_map.json`: scene order → shot id |
| 폴백 | 생성 실패 시에만 모티프 스톡; **프로시저 그라데이션 단독 금지(QA BLOCK)** |

### 5.3 렌더 경로 선택

| 옵션 | 장점 | 단점 | 권장 |
|------|------|------|------|
| **A. Hermes `render-youtube-with-tts.mjs`** | 씬 스케일·자막·검증 계약 재사용 | 롱폼 100분 무거움, Whisper 게이트 | 본선 후보 |
| **B. bible_healing render v3** | 제어 쉬움 | 규약 재구현 필요 | 스모크·병렬 |
| **C. CapCut handoff** | 편집 가능 자막 | Export 수동 | 최종 폴리시 |

**권장 전략:**  
스모크/본선 자동화는 **B(v3) + Hermes 분할 알고리즘 이식**,  
프로덕션 자막 품질은 **Whisper refine**,  
필요 시 **C로 미세 조정**.

---

## 6. 단계별 실행 계획

### Phase 0 — 계약 고정 (0.5일) ✅ 2026-08-10

- [x] `bible_healing/config/healing_caption_policy.json`  
- [x] Hermes 분할 알고리즘 Python 포팅 (`caption_split_hermes.py`) + 단위 동작 확인  
- [x] HANDOFF 갱신  

### Phase 1 — 타임드 자막 엔진 (1–2일) **P0** ✅ 스모크

1. [x] `build_cues_from_manifest.py` → 292 cues @ max 12자  
2. [x] Hermes weight timing  
3. [ ] Whisper refine (후속)  
4. [x] `render_healing_v3.py` + ASS burn-in  
5. [x] 스모크: 프레임 t30/t50 자막 문구 상이 확인  

**합격(스모크):** 말과 함께 하단 자막이 넘어감. Full은 승인 후.

### Phase 2 — 진짜 이미지 생성 (2–3일) **P0** 🔄 시작

1. [x] Imagine 3종 (candle/window/lake) → `assets/generated/ep01/`  
2. [x] 스모크 `final-smoke10-v3-realbg.mp4` 에 매핑  
3. [ ] 유닛별 12–20 모티프 배치 생성  
4. [ ] `scene_visual_map` + provenance 자동화

### Phase 3 — 본편 음성·분량 (1–2일)

1. `preview_approved` 후 full TTS (속도 고정)  
2. rest 레이어 과다 반복 축소 (품질)  
3. 분량 80–120: **대본으로 조절**, 무음 패드 금지  
4. 이중 보이스 유지 (narrator ≠ scripture)

### Phase 4 — Full 렌더 · QA (1–2일)

1. Full cues + images + TTS  
2. G1–G8 리포트  
3. 구간 검수 0–3 / 25–30 / 55–60 / 끝 5분  
4. 업로드 패키지 재생성 (배포 허용 플래그 `quality_gate: pass` 있을 때만)

### Phase 5 — (선택) CapCut 핸드오프

- Hermes CapCut Reference-A 스타일로 편집 가능 자막 트랙  
- 유튜브 softsub + hardsub 병행

---

## 7. 파일·모듈 책임 맵

| 신설/수정 | 역할 |
|-----------|------|
| `config/healing_caption_policy.json` | 폰트·줄당 글자·min display 단일 진실 |
| `scripts/build_cues_from_manifest.py` | 타임드 자막 생성 |
| `scripts/bridge_hermes_caption_split.mjs` | Hermes `splitCaptionSrtForSingleLine` 호출 |
| `scripts/generate_healing_images.py` | Imagine/Flow 배치 + provenance |
| `scripts/render_healing_v3.py` | 이미지(무텍스트) + 타임드 자막 렌더 |
| `scripts/qa_healing_render.py` | G1–G8 |
| `compose_scene_frame.py` | **폐기 또는 “타이틀 카드 전용”으로 격하** |
| `make_background_bank.py` | 개발 폴백만, 프로덕션 BLOCK |
| `extend_to_target_duration.py` | 31s 패드 **프로덕션 금지** |

Hermes 재사용:

- `electron/services/capcut-single-line-caption.mjs`  
- `scripts/refine-subtitles-with-whisper.mjs`  
- `scripts/render-youtube-with-tts.mjs` (옵션)  
- `automation/grok-imagine-media.mjs`  
- `app.js` subtitle presets  

---

## 8. 우선순위

| 순위 | 작업 | 이유 |
|------|------|------|
| **P0** | 타임드 자막 (Hermes 16/12자 규약) | 싱크 불만 직접 해결 |
| **P0** | 실제 이미지 생성 파이프 | “이미지 없음” 직접 해결 |
| **P0** | 이미지/자막 레이어 분리 | Hermes 정책 + 유지보수 |
| P1 | Whisper word timestamps | 프로덕션 싱크 |
| P1 | QA 자동화 G1–G8 | 재발 방지 |
| P2 | CapCut 핸드오프 | 편집 여유 |
| P3 | ep02 | ep01 게이트 통과 후 |

---

## 9. 일정 가안

| Phase | 공수 |
|-------|------|
| 0 계약 | 0.5d |
| 1 타임드 자막 | 1–2d |
| 2 이미지 생성 | 2–3d |
| 3 Full TTS·분량 | 1–2d |
| 4 Full 렌더·QA | 1–2d |
| **합계** | **약 6–10 근무일** |

---

## 10. 리스크

| 리스크 | 대응 |
|--------|------|
| 100분 × 다수 이미지 생성 비용/시간 | 유닛당 3컷, 배경 재사용 라운드로빈 + 핵심 유닛만 고밀도 |
| Whisper 설치/경로 | 폴백: char-weighted split (Hermes 동일 알고리즘), 게이트에 품질 등급 표시 |
| CapCut size vs px 혼동 | policy 파일에 엔진별 필드 분리 |
| 구절 전문 화면 요구 | 타임드 자막으로 전체 낭독 따라가기; 한 화면 전문 금지 |
| 이전 “완성” 오해 | deprecated + quality_gate 없으면 업로드 패키지 생성 거부 |

---

## 11. 결론

1. **Hermes에는 이미** 줄당 10–13자(UI)·**16자 단일행(CapCut RA)**·Malgun Bold·min 0.65s·Whisper 싱크·이미지 무텍스트 정책이 있다.  
2. bible_healing은 이를 쓰지 않고 **고정 프레임 글자 + 프로시저 배경**으로 우회했다.  
3. 그 결과 **싱크 실패·이미지 미생성**은 버그 한 줄이 아니라 **아키텍처 불일치**다.  
4. 업그레이드는 “예쁘게 다듬기”가 아니라 **Hermes 규약에 파이프를 다시 꽂는 것**이다.

**다음 착수 순서 (승인 시):**  
Phase 0 계약 파일 → Phase 1 타임드 자막 스모크(구절 1편) → Phase 2 이미지 1유닛 실제 생성 → 인간 검수 → Full.

---

## 부록 A. Hermes 핵심 경로 인덱스

| 주제 | 경로 |
|------|------|
| UI 자막 프리셋 | `hermes/app.js` (`subtitlePresetDefaults`) |
| 단일행 분할 | `hermes/electron/services/capcut-single-line-caption.mjs` |
| RA 스타일 JSON | `hermes/resources/pycapcut-youtube-editor/acceptance/caption-style-reference-a.v1.json` |
| RA 디자인 | `hermes/docs/superpowers/specs/2026-07-15-capcut-reference-a-caption-design.md` |
| Whisper 자막 | `hermes/scripts/refine-subtitles-with-whisper.mjs` |
| 렌더·Whisper 게이트 | `hermes/scripts/render-youtube-with-tts.mjs` |
| TTS–비주얼 싱크 개념 | `hermes/AI-Sessions/wiki/concepts/tts-sync-strategy.md` |
| 이미지 프롬프트 무텍스트 | `hermes/automation/grok-imagine-media.mjs` |
| modern 컷 밀도 | `module/modern/참고_이미지컷_밀도_규칙.md` |

## 부록 B. 현재 vs 목표 한 장

| | 지금 | 목표 |
|--|------|------|
| 줄당 글자 | ~18자 × 6줄 고정 | **12자 × 2줄** (또는 16자 × 1줄) |
| 자막 시간 | 씬 전체 동일 | **0.65s+ 가중 분할 / Whisper** |
| 이미지 | Pillow 더미 | **Imagine/Flow 장면** |
| 이미지 속 글자 | 있음 (잘못됨) | **없음** |
| 폰트 | malgun 임의 px | **Malgun Bold + policy 고정** |
| 100분 채우기 | 무음 패드 | **대본·컷 밀도** |

---

*문서 끝. 구현 착수 전 이 계획서 승인 권장.*
