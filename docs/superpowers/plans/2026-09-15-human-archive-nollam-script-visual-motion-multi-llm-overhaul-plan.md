# Human Archive — 대본·이미지매칭·모션 실체 진단 및 GPT·Gemini·Grok·Claude 4자 경쟁·교차검증 엔진 설계 계획서

> **상태:** 2026-09-15 코드·산출물 전수 실측을 바탕으로 작성한 실행 전 계획서. 승인 전에는 기존 final 파일이나 `runs/` 산출물을 수정·덮어쓰지 않는다. **D2(프로덕션 파이프라인=대안 B), D5(Studio GUI 유지+백엔드 교체), D7(human_library_replica 격리)은 사용자 확정 완료.** 나머지 D1/D3/D4/D6/D8/D9는 §8 기본값으로 진행하되 실행 중 이견이 있으면 언제든 재조정한다.
>
> **조사 방법:** 4개 병렬 조사(① nollam 파이프라인 구현 현황 ② 대본 생성 코드 ③ 이미지 매칭·생성 코드 ④ 모션/Ken Burns 렌더링)와 본인의 직접 코드 추적(트라이모델 디베이트 엔진, 역사 패러럴 엔진, Studio GUI, human_library_replica)을 종합했다. 모든 판정에는 file:line 근거를 남긴다.
>
> **선행 문서와의 관계:** 이 문서는 `2026-08-26-human-archive-script-image-motion-upgrade.md`(이하 **Aug26**)와 `2026-09-02-human-archive-retention-pacing-autonomy-master-plan.md`(이하 **Sep2**)를 대체하지 않는다. 두 문서가 제안한 계약 아키텍처·페이싱 커브 설계는 여전히 유효하며, 이 문서는 **"그 설계가 실제로 어디까지 배선됐는가"**를 2026-09-15 기준으로 재실측하고, 사용자가 명시적으로 요청한 **GPT/Gemini/Grok 3사(+Claude) 실질적 경쟁·교차검증 엔진** 설계를 추가한다.
>
> **중요한 정정(작성 중 발견):** 애초에 이 엔진을 처음부터 설계할 계획이었으나, 사용자가 "GPT/agy/Grok 활용 방법은 `D:\all-manage`에 이미 구현·사용 이력이 있다"고 알려줘 해당 저장소의 `tools/orchestration/`을 직접 확인했다. 그 결과 **이미 실전에서 여러 라운드 돌려본, 훨씬 더 엄격하게 설계된 3사(Claude/Codex=GPT/Grok) 경쟁·교차검증 엔진이 존재**했다(§5.0). 이 문서의 §5는 처음부터 새로 설계하지 않고 **그 엔진을 human_archive 도메인으로 포팅**하는 쪽으로 방향을 바꿨다.
>
> **실행 시 권장 방식:** `superpowers:executing-plans`로 단계별 checkpoint를 지키고, 버그 수정은 `superpowers:test-driven-development`, 완료 판정은 `superpowers:verification-before-completion`을 적용한다.

---

## 0. 결론부터

사용자가 "대본생성·대본구조·이미지매칭·이미지생성·영상편집이 전부 엉망 같다"고 느끼는 체감은 **정확하다.** 다만 원인은 하나가 아니라 **세 개의 서로 다른, 서로 모르는 파이프라인이 병존하면서 어느 것도 완전하지 않은 상태**에 있다.

| 파이프라인 | 문서화 상태 | 실측 품질 |
|---|---|---|
| **① CLI v5/v6** (`CLAUDE.md` §4, `generate_visual_briefs.py` 등, EP02 장희빈/쉽선비 레거시) | CLAUDE.md가 "정본"으로 명시 | **의외로 양호.** 대본-이미지 매칭 로직, 재사용 안전장치, fail-closed QA가 실제로 잘 작동한다 (§2.3 참조). 대본 생성 엔진만 미완성. |
| **② NOLLAM Studio GUI** (`studio_gui_server.py`, `tri_model_debate_engine.py`, `historical_parallel_engine.py`, 놀람파일용) | CLAUDE.md에 **전혀 언급 없음** | **거의 전부가 겉치레.** "Gemini 3.8/3.7/3.6 트라이모델 경쟁·교차검증"을 표방하지만 실제 대본 생성 경로는 100% 하드코딩 템플릿이고 LLM 호출이 0건이다 (§2.4). |
| **③ `run_*_full_pipeline.py` 계열** (`run_human_library_*`, `run_san_jose_*`, `run_neanderthal_*`) | CLAUDE.md에 **전혀 언급 없음** | 가장 최근(9/8~9/15) 활발히 수정되는 경로. 이 중 `human_library_replica`(rank1/rank2)는 **타 채널 원본 영상을 대본 문장부터 워터마크까지 1:1 복제**하는 것으로 확인됐다 (§6). 사용자 결정에 따라 이번 계획에서 프로덕션 경로로 다루지 않고 격리한다. |

**권장 방향은 세 가지다.**

