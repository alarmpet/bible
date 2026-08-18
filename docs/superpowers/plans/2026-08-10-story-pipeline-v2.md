# Story Pipeline v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** `계획서_주제_대본_다양성_품질_강화.md` v2.0의 P0~P2를 실제 현대극 생성 파이프라인의 검증 코드, 설정, 템플릿, CLI 및 운영 문서로 구현한다.

**Architecture:** `modern/story_quality.py`가 텍스트·계약·주제카드의 순수 검증 함수들을 제공하고, `modern/scripts/audit_story_quality.py`가 파일 입출력 경계를 담당한다. 사람이 편집하는 정책은 `modern/config/*.yaml`, 작품별 산출물 형식은 `modern/templates/*`에 두며 기존 `checks.py`는 호환 API를 재노출한다.

**Tech Stack:** Python 3.14, stdlib `unittest`, PyYAML 6.x, Markdown/YAML/JSON.

## Global Constraints

- 기존 `modern/runs/*` 산출물은 보존한다.
- 검증되지 않은 사연은 실화로 표시하지 않는다.
- 정확 반복 패딩은 자동 보정하지 않고 `INSUFFICIENT_STORY_MATERIAL`로 실패한다.
- 기본 분량은 100분 고정이 아니라 `quick`, `standard`, `deep`, `special`, `anthology` 중 명시한다.
- 동일 비주제 문장 3회 이상과 3문장 블록 재등장은 BLOCK이다.
- Git 저장소가 아니므로 커밋 단계는 생략하고 각 작업의 테스트 로그로 체크포인트를 대신한다.

---

### Task 1: 반복문장과 부족한 서사 재료 하드 게이트

**Files:**
- Create: `modern/story_quality.py`
- Create: `modern/tests/test_story_quality.py`
- Modify: `modern/checks.py`

**Interfaces:**
- Produces: `check_filler_repetition(text, allowlist=(), warn_ratio=0.90, block_ratio=0.80) -> dict`
- Produces: `require_story_material(text, minimum_chars) -> None`; 부족하면 `InsufficientStoryMaterial` 발생.

- [x] **Step 1: Write failing tests**

```python
def test_blocks_exact_sentence_repeated_three_times():
    report = check_filler_repetition("복도가 조용했다. " * 3)
    self.assertFalse(report["ok"])
    self.assertIn("FILLER_REPEAT_BLOCK", report["blocks"][0])

def test_rejects_material_shorter_than_required():
    with self.assertRaises(InsufficientStoryMaterial):
        require_story_material("짧은 원고", 100)
```

- [x] **Step 2: Run RED**

Run: `python -m unittest modern.tests.test_story_quality -v`  
Expected: import failure because `modern.story_quality` does not exist.

- [x] **Step 3: Implement minimal functions and compatibility imports**

Implement sentence splitting, allowlist exclusion, exact-repeat grouping, repeated 3-sentence windows, unique ratio warning/block, and minimum length exception. Re-export the two functions from `modern/checks.py`.

- [x] **Step 4: Run GREEN**

Run: `python -m unittest modern.tests.test_story_quality -v`  
Expected: all Task 1 tests pass.

### Task 2: 분량·실화성 프로젝트 계약

**Files:**
- Create: `modern/config/duration_matrix.yaml`
- Create: `modern/config/truth_modes.yaml`
- Create: `modern/config/qa_thresholds.yaml`
- Create: `modern/templates/source_packet.md`
- Create: `modern/templates/project_contract.yaml`
- Modify: `modern/story_quality.py`
- Modify: `modern/tests/test_story_quality.py`

**Interfaces:**
- Produces: `load_yaml(path) -> dict`
- Produces: `validate_project_contract(contract, source_packet=None) -> dict`
- Produces: `duration_bounds(config, tier) -> tuple[int, int]`

- [x] **Step 1: Write failing contract tests**

Test that missing `truth_mode`, missing fiction disclosure, unsupported duration tier, and L1 without a completed source packet block; test that `FICTION_REALISTIC` with disclosure passes.

- [x] **Step 2: Run RED**

Run: `python -m unittest modern.tests.test_story_quality.ProjectContractTests -v`  
Expected: missing validator functions.

- [x] **Step 3: Add YAML policies and minimal validators**

Duration tiers must be `15~25`, `25~45`, `45~70`, `80~120`, and anthology total `80~120`. Truth modes must be the five names from the v2 plan. L1 source packets require nonempty core claims, source URLs, review status, and consent state.

- [x] **Step 4: Run GREEN**

Run: `python -m unittest modern.tests.test_story_quality.ProjectContractTests -v`.

### Task 3: 콘텐츠 레인·주제카드·포트폴리오 다양성

**Files:**
- Create: `modern/config/content_lanes.yaml`
- Create: `modern/templates/topic_card.yaml`
- Create: `modern/templates/story_bible.yaml`
- Create: `modern/templates/clue_ledger.yaml`
- Create: `modern/templates/qa_report.json`
- Create: `modern/memory/portfolio_state.json`
- Modify: `modern/story_quality.py`
- Modify: `modern/tests/test_story_quality.py`

