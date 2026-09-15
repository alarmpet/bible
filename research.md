# 프로젝트 종합 기술 분석 및 연구 보고서 (Repository Deep-Dive Analysis)

> **문서 버전:** v3.0 (human_archive 파이프라인 반영 및 전면 갱신)
> **최종 갱신일:** 2026-09-15
> **대상 저장소:** `https://github.com/alarmpet/bible.git` (`d:/module/bible`)
> **이전 버전(v2.0, 2026-08-18) 대비 변경:** bible_healing의 보이스·배경 속도 락이 바뀌었고(M2/0.1배속), v2.0에는 없던 **human_archive**(현재 저장소에서 가장 활발히 개발되는 파이프라인)를 새로 추가했다. v2.0의 수치는 대부분 이 시점 기준으로 stale하다.

---

## 1. 프로젝트 개요 및 핵심 목표 (Executive Summary)

본 저장소는 YouTube 플랫폼에 최적화된 장편 롱폼 영상 콘텐츠를 자동화·반자동화 파이프라인으로 제작·검증·렌더링하는 통합 미디어 생성 시스템이다. 서로 독립적으로 발전해 온 **세 개의 파이프라인**이 한 저장소를 공유한다.

```
                              bible/ (저장소 루트)
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────────────┐
│  bible_healing/       │  │  modern/              │  │  human_archive/               │
│  구약 힐링 성경 낭독   │  │  현대 드라마 대본      │  │  놀람파일 / 쉽선비 다큐멘터리   │
├──────────────────────┤  ├──────────────────────┤  ├──────────────────────────────┤
│ • KRV 성경 원문 파싱  │  │ • 5개 콘텐츠 레인     │  │ • nollam_file_v1(주) /         │
│ • 2-Voice TTS         │  │   (검증실화/합성허구/  │  │   doodle_seonbi_v1(레거시)     │
│   (M2 나레이터+M4 낭독)│  │   반전/멜로/실험)     │  │   프로필 이원화                │
│ • 0.1배속 핑퐁 루프   │  │ • 반복·패딩 차단      │  │ • CLI v5/v6 10단계 제작 파이프라인│
│   앰비언트 비디오     │  │   품질 감사 엔진       │  │ • Claude/Codex/Grok 실측       │
│ • EPISODE_LEDGER 기반 │  │ • 캐릭터 일관성 시트   │  │   교차검증 오케스트레이션       │
│   중복 방지           │  │                       │  │ • "선언-실행 괴리" 자동 감사 게이트│
│ • 10단계 오케스트레이션│  │                       │  │                                │
│   릴리즈 게이트       │  │                       │  │                                │
└──────────────────────┘  └──────────────────────┘  └──────────────────────────────┘
```

과거 조선 시대 야담 파이프라인(`대본 sonnet/`)은 읽기 전용 레거시로 보관되며, 신규 기능은 위 세 파이프라인에서만 확장된다.

---

## 2. 전체 시스템 디렉토리 구조 (주요 항목)