1. **파이프라인을 하나로 수렴한다.** ①의 계약·QA·재사용 안전장치를 그대로 살리고, ②의 "가짜 AI 토론"을 **`D:\all-manage\tools\orchestration\`에 이미 실전 검증된 Claude/Codex(GPT)/Grok 경쟁·교차검증 엔진을 포팅한** 진짜 엔진으로 교체해 nollam_file_v1 대본·비주얼 브리프·팩트체크에 배선한다(§5). ③은 프로덕션에서 완전히 분리한다.
2. **모션 엔진의 근본 원인(전체 구간 cosine easing + 3.5% 고정 확대율)을 고친다.** 이 버그는 legacy `build_motion_clips_v2.py`와 신규 `smooth_subpixel_motion_engine.py` **두 곳 모두**에 독립적으로 재구현돼 있다(§2.5). 하나를 고쳐도 다른 하나가 남으면 문제가 재발한다.
3. **"선언과 실행의 괴리"를 막는 게이트를 만든다.** 이번 조사에서 반복적으로 발견된 패턴은 *"YAML/주석/이름에는 정교한 설계가 있는데 실제로 그것을 호출하는 코드가 없다"*는 것이다(§3). 이 패턴 자체를 막는 CI 검증(선언된 기능마다 최소 1개의 production 호출자가 있는지 자동 검사)을 Task 0에 넣는다.

---

## 1. 사용자가 지목한 5개 영역 — 실측 진단 (file:line 근거)

### 1.1 대본 생성 방식

**CLI v5/v6 경로 (`generate_verified_script.py` → `scripts/lib/script_generation.py`):**

- Sep2 마스터플랜 D9가 못박은 "Claude Messages API 4-Step 체인(Plot→Fact→Scene→Rhythm QA)"은 **정책 YAML(`config/script_policy_v3.yaml:71-94`)과 템플릿(`templates/nollam_script_prompt_v3.j2`) 파일로만 존재**하고, 이를 4번 호출하는 오케스트레이션 코드는 저장소 어디에도 없다.
- 실제 실행 경로는 `script_generation.py:160-173`의 `generate_script_candidate()`가 프롬프트를 **단 1회** 조립해 provider에 보내고 끝난다. 그런데 `build_prompt_context()`(`script_generation.py:145`)가 템플릿 경로를 `templates/seonbi_script_prompt.j2`로 **하드코딩**하고 있어서, nollam v3 템플릿이 실제로 렌더링되는 일이 없다.
- 최신 운영 빌드(`runs/ep02_jang_huibin/full-v6-001/source/script_candidate.json`, 2026-08-29)조차 `persona: "ship_seonbi"`와 seonbi beat 구조(`hook/roadmap/body/analogy/source_commentary/insight/outro`)로 생성됐다 — nollam의 `phase`/`visual_mode`/`midjourney_prompt` 필드는 없다. **"1순위 메인 프로필은 nollam_file_v1"이라는 Sep2 D1 결정이 대본 생성 단계에는 아직 전혀 반영되지 않았다.**
- provider는 Anthropic API가 아니라 `antigravity-cli`(로컬 `agy`/`antigravity` 바이너리, `script_generation.py:34-87`) 또는 `OmniRouteProvider`(로컬 OpenAI 호환 게이트웨이, `script_generation.py:90-139`)다. 저장소 전체에서 `anthropic`/`ANTHROPIC_API_KEY`/`messages.create` grep 결과가 0건이다.
- Aug26이 지적한 modulo 반복 로직(`generate_ep02_full_docu.py:324`, `generate_ep03_full_docu.py:182-218`)은 **삭제되지 않고 그대로 남아 있다.**
- 대본 품질 검증(`audit_episode_quality.py`의 `repetition_gate()`, exact/normalized/n-gram 중복 검사)은 존재하지만 CLAUDE.md의 정규 실행 순서(§4 Step1-7)에 **포함돼 있지 않아** 실제로 호출되지 않는다.

**NOLLAM Studio 경로 (`tri_model_debate_engine.py` → `historical_parallel_engine.py`):** §1.2, §2.4에서 통합 설명.

### 1.2 대본 구조

`historical_parallel_engine.py:generate_dynamic_script()`(633-855행)가 나레이션 문장의 실제 출처다. 이 함수는:

- `pair_id`/`historical_parallel` 문자열에 특정 키워드(`"산호세"`, `"마야"`, `"칭기즈"`, `"네안데르탈"` 등)가 있을 때만 손으로 쓴 전용 문장 뱅크(`_generate_san_jose_sentences` 등)를 쓴다(677-686행).
- **그 외 모든 주제는 `_generate_generic_sentences()`로 폴백한다.** 현재 Studio가 실제로 제안하는 주제 5종 세트(JWST 은하, 마야 라이다, 양자컴퓨터, 타이탄 잠수정, 뉴럴링크, 화산 분화, 스웨이츠 빙하, 영구동토층 메탄 등 — `tri_model_debate_engine.py:441-873`)는 **단 하나도** 4개 전용 뱅크에 해당하지 않는다. 즉 실제로 기획되는 주제의 거의 전부가 동일한 generic 구조로 찍힌다.
- 대본 구조(5단계 phase, 문장 수, 챕터 배분)는 `flat_texts`를 15/20/30/20/15% 비율로 기계적으로 자른 것이다(659-675행) — 내용에 따른 서사 설계가 아니다.

**증거 (v5/v6 최신 빌드 실측, 근접 반복):**
- S005: "정사 실록과 승정원일기에는 장희빈의 난동 기록이 전혀 없답니다."
- S011: "정사인 실록과 승정원일기에는 장희빈의 발악이나 난동 기록이 전혀 없답니다."
- V6-N011: "정사에는 난동 기록이 없다는 점이 기준이 됩니다."

같은 claim(`CLM-JH-001`)이 세 차례 다른 표현으로 변주 반복된다 — "구조가 단조롭다"는 사용자 체감의 직접 증거다.

### 1.3 대본-이미지(대본 맥락) 매칭

**여기가 이번 조사의 가장 의외의 결과다: CLI v5/v6 경로는 실제로 잘 작동한다.**

- `generate_visual_briefs.py:59-73`의 `_IMAGE_FACING_FIELDS`가 `focal_subject, action, place, era, camera` 등 13개 필드를 강제하고, `lib/aligned_prompt_compiler.py:159-184`의 `compile_aligned_prompt()`가 이를 실제로 조립한다.
- 최신 빌드(`runs/ep02_jang_huibin/full-v6-001/flow_image_prompts.json`) 5개 샘플 전수 확인 결과, "사약을 엎지르며 발악했다"는 낭설을 반박하는 나레이션에는 "엎질러지지 않은 그릇"이, "실록·승정원일기에 기록이 없다"는 나레이션에는 "닫힌 두 개의 공문서 상자"가 대응하는 등 **narration의 구체 의미가 시각 은유로 정확히 대응**하고 있었다.
- 재사용 안전장치(`lib/semantic_image_reuse.py`)도 촘촘하다: 문장 집합이 완전히 일치할 때만 `auto_reuse`이고, 부분 일치는 항상 사람 검토(`review_candidate`)로 보낸다. `visual_mode`/`visual_role`이 다르면 자동으로 `generate_new`로 강등한다.
- `verify_visual_assets.py`는 승인 파일 유무와 무관하게 해시·근접중복(pHash)·OCR을 항상 실행한다 — Aug26이 지적한 "승인 파일 있을 때만 검사"(fail-open)는 **해소됐다.**

**NOLLAM Studio 경로는 정반대다.**

- `visual_prompt`는 `historical_parallel_engine.py:805-808`에서 다음과 같이 조립된다:
  ```python
  visual_prompt = (
      f"{s_prompt_prefix}. Subject: Authentic historical documentary for {protag}, {d_text[:40]}. "
      f"25fps optical cadence, no subtitles, no text overlays, keep bottom 18% clear."
  )
  ```
  — 샷 스케일 접두사(영문 고정구) + 한국어 나레이션 **앞 40자를 그대로 자른 것**이 전부다. era/character/조명/구도 추론이 없다.
- 실제 이미지 생성 호출부(`flow_cdp_service.py:580`)의 프롬프트 폴백 체인은 `visual_prompt → compiled_prompt → t2v_prompt → prompt → display_text → narration` 순이다. `visual_prompt`가 비어 있으면 **한국어 나레이션 원문을 그대로 Google Flow에 보낼 위험**이 있다.
- 카메라 모션도 `motions = ["push_in", "slow_pan_left", ...]`을 `(order - 1) % len(motions)`로 단순 순환(769, 792행)한다 — 장면 내용과 무관하다.

### 1.4 이미지 생성

- CLI v5/v6: Playwright CDP로 실제 Google Flow(Nano Banana 2)를 제어하는 `generate_flow_batch.py`가 견고하게 작동한다. 다만 대체 provider로 확장 가능한 추상화는 없다 — `lib/provider_flow.py:155`는 라이브 CDP 모드에서 `NotImplementedError`를 던지는 **스텁**이고, `mode="fixture"`일 때만 PIL로 가짜 테스트 이미지를 만든다.
- Studio 경로(`flow_cdp_service.py`의 `FlowBatchManager`)도 실제 Playwright CDP 자동화가 맞다(가짜가 아니다) — 다만 앞서 §1.3에서 본 얕은 프롬프트를 그대로 전송한다.
- **fps 불일치:** Sep2 D2/CLAUDE.md는 Human Archive를 25fps로 못박지만, `lib/cinematic_editing_director.py:9`는 "1080p **30fps** normalization"을 불변 규칙으로 선언한다. 실제로 두 개의 다른 fps 정책이 코드베이스에 공존한다.

### 1.5 영상편집(줌/아웃/Ken Burns 등)

**Aug26이 8월에 진단한 버그가 그대로 남아 있고, 새 엔진이 같은 버그를 재구현했다.**

| 항목 | `build_motion_clips_v2.py` (legacy, CLAUDE.md 정본) | `smooth_subpixel_motion_engine.py` (신규, "Inviolable Rule 3: 0-Pixel Judder" 자칭) |
|---|---|---|
| 확대율/easing | `1.00→1.035` 고정, `total_frames` 전체에 cosine easing (`:77-86`) — Aug26이 지적한 버그와 동일 | `cosine_easing()`을 여러 구간에 적용하지만 `1.0+0.04*eased`, `1.04+0.12*eased` 등 확대 델타가 작고(4~12%), Aug26이 근접중복 78~84%로 실측한 것과 같은 메커니즘 |
| motion map 키 불일치 | `SHOT_MOTION_MAP`은 `ch1_001~012`만 정의. 실제 shot_id는 `ha002_v6_shot_001` 형식 → **112개 전부(100%)**가 4종 fallback 순환으로 처리됨 (진단 당시보다 악화) | — |
| named preset 중복 | `kenburns_zoom_pan_in`/`pan_right`/`kenburns_hero_push`가 완전히 동일한 수식 공유 (`:94-96`) | — |
| 방향 역전 | `tilt_up`이 `crop_y = max_dy*(1-ease)`이고 `max_dy(t)`는 증가함수라 곱은 0→상승→0으로 역전 (수식으로 재현 확인) | — |
| 이중 H.264 인코딩 | 모션 클립 1차 인코딩(`libx264 -crf 18`) + 자막 번인 시 `render_episode_v2.py:49-60` 2차 인코딩, 총 2회 손실압축 | 미검증(최종 mux 단계 공유) |
| 검증 여부 | Aug26이 ffprobe/mpdecimate로 실측(근접중복 78.5~83.7%) | **실측 없이 "0-Pixel Judder"를 이름에 못박음.** 실제 근접중복률을 측정한 흔적이 없다 |

- `postflight_release.py`에 모션 cadence 검사 함수(`check_decoded_stream_motion_mae`)가 정의돼 있지만 **`verify_postflight()` 본문 어디에서도 호출되지 않는 죽은 코드**다. `motion_diversity_passed`는 release manifest JSON에 이미 들어있는 값을 그대로 읽는 스키마 체크일 뿐, 디코드 프레임에서 직접 계산하지 않는다.
- 최신 빌드 실측: `full-v6-001`(2026-08-29, doodle_seonbi 레거시)은 112샷 평균 9.5초로 25초 상한 초과가 0건 — 이는 **렌더러가 고쳐진 게 아니라 업스트림 샷 플래닝이 짧아져서** 우연히 상한을 벗어난 것이다. `runs/nollam_file/2026-09-08~09/*` 빌드들은 `candidate/motion_clips`가 전부 비어 있어 nollam 프로필에서는 아직 모션 렌더 실측 자체가 불가능하다.

### 1.6 페이싱 커브(nollam_decay_20m)도 "배선 안 된 설계"다

- `config/visual_pacing_profiles.yaml`에 7구간 감쇠 곡선이 실제로 정의돼 있고, `lib/pacing_scheduler.py`가 이 로직을 구현했다.
- 그러나 `pacing_scheduler.py`는 **`tests/test_pacing_scheduler.py`와 `tests/test_nollam_synthetic_e2e.py`에서만 호출되고, 프로덕션 스크립트 어디에서도 import되지 않는다.** 실제 운영 진입점 `plan_narration_shots.py`/`shot_timing.py`의 `plan_shot_timing()`은 여전히 정적 `narration_aligned_hybrid_v1` 프로필을 하드코딩(`shot_timing.py:132`)한다.

---

## 2. "3사 AI 경쟁·교차검증"의 현재 실체 — `tri_model_debate_engine.py` 정밀 해부

사용자가 요청한 "GPT/Gemini/Grok을 경쟁·교차검증 구조로 배치"는 **이미 저장소 안에 유사한 것이 존재한다.** 다만 실제로 열어보면 다음과 같다.

1. **모델 다양성이 가짜다.** `tri_model_llm_bridge.py:49-51`: `default_model_38 = "gemini-2.5-pro"`, `default_model_37 = "gemini-2.5-flash"`, `default_model_36 = "gemini-2.5-flash"` — "Gemini 3.7"과 "Gemini 3.6"은 **동일 모델을 다른 페르소나 이름만 붙여 두 번 호출**한다. 서로 다른 모델이 서로의 사각지대를 잡아내야 하는데, 두 좌석이 사실상 같은 모델이라 독립적인 교차검증 효과가 없다.
2. **GPT/Grok/Claude는 이 엔진에 전혀 연결돼 있지 않다.** 저장소 전체에서 `openai`/`gpt`/`grok`/`xai` 문자열 grep 결과 0건(코드 기준)이다.
3. **API 키가 없으면 100% 하드코딩 텍스트다.** `get_status()`(`tri_model_llm_bridge.py:85-117`)가 `GEMINI_API_KEY` 부재 시 `HYBRID_ARCHIVAL_ENGINE` 모드로 표시하지만, 실제로는 미리 써놓은 한국어 문장을 그대로 반환한다.
4. **API 키가 있어도, 실제로 최종 산출물(`master_1200s_manifest.json`)을 만드는 경로는 LLM을 한 번도 부르지 않는다.** `orchestrate_deep_tri_model_script()`(`tri_model_debate_engine.py:1004-1322`)의 5라운드 중:
   - Round 1 "독립 제안"(`p_38, p_37, p_36`, 1080-1122행)은 `parallel_match` 딕셔너리 값을 f-string에 끼운 **정적 딕셔너리**다. `generate_llm_response()` 호출이 없다.
   - Round 2 "교차비판"(`critiques`, 1140-1145행)은 아예 **고정 한국어 문장**이다(`"Gemini 3.7의 대본 중 '{protagonist}' 관련 민간 전승은..."` 형태로 변수만 채워진다).
   - Round 3 "팩트체크"만 실제 로직(`SentenceHistoricalFactChecker.audit_sentence`)을 호출하지만, 이것도 LLM이 아니라 **정규식 키워드 매칭**이다(`sentence_fact_checker.py:51-` `HISTORICAL_FACT_PATTERNS`). 등록된 패턴은 칭기즈칸 사인설, 산호세 호 인양설 등 **§1.2에서 확인한 4개 전용 소재에 국한**된다. 실제 기획 중인 우주/양자컴퓨팅/지구과학 주제 문장은 이 패턴에 하나도 걸리지 않아 자동으로 Grade A(공인 사실)로 통과한다 — **검증이 아니라 무검증에 가깝다.**
5. **감사 파일이 "합의 점수 98.8/100", "학술적 엄밀성 완벽 검증"이라고 자신 있게 적지만**, 위 4개 사실을 알고 나면 이 점수들도 하드코딩된 상수이거나(`consensus_score: 98.8`, 코드에 고정값), 무검증 통과의 결과다.

**결론:** 이 엔진은 "실패했다"기보다 **한 번도 진짜로 만들어진 적이 없는 프로토타입 UI**에 가깝다. 5라운드짜리 화면 연출은 잘 만들어졌지만 그 뒤에 실제 모델 호출·실제 비평·실제 팩트체크가 거의 없다. 이것이 사용자가 "겨루고 검증한다더니 결과물은 계속 이상하다"고 느끼는 이유의 상당 부분을 설명한다.

---

## 3. 구조적 근본 원인: "선언과 실행의 괴리" + 파이프라인 3중화

이번 조사에서 5개 영역 모두 같은 패턴이 반복됐다.

- YAML/스키마/주석/함수 이름에는 정교한 설계가 있다 (`nollam_decay_20m`, "Claude 4-Step 체인", "Inviolable Rule 3: 0-Pixel Judder", "Tri-Model 만장일치 99.94점").
- 그런데 그것을 실제로 실행하는 production 코드 경로가 없거나, 있어도 테스트에서만 호출되거나, 하드코딩 텍스트로 대체돼 있다.
- 문서(`CLAUDE.md`)는 이 중 가장 오래되고 가장 검증된 경로(①CLI v5/v6)만 "정본"이라 말하지만, 실제로 가장 활발히 수정되는 것은 ②Studio와 ③run_*_pipeline이다.
- git 위생도 이를 방증한다: `human_archive`는 `D:\module\bible`(브랜치 `feat/full-media-pipeline-freeze`, origin 대비 51 커밋 앞섬)의 하위 디렉터리인데, 163개 파일만 추적되고 **500개 이상이 미추적(untracked) 상태**다. R1~R7 수정 파일 대부분(`host_overlay.py`, `shot_timing.py` 관련, config 전체)과 `CLAUDE.md` 자체도 커밋되지 않았다. 최근 30개 커밋은 주로 flow-automation과 human_library_replica 작업이고, Sep2 마스터플랜이 지시한 핵심 수정과는 무관하다.

**이 문서의 Task 0은 이 패턴 자체를 막는 게이트(선언된 기능마다 production 호출자 존재를 자동 검사)를 만드는 것이다.** 그렇지 않으면 이번에 설계하는 GPT/Gemini/Grok 엔진도 같은 운명(정교한 이름의 죽은 코드)을 맞을 위험이 있다.

---

## 4. 대안 비교

### 대안 A — Studio(②)의 tri_model 엔진에 실제 API 호출만 추가

- 장점: 변경 범위가 작다. 이미 있는 5라운드 UI/이벤트 스트리밍을 재사용한다.
- 단점: 모델 다양성 문제(3.7=3.6)가 남고, 팩트체커가 여전히 4개 소재 전용 룰북이라 새 주제에 무력하다. ①의 이미 검증된 계약·QA·재사용 안전장치와 통합되지 않은 채 별도 시스템으로 계속 분기한다.
- 판정: 임시방편. 채택하지 않는다.

### 대안 B — ①(CLI v5/v6)의 계약 아키텍처를 그대로 nollam_file_v1까지 확장하고, 그 위에 `D:\all-manage`의 실전 검증된 Claude/Codex(GPT)/Grok 경쟁·교차검증 엔진을 포팅한다

- 장점: 이미 검증된 fail-closed QA·재사용 안전장치·프롬프트 컴파일러(`aligned_prompt_compiler.py`)를 재사용할 수 있고, 경쟁·교차검증 엔진 자체도 처음부터 설계하지 않고 `D:\all-manage\tools\orchestration\`의 이미 여러 라운드 실전 운용된 코드를 포팅한다(§5.0). Studio GUI는 "죽이지" 않고 이 엔진의 얇은 프런트엔드로 재배선하면 된다(사용자가 이미 써본 화면을 유지).
- 단점: ②의 5라운드 이벤트 스트리밍 UI 코드를 상당 부분 다시 연결해야 하고, all-manage 엔진은 트레이딩 전략 리뷰용으로 설계돼 있어 대본/비주얼 도메인에 맞게 role prompt와 출력 스키마를 새로 써야 한다.
- 판정: **권장안.**

### 대안 C — 세 파이프라인을 병존시키되 문서만 정비

- 장점: 코드 변경이 거의 없다.
- 단점: 근본 문제(가짜 AI 토론, 모션 판터, 대본-이미지 분리)가 전혀 해결되지 않는다.
- 판정: 채택하지 않는다.

---

## 5. 목표 아키텍처: `D:\all-manage`의 실전 엔진을 포팅한 Claude·GPT(Codex)·Grok(+Gemini) 경쟁·교차검증

### 5.0 기존 자산: `D:\all-manage\tools\orchestration\` — 이미 만들어져 있고, 이미 더 엄격하다

사용자 확인 후 `D:\all-manage`(트레이딩 전략 리서치 프로젝트)를 조사한 결과, `tools/orchestration/contract.py` + `run_round.py` + `prompt_assembly.py`에 **Claude(오케스트레이션 세션 자신) / Codex(=GPT, `codex` CLI) / Grok(`grok` CLI)** 3사가 같은 문제를 독립적으로 검토·설계·비평하는 엔진이 이미 구현돼 있고, `reports/orchestration/2026-09-*` 아래 여러 라운드가 실제로 실행된 기록이 남아 있다. 이 엔진은 human_archive의 `tri_model_debate_engine.py`보다 설계가 더 엄격하며, 새로 설계하는 대신 **포팅하는 쪽이 명백히 낫다.** 핵심 설계 원칙(그대로 가져올 것들):

| all-manage 엔진의 원칙 | 무엇을 막는가 | human_archive 적용 |
|---|---|---|
| **"Agreement is not evidence"** — Round 결과를 자동으로 합치거나 투표로 확정하지 않고, 항상 `diverge`로 **불일치를 표로 드러낸다**. 전원 합의도 "검증됐다"가 아니라 "아무도 반박하지 않았다"로만 취급한다. | 현재 `tri_model_debate_engine.py`가 `consensus_score: 98.8` 같은 값을 아무 근거 없이 자신 있게 찍는 문제 | 팩트체크/대본 아웃라인 라운드의 최종 산출물에 "합의 점수" 같은 단일 숫자를 만들지 않는다. 대신 `divergence.md`처럼 불일치를 그대로 노출한다 |
| **`has_contract()`** — 출력에 정해진 `## VERDICT/FINDINGS/NUMBERS/UNCERTAINTY`(또는 설계용 `## HYPOTHESIS/...`) 헤딩이 없으면 "답변 없음"으로 실패 처리. 바이트가 나왔다고 성공으로 세지 않는다 | 현재 엔진이 나레이션 요약 두 문장만 나와도 "완료"로 세는 문제 | 동일한 구조화 계약을 대본/비주얼 브리프/모션 QA 스키마로 각색해 재사용 |
| **`check_independence()`** — 라운드 디렉터리에 먼저 쓰인 답변의 mtime을 나중 참가자가 실행 중 읽을 수 있었는지 타임스탬프로 검사, 오염 가능성을 리포트에 남김 | "독립 제안"이라고 부르지만 사실은 순차 실행이라 뒤 모델이 앞 모델 결과를 참조할 수 있는 은폐된 결함 | 그대로 재사용. Round 1(제안) 단계에 항상 실행 |
| **역할 로테이션** (`assign(rotation)`) — 라운드마다 누가 proposer/adversary/replicator를 맡을지 순환시켜 "한 모델이 항상 초안을 쓰고 다른 모델은 항상 비평만 하는" 구조적 편향을 방지 | 현재 설계 초안에서 Claude를 영구 조정자로 고정하려 했던 것과 같은 함정 | 그대로 재사용. 특정 vendor가 항상 "먼저 쓰는 사람"이 되지 않게 함 |
| **숫자는 문자열이 아니라 허용오차로 비교** (`NUMERIC_TOLERANCE=0.01`) — `-0.131976`과 `-0.1320`을 다른 값이 아니라 같은 값으로 인정 | 사소한 반올림 차이를 전부 "충돌"로 오탐하는 문제 | 씬 duration, 문장 길이, 컷 수 등 수치 비교에 동일하게 적용 |
| **transient 오류만 재시도** (`is_transient`, capacity/rate-limit/timeout 정규식) — 실제 결함은 재시도로 숨기지 않는다 | 일시적 API 오류와 진짜 실패를 구분 못 해 무한 재시도하거나 진짜 실패를 숨기는 문제 | 그대로 재사용 |
| **Claude는 API로 호출하지 않고, 오케스트레이션 세션 자신이 그 역할을 맡는다** (`start`가 Claude용 프롬프트 파일만 써두고 세션이 직접 이어받음) | Anthropic API 키/과금을 별도로 설정할 필요 없이, 이미 실행 중인 Claude Code 세션 자체를 한 좌석으로 활용 | human_archive에서도 동일하게 적용 가능 — 또는 자동화가 필요하면 Claude를 Agent(subagent) 좌석으로 spawn |

**결론:** Task 2(§7)는 새 provider abstraction을 설계하는 게 아니라 **`D:\all-manage\tools\orchestration\{contract.py, prompt_assembly.py, run_round.py}`를 `human_archive/scripts/lib/orchestration/`으로 포팅하고, `AGENTS.md`의 "Hard gates"와 `docs/orchestration/prompts/*.md`에 해당하는 human_archive 버전(채널 정책·금지어·팩트 게이트)을 새로 쓰는 작업**이다.

### 5.1 역할 매핑 (all-manage의 `ROLES`/`DESIGN_ROLES`를 도메인에 맞게 각색)

all-manage는 두 가지 role 세트를 쓴다: 검토용 `(proposer, adversary, replicator)`와 창작용 `(designer, critic)`. human_archive도 태스크 성격에 따라 그대로 나눈다.

| 태스크 | Role 세트 | 참가자(좌석) | 산출물 |
|---|---|---|---|
| **대본 아웃라인/챕터 구조** | `designer` × 3 → `critic` × 3 | Claude, Codex(GPT), Grok — 필요시 Gemini(§5.7) 4번째 | `proposal.{claude,codex,grok}.md` → `critique.*.md` → `divergence.md` |
| **팩트체크(신규 주제, 룰북 밖)** | `proposer/adversary/replicator` | Claude(proposer, claim별 1차 판정), Codex(adversary, 반박·출처 검증), Grok(replicator, 독립 재계산·최신 정보 대조) | `verdict`(SOUND/DEFECTIVE/CANNOT_DETERMINE) + `findings`(P0/P1/P2) + `numbers` + `divergence.md` |
| **씬 시각 브리프 설계** | `designer/critic`, **Gemini를 4번째 참가자로 추가**(§5.7) | Claude+Codex+Grok(서사-이미지 정합성 비평 중심) + Gemini(비전/구도 설계 중심) | 씬별 `focal_subject/action/place/era/camera` 필드 제안 + 교차비평 |
| **모션/영상 QA** | `proposer/adversary/replicator` (비전 입력 포함) | Gemini + GPT(둘 다 비전 가능) + 룰기반 deterministic 검사(pHash/OCR 등 항상 병행) | `visual_semantic_evaluator`(Aug26 §12.6) 인터페이스의 provider adapter로 연결 |

> Role 로테이션 규칙(`assign(rotation)`)을 그대로 가져온다 — 같은 vendor가 매 라운드 항상 같은 역할(예: 항상 Claude가 초안)을 맡지 않도록 라운드 인덱스로 순환시킨다.

### 5.2 3단계 프로토콜 (all-manage의 `propose → critique → diverge`를 그대로 재사용)

```mermaid
flowchart TD
    A[동일한 업스트림 컨텍스트<br/>승인 claim/evidence, 채널 정책, 이전 씬] --> B1[propose: 독립 제안<br/>참가자들이 서로의 출력을 보지 못한 채 동일 문제에 각자 응답<br/>check_independence로 오염 여부 검사]
    B1 --> B2[critique: 교차 비평<br/>모든 제안을 모두가 공격, 자기 것도 예외 없음<br/>구조화 계약(VERDICT/FINDINGS/NUMBERS/UNCERTAINTY)]
    B2 --> B3[diverge: 표로 정리, 병합하지 않음<br/>verdict 불일치 또는 수치 충돌 시 UNRESOLVED]
    B3 --> C{UNRESOLVED?}
    C -->|No| D[구조화 산출물 채택 + 감사 로그]
    C -->|Yes| E[사람 승인 게이트로 escalate<br/>Sep2의 3개 사람 접점 중 하나에 흡수]
```

- **propose:** 참가자 전원에게 **완전히 동일한 문제**(승인된 claim/evidence, 채널 정책, 직전 씬 컨텍스트)를 병렬로 보낸다. `check_independence()`로 한쪽이 다른 쪽이 먼저 쓴 답을 읽었을 가능성을 타임스탬프로 검사하고, 있으면 리포트에 명시한다(조용히 숨기지 않는다).
- **critique:** 모든 제안을 모든 참가자가 공격한다(자기 제안도 예외 없이). `{severity(P0/P1/P2), claim, evidence, impact}` 구조화 계약으로만 응답을 인정한다.
- **diverge:** **병합·합의점수 계산을 하지 않는다.** verdict가 갈리거나(`len(verdicts) > 1`) 수치가 허용오차 밖에서 충돌하면(`conflicting`) 그 라운드는 `UNRESOLVED`다. UNRESOLVED는 이 파이프라인에서 Sep2 §7의 "3개 사람 접점" 중 하나로 흡수한다 — Claude가 임의로 무시하거나 조용히 다수결 처리하지 않는다.

### 5.3 Fail-closed 규칙 (all-manage에서 그대로 가져옴 + human_archive 전용 1건 추가)

1. **`has_contract()` 없이는 "완료"가 아니다.** 정해진 헤딩이 없는 응답은 malformed로 분류하고 `REVIEW_REQUIRED`.
2. **참가자 2곳 미만 성공 시 라운드 전체가 실패다.** all-manage의 `_fan_out`은 실패한 참가자를 `*.FAILED.md`로 남기고, `diverge`의 `absent`/`missing` 집계가 "adversary 없이 내린 판정은 adversarial 결과가 아니다"라고 명시적으로 경고한다 — 이 문구를 그대로 채택한다.
3. **transient 오류만 재시도(최대 1~2회, backoff).** capacity/rate-limit/timeout이 아닌 실패는 재시도하지 않고 즉시 `REVIEW_REQUIRED`.
4. **[human_archive 추가] 시뮬레이션/fixture 모드는 `provenance: "simulated_fixture"`로 표기하고 release 게이트를 자동 차단한다.** all-manage는 로컬 리서치용이라 이 개념이 없지만, human_archive는 실제 채널 발행 게이트가 있으므로 이 표기가 Sep2/Aug26의 fail-closed 원칙과 일치하도록 새로 추가한다.
5. **모든 라운드 원문(prompt/response)을 `assignment.json` + `*.{participant}.md` 원본 그대로 보존한다.** all-manage 그대로.

### 5.4 어디에 적용하는가

| 적용 지점 | 현재 상태 | 이 엔진 적용 후 |
|---|---|---|
| 주제 기획(topic ideation) | Studio의 5개 후보가 전부 하드코딩 딕셔너리 | `propose→critique→diverge`를 거친 실제 3~4자 제안·비평, UNRESOLVED는 사람 접점1로 |
| 대본 아웃라인/챕터 구조 | `historical_parallel_engine`의 4개 소재 전용 뱅크 + generic 폴백 | 참가자 독립 초안 → 교차비평 → `divergence.md`. **모든 주제**에 동일 적용(하드코딩 뱅크 불필요) |
| 팩트체크 | 정규식 룰북(4개 소재 한정) | 룰북은 1차 스크리닝만 담당, 룰북 밖 주제는 `proposer/adversary/replicator` 라운드로 Grade 판정 |
| 씬 시각 브리프 | ①은 양호, ②는 40자 절삭 템플릿 | ②를 폐기하고 ①의 `aligned_prompt_compiler.py` 필드 세트에 대해 `designer/critic` 라운드(Gemini 포함) 추가 |
| 모션/영상 QA(VLM) | Aug26이 제안한 `visual_semantic_evaluator` 인터페이스가 `manual_only`만 구현 | `proposer/adversary/replicator`를 비전 provider(Gemini+GPT) adapter로 연결, 불일치 시 `REVIEW_REQUIRED` |

### 5.5 비용/지연 가드레일

- Sep2 §9의 "$4.5/편" 목표를 지키기 위해, **고빈도 저위험 태스크(씬 100~180개 규모의 1차 드래프트, 중복 탐지)는 라운드 프로토콜을 돌리지 않고 좌석 하나(가장 저렴한 모델)로 처리**하고, **저빈도 고위험 태스크(주제 확정, 챕터 아웃라인, 최종 팩트 판정, 씬 브리프 확정)만 propose→critique→diverge 풀 프로토콜**을 돌린다.
- all-manage의 `DEFAULT_TIMEOUT=1800`, `GROK_MAX_TURNS=80`처럼 실측 기반 타임아웃/턴 예산을 그대로 참고하되, 대본/비주얼 태스크는 트레이딩 리뷰보다 훨씬 짧게 끝나므로 human_archive 전용 값으로 재보정한다(초기값은 all-manage 값을 상한으로 시작해 실측 후 축소).

### 5.6 Gemini(agy)를 4번째 참가자로 추가하는 이유와 방법

all-manage의 3사(Claude/Codex/Grok)에는 Gemini가 없다. 그러나 human_archive는 이미 `lib/visual_brief_provider.py`에서 `agy`/`antigravity` CLI(Gemini 계열)를 호출하고 있어(§1.1), 이 CLI를 **비전/씬 설계 전용 4번째 참가자**로 추가하는 비용이 낮다.

- `tools/orchestration/run_round.py`의 `PARTICIPANTS = ("claude", "codex", "grok")`에 `"gemini"`를 추가하고, `_invoke()`에 `_run_gemini()`를 `visual_brief_provider.py`의 기존 `agy` 호출 패턴(`subprocess.run([agy_cmd, "generate", ...])`)으로 구현한다.
- Gemini는 텍스트 전용 라운드(팩트체크 등)에는 선택적으로만 참여시키고, **씬 시각 브리프/모션 QA처럼 이미지·구도 판단이 중요한 라운드에는 항상 참여**시킨다.
- 4자가 모두 참여하는 라운드에서도 §5.3 규칙 2("2곳 미만 성공 시 실패")는 vendor 4종 기준으로 유지한다.

---

## 6. `human_library_replica`(rank1/rank2 exact clone) 격리 조치 — 사용자 결정 반영

조사 중 `run_human_library_rank2_exact_clone_pipeline.py`(2026-09-15 최종 수정)와 `2026-09-11-human-library-1to1-exact-replication-master-plan.md`를 확인한 결과, 이 파이프라인은:

- "인류의 서재" 채널의 **특정 실제 영상**(`o-x6sIGANPY` 등)을 원본으로 삼아 **대본 문장을 문장 단위로 그대로(verbatim) 복제**한다 — `runs/human_library_replica/rank2_forgotten_civilization/script/master_script_clean.json`의 문장이 `scratch/human_library_top3/rank2_o-x6sIGANPY_full_transcript.txt`와 개행 단위로 일치했다.
- 컷 수(837개)·오디오 길이(샘플 프레임 단위)·프레임레이트(30fps)까지 원본과 동일하게 맞춘다.
- rank1 계획서(`2026-09-11-human-library-1to1-exact-replication-master-plan.md`)는 심지어 **원본 채널의 우측 상단 황금 엠블럼 워터마크**까지 "1:1 필수 산출물로 복원"한다고 명시한다.
- rank1은 이미 문장별 TTS 오디오까지 생성 완료된 상태였다.

사용자는 이를 **"내부 벤치마크 연구용으로만 격리"**하기로 결정했다(원래 의도도 "벤치마크 삼아 해보고 학습" — 배포 목적이 아니었다). 다만 사용자는 그 학습 목적조차 "엉망인 영상"이 나와서 달성하지 못했다고 확인했다 — 이는 §1.5/§2에서 이미 확인한 모션 엔진 버그(전체 구간 cosine easing, 이중 H.264 인코딩)와 대본-이미지 매칭 부실이 nollam Studio·run_human_library_* 계열 전반에 공통으로 영향을 미친다는 방증이다. 즉 Task 4(모션 엔진)·Task 1(대본 생성)의 수정은 프로덕션뿐 아니라 이 내부 연구용 파이프라인의 학습 가치를 회복하는 데도 그대로 적용된다 — 단, 산출물은 여전히 비공개·비발행이다.

이에 따른 조치:

1. **프로덕션 경로에서 완전히 배제한다.** §5의 4자 검증 엔진, §1의 대본/이미지/모션 개선 작업은 `human_library_replica`, `run_human_library_*_exact_clone_pipeline.py`, `run_human_library_*_full_production.py`, `run_san_jose_*`, `run_neanderthal_*`을 대상으로 하지 않는다.
2. **원본 채널 브랜딩 자산(워터마크·엠블럼·HUD 디자인)은 즉시 제거한다.** `2026-09-11-human-library-1to1-exact-replication-master-plan.md` §"브랜딩/HUD 복원" 항목은 철회하고, 관련 자산이 `assets/branding/`에 생성돼 있다면 삭제한다.
3. **verbatim 대본 텍스트를 실제 나레이션/TTS 입력으로 사용하지 않는다.** 이번 조사에서 rank1의 문장별 TTS wav가 이미 생성된 것을 확인했다 — 이 결과물이 어떤 경로로도 실제 채널 업로드용 산출물과 연결되지 않는지 확인하고, 연결돼 있다면 즉시 차단한다.
4. **디렉터리를 물리적으로 분리한다.** `runs/human_library_replica/` → `research/human_library_benchmark_internal_only/`로 이동하고, 최상위에 `DO_NOT_PUBLISH.md`(비공개·비발행 명시)를 둔다. 렌더/발행 스크립트(`release_episode.py`, `postflight_release.py` 등)의 입력 경로 화이트리스트에서 이 디렉터리를 명시적으로 제외하는 가드를 코드에 추가한다(Task 9).
5. **유지할 것:** 컷 길이 분포, phase별 컷 비율, 오디오 러프니스 등 **구조적 메타데이터만** 벤치마크 연구 자료로 남긴다 — 이는 Sep2 §3의 "인류의 서재 30편 실측 데이터"와 같은 성격의 정당한 벤치마킹이며, 원본의 구체적 대사·워터마크·1:1 프레임 매칭과는 구분한다.

---

## 7. 구현 Task 목록

### Task 0 — "선언-실행 괴리" 방지 게이트 + git 위생

**Create**
- `human_archive/scripts/audit_declared_vs_wired.py` — YAML/스키마에 선언된 기능(예: `nollam_decay_20m`, `claude_chain.step_*`)마다 production 진입점(CLAUDE.md에 문서화된 실행 순서 또는 `run_*.py`)에서 실제로 import/호출되는지 정적 분석으로 검사. 호출자가 0건이면 FAIL.
- `human_archive/tests/test_declared_vs_wired.py`

**작업**
1. `pacing_scheduler.py`, `host_overlay.py`의 nollam 가드, `nollam_file_postflight.py` 등 R1~R7 관련 파일을 `git add`로 스테이징하고 커밋한다(500개+ 미추적 파일 중 실제 프로덕션 코드만 선별).
2. `.gitignore`에 `runs/`, `audit/`, `scratch/` 등 산출물 디렉터리를 명시해 미추적 파일 수를 근본적으로 줄인다.
3. `CLAUDE.md`의 미스테이징 수정(+19/-5)을 커밋한다.

**완료 기준:** `git status`에서 `human_archive` 미추적 파일이 산출물 디렉터리 제외 0건. `audit_declared_vs_wired.py`가 CI에서 매 PR마다 실행된다.

### Task 1 — 파이프라인 수렴: nollam_file_v1을 ①CLI v5/v6 계약 위에 이식

**Modify**
- `human_archive/scripts/lib/script_generation.py` (템플릿 경로 하드코딩 제거, profile 기반 선택)
- `human_archive/scripts/generate_verified_script.py`

**작업**
1. `build_prompt_context()`의 `seonbi_script_prompt.j2` 하드코딩을 `channel_profiles.yaml`의 `script_template_path`를 읽도록 바꾼다.
2. nollam_file_v1 프로필 선택 시 `nollam_script_prompt_v3.j2`가 실제로 렌더링되는지 회귀 테스트로 고정한다.
3. `aligned_prompt_compiler.py`의 `compile_nollam_prompt()`(이미 존재, §1.3)를 Studio 경로 대신 nollam 운영 진입점으로 승격한다.

**완료 기준:** nollam_file_v1 빌드의 `script_candidate.json`이 nollam phase 구조(`phase_1_hook`~`phase_5_epilogue`)와 `visual_mode` 필드를 갖는다.

### Task 2 — `D:\all-manage` 오케스트레이션 엔진을 human_archive로 포팅 (§5 설계 구현)

**Port (신규 작성이 아니라 이식)**
- `D:\all-manage\tools\orchestration\contract.py` → `human_archive/scripts/lib/orchestration/contract.py` (거의 그대로, `DESIGN_SECTION`/`SECTION` 정규식은 도메인 무관하므로 변경 최소화)
- `D:\all-manage\tools\orchestration\run_round.py` → `human_archive/scripts/run_consensus_round.py` (`PARTICIPANTS`에 `"gemini"` 추가 — §5.6, `ROUNDS` 경로를 `human_archive/audit/orchestration/`으로 변경)
- `D:\all-manage\tools\orchestration\prompt_assembly.py` → `human_archive/scripts/lib/orchestration/prompt_assembly.py` (`AGENTS.md`의 "Hard gates" 참조를 human_archive의 채널 정책 파일로 교체)

**Create (도메인 전용 신규 작성)**
- `human_archive/docs/orchestration/prompts/{proposer,adversary,replicator,designer,critic}.md` — 대본/팩트체크/비주얼 브리프 태스크에 맞는 role 지시문 (all-manage의 트레이딩 전용 문구를 대체)
- `human_archive/docs/orchestration/hard_gates.md` (또는 `CLAUDE.md` 내 전용 섹션) — `prompt_assembly.assemble()`이 참조할 "Hard gates" 목록: 채널 정책(호스트 0%, era 필수, must_not 등), 팩트 등급 기준, 재사용 규칙 등을 번호 목록으로 명시. `hard_gates()`가 5개 미만이면 예외를 던지는 all-manage의 안전장치(`GatesNotFound`)를 그대로 유지
- `human_archive/scripts/lib/orchestration/_run_gemini.py` — §5.6의 Gemini(agy CLI) 참가자 어댑터
- `human_archive/tests/test_orchestration_contract.py`, `test_orchestration_independence.py` — all-manage의 `tests/orchestration/test_contract.py`, `test_run_round.py`를 참고해 이식

**Quarantine**
- `human_archive/scripts/tri_model_debate_engine.py`, `tri_model_llm_bridge.py` — §2에서 확인한 하드코딩 경로를 `run_consensus_round.py`로 완전히 교체한 뒤, 기존 Studio UI 이벤트 스트리밍만 재사용하도록 얇은 어댑터로 축소

**완료 기준:** all-manage의 `tests/orchestration/`과 동등한 커버리지(contract 파싱, `has_contract`, `check_independence`, 재시도/transient 판정)가 human_archive에도 있고, API 키/CLI 부재 시 산출물에 `provenance: "simulated_fixture"`가 남아 release 게이트가 이를 차단한다(§5.3 규칙 4, all-manage에는 없는 human_archive 전용 추가 규칙).

### Task 3 — 팩트체크 이중화 (룰북 1차 + 2-vendor 합의 최종) — ✅ 완료 (2026-09-15, 커밋 `276ab76`)

**Modify**
- `human_archive/scripts/sentence_fact_checker.py` (1차 스크리닝으로 역할 축소, 코드 변경 없음 — `status: VERIFIED_FACT`가 이미 "무검증 기본값"의 정확한 시그널이라 이 값을 트리거로 사용)
- `human_archive/scripts/run_consensus_round.py`에 `escalate_claim()` 신설 — Claude 좌석 없는 codex+grok 2자 무인 에스컬레이션
- `human_archive/scripts/tri_model_debate_engine.py`의 `execute_fact_check()` 재작성 — `VERIFIED_FACT` 기본값 문장을 claim_id 단위로 dedup해 에스컬레이션, 불일치/실패는 신규 `REVIEW_REQUIRED` 등급(텍스트 미변경, 사람 검토 대기)으로 처리. 하드코딩됐던 `critique_msg`와 `final_grade`("A+ 학술적 엄밀성 완벽 검증")도 실제 에스컬레이션 결과 기반 정직한 요약으로 교체.

**완료 기준 검증:** 8개 통합 테스트(mock) + 7개 단위 테스트, 81/81 통과. 실제 라이브 검증도 완료 — EP02 `CLM-JH-001`을 실제 codex+grok 라운드에 돌려 등급을 A→B로 하향 조정하고 문장 반복 결함을 실제로 잡아냈다(`audit/orchestration/2026-09-15-ep02-clm-jh-001-smoketest/`).

**추가 발견(사용자 제공 `C:\Users\shs\Downloads\tf\portable-setup.md` 반영):** codex의 `-m` 플래그가 항상 존중되지 않아 `~/.codex/config.toml`의 값으로 조용히 대체될 수 있다는 실전 사례(같은 날 4개 라운드가 의도한 `gpt-5.6-luna` 대신 `gpt-6-astra`로 돎)를 반영해 `check_model_drift()`를 추가, stderr의 실제 모델 배너를 신뢰하도록 했다. agy(진짜 Antigravity CLI, `~/AppData/Local/agy/bin/agy.exe`)는 이 PC에 설치돼 있지 않아(npm의 구버전 `gemini-cli` 래퍼만 있고 무료 티어가 폐지됨) 사용자 결정에 따라 당분간 배선하지 않음 — `_run_gemini` 확장 지점은 코드에 남겨둠.

### Task 4 — 모션 엔진 근본 수정 (Aug26 Task 8 설계를 현재 파일 2곳에 동시 적용) — ✅ 핵심 완료 (2026-09-15, 커밋 `4c138fc`)

**Create**
- `human_archive/scripts/lib/motion_engine_v3.py` — `ease_ramp_cruise()`(시작/끝 15% ramp + 등속 cruise, velocity-continuous), `motion_intent` 기반 단일 트라젝토리 공식(named preset 완전 폐기), duration-aware 확대폭, 원본 해상도 그대로 샘플링, FFV1/MKV 무손실 기본값
- `human_archive/scripts/build_motion_clips_v3.py` — v2와 동일한 `--build`/`--limit` CLI, `motion_intent` 필드 우선·키워드 분류기·`static` 폴백(라운드로빈 완전 제거)
- `human_archive/tests/test_motion_cadence.py` — **실제** 고주파 체커보드 이미지를 렌더링해 ffmpeg `mpdecimate`로 근접중복률 실측(mock 아님)

**Modify**
- motion map(ID 키 매칭) 자체를 폐기하고 `motion_intent` 필드 기반으로 전환(Aug26 §8.2 방식 채택)
- `render_episode_v2.py` — 모션 클립이 `.mkv`(FFV1 무손실)면 그대로 concat, `.mp4`(레거시)와 섞이면 즉시 실패. 최종 mux가 유일한 손실 인코딩이 됨

**Quarantine**
- `human_archive/scripts/build_motion_clips_v2.py`, `human_archive/scripts/smooth_subpixel_motion_engine.py` — 상단에 폐기 고지 추가, 코드는 감사용으로 보존

**완료 기준 검증:** 26개 단위 테스트(단조성, 방향역전 회귀, preset 중복 회귀, duration-aware 확대폭) + 4개 실측 테스트, 116/116 통과. **실측 근접중복률**: push_in 2.7%, pan_right/tilt_up 0.0% (레거시 실측 78~84% 대비). `tilt_up` 방향 역전은 축이 두 고정값 사이 단조 보간으로만 정의되어 구조적으로 재발 불가능.

**미완료(후속 과제로 명시):** `run_san_jose_full_pipeline.py`, `run_san_jose_20min_flow_production.py`, `run_neanderthal_full_pipeline.py` 3개 정당한 프로덕션 스크립트가 아직 `smooth_subpixel_motion_engine.py`를 직접 호출 중 — v3로 전환 필요. **흥미로운 발견**: `motion_engine_v3.py`/`build_motion_clips_v3.py`라는 이름의 파일이 이미 (다른 세션이) 만들어 두었으나, 내용을 열어보니 같은 버그 있는 `smooth_subpixel_motion_engine.py`로 그대로 포워딩하는 얇은 어댑터였고 `build_motion_clips_v3.py`는 여전히 `[idx % 3]` 라운드로빈과 비-무손실 H.264였다 — 이번 진단 전체를 관통하는 "이름은 v3인데 내용은 안 고쳐진" 패턴이 모션 엔진 자리에도 그대로 있었다. 이번 커밋으로 실제 수정본으로 교체했다.

### Task 5 — `postflight_release.py`의 죽은 모션 게이트를 실제로 연결 — ✅ 완료 (2026-09-15, 커밋 `7587ed3`)

**Modify**
- `human_archive/scripts/postflight_release.py` — `check_decoded_stream_motion_mae()`를 `verify_postflight()` 본문에서 실제로 호출
- `human_archive/scripts/lib/build_manifest.py`, `generate_release_manifest_v4/v5` — 실제 호출자 연결(현재 정의만 있고 호출 0건)

**완료 기준 검증:** `check_decoded_stream_motion_mae()`와 동일한 루마·슬라이딩윈도우 MAE 수식을 스트리밍으로 재구현한 `measure_decoded_video_motion_diversity()`를 신설해 `verify_postflight()`가 모든 v4/v5 release에서 실제 디코드 영상으로 매번 새로 측정하도록 배선했다(메모리에 전체 프레임을 올리지 않고 윈도 크기만큼만 버퍼링 — 20분 릴리즈는 약 3만 프레임). 디코드 실패는 조용히 통과시키지 않고 즉시 fail-closed 처리한다. `generate_release_manifest_v4/v5`의 `motion_diversity_passed`도 무조건 `True` 기본값 대신 실측값을 기본값으로 사용하도록 바꿨다. 신규 테스트 4개(매니페스트가 거짓으로 PASS를 주장해도 실측이 release를 차단하는지, 측정이 통과하면 차단하지 않는지, 매니페스트 생성기가 더 이상 `True`를 무조건 찍지 않는지, 신규 스트리밍 구현이 실제 ffmpeg 인코딩 정지/모션 클립에서 기존에 검증된 배치 버전과 같은 방향으로 판정하는지) + 기존 postflight/motion 게이트 스위트 전체 통과.

**부수 발견:** 검증 중 `test_human_library_exact_clone_gate_suite.py::test_gate_5_branding_and_hud_assets`가 이미 깨져 있는 것을 발견 — Task 9(88e4242)가 §6 결정에 따라 원본 채널 브랜딩 자산을 의도적으로 삭제했는데, 이 테스트는 여전히 그 자산이 존재해야 한다고 단언한다. Task 5와 무관해 별도 백그라운드 작업으로 분리했다(`task_ffaa66ff`).

### Task 6 — fps 정책 단일화 — ✅ 완료 (2026-09-15, 커밋 `222d747`)

**Modify**
- `human_archive/scripts/lib/cinematic_editing_director.py:9` — "30fps normalization" 선언을 채널 프로필에서 읽도록 변경
- 25fps(Human Archive)와 30fps(향후 별도 profile 실험) 중 무엇이 nollam_file_v1의 정본인지 §8 D1로 확정

**완료 기준 검증:** `config/channel_profiles.yaml`은 이미 3개 프로필(`nollam_file_v1`/`doodle_seonbi_v1`/`human_archive_cinematic_v1`) 전부 `fps: 25`로 선언돼 있었고 "30fps 실험 프로필"은 애초에 존재하지 않았다 — D1 확정대로 25fps가 유일한 정본. `cinematic_editing_director.py`의 `default_fps=30` 하드코딩만 이 설정과 독립적으로 어긋나 있었는데, 단순 주석이 아니라 `normalize_clip()`의 실제 ffmpeg `-vf fps=` 필터에 그대로 들어가는 진짜 인코딩 파라미터였다(`run_neanderthal_full_pipeline.py` 등 정당한 프로덕션 스크립트가 기본값으로 30fps 인코딩 중이었음). `_resolve_default_fps()`를 신설해 `channel_profiles.yaml`에서 읽게 하고 읽기 실패 시에만 25로 폴백하도록 수정. `build_cinematic_master_pipeline.py`의 `--fps` CLI 기본값도 30→25로 정정. 신규 테스트 5개 통과.

### Task 7 — pacing_scheduler.py 실배선

**Modify**
- `human_archive/scripts/plan_narration_shots.py`, `human_archive/scripts/lib/shot_timing.py` — `narration_aligned_hybrid_v1` 하드코딩을 제거하고 채널 프로필의 `pacing_profile_id`(`nollam_decay_20m` 등)를 읽어 `pacing_scheduler.py`를 호출

**완료 기준:** nollam_file_v1 빌드의 실제 샷 길이 분포가 Sep2 §4의 7구간 감쇠 곡선과 일치한다(현재는 테스트에서만 확인 가능).

### Task 8 — 씬 시각 브리프 교차검증 확장 (§5.5)

**Modify**
- `human_archive/scripts/generate_visual_briefs.py`, `lib/aligned_prompt_compiler.py` — Gemini Pro(설계)+GPT(비평)+Grok(진부함/반복 체크) 3자 교차검증을 씬 브리프 생성에 연결

### Task 9 — `human_library_replica` 격리 (§6 실행)

**작업**
1. `runs/human_library_replica/` → `research/human_library_benchmark_internal_only/` 이동, `DO_NOT_PUBLISH.md` 추가
2. `release_episode.py`, `postflight_release.py` 등 발행 관련 스크립트에 입력 경로 화이트리스트 가드 추가(이 디렉터리 경로가 인자로 들어오면 즉시 실패)
3. 원본 채널 브랜딩 자산 삭제, rank1 TTS 산출물이 실제 발행 경로와 연결되지 않았는지 확인

---

## 8. 결정 사항 표

| # | 결정 항목 | 권장 정본(기본값) | 대안 | 영향 파일 |
|---|---|---|---|---|
| **D1** | **fps 정본** | **25fps** (Sep2/CLAUDE.md 기존 결정 유지) | 30fps(`cinematic_editing_director.py` 새 선언) | `cinematic_editing_director.py`, `postflight_release.py` |
| **D2** | **프로덕션 파이프라인** | **①CLI v5/v6 계약을 nollam_file_v1까지 확장**(대안 B, 사용자 확정) | ②Studio 자체 강화(대안 A) | 전체 |
| **D3** | **엔진을 새로 설계할지, `D:\all-manage`를 포팅할지** | **포팅**(§5.0) — 이미 실전 검증됨, "합의는 증거가 아니다" 등 더 엄격한 원칙 보유 | 처음부터 새로 설계 | Task 2 |
| **D4** | **라운드 적용 범위 1차 파일럿** | **팩트체크 + 씬 시각 브리프**부터 (비용/리스크가 크고 §1.3에서 이미 부분 검증된 영역과 인접) | 주제 기획부터 전면 적용 | Task 2, 3, 8 |
| **D5** | **Studio GUI(`studio_gui_server.py`) 존치 여부** | **유지, 단 백엔드를 `run_consensus_round.py`로 교체**(사용자가 이미 사용 중인 화면이므로, 사용자 확정) | 폐기하고 CLI 전용으로 전환 | `studio_gui_server.py` |
| **D6** | **모션 엔진 통합 대상** | **`motion_engine_v3.py` 신설, 기존 2개 엔진 모두 격리** | `smooth_subpixel_motion_engine.py`만 부분 수정 | Task 4 |
| **D7** | **human_library_replica 처리** | **내부 벤치마크 연구용으로만 격리**(사용자 확정) | — | Task 9 |
| **D8** | **UNRESOLVED 라운드 처리 기준** | **verdict 불일치 또는 수치 충돌(허용오차 밖) 시 무조건 사람 승인 접점으로 escalate**(all-manage 원칙 그대로) | 2곳 합의 시 자동 확정(더 빠르지만 all-manage 철학과 배치) | Task 2, 3 |
| **D9** | **Gemini(agy)를 몇 번째 참가자로, 어느 라운드에** | **4번째 참가자, 비전/씬 브리프 라운드에는 항상 참여, 텍스트 전용 라운드는 선택적**(§5.6) | 모든 라운드에 상시 4자 참여(비용 증가) | `run_consensus_round.py` |

---

## 9. 우선순위와 체크포인트

### P0 — 안전·위생 (1~2일)
Task 0(git/게이트), Task 9(human_library_replica 격리)를 먼저 한다. 이 두 가지는 다른 모든 작업의 전제조건이다.

**Checkpoint 1:** git 위생 보고서, replica 격리 완료 확인, `DO_NOT_PUBLISH.md` 존재.

### P1 — 파이프라인 수렴 + 4자 엔진 코어 (5~7일)
Task 1, 2를 수행한다. 먼저 팩트체크(Task 3, 상대적으로 스키마가 단순)에 4자 엔진을 시범 적용한다.

**Checkpoint 2:** D8 결정에 따른 팩트체크 합의 로직이 실제 API 호출로 동작하는 것을 신규 주제(4개 전용 소재 밖) 1건으로 시연.

### P2 — 씬 브리프·모션 근본 수정 (7~10일)
Task 4, 5, 6, 7, 8을 수행한다.

**Checkpoint 3:** HA002 동일 60~90초 구간으로 legacy 모션 vs v3 모션 A/B, mpdecimate 실측 비교(Aug26 Task 10 방식 재사용).

### P3 — 전체 파일럿 릴리스
nollam_file_v1 신규 에피소드 1편을 P1~P2 전부 적용한 상태로 끝까지 생성.

**Checkpoint 4:** 4자 감사 로그(구조화 JSON) → 팩트체크 합의 기록 → 씬 브리프 교차검증 기록 → 모션 QA 실측치 → 사람 최종 승인 순으로 검토.

---

## 10. 위험과 완화책

| 위험 | 완화 |
|---|---|
| GPT/Grok API 계약·요금·rate limit 미확보 상태에서 설계만 앞섬 | Task 2를 "provider adapter 인터페이스 우선 구현 + 1곳은 실제 키로 검증, 나머지는 mock으로 계약 테스트"부터 시작 |
| 4자 병렬 호출로 인한 지연/비용 증가 | §5.5 가드레일(고빈도 태스크는 좌석 1개 단독 처리) + 저빈도 태스크만 propose→critique→diverge 풀 프로토콜 |
| Studio GUI 백엔드 교체 중 사용자가 쓰던 화면이 일시적으로 깨짐 | Task 2를 feature flag로 감싸 구버전 경로와 병행 운영 후 전환 |
| 모션 엔진 교체가 기존 승인된 빌드의 재현성을 깨뜨림 | v3를 새 build ID에서만 사용, 기존 `full-v6-001` 등은 read-only 보존(Aug26 원칙 유지) |
| human_library_replica 격리 후에도 다른 스크립트가 그 경로를 참조 | Task 9의 화이트리스트 가드를 `release_episode.py` 진입점에 강제해 우회 불가능하게 함 |
| "선언-실행 괴리" 게이트(Task 0)가 오탐으로 정상 코드를 막음 | 초기에는 warning만 내고 CI hard-fail은 2주 유예 후 전환 |

---

## 11. 최종 합격 기준

### 구조
- `audit_declared_vs_wired.py`가 선언된 기능(YAML/스키마) 대비 production 호출자 0건인 항목을 0건으로 보고
- `human_archive` git 미추적 파일 0건(산출물 디렉터리 제외)

### 대본
- nollam_file_v1 빌드가 실제로 nollam phase 구조로 생성됨(Task 1)
- 4개 전용 소재 밖 주제도 generic 템플릿이 아니라 4자 엔진의 실제 응답으로 생성됨

### 대본-이미지 매칭
- ①에서 이미 검증된 5축 의미 대응 품질을 nollam_file_v1에도 동일하게 적용(§1.3 기준 유지)
- Studio의 40자 절삭 템플릿(§1.3) 완전 제거

### 팩트체크
- 신규 주제 문장의 Grade 판정이 2곳 이상 vendor 합의를 거친 기록을 가짐(하드코딩 룰북 단독 판정 0건)

### 모션
- legacy 2개 엔진(`build_motion_clips_v2.py`, `smooth_subpixel_motion_engine.py`) 격리, `motion_engine_v3.py`로 통합
- 근접중복률·방향역전·이중인코딩 Aug26 최종 합격 기준 충족
- `postflight_release.py`의 모션 QA가 실제로 release를 차단할 수 있음(회귀 테스트로 고정)

### 경쟁·교차검증 엔진 (all-manage 포팅)
- `has_contract()` 없는 응답이 "완료"로 집계된 사례 0건
- API/CLI 실패 시 자동 PASS/정적 템플릿 대체 0건 — 전부 `REVIEW_REQUIRED` 또는 `UNRESOLVED`
- `check_independence()`가 오염 가능성을 검출한 라운드는 전부 로그에 기록됨(조용히 통과 0건)
- verdict 불일치 또는 수치 충돌(허용오차 밖) 라운드가 사람 승인 없이 최종 산출물로 채택된 사례 0건

### human_library_replica
- 프로덕션 발행 경로에서 물리적으로 분리, 원본 채널 브랜딩 자산 제거 완료