**Interfaces:**
- Produces: `validate_topic_cards(cards, expected_count=8) -> dict`
- Produces: `audit_portfolio(episodes) -> dict`
- Produces: `validate_clue_ledger(project_contract, clues) -> dict`

- [x] **Step 1: Write failing tests**

Cover exactly eight cards, at least four represented lanes, max two repeated protagonist roles, five-lane portfolio rows, no three consecutive identical `pov + chronology`, and three clues per L3 twist.

- [x] **Step 2: Run RED**

Run: `python -m unittest modern.tests.test_story_quality.DiversityContractTests -v`.

- [x] **Step 3: Implement validators and templates**

Return reports with stable keys `ok`, `blocks`, `warns`, and `measures`. Similarity thresholds remain warnings; categorical duplicate rules provide deterministic blocks.

- [x] **Step 4: Run GREEN**

Run: `python -m unittest modern.tests.test_story_quality.DiversityContractTests -v`.

### Task 4: 실제 QA CLI와 smoke_g4 회귀 방지

**Files:**
- Create: `modern/scripts/audit_story_quality.py`
- Create: `modern/tests/test_audit_story_quality_cli.py`
- Modify: `modern/runs/smoke_g4/build_chapters.py`

**Interfaces:**
- CLI: `python modern/scripts/audit_story_quality.py --text PATH [--contract PATH] [--source-packet PATH] [--output PATH]`
- Exit `0` when report `ok=true`, exit `2` when any block exists.

- [x] **Step 1: Write CLI failing tests**

Use temporary files and subprocess. A clean fixture must return 0 and valid JSON; three repeated sentences must return 2 and include `FILLER_REPEAT_BLOCK`.

- [x] **Step 2: Run RED**

Run: `python -m unittest modern.tests.test_audit_story_quality_cli -v`.

- [x] **Step 3: Implement CLI and remove cyclic expansion**

The CLI calls real validators. Replace `smoke_g4` cyclic `expand()` and final while-loop with `require_story_material`; do not mutate existing `final.txt`.

- [x] **Step 4: Run GREEN and audit current smoke outputs**

Run clean CLI fixtures, then run the audit on `modern/runs/smoke_g1/final.txt` and `modern/runs/smoke_g4/final.txt`. Expected: g4 exits 2 for repetition; g1 has no exact-repeat block after allowlist/normalization rules.

### Task 5: 프롬프트와 운영 문서 통합

**Files:**
- Modify: `modern/v12_modern_main_SONNET.md`
- Modify: `modern/duration_default.md`
- Modify: `modern/README.md`
- Modify: `modern/scripts.md`
- Modify: `modern/부록_양식.md`

**Interfaces:**
- Consumes: configuration and template paths created in Tasks 1~4.
- Produces: one documented workflow from portfolio audit through analytics feedback.

- [x] **Step 1: Update human-facing contracts**

Document the five lanes, truth gate, 8-card selection, Execution DNA, variable duration, pilot gate, filler block, and CLI commands. Remove statements that call 100 minutes the unconditional default or mark smoke_g4 as passed.

- [x] **Step 2: Run documentation consistency audit**

Run a script that checks every referenced local path exists, Markdown fences are balanced, old unconditional `100분 기본` phrases are absent from active docs, and UTF-8 decoding is strict.

### Task 6: Full regression and acceptance verification

**Files:**
- Modify only if a failing test proves a defect in the new implementation.

- [x] **Step 1: Run all unit tests**

Run: `python -m unittest discover -s modern/tests -v`.

- [x] **Step 2: Run legacy self-test**

Run: `python modern/checks.py`.

- [x] **Step 3: Run CLI regression**

Audit clean fixture, smoke_g1, and smoke_g4; confirm clean/g1 policy result and g4 repeat block.

- [x] **Step 4: Review against v2 spec**

Confirm the implementation covers truth modes, five lanes, 15 sequence IDs in documentation/templates, 8-card validation, character/story/clue templates, duration tiers, filler block, CLI, and portfolio rules. Record any P2 analytics automation not implemented as an explicit remaining item rather than claiming it complete.

---

## Execution Result

- 로컬 구현·설정·템플릿·CLI·문서 통합과 회귀 검증 완료.
- 신규 단위/통합 테스트 29개 통과.
- `smoke_g1` QA 통과, 기존 `smoke_g4`는 반복 패딩 회귀 표본으로 정상 차단.

## Remaining External Integration

- [ ] YouTube Analytics 인증 연결 후 `analytics/analytics_log.csv` 자동 수집.
- [ ] 같은 레인·길이 표본 3편 이상 축적 후 유지율 기준선과 유사도 임계치 보정.
- [ ] 운영 스케줄러가 정해지면 최근 20편 월간 포트폴리오 감사 자동 실행.