```
bible/
├── CLAUDE.md                    # human_archive(놀람파일) 운영 매뉴얼 — 저장소 루트를 차지
├── bible_healing/CLAUDE.md      # bible_healing 전용 매뉴얼 (2026-09-15, 루트 CLAUDE.md와 분리)
├── manual.md, research.md       # 크로스 프로젝트 운영 노트
├── pytest.ini                   # bible_healing/modern/human_archive 테스트를 모두 수집
├── requirements.txt
│
├── bible_healing/                # [파이프라인 A] 구약 힐링 성경 낭독 시스템
│   ├── assets/movie-sample/pingpong-1min/   # 1분 앰비언트 배경 12종
│   ├── config/media_rules_lock.json         # 보이스·자막·배경 락(정본)
│   ├── data/                                # 성경 원문 OSIS XML 및 파싱 JSON
│   ├── scripts/                             # 오케스트레이션·TTS·자막·렌더링·QA 스크립트
│   └── tests/
│
├── modern/                       # [파이프라인 B] 현대 드라마 대본 시스템
│   ├── config/content_lanes.yaml            # 5개 레인 정의(L1_TRUE~L5_ROTATION)
│   ├── story_quality.py                     # 반복/패딩/단서-회수 감사 규칙 본체
│   ├── scripts/audit_story_quality.py       # 위 규칙을 호출하는 CLI 래퍼
│   └── tests/
│
├── human_archive/                # [파이프라인 C] 놀람파일 / 쉽선비 다큐멘터리 시스템
│   ├── config/channel_profiles.yaml         # nollam_file_v1(기본) / doodle_seonbi_v1(레거시) 등
│   ├── scripts/                             # 대본·이미지·모션·릴리즈 CLI 전체
│   │   ├── lib/orchestration/               # Claude/Codex/Grok 교차검증 엔진(all-manage 포팅)
│   │   ├── audit_declared_vs_wired.py       # "선언-실행 괴리" 정적 감사 게이트
│   │   └── postflight_release.py            # 릴리즈 최종 검증(모션·provenance 게이트 포함)
│   ├── templates/, schemas/, docs/orchestration/
│   └── tests/                               # 프로젝트 내 최대 규모 테스트 스위트
│
└── docs/superpowers/plans/       # 3개 파이프라인 공통 작업계획·감사 문서 보관소
```

---

## 3. 파이프라인 A: 구약 힐링 성경 낭독 시스템 (`bible_healing`)

### 3.1 기획 의도
- 타깃: 밤에 불안·불면·번아웃으로 힘들어하는 시청자.
- 구조: 공감 오프닝 훅 → 구약 성경 낭독(시편·잠언 등) → 묵상/위로.
- 목표 분량: 약 100분(±20%).

### 3.2 10단계 오케스트레이션 파이프라인 (`run_full_media_pipeline.py`)

단일 진입점을 통해 다음 순서를 통과해야 배포본으로 승인된다: `media_rules_preflight` → `build_full_job` → `tts_multi_voice` → `verify_voice_provenance` → `rebuild_authoritative_full_audio` → `verify_authoritative_audio` → `build_full_audio_aligned_ass` → `qa_ass` → `render_authoritative_full` → `media_rules_postflight`.

### 3.3 음성 규격 (`config/media_rules_lock.json`, 2026-09-15 기준 실측)

| 구분 | 나레이터(`narrator`) | 성경 낭독(`scripture`) |
|---|---|---|
| 보이스 | **M2** (2026-09-15 이전엔 F5였다) | M4 |
| 속도 | 0.95 | 0.86 |
| 피치 | **0%** (F5 시절의 -4% asetrate 피치시프트 제거, highpass/lowpass/EQ 체인으로 대체) | -10% (`asetrate=24000*0.90`) |
| total_step | 10 | 10 |
| 쉼(silence) | 0.25s | 0.35s |
| 합성 단위 | 장면 단위 | 절 단위 1회, `max_chunk` 90자 |

값의 원본은 `media_rules_lock.json`이며, 문서와 다르면 이 파일을 기준으로 삼고 문서도 함께 수정한다.

### 3.4 자막·챕터 표시
- 본문 자막: 최대 2줄, 한 줄 14~18자(hard 20자), 1080p 기준 본문 96px/성경 100px.
- 우측 상단 챕터 라벨: 현재 읽는 성경 권/장/절 또는 주제를 지속 표시, 하단 자막 크기의 약 70%(70px).
- 자막은 실제 오디오 세그먼트 타임코드를 따르며 오차 허용은 0.5초 이내.

### 3.5 배경 영상
- 소스: `assets/movie-sample/pingpong-1min/*.mp4` 12종, 핑퐁(정/역방향) 루프.
- 재생 속도: `setpts=10*PTS` — **0.1배속 초슬로우 모션** (2026-09-15 이전엔 `setpts=3*PTS`, 0.333배속이었다).
- 전환 주기: 정확히 60초마다 다음 샘플로 순환.

### 3.6 에피소드 원장(EPISODE_LEDGER)
완성된 에피소드는 로컬에 영구 보존하고 `EPISODE_LEDGER.md`에 기록한다. 다음 에피소드 기획 시 직전 에피소드와 겹치지 않도록 시편·잠언·전도서·이사야/선지서·모세오경 등 성경 권을 순환 배치한다(중복률 0% 원칙).

> **2026-09-15 저장소 구조 변경:** 저장소 루트 `CLAUDE.md`는 원래 이 bible_healing 매뉴얼이었으나, human_archive 작업이 같은 경로를 자체 매뉴얼로 대체하며 충돌했다. 이후 루트는 human_archive가 쓰고, bible_healing 고유 지침은 `bible_healing/CLAUDE.md`로 분리했다.

---

## 4. 파이프라인 B: 현대 드라마 대본·영상 시스템 (`modern`)

### 4.1 기획 의도
2015~2026년 현대 한국을 배경으로 한 드라마 대본을 AI 생성 특유의 반복·개연성 붕괴·캐릭터 어색함을 시스템적으로 차단하며 제작한다.

### 4.2 콘텐츠 레인 (`config/content_lanes.yaml`, 2026-09-15 기준 실측)

이전 버전 문서(v2.0)가 설명한 "L1 약자 통쾌 역전극 / L2 가족 파탄 회복 / L3 범죄·사기 추적 / L4 직업 현장 갈등 / L5 시대 이슈" 레인 구성은 **더 이상 실제 설정과 일치하지 않는다.** 현재 정의는 다음과 같다.

| 레인 | 라벨 | truth_modes |
|---|---|---|
| `L1_TRUE` | 검증 실화 | TRUE_VERIFIED, TRUE_PERMISSIONED |
| `L2_HEART` | 감동 합성허구 | INSPIRED_COMPOSITE, FICTION_REALISTIC |
| `L3_TWIST` | 공정 반전 | FICTION_REALISTIC, FICTION_HEIGHTENED |
| `L4_MAKJANG` | 고밀도 멜로·복수 | FICTION_HEIGHTENED |
| `L5_ROTATION` | 실험 회차 | INSPIRED_COMPOSITE, FICTION_REALISTIC, FICTION_HEIGHTENED |

채널 약속(`channel_promise`): "감정적으로 선명하고 인과가 납득되며 끝난 뒤 한 장면이 남는 한국형 드라마". 포트폴리오 규칙(`portfolio`)은 최근 20편 창(`recent_window`) 안에서 레인당 최소 1편~최대 3편을 강제해 한 레인 편중을 막는다.

### 4.3 스토리 품질 감사 엔진

규칙 본체는 `modern/story_quality.py`에 있고(CLI 래퍼는 `modern/scripts/audit_story_quality.py`), 실측 확인된 감사 항목은 다음과 같다.

- `check_filler_repetition()`: 동일 문장 반복 시 `FILLER_REPEAT_BLOCK`, 3문장 블록 재등장 시 `REPEATED_BLOCK`.
- `require_story_material()`: 분량 미달 시 `InsufficientStoryMaterial` 예외.
- `validate_clue_ledger()`: 미스터리/반전 계열 레인의 단서 회수 여부 검증.
- `validate_project_contract()` / `validate_topic_cards()`: 프로젝트 계약서·주제 카드 스키마 검증.
- `audit_portfolio()`: 위 포트폴리오 레인 분산 규칙 검증.

### 4.4 캐릭터 일관성
`참고_캐릭터_일관성_시트.md` 등 캐릭터 참조 시트를 두어 회차 간 인물 묘사 드리프트를 막는다(구체적 다각도 턴어라운드 체계의 세부 절차는 이번 갱신에서 재확인하지 못했다 — 필요 시 `modern/README.md`/`modern/HANDOFF.md`를 직접 확인할 것).

---

## 5. 파이프라인 C: 놀람파일 / 쉽선비 / Human Archive 다큐멘터리 시스템 (`human_archive`)

v2.0에서 다루지 않았던 섹션이다. 저장소에서 가장 크고(테스트 스위트 기준 최대 규모), 가장 활발히 개발되는 파이프라인이며, 2026-09-15 하루 동안 `docs/superpowers/plans/2026-09-15-human-archive-nollam-script-visual-motion-multi-llm-overhaul-plan.md`의 Task 0~9(정적 감사 게이트, 대본/이미지 프롬프트 파이프라인 수렴, 오케스트레이션 엔진 완성, 모션 엔진 교체, 모션 QA 릴리즈 게이트, fps/페이싱 정책 통일, 시각 브리프 교차검증, human_library_replica 격리)가 전부 완료됐다.

### 5.1 채널 프로필 이원화 (`config/channel_profiles.yaml`)

- **`nollam_file_v1` (1순위, 기본값)** — "놀람파일": 포토리얼리스틱 시네마틱 다큐(인류의 서재 벤치마크), 호스트 아바타 **0%**(완전 배제), 배송 프로필 `trend_explainer_20m`(목표 1200초, 14~26분 허용), 시간 감쇠 페이싱 곡선 `nollam_decay_20m`(Cold Open 4.0초 → Outro 12.5초, 7구간), 대본은 `config/script_policy_v3.yaml` + `templates/nollam_script_prompt_v3.j2`, 내레이터 보이스는 SuperTonic3 `M2_WARM`.
- **`doodle_seonbi_v1` (2순위, 레거시)** — "쉽선비": 조선 역사 두들 일러스트, 호스트 캐릭터 8~12%(최소 7샷 간격)로 제한.

### 5.2 CLI v5/v6 제작 파이프라인 (10단계)

`CLAUDE.md`에 문서화된 정본 순서: 1차 사료·Claim 인벤토리 → 대본 생성 → 팩트·페르소나 검증 게이트 → SuperTonic3 문장 TTS·실측 타임라인 → 샷 타이밍·의미 브리프·Flow 이미지 요청 → 콜드오픈+커버리지 이중 파일럿 → 전체 이미지 생성 → 전체 QA·사람 승인 → 모션·자막·최종 렌더 → 포스트플라이트·릴리즈 승격.

### 5.3 Claude/Codex/Grok 교차검증 오케스트레이션 (`scripts/lib/orchestration/`)

`D:\all-manage`에서 실전 검증된 엔진을 포팅했다(`run_consensus_round.py`). 핵심 원칙: "합의는 증거가 아니다"(propose → critique → diverge, 병합·점수화 금지), `has_contract()`(정해진 헤딩 없는 응답은 실패로 집계), `check_independence()`(한 참가자가 다른 참가자 작업 중 파일을 읽었을 가능성을 mtime으로 검출), 역할 로테이션. 현재 실제로 연결된 것은 **codex+grok** 2자 실시간 교차검증(`escalate_claim()`)이며, 문장 팩트체크·씬 시각 브리프 비평·대본 구조 토론(`tri_model_debate_engine.py`) 세 곳에 실전 배선돼 있다. Gemini(agy CLI)는 이 PC에 실제 바이너리가 없어 어댑터(`lib/orchestration/_run_gemini.py`)만 준비된 미배선 확장점이다.

### 5.4 "선언-실행 괴리" 방지 게이트 (`scripts/audit_declared_vs_wired.py`)

이번 조사에서 반복적으로 발견된 패턴 — YAML/스키마에는 정교한 설계가 선언돼 있는데 실제로 그걸 호출하는 production 코드가 없는 것 — 을 정적으로 검사하는 큐레이티드 레지스트리 기반 게이트. `--strict` 플래그로 CI 하드게이트 전환이 가능하며, 알려진 미해결 항목(예: `generate_release_manifest_v4/v5`가 아직 실제 호출자 없음, Sep2 마스터플랜의 4-Step Claude 체인이 아직 config 선언에만 존재)은 `accepted=True`로 정직하게 추적한다.

### 5.5 모션 엔진과 릴리즈 게이트

기존 두 모션 엔진(`build_motion_clips_v2.py`, `smooth_subpixel_motion_engine.py`)은 전체 구간 cosine easing으로 근접중복률 78~84%가 실측돼 격리됐다. `motion_engine_v3.py`(시작/끝 짧은 ramp + 등속 cruise 궤적)로 교체해 같은 측정 기법으로 근접중복률 0~3%를 실측 검증했다. `postflight_release.py`의 `verify_postflight()`는 이제 실제 디코드된 프레임에서 모션 다양성을 재측정해 릴리즈를 차단할 수 있고(매니페스트가 자체 신고하는 boolean을 더 이상 그대로 신뢰하지 않음), `orchestrate_deep_tri_model_script()`의 아직 실측화되지 않은 라운드가 있으면 `provenance: "simulated_fixture"`로 정직하게 표기해 같은 게이트가 자동 차단한다.

---

## 6. 외부 인프라 및 기술 스택

| 컴포넌트 | 기술 | 비고 |
|---|---|---|
| Python 환경 | 3.13.5 | 저장소 루트 `pytest.ini`가 `bible_healing/tests`, `modern/tests`, `human_archive/tests` 세 곳을 모두 수집 (2026-09-15 이전에는 human_archive가 루트 실행 시 빠졌다) |
| TTS 엔진 | SuperTonic3 로컬 HTTP 서버(`http://127.0.0.1:3093`) | bible_healing·human_archive 공통 사용, 보이스 락은 프로젝트별로 다름(M2/M4 vs M2_WARM) |
| 영상 합성 | FFmpeg/ffprobe | 세 파이프라인 공통 |
| Google Flow (ImageFX) | Playwright CDP 브라우저 제어 | human_archive 전용, 이미지 생성 |
| 교차검증 LLM CLI | `codex`, `grok` (subprocess) | human_archive 오케스트레이션 엔진에서 실사용; Gemini(`agy`)는 미설치 |
| Node.js 오케스트레이터 | Hermes(`render-youtube-with-tts.mjs`) | bible_healing·modern 공통 |

---

## 7. 현재 상태 (2026-09-15 기준)

- **bible_healing**: 보이스/배경 속도 락 갱신(M2·0.1배속) 완료, EPISODE_LEDGER 기반 성경 권 순환 시스템 도입.
- **modern**: 콘텐츠 레인 5종(L1_TRUE~L5_ROTATION) 및 포트폴리오 분산 규칙 가동 중.
- **human_archive**: 2026-09-15 오버홀 플랜의 Task 0~9(정적 감사 게이트, 대본/이미지 파이프라인 수렴, 오케스트레이션 엔진, 모션 엔진 교체, 릴리즈 게이트, fps/페이싱 통일, 시각 브리프 교차검증, replica 격리) 전부 완료. 남은 후속 과제(리트로스펙티브에서 발견): `pacing_scheduler.py`의 남은 중복 구현 정리, nollam 스크립트 phase 명명 체계의 일부 잔여 불일치, `tri_model_llm_bridge.py`의 "Gemini 3.8/3.7/3.6" 페르소나 프레이밍 등은 각각 별도 후속 세션으로 분리돼 있다.
- **저장소 전체**: 저장소 루트에서 `pytest --collect-only` 실행 시 세 파이프라인 합쳐 약 975개 테스트가 수집된다(사전에 알려진, 무관한 collection error 1건 — `human_archive/tests/test_biphasic_motion.py`의 stale import — 제외). 이 숫자는 활발히 변하므로 특정 시점의 스냅샷으로만 취급할 것.

---
*이 문서는 2026-09-15 시점에 실제 설정 파일(`media_rules_lock.json`, `content_lanes.yaml`, `channel_profiles.yaml` 등)과 코드를 직접 대조해 검증한 내용만 반영했다. 검증하지 못한 세부사항은 추정하지 않고 "재확인 필요"로 명시했다.*
