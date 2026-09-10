

# channel github-longform

## summary
2026-09-02 기준 GitHub에서 Claude/LLM 기반 장편 텍스트 생성 오픈소스 22개를 실제로 열어(README·핵심 스크립트·SKILL.md·GitHub API) 조사했다. 결론: (1) 활발하고 우리와 구조가 가장 가까운 것은 NousResearch/autonovel(1,537★, Claude Sonnet 4.6 작성·Opus 4.6 심사, 기계적 slop 스코어+LLM 심사 이중 게이트, Elo 토너먼트, 4-페르소나 리더 패널, adversarial cut 패스)과 zenstory-ai/oh-story-claudecode(6,391★, 2026-09-02 커밋, Claude Code/Antigravity/Codex 스킬팩, ≤12KB 고정 7칸 핫컨텍스트 카드 + 프롬프트에 넣지 않는 _tracking-state.json + 히트작 역분석 리듬/감정 모듈 라이브러리 + 훅 기반 차단 검증)이다. (2) '세계관 바이블(읽기 전용) + 파생 상태 카드(장마다 갱신) + 이전 장 꼬리(tail) + 다음 장 아웃라인 창'이 사실상 표준 컨텍스트 구성법이며, 요약 메모리(RecurrentGPT)·엔티티 시트(story-skills continuity/state.md)·결정론적 검증 CLI(story continuity)가 일관성 유지의 3축이다. (3) 반복·패딩 방지는 '단어 티어별 금지어+문장길이 변동계수+접속부사 비율' 같은 기계 검사와 '삭제 후보 JSON'(autonovel adversarial_edit) 및 '분량 미달 시 자동 패딩 금지, 사용자에게 보고'(oh-story) 규칙으로 처리한다. (4) 구조화 출력은 심사·상태 파일(JSON)에는 널리 쓰이나 본문 생성은 대부분 plain markdown이다(우리 JSON Schema 검증 방식이 더 엄격함). (5) 다중 후보+심사는 autonovel(Swiss-Elo, Opus 심판)과 NovelWithLLMs(온도 0.4~0.8로 5~10개 생성, 사람 선택)만 실제 구현. (6) Anthropic Cookbook의 evaluator-optimizer(PASS/NEEDS_IMPROVEMENT/FAIL + 이전 시도·피드백 누적 전달)와 claude-code-action(PR 리뷰 자동화)은 우리 검증·승인 단계에 직접 이식 가능하나, Claude Engineer는 코드 도구 생성용이며 2024-12 이후 커밋이 없어 관련성이 낮다. (7) 조사한 프로젝트는 거의 소설용이라 사료 claim 근거 연결·한국어 문장길이(중앙값 28자)·TTS 문장 단위 출력은 아무도 다루지 않는다 — 비소설 근거 연결은 Stanford STORM(31.2k★)의 '관점 유도 질문→아웃라인→인용 포함 섹션 작성' 패턴이 유일한 참고점이다.

## items

### NousResearch/autonovel (Hermes Agent 자율 소설 파이프라인)
- url: https://github.com/NousResearch/autonovel
- what: 시드 컨셉→세계관(gen_world.py)·인물(gen_characters.py)·아웃라인(gen_outline.py)·보이스 지문(voice_fingerprint.py)·canon(gen_canon.py) 5개 층을 만들고 foundation_score>7.5가 될 때까지 반복, 이후 draft_chapter.py로 장을 순차 작성(score>6.0 통과, 미달 시 재작성), adversarial_edit.py(삭제 후보)·reader_panel.py(4-페르소나)·gen_revision.py로 자동 퇴고(plateau 감지로 종료), 마지막에 Opus 이중 페르소나(문학 비평가/소설 교수) 리뷰 루프. 첫 결과물 19장 79,456단어.
- pattern: 컨텍스트 구성: draft_chapter.py는 voice.md + world.md + characters.md + 해당 장 아웃라인(정규식 추출) + 다음 장 아웃라인 앞 ~10줄 + 직전 장 마지막 2,000자(prev_tail)만 넣고 '~3,200단어, 요약·절단 금지', temperature 0.8, 출력은 plain markdown(ch_NN.md). 아웃라인 형식: 장마다 POV/Location/Save-the-Cat beat/% mark/감정 아크(시작→끝)/try-fail 유형(Yes-but·No-and…)/Beats/Plants/Payoffs/단어 목표 + 복선 원장(Foreshadowing Ledger: Thread·Planted·Reinforced·Payoff·Type, 15개 이상, 심기→회수 거리 3장 이상), 막 구조 0–23/23–50/50–77/77–100%, 'yes-but·no-and 60%+', '조용한 장 3개 이상'. 검증: evaluate.py의 slop_score()가 API 없이 TIER1_BANNED(18어)·TIER2_SUSPICIOUS(24어)·TIER3_FILLER 정규식, em-dash 밀도(>15/1000단어), 문장길이 변동계수(균일하면 감점), 단락 첫머리 접속부사 비율, FICTION_AI_TELLS(14 정규식), STRUCTURAL_AI_TICS(6, 'not X but Y'), TELLING_PATTERNS를 합산해 최대 10점 감점; LLM 심사는 장 9차원(voice adherence, beat coverage, character voice, plants seeded, prose quality, continuity, canon compliance, lore integration, engagement) 0–10점('AI 생성 장의 중앙값은 6'). 다중 후보: compare_chapters.py가 Swiss 4라운드 Elo(초기 1500, K=32) 토너먼트, 심판 claude-opus-4-6, 무승부 금지, 3,000단어로 절단, JSON 저장(포지션 스왑 없음). reader_panel.py는 The Editor/The Genre Reader/The Writer/The First Reader 4인이 JSON 10필드(momentum_loss, cut_candidate, missing_scene, best_scene, worst_scene, would_recommend…)를 내고 find_disagreements()가 의견 갈린 장을 '편집 결정 필요'로 표시. 패딩 방지: adversarial_edit.py가 FAT/REDUNDANT/OVER-EXPLAIN/GENERIC/TELL/STRUCTURAL 6분류로 10~20개 구절을 JSON(quote·type·reason·action CUT|REWRITE·fat %)으로 제안만 하고 자동 적용은 안 함.
- applicability: 우리 파이프라인에 가장 직접적. (a) 아웃라인 JSON Schema에 % mark·감정 아크·Plants/Payoffs·단어(초) 목표 필드를 넣어 5단계 구조(0–10/10–30/30–70/70–90/90–100%)를 강제, (b) 세그먼트 생성 시 prev_tail+next-outline 창 방식으로 컨텍스트 절약, (c) evaluate.py를 한국어판으로 이식(문장길이 CV·접속부사 비율·금지 표현 티어·반복 n-gram)해 사실 검증 전에 API 없이 1차 게이트, (d) 훅 구간만 3~5 후보 생성 후 Opus급 심판 Elo 비교, (e) 18~20분 초과분은 adversarial cut JSON→사람 승인으로 처리.
- evidence: GitHub API 2026-09-02 확인: stars 1,537, forks 294, created 2026-03-14, pushed_at 2026-03-20, open issues 20, default branch master. README·draft_chapter.py·evaluate.py·gen_outline.py·compare_chapters.py·reader_panel.py·adversarial_edit.py 직접 열람. 모델: AUTONOVEL_WRITER_MODEL 기본 claude-sonnet-4-6, AUTONOVEL_JUDGE_MODEL 기본 claude-opus-4-6.
- caveat: 라이선스 미지정(API license null) → 코드 복사 불가, 패턴만 차용. 마지막 push가 2026-03-20으로 5개월 정체(추정: 일회성 실험 공개). 소설 전용이라 사실 근거(claim) 연결 개념 없음. Elo 비교에 포지션 스왑이 없어 순서 편향 가능(우리가 넣으면 개선).

### zenstory-ai/oh-story-claudecode (구 worldwonderer, 중국 웹소설 스킬팩)
- url: https://github.com/zenstory-ai/oh-story-claudecode
- what: 장편·단편 웹소설의 순위 스캔(/story-long-scan)→히트작 역분석(/story-long-analyze, 拆文库)→집필(/story-long-write)→AI 티 제거(/story-deslop)→표지까지 전 과정을 Claude Code 스킬+에이전트 7종(story-architect=Opus, character-designer/narrative-writer/story-researcher=Sonnet, consistency-checker/story-explorer/chapter-extractor=Haiku)으로 구성. Claude Code·Antigravity·OpenCode·Codex 등 지원, npx skills add로 설치. v0.7.9(2026-08-30).
- pattern: 컨텍스트 구성: 장 작성 전 references/workflow-chapter.md(13단계)·long-format.md·writing-craft.md·long-chapter-quality.md·long-chapter-hooks.md + 권별 대강·해당 장 세강(细纲) + 追踪/上下文.md(고정 7칸, ≤12KB: 장 번호·현재 장소/시간·POV와 정서·핵심 플롯 상태 2~3문장·등장 인물·다음 장 훅·제약 잠금[사용자 지정 분량/필수 사건/금지/정지점]) + 장르 산문 카드 + 对标/{책}/剧情/情绪模块.md·节奏.md. _tracking-state.json은 '유일한 구조화 권위'지만 본문 프롬프트에는 넣지 않음(토큰 절약). 인물이 2장 이상 부재 시에만 追踪/角色状态/{이름}.md 로드, 복선은 ID 한 줄씩(伏笔.md). 장 완료 후 tracking_commit.py가 JSON(chapter_id, word_count, constraint_lock{range_words,must_occur,forbidden,stop_point}, plot_state_delta{foreshadowing_planted/resolved, character_shifts})을 커밋하고 逐章记录/第NNN章.md에 ≤1,536B(상한 3,072B) 델타 요약만 저장(정적 인물 설정 반복 금지). 검증 훅: guard-outline-before-prose.sh(세강 없으면 본문 생성 차단), check-prose-after-write.sh(절단·공학 용어·독성 문형·분량 미달 경고), detect-story-gaps.sh(세션 시작 시 설정 결손·복선 단절 탐지), validate-story-commit.sh. 패딩 방지: 분량 범위 미달 시 '자동 패딩 금지, 사용자에게 회부', 문장 길이 변동 필수, 회상 문단 금지, '장면이 위험·정보·관계·자원·결정·행동·독자 이해 중 하나를 바꾸지 않으면 무효'(v0.7.9에서 최소 글자수·대사 비율 같은 기계 할당량 제거). 벤치마크: 히트작을 장별 요약+黄金三章 심층 해부+情节节点(54개, 원문 인용+감정 마커 −9~+9)로 분해해 '리듬/핵심 정보 점진/감정 폭발 주기'를 참조 파일로 주입. De-AI: 로컬 lint(확정 패턴 차단)→선택적 외부 검출기(朱雀)→사람 읽기 판단 3단계.
- applicability: 우리와 가장 유사한 운영 모델(Claude Code 스킬+에이전트, Antigravity 지원 명시). (a) '인류의 서재' 30편을 拆文库 방식(분당 감정 마커·정보 공개 리듬·훅 위치)으로 분해해 대본 생성 참조 파일로 주입, (b) 에피소드 상태 카드를 ≤12KB 고정 칸으로 설계하고 claim inventory JSON은 프롬프트 밖에 두되 필요한 ID만 로드, (c) '아웃라인 없이 대본 생성 차단' PreToolUse 훅과 '작성 후 분량·절단 경고' PostToolUse 훅을 agy/Codex 프로바이더 앞뒤에 삽입, (d) 세그먼트 완료 후 델타 요약(≤1.5KB)만 다음 세그먼트에 전달.
- evidence: GitHub API 2026-09-02 확인(worldwonderer→zenstory-ai 리다이렉트): stars 6,391, forks 941, MIT, created 2026-04-22, pushed_at 2026-09-02T11:52Z, open issues 9. README_EN.md, README.md(중문), skills/ 목록(13개), skills/story-long-write/SKILL.md 직접 열람.
- caveat: 중국어 웹소설(起点·番茄) 관행 중심; 스킬 파일이 중국어라 이식 시 번역·규칙 재정의 필요. 7칸 카드 명칭은 SKILL.md 요약 추출이므로 원문 재확인 권장. 다중 후보·심사는 없고 결정론적 게이트 위주. 사실 근거 연결 개념 없음.

### danjdewhurst/story-skills (Codex·Claude Code 플러그인 + story CLI)
- url: https://github.com/danjdewhurst/story-skills
- what: YAML frontmatter 마크다운으로 story bible(story.md)·인물·세계관·파벌·아티팩트·플롯 아크·scene 레지스트리·continuity 상태·질문/약속(promises)·타임라인·장 초고를 관리하는 7개 스킬(story-init, worldbuilding, character-management, plot-structure, chapter-writing, revision-continuity, story-maintenance)과, 이를 '컴파일러의 타입 오류처럼' 검사하는 결정론적 CLI(story validate/continuity/links/reindex/next/build --format epub).
- pattern: 컨텍스트 구성(chapter-writing SKILL.md): 초고 전 story.md, chapters/_index.md(이전 장·분량), plot/_index.md(아크 상태·다음 비트), plot/timeline.md, scenes/_index.md, continuity/state.md(인물·물건·지식 상태), continuity/questions·promises/_index.md, 직전 장 파일, 활성 아크 파일을 읽음 → 범위 결정(사용자와 합의) → 비트별 아웃라인(장면·달성 목표·POV/장소·아크 진전·복선·상태 변화) 승인 → 집필 → 사후 갱신(chapters/_index, timeline, 아크 파일, scenes/ 레코드[chapter, scene, pov, location, characters, arcs-advanced, status, state-changes], continuity/state.md, 복선 planted/paid-off) → story wordcount/reindex/links/validate/next 실행. 일관성: 죽은 인물 재등장 차단(mentions 필드 예외), payoff가 setup보다 먼저 오면 오류, 미해결 질문 추적, 장면 캐스트 검증, 아티팩트 destroyed→active 모순 탐지. 구조화: schemas/story.schema.json으로 프로젝트 계약 정의, story validate가 스키마·frontmatter·레지스트리·분량 경고 검사.
- applicability: 우리 '사실·페르소나 검증' 단계의 결정론적 부분을 CLI화하는 모델. (a) claim inventory를 continuity/state.md처럼 '이미 언급된 claim ID / 아직 미공개 claim / 훅에서 제기한 open question' 원장으로 유지, (b) '훅(0~10%)에서 던진 질문이 절정(70~90%) 전에 회수되는가'를 promise-before-payoff 검사로 기계 검증, (c) 대본 JSON Schema에 각 문장의 claim_ids 필드를 두고 미인용 사실 문장을 오류로 처리.
- evidence: GitHub API 2026-09-02 확인: stars 199, forks 25, MIT, created 2026-02-12, pushed_at 2026-09-01T19:50Z, open issues 1. README, skills/ 목록, skills/chapter-writing/SKILL.md 직접 열람.
- caveat: 모델 불문(markdown 기반)이라 Claude 특화 최적화는 없음. 소설용 엔티티(인물 생사·소유물) 중심이라 사료 claim 스키마는 직접 설계 필요. 분량 검사는 경고 수준.

### ThomasHoussin/Claude-Book (Claude Code 멀티에이전트 소설 프레임워크)
- url: https://github.com/ThomasHoussin/Claude-Book
- what: bible/(style.md, structure.md, characters/*.md, universe/)를 생성 중 '읽기 전용' 기준으로 두고 CLAUDE.md 오케스트레이터가 chapter-planner→chapter-writer→perplexity-improver→style-linter→character-reviewer→continuity-reviewer→state-updater 순으로 6개 서브에이전트(.claude/agents/*.md)를 돌림. 기존 책에서 바이블을 추출·병합하는 도구와 build-ebook.ps1 포함. 기본 출력 프랑스어.
- pattern: 컨텍스트 구성: 장마다 synopsis + plan.md(전체 장 계획) + state/current/situation.md(인물 위치·플롯 상태) + bible/style.md + bible/characters/*.md. 상태는 state/chapter-NN/으로 버전 보관하고 state/current 심링크가 최신을 가리킴; timeline/history.md는 append-only. chapter-planner 출력(.work/chapter-XX-plan.md): Objective / Starting Point(직전 장 끝과 정확히 일치 검증) / Beats 5~10개(플롯 비트와 감정 비트 교대) / Ending Hook(클리프행어·질문·계시·긴장 중 택1) / Characters Involved(역할·감정 아크) / Key Elements. 검증: 3개 리뷰어가 게이트, 실패 시 피드백 리포트를 writer에 전달해 최대 3회 반복. 반복·AI 패턴 방지: perplexity-improver가 로컬 Ministral-3-8B로 저(低)퍼플렉시티(예측 가능한) 문장을 찾아 재작성(CUDA GPU 필요). 구조화 출력·다중 후보 없음.
- applicability: (a) '읽기 전용 바이블 vs 장마다 버전되는 상태 디렉터리 + current 심링크' 구조는 우리 에피소드 산출물 관리에 그대로 적용 가능, (b) 세그먼트 플랜의 Starting Point=직전 세그먼트 끝 일치 검사와 Ending Hook 유형 명시는 5단계 구조 전환부 설계에 유용, (c) 리뷰어 3종 분리(문체/페르소나/연속성) + 최대 3회 루프는 우리 페르소나 검증에 대응.
- evidence: GitHub API 2026-09-02 확인: stars 112, forks 30, MIT, created 2025-12-29, pushed_at 2026-01-22, open issues 0. README, CLAUDE.md, .claude/agents/ 목록, chapter-planner.md 직접 열람.
- caveat: 2026-01-22 이후 커밋 없음(정체). 퍼플렉시티 개선은 NVIDIA GPU+로컬 모델 의존이며 한국어 소형 모델 퍼플렉시티는 신뢰도 낮을 것(추정). 프랑스어 기본.

### forsonny/Claude-Code-Novel-Writer
- url: https://github.com/forsonny/Claude-Code-Novel-Writer
- what: manuscript/chapters/를 '진실의 원천'으로 두고 characters/·worldbuilding/·planning/ 디렉터리, .agents/roles/ 7역할(chapter-writer, character-developer, continuity-editor, error-recovery, plot-architect, smart-planner, worldbuilder), .agents/skills/ 5워크플로(plan-novel, write-chapter, continuity-pass, revise-chapter, finalize-manuscript)로 구성. AGENTS.md 호환으로 Claude Code·OpenAI Codex·Pi에서 동일 동작.
- pattern: 컨텍스트 구성(write-chapter SKILL.md): 해당 장 아웃라인 비트 + 직전 장 + 관련 이전 장 + 인물 상태 + 세계 상태 + 연속성 노트 + roles/chapter-writer.md. 초고 전 ./sync-state.sh --quiet로 원고 파일에서 추적 상태를 재생성(상태 파일을 손으로 안 고침), 기존 실질 원고 덮어쓰기 거부. 사후 automation/quality-check.sh: 최소 1,200단어·최대 7,000단어·평균 문단 120단어·최장 문단 350단어 경고, 대사 비율(따옴표 단어/전체) 산출. 구조화 출력·다중 후보 없음; '조각난 장면 여러 개보다 일관된 한 장'을 우선.
- applicability: (a) sync-state.sh처럼 상태 파일을 산출물(대본 JSON·타이밍 파일)에서 파생 생성하는 방식은 우리 수작업 규칙표 의존을 줄임, (b) quality-check.sh를 한국어 대본용으로 바꿔 '분당 문장 수 12.7 ±, 문장 중앙값 28자, 세그먼트 초 길이' 기계 신호 출력, (c) 멀티 하네스(AGENTS.md) 구조는 우리 agy/Codex/json-file 프로바이더 병행과 동일 문제를 다룸.
- evidence: GitHub API 2026-09-02 확인: stars 130, forks 24, license null, created 2025-08-15, pushed_at 2026-08-21, open issues 0. README, .agents/roles·skills 목록, skills/write-chapter/SKILL.md, automation/quality-check.sh 직접 열람.
- caveat: 라이선스 미지정. 기계 검사는 구조 지표만 있고 반복 구절·금지어 검사는 없음.

### anthropics/claude-cookbooks — patterns/agents (evaluator_optimizer, orchestrator_workers 등)
- url: https://github.com/anthropics/claude-cookbooks/tree/main/patterns/agents
- what: Anthropic 공식 쿡북. patterns/agents에 basic_workflows.ipynb(프롬프트 체이닝·라우팅·병렬화), evaluator_optimizer.ipynb, orchestrator_workers.ipynb, async_multi_agent_orchestration.ipynb가 있으며 'Building Effective Agents' 논문의 참조 구현. 그 외 misc/prompt_caching.ipynb, misc/how_to_enable_json_mode.ipynb, capabilities/summarization, tool_use/memory_cookbook.ipynb, multimodal/using_sub_agents.ipynb(Haiku 서브에이전트+Opus).
- pattern: evaluator_optimizer.ipynb: generate()는 '<thoughts>·<response>' XML로 출력하고 '이전 세대 피드백이 있으면 반영하라'고 지시; evaluate()는 <evaluation>PASS|NEEDS_IMPROVEMENT|FAIL</evaluation>+<feedback>를 내며 '모든 기준 충족·추가 제안 없음'일 때만 PASS; loop()는 매 회 'Previous attempts: …' 목록 + 'Feedback: …'을 generator 컨텍스트로 누적 전달하고 PASS 시 (result, chain_of_thought) 반환. extract_xml()로 태그 파싱. 장편 전용 예제는 없음.
- applicability: 우리 '사실·페르소나 검증→재생성' 루프의 기본 형태. 검증 결과를 PASS/NEEDS_IMPROVEMENT/FAIL 3값 + 구체 피드백으로 규격화하고, 재생성 프롬프트에 '이전 시도 요약+피드백'을 누적 전달하되 상한 회수(Claude-Book의 3회, autonovel의 plateau)를 둔다. 프롬프트 캐싱 노트북은 에피소드 바이블·claim inventory를 캐시 블록으로 고정해 세그먼트 반복 호출 비용을 줄이는 데 참고.
- evidence: GitHub API 2026-09-02 확인: stars 52,362, forks 6,249, MIT, pushed_at 2026-08-28. 디렉터리 목록·evaluator_optimizer.ipynb(raw) 직접 열람.
- caveat: 예제 과제는 코드 생성이며 장편 텍스트용 레시피(장 요약 메모리·엔티티 시트)는 없음. 우리 프로바이더가 CLI(agy/Codex)라 SDK 코드가 아닌 프롬프트/파일 규약으로 옮겨야 함.

### anthropics/claude-code-action (GitHub Actions 연동)
- url: https://github.com/anthropics/claude-code-action
- what: PR/이슈에서 @claude 멘션·이슈 배정·명시적 prompt 입력으로 Claude Code를 실행해 PR 리뷰·요약·수정 구현·Q&A를 수행하는 공식 GitHub Action. 모드 자동 감지, prompt·claude_args 입력, Anthropic API/Bedrock/Vertex/Foundry 인증, 결과를 구조화 JSON action output으로 노출.
- pattern: '변경 diff를 읽고 규칙 파일 기준으로 리뷰 코멘트' 흐름. 워크플로 YAML에 prompt(예: 대본 PR이면 claim 인용 검사·페르소나 규칙 위반 표기)와 허용 도구를 넣고, 결과 JSON을 후속 잡의 게이트로 사용.
- applicability: 우리 파이프라인의 '사람 승인 다수' 단계를 PR 기반으로 옮기면 대본 JSON·시각 브리프 변경에 자동 리뷰 코멘트(사실 검증 요약, 5단계 비율 이탈, 문장길이 통계)를 달 수 있음. 단 현재 D:/module은 git 저장소가 아니어서 선행 작업(리포화, 산출물 버전 관리) 필요.
- evidence: GitHub API 2026-09-02 확인: stars 8,775, forks 2,112, MIT, created 2025-05-19, pushed_at 2026-09-01, open issues 748. README 직접 열람.
- caveat: GitHub 호스팅 러너에서 실행되므로 브라우저 CDP(Google Flow) 단계나 로컬 TTS(SuperTonic3)와는 결합 불가—텍스트 단계(대본·브리프 JSON 리뷰)에만 적용. 대용량 사료 파일은 리포 크기 제약.

### Doriandarko/claude-engineer (Claude Engineer v3)
- url: https://github.com/Doriandarko/claude-engineer
- what: Claude 3.5 Sonnet이 필요 도구를 스스로 설계·구현·핫리로드하는 CLI/웹 인터페이스형 코딩 어시스턴트. 도구 생성기·코드 실행기·파일 관리·웹 스크레이퍼·패키지 관리 등 내장.
- pattern: 자기 확장형 도구 생성 루프. 장편 텍스트 생성 관련 컨텍스트·아웃라인·일관성 기법은 없음.
- applicability: 낮음. 우리 CLI 프로바이더 추상화(agy/Codex/json-file) 설계 참고 정도이며, Claude Code/Agent SDK가 같은 역할을 공식 지원하므로 도입 이유 없음.
- evidence: GitHub API 2026-09-02 확인: stars 11,218, forks 1,160, license null, pushed_at 2024-12-12(약 21개월 정체), open issues 50. README 직접 열람.
- caveat: 2024-12 이후 커밋 없음, 라이선스 미지정, Claude 3.5 Sonnet 고정.

### stanford-oval/storm (STORM / Co-STORM)
- url: https://github.com/stanford-oval/storm
- what: 주제만 주면 인터넷/사용자 코퍼스를 조사해 위키 수준의 인용 포함 장문 기사를 쓰는 시스템. 사전 집필(유사 문서 조사로 관점 발굴→관점별 질문→'작가↔전문가' 모의 대화로 근거 수집)→아웃라인→섹션별 작성(인용 삽입)→polish. Co-STORM은 사람이 개입하는 동적 마인드맵+턴 관리. litellm으로 모델 선택, DSPy 기반, pip install knowledge-storm.
- pattern: 비소설 근거 연결의 표준형: 검색 결과를 근거 단위로 수집→관점 유도 질문으로 커버리지 확대→아웃라인→섹션별로 관련 근거만 검색해 작성→인용 유지. 다중 관점 질문이 통념 대비 반전 소재 발굴에 유리.
- applicability: 우리 '사료 claim inventory' 단계에 '관점 유도 질문 생성'을 추가하면 '통념 균열(10~30%)' 소재를 체계적으로 찾을 수 있고, 섹션별 근거 검색→인용 유지 구조는 대본 문장마다 claim_id를 달아야 하는 우리 검증과 정합. 5단계 서사 구조는 없으므로 아웃라인 단계는 별도 규격 필요.
- evidence: README(2026-09-02 열람): stars 31.2k, forks 2.9k, MIT. commits 페이지: 최근 커밋 2025-09-30, 그 전 2025-05-02, 2025-04-13. GitHub API는 403(레이트리밋)으로 미확인.
- caveat: 위키 문체(중립·설명)라 다큐 서사 톤과 다름. 2025-09-30 이후 커밋 없음(약 1년). Claude 지원은 litellm 경유(README 예제는 GPT).

### aiwaves-cn/RecurrentGPT
- url: https://github.com/aiwaves-cn/RecurrentGPT
- what: LSTM 구조를 자연어로 흉내 내 임의 길이 텍스트를 생성하는 연구 코드. 매 스텝 입력=현재 문단 + 다음 문단 계획 + 검색된 장기 기억; 출력=새 문단 + 다음 계획 + 단기 기억(최근 문단 요약) 갱신 + 장기 기억(모든 문단 요약, 임베딩 검색) 저장.
- pattern: '요약 메모리(단기) + 임베딩 검색 메모리(장기) + 다음 단위 계획'의 3요소 순환. 프롬프트에 전체 본문 대신 요약·계획만 넣어 컨텍스트 폭발 방지.
- applicability: 세그먼트 순차 생성 시 '직전 세그먼트 요약(단기) + 이미 사용한 claim 검색(장기) + 다음 세그먼트 계획' 구조로 이식 가능. 다만 18~20분 대본(약 4~5천자)은 현대 모델 컨텍스트에 통째로 들어가므로 장기 기억은 시리즈 간 재활용(이전 에피소드 참조)에 더 유용.
- evidence: README(2026-09-02 열람): stars 약 1,000, GPL-3.0; commits 페이지 최근 커밋 2024-05-15('update code to support latest version of OpenAI and Gradio'), 이전 2023-07-03. GitHub API 403.
- caveat: 2024-05 이후 정체, OpenAI 기반, GPL-3.0(코드 차용 시 라이선스 전파).

### THUDM/LongWriter (AgentWrite)
- url: https://github.com/THUDM/LongWriter
- what: 10,000단어 이상 생성을 위한 plan-then-write 파이프라인 AgentWrite(plan.py로 문단별 단어 목표 계획→write.py로 이전 문단을 컨텍스트로 순차 작성)와 LongBench-Write 평가(길이 점수 S_l, GPT-4o 품질 점수 S_q), 학습된 LongWriter-glm4-9b/llama3.1-8b, 2025-06 LongWriter-Zero-32B(RL).
- pattern: 아웃라인 항목마다 '단어 수 목표'를 명시하고 순차 작성해 총 길이를 맞추는 방식 + 길이/품질 분리 채점.
- applicability: 우리 세그먼트 계획에 '초 단위 목표(=문장 수 목표: 12.7문장/분)'를 필드로 넣고, 실측 TTS 타이밍과의 오차를 LongBench-Write의 길이 점수처럼 별도 지표로 관리.
- evidence: README(2026-09-02 열람): stars 1.9k, Apache-2.0; commits 페이지 최근 커밋 2025-06-24, 2025-06-23. GitHub API 403.
- caveat: 연구용 데이터 생성 파이프라인이라 일관성·검증 장치 없음. 2025-06 이후 커밋 없음.

### desik1998/NovelWithLLMs
- url: https://github.com/desik1998/NovelWithLLMs
- what: 코드 없이 Claude 3 Sonnet(Bedrock Playground)만으로 35K+ 단어 소설을 쓴 방법론 기록. '이벤트 하나씩 생성→기존 스토리에 붙이기' 반복, 고수준 플롯 변형 여러 개→장 구조 여러 개→이벤트별 확장.
- pattern: 컨텍스트: 대화형이 아니라 '지금까지의 전체 스토리(이벤트 목록)'를 단일 프롬프트에 넣고 다음 이벤트 생성. 반복 방지: 모델의 실패 유형(사건 반복·서두름)을 관찰해 구체 제약(예: '역사 사건은 연도별로 설명')을 추가. 다중 후보: 온도 0.4~0.8로 5~10개 생성 후 사람이 최선 선택(자동 심사 없음이 병목).
- applicability: '실패 유형 관찰→제약 규칙 추가' 사이클을 우리 에피소드별 규칙표 개선에 반영; 훅 구간 다중 온도 샘플링은 autonovel의 심판과 결합해야 실용적.
- evidence: GitHub API 2026-09-02 확인: stars 25, forks 3, MIT, pushed_at 2024-04-09. README 직접 열람.
- caveat: 2024-04 정체, Claude 3 Sonnet 시절, 코드 없음, 비용 $50~100 보고.

### datacrystals/AIStoryWriter
- url: https://github.com/datacrystals/AIStoryWriter
- what: 프롬프트→초기 아웃라인→장별 아웃라인·집필→퇴고 3단계로 소설 길이 텍스트 생성. 단계별로 다른 모델(ollama/google/openrouter, '{provider}://{model}@{host}?param' 표기)을 섞어 쓰는 실험 도구.
- pattern: 단계별 모델 믹스(아웃라인·집필·퇴고에 다른 모델). 반복 구절 감소는 README에 '개선 필요'로 명시된 미해결 과제.
- applicability: 우리 프로바이더 추상화에 '단계별 프로바이더 지정'(아웃라인=agy, 세그먼트=Codex, 검증=json-file 등)을 넣는 근거. 반복 문제 해결책은 없음.
- evidence: GitHub API 2026-09-02 확인: stars 258, forks 64, AGPL-3.0, pushed_at 2025-11-24, open issues 14. README 직접 열람.
- caveat: AGPL-3.0, Claude 명시 지원 없음, 2025-11 이후 커밋 없음.

### raestrada/storycraftr
- url: https://github.com/raestrada/storycraftr
- what: CLI(init/outline/worldbuilding/chapters/iterate/chat)로 세계관·아웃라인·장을 생성하고 iterate 서브커맨드(check-names, insert-chapter, refine-motivation 등)로 사후 수정하는 도구. OpenAI/OpenRouter/Ollama, 어시스턴트 스레드로 대화 이력 유지.
- pattern: '생성 후 iterate로 부분 재작성' 명령 체계(이름 검사·장 삽입·동기 다듬기).
- applicability: 우리 대본 수정 CLI에 iterate 스타일 서브커맨드(예: check-claims, tighten-segment, refine-hook)를 두면 전체 재생성 없이 국소 수정 가능.
- evidence: GitHub API 2026-09-02 확인: stars 164, forks 29, MIT, pushed_at 2026-03-06, open issues 14. README 직접 열람.
- caveat: Claude 미지원(OpenAI 계열), 반복 방지·구조화 출력·다중 후보 없음.

### KazKozDev/NovelGenerator
- url: https://github.com/KazKozDev/NovelGenerator
- what: 전제+장 수 입력으로 다중 플롯 스레드 소설을 생성하는 TypeScript/React 앱. 인물별 '지금 무엇을 아는가' 추적, 병렬 플롯 스레드의 연대기 동기화, 감정 아크 논리 검사 강조.
- pattern: 인물 지식 상태 추적(who-knows-what)과 스레드 동기화.
- applicability: 다큐에서는 '시청자가 현재 아는 정보' 추적(oh-story의 讀者已知 vs 作者真相과 동일 개념)으로 변환해 훅→증거 개방 순서에서 정보 공개 순서 위반을 검출.
- evidence: GitHub API 2026-09-02 확인: stars 144, forks 34, license NOASSERTION, pushed_at 2025-11-05, open issues 9. README 직접 열람.
- caveat: README가 마케팅 서사 위주라 구현 세부(스키마·모델) 불명(추정: 브라우저 앱, 모델 미확인).

### AgriciDaniel/claude-youtube (Claude Code 유튜브 스킬)
- url: https://github.com/AgriciDaniel/claude-youtube
- what: 채널 감사·SEO·리텐션 대본·썸네일·콘텐츠 전략·쇼츠·수익화 서브스킬. /youtube script는 훅 5유형(shock, problem-agitation, story, curiosity-gap, social proof, 위험도 표시)+hook/intro/content 블록+60~90초마다 패턴 인터럽트+CTA 배치, references/retention-scripting-guide.md 참조.
- pattern: 훅 다중 변형(위험도 라벨) 제시, 고정 간격 패턴 인터럽트, 참조 파일 기반 규칙 주입(구조화 JSON 아님, 마크다운).
- applicability: 우리 '인지부조화 훅(0~10%)'에 훅 유형 태그+위험도 필드를 두고 여러 변형을 생성·심사; 패턴 인터럽트 간격(60~90초)을 세그먼트 계획의 체크 항목으로.
- evidence: GitHub API 2026-09-02 확인: stars 343, forks 68, MIT, created 2026-03-05, pushed_at 2026-04-10. README 직접 열람.
- caveat: 영어 마케팅 관행 기준, 근거 검증·장편 일관성 기능 없음.

### rahulanand1103/youtube-script-writer
- url: https://github.com/rahulanand1103/youtube-script-writer
- what: 제목·언어·톤·길이(15초~30분)를 받아 create_blueprint.py(초기 아웃라인)→researcher.py(You.com 검색)→refined_blueprint.py(조사 반영 아웃라인)→writer.py(섹션별 작성)로 대본 생성. blueprint·refined_blueprint 모듈에 structured_output_schema.py.
- pattern: 조사 전/후 2단계 아웃라인(초안→조사 반영 정제)과 아웃라인의 구조화 출력 스키마.
- applicability: 우리 claim inventory 이후 '아웃라인 초안→claim 커버리지 검사→정제 아웃라인' 2단계로 확장하는 근거.
- evidence: GitHub API 2026-09-02 확인: stars 35, forks 6, MIT, pushed_at 2025-03-08. README 직접 열람.
- caveat: OpenAI 전용, 2025-03 이후 정체, 일관성·반복 방지 장치 없음.

### K-Arthur/script-generator (유튜브 다큐 대본 생성기)
- url: https://github.com/K-Arthur/script-generator
- what: 복잡한 원전 자료를 업로드(/api/upload-file)해 청킹·병렬 처리 후 다큐 대본을 생성(/api/generate-script)하고 /api/validate-script로 검증하는 FastAPI+React 앱. app/config/llm.yaml(온도·토큰·검증 임계치), quality_control.yaml(가독성·문체·일관성 검사).
- pattern: 원전 청킹→생성→검증 API 분리와 설정 파일 기반 품질 임계치.
- applicability: '다큐 대본' 표방 프로젝트 중 유일하지만 개인 실험작(0★, 커밋 2회)이라 구조 아이디어 이상의 가치는 없음.
- evidence: GitHub API 2026-09-02 확인: stars 0, forks 0, license null(README는 MIT 표기), pushed_at 2025-01-28, 커밋 2회. README 직접 열람.
- caveat: OpenAI 전용, 사실상 방치.

### sergebulaev/youtube-skills
- url: https://github.com/sergebulaev/youtube-skills
- what: Claude Code/Codex용 유튜브 마케팅 스킬 9종(제목·설명·훅 스크립터·썸네일 브리프·커뮤니티 포스트·콘텐츠 플래너 등). Hook Scripter는 롱폼 첫 30초/쇼츠 첫 3초를 '인트로 없이, 설계된 루프'로 작성.
- pattern: '첫 30초 오픈 루프' 전용 스킬 분리.
- applicability: 훅 세그먼트 전용 프롬프트를 별도 스킬로 분리하는 정도. 장편 구조 없음.
- evidence: GitHub API 2026-09-02 확인: stars 8, forks 2, MIT, created 2026-07-02, pushed_at 2026-09-02. README 직접 열람.
- caveat: 초기 프로젝트, 구조화 출력·심사 없음.

### fangfufu/LLM-book-generator
- url: https://github.com/fangfufu/LLM-book-generator
- what: 제목→장 아웃라인→섹션 본문→전후 부속물→마케팅 문구까지 생성해 DOCX로 조판. Gemini/Ollama, LLM 응답 캐시, LaTeX 수식 이미지화.
- pattern: 단계별 응답 캐시로 재실행 비용 절감.
- applicability: 우리 세그먼트 재생성 시 변경된 세그먼트만 다시 호출하도록 프롬프트 해시 캐시를 두는 근거 정도.
- evidence: README(2026-09-02 열람): stars 41, GPLv3. API 미조회. 마지막 커밋 미확인.
- caveat: 일관성·검증 없음, GPLv3.

### jimmyjjz/lf-vid-gen (롱폼 스토리 영상 생성기)
- url: https://github.com/jimmyjjz/lf-vid-gen
- what: 형식 지정된 대본(LLM 또는 수기)→Tortoise TTS→Diffusers 이미지→MoviePy 편집으로 15분급 영상 자동 생성(VRAM 4~5GB).
- pattern: 대본 형식 스펙을 프로그램이 출력해 LLM에 맞추게 하는 방식.
- applicability: 우리 파이프라인과 후반부(TTS·이미지·편집)가 겹치나 대본 생성 기법은 없음.
- evidence: README(2026-09-02 열람): stars 1, Apache-2.0. API 미조회.
- caveat: 개인 프로젝트, 대본 품질 장치 없음.

### Picrew/awesome-llm-story-generation (큐레이션 목록)
- url: https://github.com/Picrew/awesome-llm-story-generation
- what: LLM 시대 스토리·소설·대본 생성 논문과 오픈소스(generative_agents, RecurrentGPT, ibsen[감독-배우 에이전트 대본], LongAlign, LongWriter, SEED-Story, MoPS, Suri, StoryER 등) 정리. DOC(상세 아웃라인 제어)·Re3(재귀 재프롬프트·수정)·Agents' Room·Dramatron 등 장편 일관성 논문 포함.
- pattern: 학술 계열 기법 지도: 상세 아웃라인 제어(DOC), 재귀 재프롬프트+수정 패스(Re3), 순환 메모리(RecurrentGPT), 계획-작성(LongWriter).
- applicability: 추가 조사 출발점. 특히 DOC의 '아웃라인 각 노드에 대한 상세 제어+일관성 검출기' 개념은 우리 5단계 아웃라인 스키마 설계에 참고.
- evidence: README 2026-09-02 열람. 스타·커밋일 미확인.
- caveat: 목록 자체는 코드가 아님.

## patterns

- **읽기 전용 바이블 + 파생 상태 카드 분리 주입** (대본 생성(세그먼트 순차 확장) — 현재 에피소드별 수작업 규칙표를 '바이블(고정) + 상태 카드(자동 갱신)'로 분리): 생성 중 절대 바뀌지 않는 바이블(문체 규칙·페르소나·구조 규칙·claim inventory)과, 세그먼트마다 갱신되는 소형 상태 카드(≤12KB 고정 칸: 현재 위치/%·직전 세그먼트 요약 2~3문장·이미 공개한 claim ID·아직 회수 안 된 질문(open loop)·다음 훅·제약 잠금[목표 초·필수 claim·금지 표현])를 분리한다. 전체 상태 JSON(_tracking-state.json)은 프롬프트에 넣지 않고 필요한 ID만 로드. 상태는 세그먼트별 디렉터리로 버전화하고 current 심링크로 최신을 가리킨다. [seen in: zenstory-ai/oh-story-claudecode (追踪/上下文.md 7칸 ≤12KB, _tracking-state.json 프롬프트 제외, 逐章记录 ≤1,536B 델타 요약), ThomasHoussin/Claude-Book (bible/ 읽기 전용, state/chapter-NN + state/current 심링크, timeline/history.md append-only), danjdewhurst/story-skills (story.md + continuity/state.md + scenes/_index.md), aiwaves-cn/RecurrentGPT (단기 요약 메모리 + 장기 검색 메모리)]
- **아웃라인 필드 규격화 + 복선/질문 원장(Ledger)** (구성(아웃라인) — Codex --output-schema 경로에 바로 적용 가능): 아웃라인을 자유 서술이 아니라 세그먼트별 고정 필드(% mark, 단계 라벨[훅/균열/증거/절정/통찰], 감정 아크 시작→끝, 정보 공개 유형[통념 제시/균열/증거/반전], 사용 claim_ids, 심는 질문(Plant)과 회수(Payoff), 목표 초·문장 수, 종료 훅 유형)로 JSON Schema화하고, 별도 원장에 '질문 제기 세그먼트→강화→회수 세그먼트'를 기록해 회수 거리·개수 제약(예: 최소 N개, 심기→회수 ≥2세그먼트)을 스키마 검증으로 강제한다. 5단계 % 구간과 STORM식 관점 유도 질문으로 '통념 균열' 소재를 아웃라인 단계에서 확보. [seen in: NousResearch/autonovel gen_outline.py (POV/Save-the-Cat beat/% mark/감정 아크/try-fail/Plants/Payoffs/단어 목표 + Foreshadowing Ledger ≥15, 거리 ≥3장, 막 비율 0–23/23–50/50–77/77–100%), ThomasHoussin/Claude-Book chapter-planner (Objective/Starting Point/Beats 5~10 교대/Ending Hook 유형), danjdewhurst/story-skills (continuity/promises, questions 원장, payoff-before-setup 오류), stanford-oval/storm (관점 유도 질문→아웃라인→섹션), rahulanand1103/youtube-script-writer (조사 전/후 2단계 blueprint 스키마)]
- **슬라이딩 창 컨텍스트: 직전 세그먼트 꼬리 + 다음 세그먼트 아웃라인 머리** (대본 생성 — SuperTonic3 문장 TTS 전제이므로 세그먼트 경계 문장의 이음새 품질에 직접 영향): 세그먼트 생성 프롬프트에 이전 본문 전체 대신 '직전 세그먼트 마지막 N자(prev_tail) + 다음 세그먼트 아웃라인 첫 몇 줄'만 넣어 연결부 자연스러움과 앞당겨 말하기(spoiler) 방지를 동시에 잡는다. 순차 생성이며 각 세그먼트에 초·문장 수 목표를 명시하고 '요약·절단 금지'를 지시. 한 세그먼트 완료 후 델타 요약(≤1.5KB)만 상태 카드에 반영. [seen in: NousResearch/autonovel draft_chapter.py (prev_tail 2,000자 + 다음 장 아웃라인 ~10줄, 목표 ~3,200단어, temp 0.8), THUDM/LongWriter AgentWrite (문단별 단어 목표 계획→순차 작성), desik1998/NovelWithLLMs (이벤트 단위 순차 확장), forsonny/Claude-Code-Novel-Writer write-chapter (직전 장 + 해당 비트만 로드)]
- **기계적 slop 스코어(무API) + LLM 심사 이중 게이트** (사실·페르소나 검증 — 사실 검증 전에 저비용 문체 게이트를 두어 재생성 비용 절감): API 호출 없이 정규식/통계로 1차 감점(티어별 금지 표현, 문장길이 변동계수, 단락 첫머리 접속부사 비율, 반복 n-gram, 'not X but Y'류 구조 틱, 감정 명명(telling) 패턴, 분량·절단 검사)을 계산하고, 통과분만 LLM 심사(9차원 0–10, '평균 AI 장=6' 앵커, 임계치 6.0)로 보낸다. 한국어판 지표는 벤치마크(문장 중앙값 28자, 12.7문장/분)에서 도출하고 분당 문장 수·세그먼트 초 길이·'~것이다/~했던 것이다' 반복 비율 등을 추가. [seen in: NousResearch/autonovel evaluate.py (TIER1/2/3, em-dash >15/1000, 문장길이 CV, FICTION_AI_TELLS 14, STRUCTURAL_AI_TICS 6, 감점 상한 10; 장 9차원 LLM 심사), forsonny/Claude-Code-Novel-Writer quality-check.sh (1,200~7,000단어, 문단 평균 120/최장 350, 대사 비율), zenstory-ai/oh-story-claudecode (check-prose-after-write.sh, scripts/check-ai-patterns.js, banned-words.md, 3단계 deslop), ThomasHoussin/Claude-Book (perplexity-improver, style-linter)]
- **Evaluator–Optimizer 루프(피드백 누적 전달, 상한·정체 감지)** (검증→재생성 — 현재 '검증 실패 시 처리' 규약을 3값+피드백 메모리로 표준화): 검증 결과를 PASS / NEEDS_IMPROVEMENT / FAIL 3값 + 구체 피드백(XML 또는 JSON)으로 규격화하고, 재생성 프롬프트에 '이전 시도 요약 + 피드백' 목록을 누적 전달한다. 최대 반복(3회) 또는 점수 정체(plateau) 시 사람에게 회부. 리뷰어는 문체/페르소나/연속성(사실)로 역할 분리. [seen in: anthropics/claude-cookbooks patterns/agents/evaluator_optimizer.ipynb (loop/generate/evaluate, Previous attempts+Feedback 누적, extract_xml), ThomasHoussin/Claude-Book (style-linter·character-reviewer·continuity-reviewer, 최대 3회), NousResearch/autonovel (score>6.0 재작성, plateau 감지, Opus 이중 페르소나 리뷰), zenstory-ai/oh-story-claudecode (consistency-checker S1–S4 등급 보고)]
- **훅 구간 다중 후보 + 심판(토너먼트/페르소나 패널)** (구성(훅) 및 사람 승인 — 승인자가 후보 전체가 아니라 심판이 갈린 항목만 보게 하여 승인 부담 감소): 전체 대본이 아니라 리텐션이 결정되는 훅(0~10%)과 절정 진입부만 온도·프롬프트 변형으로 3~5개 후보를 만들고, 상위 모델 심판이 쌍대 비교(무승부 금지, A/B 위치 스왑 추가)로 Elo 순위를 매기거나, 시청자 페르소나 4인(예: 역사 애호가/캐주얼 시청자/편집자/사료 검증자)이 JSON 고정 필드로 채점해 의견이 갈린 항목만 사람에게 올린다. [seen in: NousResearch/autonovel compare_chapters.py (Swiss 4라운드 Elo 1500/K=32, Opus 4.6 심판) 및 reader_panel.py (4 페르소나 JSON 10필드, find_disagreements), desik1998/NovelWithLLMs (온도 0.4~0.8 5~10개 생성, 사람 선택), AgriciDaniel/claude-youtube (훅 5유형+위험도 라벨 다중 제시)]
- **Adversarial cut 패스: 패딩 대신 삭제 후보 JSON, 분량 미달은 자동 채움 금지** (대본 후처리 — 실측 샷 타이밍 결과(총 길이)를 받아 되돌아오는 조정 루프): 목표 길이(18~20분) 초과 시 모델에게 FAT/REDUNDANT/OVER-EXPLAIN/GENERIC/TELL/STRUCTURAL 분류로 10~20개 삭제·재작성 후보를 인용문+이유+action(CUT|REWRITE) JSON으로 제안만 시키고 사람이 승인해 적용한다. 반대로 분량 미달이면 필러로 채우지 말고 '미달' 플래그를 올려 claim inventory에서 추가 근거를 배정한다. 각 세그먼트는 '위험·정보·관계·결정·시청자 이해 중 하나를 바꾸지 않으면 무효' 규칙으로 장식적 세그먼트를 제거. [seen in: NousResearch/autonovel adversarial_edit.py (6분류, JSON 제안 전용, edit_logs/), zenstory-ai/oh-story-claudecode (범위 미달 시 자동 패딩 금지·사용자 회부, v0.7.9 장면 유효성 기준), raestrada/storycraftr (iterate 국소 수정 서브커맨드)]
- **결정론적 연속성 검사기 + 생성 전/후 훅(hook) 차단** (사실·페르소나 검증 및 프로바이더 호출 전후 훅 — 이미 JSON Schema 검증이 있으므로 의미 검사기만 추가): LLM이 아닌 스크립트가 '아웃라인 없이 본문 생성 금지'(사전 차단), '문장→claim_id 매핑 누락', '훅에서 제기한 질문 미회수', '이미 공개한 사실을 나중에 처음 공개하듯 서술', '세그먼트 % 구간 이탈'을 컴파일러 오류처럼 보고한다. 세션 시작 시 결손 탐지 스크립트로 바이블 공백(미배정 claim, 누락 아웃라인)을 먼저 알린다. [seen in: danjdewhurst/story-skills (story continuity/validate/links, schemas/story.schema.json, 사망 인물 재등장·payoff-before-setup 오류), zenstory-ai/oh-story-claudecode (guard-outline-before-prose.sh 차단, detect-story-gaps.sh, validate-story-commit.sh), forsonny/Claude-Code-Novel-Writer (sync-state.sh로 원고에서 상태 재생성), KazKozDev/NovelGenerator (인물 지식 상태 추적→시청자 기지 정보 추적으로 변환)]
- **벤치마크 역분석 라이브러리(拆文库) 주입** (구성 — 현재 벤치마크 통계(5단계 비율·문장 중앙값·분당 문장)를 참조 파일 규격으로 확장): 히트작(우리는 '인류의 서재' 30편)을 장/세그먼트별 요약, 정보 공개 순서, 감정 마커(−9~+9) 시계열, 훅 위치·간격(패턴 인터럽트 60~90초), 문장 통계로 분해해 '리듬 파일'과 '감정 모듈 파일'로 저장하고, 대본 생성 시 참조 권위 파일로 로드해 문체·리듬·감정 곡선 이탈을 막는다. [seen in: zenstory-ai/oh-story-claudecode (拆文库/{책}/剧情/节奏.md·情绪模块.md, 情节节点 54개 −9~+9, 对标/ 참조 뷰), NousResearch/autonovel (voice_fingerprint.py로 보이스 지문→voice.md 가드레일), AgriciDaniel/claude-youtube (references/retention-scripting-guide.md 참조 파일 규칙 주입), stanford-oval/storm (유사 문서 조사로 관점 발굴)]
- **단계별 모델/프로바이더 라우팅과 프롬프트 캐싱** (전체(프로바이더 추상화) — agy/Codex/json-file 선택을 에피소드 단위가 아니라 단계 단위로): 아웃라인·구조 설계=상위 모델, 세그먼트 작성·조사=중간 모델, 기계 검사·상태 조회·요약 추출=경량 모델(또는 무API 스크립트)로 배정하고, 바이블·claim inventory 같은 고정 블록은 캐시 프리픽스로 두어 세그먼트 반복 호출 비용을 줄인다. [seen in: zenstory-ai/oh-story-claudecode (story-architect=Opus, narrative-writer=Sonnet, consistency-checker/chapter-extractor=Haiku), NousResearch/autonovel (writer=Sonnet 4.6, judge=Opus 4.6), datacrystals/AIStoryWriter (단계별 provider://model 믹스), anthropics/claude-cookbooks (misc/prompt_caching.ipynb, multimodal/using_sub_agents.ipynb)]
- **PR 기반 자동 리뷰(GitHub Actions)로 사람 승인 보조** (사람 승인 단계(텍스트 산출물 한정) — 전제: 프로젝트를 git 리포로 전환(현재 D:/module은 git 아님), 브라우저 CDP·TTS 단계는 제외): 대본·시각 브리프 JSON을 git으로 관리하고 PR마다 claude-code-action이 규칙 파일(바이블·검증 규칙)을 읽어 claim 인용 누락·5단계 비율 이탈·문체 통계·페르소나 위반을 코멘트로 남기며, 구조화 JSON output을 후속 잡 게이트로 사용한다. [seen in: anthropics/claude-code-action (prompt/claude_args, @claude·issue 배정·명시 prompt 트리거, 구조화 JSON action outputs)]


# channel anthropic-official

## summary
Anthropic 공식 자료(claude-api 스킬, docs/platform.claude.com, Claude Cookbooks 저장소·호스팅 사이트, code.claude.com Agent SDK 문서)를 2026-09-02 기준으로 직접 확인했다. 결론: (1) 우리 파이프라인의 JSON Schema 검증 단계(대본·시각 브리프·채점)는 API 네이티브 구조화 출력(output_config.format=json_schema, SDK messages.parse+Pydantic)으로 바로 치환 가능하되, minLength/maxLength/minimum/maximum·재귀 스키마·additionalProperties≠false가 미지원이므로 schemas/*.schema.json을 SDK 변환(transform_schema)에 맞춰 손질해야 한다. Cookbook의 'JSON mode'(prefill) 레시피는 4.6+ 모델에서 prefill이 400 에러라 채택 불가. (2) 사료·스타일 가이드·페르소나 계약을 안정 프리픽스로 두고 프롬프트 캐싱(Opus 5/Fable 5.1 최소 512토큰, 캐시 읽기 0.1x, Fable 5.1은 0.025x)을 걸면 5단계 순차 생성·샷별 브리프·장별 채점의 반복 입력 비용이 대부분 사라진다. (3) 110장 이미지 채점은 비전 입력(1920×1080=2,691 시각토큰, 고해상도 티어) + 구조화 출력 + Batch API(50% 할인, 캐시와 중첩) 조합이 정석이며, Cookbook content_moderation 레시피의 'LLM은 타입 필드만 추출, 판정은 결정론적 규칙 엔진'이 우리 fail-closed 게이트와 정확히 같은 설계다. (4) LLM-as-judge는 docs develop-tests·building_evals·evaluator_optimizer가 루브릭+<thinking>→판정, 생성 모델과 다른 모델로 채점, Likert/이진 출력을 권고. (5) 오케스트레이션은 Agent SDK(query()+output_format, ResultMessage.total_cost_usd) 또는 headless `claude -p --bare --output-format json --json-schema`가 현재 antigravity-cli/codex-cli/json-file 프로바이더와 같은 형태라 provider 하나 추가로 붙는다. Dynamic Workflows(agent/parallel/pipeline, 동시 16, 재개 가능)는 110샷 fan-out+회의적 검증에 적합하지만 토큰 사용량이 크다. 비용(추정, 한국어 1자≈0.8~1.0토큰·4.7+ 토크나이저 가정, count_tokens 무료로 실측 권장): 대본 25,000자 1회 생성 Opus 5 ≈ $1.2~1.6, Sonnet 5 ≈ $0.5, Fable 5.1 ≈ $2.3~2.8; 브리프 110샷(10샷 단위+캐시) Opus 5 ≈ $3.1(Batch $1.6), Sonnet 5 ≈ $1.25(Batch $0.65); 이미지 채점 110장 Opus 5 ≈ $3.0(Batch $1.5, 1456×819 다운스케일 시 $2.4), Sonnet 5 ≈ $1.2(Batch $0.6), Haiku 4.5 ≈ $0.7(Batch $0.35), Fable 5.1 ≈ $5.8; 대본 QA 판정 Opus 5 ≈ $0.4; 재사용 판정 30후보 Sonnet 5 ≈ $0.4. 편당 합계: 권장 혼합(대본 Opus 5 + 나머지 Sonnet 5, 캐시+Batch) ≈ $3.5~4.5, 전부 Opus 5 동기·무캐시 ≈ $9~12, 전부 Fable 5.1 ≈ $14~20 (모두 추정). 환경 확인: 현재 human_archive 스크립트에 anthropic import 없음, ANTHROPIC_API_KEY 미설정, python anthropic SDK·gh·ant CLI 미설치. 저장소 근거: anthropics/anthropic-cookbook → claude-cookbooks로 리네임(52.4k★, 6.2k fork, 최근 push 2026-08-28, 호스팅 platform.claude.com/cookbook), claude-agent-sdk-python 8.0k★(v0.2.151, 2026-09-01), claude-code-action 8,775★(push 2026-09-01).

## items

### Claude Cookbooks 저장소(구 anthropic-cookbook)
- url: https://github.com/anthropics/claude-cookbooks
- what: Anthropic 공식 레시피 모음. GitHub anthropics/anthropic-cookbook은 claude-cookbooks로 리다이렉트. 디렉터리: capabilities/(classification, summarization, content_moderation, RAG…), misc/(batch_processing, building_evals, prompt_caching, how_to_enable_json_mode, using_citations, generate_test_cases…), multimodal/(best_practices_for_vision, using_sub_agents, crop_tool…), patterns/agents/(basic_workflows, orchestrator_workers, evaluator_optimizer, async_multi_agent_orchestration), claude_agent_sdk/(00~08), cost_optimization/, tool_use/, tool_evaluation/, managed_agents/. 호스팅판은 platform.claude.com/cookbook/<slug>.
- pattern: 참조 저장소(인덱스)
- applicability: 높음. 아래 개별 레시피의 상위 인덱스. 우리 파이프라인 도입 시 노트북 코드를 그대로 쓰기보다 패턴(캐싱·배치·judge·워크플로)을 스크립트에 이식하는 용도.
- evidence: GitHub API 2026-09-02 확인: stargazers 52,362, forks 6,249, pushed_at 2026-08-28T21:53Z, open issues 321, default branch main. README에 Summarization/JSON mode/Prompt caching/Automated evaluations/Vision/Sub-agents/Cost optimization 항목 명시.
- caveat: 노트북 다수가 claude-opus-4-1·sonnet-4-6 등 이전 모델 ID를 쓰며, 일부(how_to_enable_json_mode)는 4.6+에서 제거된 prefill 기법이라 그대로 복사하면 400 에러. 모델 ID는 claude-api 스킬 표(claude-opus-5 등)로 교체 필요.

### Structured outputs (docs)
- url: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- what: output_config.format={type:'json_schema', schema} 로 응답 JSON을 스키마에 강제. Python SDK는 client.messages.parse(output_format=PydanticModel) → response.parsed_output. 지원 모델: Opus 5/4.8/4.7/4.6, Sonnet 5/4.6/4.5, Haiku 4.5, Fable 5/5.1, Mythos. 미지원: 재귀 스키마, minimum/maximum, minLength/maxLength, minItems>1, additionalProperties가 false가 아닌 값, 외부 $ref. SDK가 미지원 제약을 자동 제거하고 description에 옮긴 뒤 원본 스키마로 재검증. 문법 컴파일은 첫 호출 지연 후 24h 캐시. output_config.format 변경 시 프롬프트 캐시 무효화. strict:true 툴 입력 검증은 별도 기능.
- pattern: 스키마 강제 출력
- applicability: 매우 높음. 대본 생성(episode_contract_v2·script JSON), 시각 브리프(visual_brief_manifest 112건), 이미지 채점(점수 JSON), 재사용 판정 결과를 API 레벨에서 스키마 보장 → 현재 사후 JSON Schema 검증·재시도 루프를 줄일 수 있음. schemas/*.schema.json 중 minLength/maxLength/pattern 등이 있으면 SDK transform_schema 결과를 확인하고, 재검증은 기존 검증기를 유지.
- evidence: docs 본문 2026-09-02 확인. Python SDK v1.0+는 client.beta.messages.create(output_format=…)를 TypeError로 거부하므로 output_config 사용.
- caveat: citations와 output_config.format은 같은 요청에서 병용 불가(400). Fable 5.1은 tool_choice any/tool 강제도 400이라 '툴로 JSON 강제' 대안은 Fable 5.1에서 불가.

### Prompt caching (docs)
- url: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- what: tools→system→messages 순 프리픽스 캐시. 5분 쓰기 1.25x, 1시간 쓰기 2x, 읽기 0.1x(Fable 5.1·Mythos 5.1은 0.025x=$0.25/MTok). 최소 캐시 길이: Opus 5/Fable 5/5.1 512토큰, Opus 4.8/Sonnet 5/4.6 1,024, Opus 4.7 2,048, Opus 4.6/Haiku 4.5 4,096. 브레이크포인트 최대 4, 20블록 lookback. 이미지·document 블록도 캐시 가능. 동시 요청은 첫 응답 시작 후에야 캐시 히트. 이미지 추가/제거·tool_choice·effort 변경은 상위 레벨까지 무효화.
- pattern: 안정 프리픽스 캐싱(세계관 바이블·사료·스타일 가이드 재사용)
- applicability: 매우 높음. (a) 대본 5단계 순차 생성: persona 계약+스타일 가이드+claim inventory(약 50K토큰 추정)를 system 앞부분에 고정하고 이전 단계 출력을 뒤에 붙여 5회 호출 → 입력비 대부분 0.1x. (b) 샷별 브리프 110회: 규칙표+대본+타이밍을 프리픽스로. (c) 이미지 채점 110장: 루브릭+참조 이미지를 프리픽스로(이미지 블록 캐시 가능). 배치 처리 시 1h TTL 권장(docs batch 페이지).
- evidence: docs 표 2026-09-02 확인. Cookbook misc/prompt_caching.ipynb(최근 커밋 2026-02-20, 'automatic caching' 반영, 모델 claude-sonnet-4-6)는 187K토큰 책을 system에 넣고 캐시 히트 시 4.89s→1.48s(3.3x) 시연.
- caveat: Haiku 4.5는 최소 4,096토큰이라 2K짜리 채점 루브릭은 캐시 안 됨. datetime·UUID·정렬 안 된 json.dumps 같은 프리픽스 변동이 캐시를 조용히 깨므로 usage.cache_read_input_tokens 로 검증. 110장 병렬 채점은 첫 요청 응답 후 나머지를 보내야 캐시 히트.

### Message Batches API (docs)
- url: https://platform.claude.com/docs/en/build-with-claude/batch-processing
- what: 요청 묶음을 비동기 처리, 모든 토큰 50% 할인(입력·출력·캐시 포함). 배치당 100,000요청 또는 256MB, 대부분 1시간 내 완료, 24시간 만료, 결과 29일 보관. 비전·툴(서버 툴 포함)·구조화 출력·extended thinking 지원. 프롬프트 캐싱과 중첩되나 best-effort(히트율 30~98%), 1h TTL 권장. max_tokens:0(캐시 프리워밍)은 불가.
- pattern: 대량 저비용 오프라인 처리
- applicability: 높음. 사람 승인 대기 중에 돌리는 비실시간 단계에 적합: 110장 이미지 의미 채점, 110샷 브리프, 재사용 후보 30건 판정, 회귀 eval 세트. 결과는 custom_id로 매칭(순서 비보장) → shot_id를 custom_id로.
- evidence: docs 2026-09-02 확인(Opus 5 배치 $2.5/$12.5, Sonnet 5 $1/$5, Haiku 4.5 $0.5/$2.5, Fable 5.1 $5/$25 per MTok). Cookbook misc/batch_processing.ipynb는 base64 이미지 요청을 배치에 섞는 예제 포함(모델 claude-sonnet-4-6).
- caveat: Fast mode·server-side fallbacks 파라미터는 배치에서 거부. 파이프라인이 fail-closed 게이트로 다음 단계를 막고 있으면 24h 지연이 허용되는지 단계별로 판단 필요(파일럿 12+8은 동기, 전체 82장은 배치 등).

### Vision (docs)
- url: https://platform.claude.com/docs/en/build-with-claude/vision
- what: image 블록(base64/url/file_id). JPEG/PNG/GIF/WebP. 1M 컨텍스트 모델은 요청당 600장(200K 모델 100장), 요청에 20장 초과 시 각 이미지 2000px 제한. 시각토큰=⌈w/28⌉×⌈h/28⌉. 고해상도 티어(Claude 4.7 이후: Opus 5/4.8/4.7, Sonnet 5, Fable): 최대 long edge 2576px·4784토큰, 1920×1080은 리사이즈 없이 2,691토큰. 표준 티어(Haiku 4.5 등): 1920×1080→1456×819, 1,560토큰. 다중 이미지는 'Image 1:' 라벨을 앞에 붙여 비교. 이미지를 텍스트 앞에 두는 게 유리. 한계: 사람 식별 불가, 소수·소형 객체 카운팅 부정확, AI 생성 여부 판별 불가.
- pattern: 이미지-텍스트 일치 채점 입력
- applicability: 매우 높음. Flow 생성물(실측 1920×1080 PNG 119장 확인)을 브리프(focal_subject/action/place/era/prop_motifs)와 대조 채점, 승인 자산 vs 후보 비교로 재사용 판정, OCR 결과 교차검증(글자·서비스 마크 유무). 비용 절감을 위해 1456×819로 다운샘플 권장(docs 명시).
- evidence: docs 2026-09-02 확인. 예시: Opus 5 고해상도 1000×1000 = $6.48/1000장, 4K = $23.92/1000장. 우리 1920×1080 1장 = Opus 5 $0.0135, Sonnet 5 $0.0054, Haiku 4.5 $0.00156, Fable 5.1 $0.027(추정 계산).
- caveat: '글자 없음' 검사에서 작은 텍스트는 놓칠 수 있어 OCR/pHash와 병행 유지. AI 생성 감지 용도로는 쓰지 말 것.

### Cookbook: Best practices for vision
- url: https://platform.claude.com/cookbook/multimodal-best-practices-for-vision
- what: 역할 부여('You have perfect vision…')·<thinking> 단계로 카운팅 정확도 개선, 이미지 few-shot(예시 이미지-정답 쌍), 참조 이미지 여러 장과 대상 이미지를 함께 넣어 카테고리 판별(object identification from examples), 다중 이미지 합성, 표/텍스트 추출.
- pattern: 참조 이미지 few-shot 비교 판정
- applicability: 높음. 승인된 doodle_seonbi_v1.png·연속성 그룹 대표 이미지를 참조로 넣고 후보 이미지의 스타일·인물 일치(호스트 마스코트 미포함 규칙 등)를 판정하는 프롬프트 골격으로 사용.
- evidence: GitHub multimodal/best_practices_for_vision.ipynb 최근 커밋 2025-11-28(Lint+Format #305), 모델 claude-opus-4-1. 호스팅 페이지 2026-09-02 확인.
- caveat: few-shot 효과는 케이스별 편차가 있다고 명시. 모델 ID 갱신 필요.

### Cookbook: Content moderation with vision + JSON schema + rule engine
- url: https://platform.claude.com/cookbook/capabilities-content-moderation-guide
- what: 정책 문서를 Opus로 1회 컴파일해 JSON 규칙으로 만들고, 콘텐츠(텍스트+이미지)에서 Sonnet이 output_config json_schema로 타입 필드만 추출(예: depicted_person_apparent_under_25, text_coverage enum)한 뒤, 모델을 호출하지 않는 결정론적 엔진이 approve/flag/block/needs_review를 3값 논리로 판정. 22/22 정확, 감사 추적 포함.
- pattern: 스키마 추출 → 결정론 판정(모델은 사실만, 규칙은 코드)
- applicability: 매우 높음. 우리 이미지 QA(글자·연도·워터마크·서비스마크 금지, 비호스트에 마스코트 금지, 한글 anchor 차단)와 재사용 판정을 '모델이 필드 추출, verify_visual_assets.py가 규칙 판정' 구조로 옮기면 fail-closed·재현성이 유지됨. 판정 이유가 필드 단위로 남아 사람 승인 화면에 그대로 노출 가능.
- evidence: 호스팅 페이지 2026-09-02 확인(코드에 output_config format json_schema + image_block 사용).
- caveat: 'unknown' 필드가 있으면 needs_review로 떨어지는 설계라, 우리 승인 게이트도 unknown을 통과로 취급하지 않도록 매핑해야 함.

### Cookbook: Using vision with tools / Extracting structured JSON
- url: https://platform.claude.com/cookbook/tool-use-vision-with-tools
- what: 이미지+툴 input_schema로 구조화 추출(영양표→JSON). 자매 레시피 tool-use-extracting-structured-json은 Haiku 4.5로 기사 요약 점수(coherence 0-100 등)·NER·감성·분류를 input_schema로 강제.
- pattern: 툴 스키마로 JSON 강제(구조화 출력의 대안)
- applicability: 중간. output_config.format이 스키마 제약(예: additionalProperties true 필요)을 못 받을 때의 우회. 채점 필드에 0-100 점수·enum을 두는 스키마 예시로 참고.
- evidence: 호스팅 페이지 2026-09-02 확인(모델 claude-opus-4-1 / claude-haiku-4-5).
- caveat: Fable 5.1은 tool_choice any/tool 강제 불가 → auto+지시문 또는 output_config 사용. 새 코드는 structured outputs 우선.

### Files API (docs)
- url: https://platform.claude.com/docs/en/build-with-claude/files
- what: 이미지·PDF·텍스트를 1회 업로드 후 file_id로 반복 참조. 파일 500MB, 조직 1TB, 업로드/목록/삭제 무료(사용 시 입력 토큰만 과금). expires_in_seconds(1h~90일)로 자동 만료. 워크스페이스 전체가 접근 가능.
- pattern: 참조 자산 재사용
- applicability: 높음. 승인 자산(doodle_seonbi_v1.png, 연속성 그룹 대표 이미지, 스타일 레퍼런스)을 file_id로 올려 110장 채점·재사용 판정 요청마다 base64 재전송을 피함. 배치 요청과 결합 가능.
- evidence: docs 2026-09-02 확인. Files API는 베타 종료(헤더 불필요), client.files.upload.
- caveat: Bedrock/Vertex 미지원. 워크스페이스 공유 범위이므로 미공개 에피소드 자산은 전용 워크스페이스 키로.

### Long context prompting (docs, prompting best practices)
- url: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- what: 20K+ 토큰 입력 시: 긴 문서를 프롬프트 맨 위, 질의·지시는 맨 아래(최대 30% 품질 향상), 다중 문서는 <documents><document index><source><document_content> XML, 작업 전 관련 인용문을 <quotes>에 먼저 뽑게(quote-first).
- pattern: 장문 사료 배치·인용 우선
- applicability: 높음. claim inventory·source snapshot을 XML document로 상단 배치하고 대본 생성/사실 검증 시 근거 인용을 먼저 출력하게 하면 claim-evidence span 결속과 사실 검증 보고서 생성이 쉬워짐. 캐싱 프리픽스 순서와도 일치(문서 먼저→캐시).
- evidence: docs § Long context prompting 2026-09-02 확인(long-context-tips.md 단독 페이지는 404, 통합 페이지로 이동).
- caveat: 우리 스크립트가 지시를 앞에 두는 구조면 순서를 뒤집어야 캐시와 품질 모두 이득.

### Cookbook: Summarization guide + 평가(promptfoo)
- url: https://platform.claude.com/cookbook/capabilities-summarization-guide
- what: 기본/다샷/가이드형/도메인 특화(XML 섹션 출력)/청킹 후 메타 요약/요약 인덱스 RAG. 평가는 promptfoo로 BLEU·ROUGE·llm_eval.py(일관성·관련성·사실성 LLM 채점)·contains. 청킹은 2000자 단위 Haiku, 종합은 Sonnet.
- pattern: 긴 문서 분할·메타 요약 + 자동 평가
- applicability: 중간~높음. 사료 스냅샷(긴 원문) → claim inventory 요약 단계에 청킹·메타 요약 적용, 요약 품질을 llm_eval 식 루브릭으로 회귀 테스트. 다만 1M 컨텍스트에서는 사료 대부분이 통째로 들어가므로 청킹은 초장문에만.
- evidence: GitHub capabilities/summarization/guide.ipynb 최근 커밋 2026-02-17(모델 4.6으로 갱신), evaluation/README.md에 bleu_eval.py·rouge_eval.py·llm_eval.py 명시. 호스팅 페이지 2026-09-02 확인.
- caveat: ROUGE/BLEU는 한국어 다큐 대본 품질 지표로 부적합, LLM 루브릭 채점만 이식.

### Citations (docs·cookbook)
- url: https://platform.claude.com/cookbook/misc-using-citations
- what: document 블록에 citations:{enabled:true} → 응답 text 블록마다 cited_text·document_index·char_location(start/end char) 또는 page_location 반환. 프롬프트 기반 인용보다 recall/precision 높고 출력 토큰 절감.
- pattern: 근거 span 결속
- applicability: 높음(사실 검증 단계). 대본 문장별 claim을 source snapshot document에 대해 char_location으로 결속시켜 fact_check_report_v2의 evidence span을 자동 채움.
- evidence: docs citations 페이지·cookbook 2026-09-02 확인(모델 claude-sonnet-4-6).
- caveat: citations와 output_config.format 병용 불가 → 인용 호출과 JSON 정리 호출을 2단계로 나누거나, 인용 응답을 코드로 파싱.

### LLM-based grading / evals (docs: Develop tests)
- url: https://platform.claude.com/docs/en/test-and-evaluate/develop-tests
- what: 평가 설계 원칙(작업 특화·자동화·양 우선), 코드 기반/휴먼/LLM 기반 채점. LLM 채점 시: 상세 루브릭, 입력+출력 함께 제공, 판정 전 추론 유도, Likert(1-5)/이진/서열 출력, 생성 모델과 다른 모델로 채점. 예제: 톤 Likert, PHI 이진, 문맥 활용 서열.
- pattern: LLM-as-judge
- applicability: 매우 높음. 대본 QA: 5단계 구조 비율(0~10/10~30/30~70/70~90/90~100%) 준수, 문장 중앙값 28자·12.7문장/분 벤치마크 근접도, 쉽선비 페르소나 톤(Likert), claim 결속 여부(이진) → 구조화 출력으로 점수 JSON. 이미지 채점: 브리프-이미지 일치 서열 점수.
- evidence: docs 2026-09-02 확인(예제 모델 claude-opus-5).
- caveat: '다른 모델로 채점' 권고 → 대본을 Opus 5로 쓰면 판정은 Sonnet 5 또는 Fable 5.1 등으로 분리. 구조 비율·문장 길이 같은 결정적 지표는 코드로 계산하고 LLM은 주관 지표만.

### Cookbook: Building evals
- url: https://platform.claude.com/cookbook/misc-building-evals
- what: 코드 채점(정규식/정확일치), 휴먼 채점, 모델 채점. 모델 채점 프롬프트 골격: <answer>…</answer><rubric>…</rubric> → <thinking> 후 <correctness>correct|incorrect</correctness>.
- pattern: 루브릭 그레이더 프롬프트 템플릿
- applicability: 높음. 페르소나 검증(validate_seonbi_persona.py)과 사실 검증 보고서에 LLM 판정 항목을 추가할 때 그대로 쓸 수 있는 골격.
- evidence: GitHub misc/building_evals.ipynb 최근 커밋 2025-11-28, 모델 claude-opus-4-1. 호스팅 페이지 2026-09-02 확인.
- caveat: XML 태그 출력 대신 structured outputs로 correctness enum을 받는 편이 파싱 안전.

### Cookbook: Evaluator-optimizer
- url: https://platform.claude.com/cookbook/patterns-agents-evaluator-optimizer
- what: 생성기와 평가기를 루프로 묶어 PASS/NEEDS_IMPROVEMENT/FAIL + 피드백을 다음 생성 컨텍스트에 넣어 재생성. 명확한 기준이 있고 피드백으로 개선되는 작업에 적합.
- pattern: 생성→판정→재생성 루프
- applicability: 높음. 대본 생성 직후 자동 QA(구조·길이·페르소나·claim 결속)에서 NEEDS_IMPROVEMENT면 위반 목록을 첨부해 해당 단계만 재생성, 최대 N회 후 REVIEW_REQUIRED로 사람에게. 시각 브리프도 validate_image_requests.py 실패 항목만 재생성.
- evidence: GitHub patterns/agents/evaluator_optimizer.ipynb 최근 커밋 2025-11-28. Anthropic 'Building effective agents'(2024-12-19) 5개 워크플로 중 하나. 호스팅 페이지 2026-09-02 확인.
- caveat: 사람 승인 게이트를 대체하지 않음. 루프 상한과 캐시 프리픽스 유지(피드백은 프리픽스 뒤에).

### Cookbook: Basic workflows / Orchestrator-workers / Async multi-agent
- url: https://platform.claude.com/cookbook/patterns-agents-basic-workflows
- what: prompt chaining(단계별 출력 → 다음 입력, 사이에 코드 게이트), parallelization(ThreadPoolExecutor로 동일 프롬프트 다중 입력), routing, orchestrator-workers(오케스트레이터가 XML로 하위 작업 생성 → 워커 병렬 → 종합, 모델 Sonnet 4.6), async_multi_agent_orchestration(asyncio 허브·인박스, 모델 Opus 4.8).
- pattern: Outline-to-Book 순차 확장 + 병렬 fan-out
- applicability: 높음. 대본: 아웃라인(5단계·문장 예산) → 단계별 확장(chain, 각 단계 후 코드 검증) → 문장 단위 다듬기. 브리프: 샷 목록을 10샷 단위로 parallel 처리. 워크플로 코드가 우리 스크립트(compile_narrative_outline.py, build_expanded_script.py)와 동일 구조라 이식 비용 낮음.
- evidence: 호스팅 페이지·GitHub patterns/agents 디렉터리(README, util.py, prompts/) 2026-09-02 확인.
- caveat: 'production code가 아님'이라고 명시. 병렬 시 캐시 히트를 위해 첫 요청 응답 후 나머지 발사.

### Cookbook: Using Haiku as a sub-agent (multimodal)
- url: https://platform.claude.com/cookbook/multimodal-using-sub-agents
- what: 상위 모델이 하위 프롬프트를 작성, Haiku 서브에이전트가 PDF→PNG 이미지들을 ThreadPoolExecutor로 병렬 추출, 상위 모델(Opus)이 종합.
- pattern: 저가 워커 fan-out + 고가 종합
- applicability: 높음. 110장 1차 채점을 Haiku 4.5/Sonnet 5로 병렬, 경계 사례(점수 중간·unknown)만 Opus 5로 재판정(cost-optimization docs의 '실패만 상위 effort로 재실행' 패턴).
- evidence: 호스팅 페이지 2026-09-02 확인(모델 ID는 haiku-4-5 / opus-4-1로 오래됨).
- caveat: Haiku 4.5는 표준 해상도 티어(1920×1080→1,560토큰)·200K 컨텍스트·캐시 최소 4,096토큰.

### Claude Agent SDK 개요·Python 레퍼런스·구조화 출력
- url: https://code.claude.com/docs/en/agent-sdk/overview
- what: Claude Code 하네스를 Python/TS 라이브러리로. query(prompt, options=ClaudeAgentOptions(model, system_prompt, allowed_tools, permission_mode, max_turns, output_format={'type':'json_schema','schema':…}, cwd, agents, hooks, mcp_servers, setting_sources)) → ResultMessage(result, structured_output, total_cost_usd, usage, session_id). 스키마는 draft-07, 재프롬프트로 검증 실패 시 error_max_structured_output_retries. 서브에이전트·훅·세션 재개 지원.
- pattern: 에이전트 하네스 오케스트레이션 + 스키마 결과
- applicability: 높음. generate_verified_script.py / generate_visual_briefs.py의 provider 목록(antigravity-cli, codex-cli, json-file, omniroute)에 'claude-agent-sdk' provider 추가: 스키마를 output_format으로 넘기고 structured_output을 기존 검증기에 통과시키면 현재 흐름 유지. total_cost_usd로 편당 비용 감사 로그 확보. 사실 검증처럼 파일 읽기·검색이 필요한 단계에 built-in Read/Grep 활용.
- evidence: code.claude.com overview·python·structured-outputs 페이지 2026-09-02 확인. GitHub anthropics/claude-agent-sdk-python 8.0k★, 1.3k fork, 최근 커밋 2026-09-01(v0.2.151). Cookbook claude_agent_sdk/00~08 노트북 존재.
- caveat: 단일 요청 API보다 토큰·지연 큼(에이전트 루프). 제3자 제품에 claude.ai 로그인/구독 사용 불허 → API 키. 단순 생성 단계는 Messages API + structured outputs가 더 싸고 단순(claude-api 스킬의 'Start simple' 권고).

### Headless Claude Code (claude -p)
- url: https://code.claude.com/docs/en/headless
- what: claude -p '<prompt>' --bare --output-format json --json-schema '<schema>' --allowedTools 'Read' → stdout JSON의 structured_output·session_id·total_cost_usd. stdin 파이프(10MB 상한), 종료코드로 분기, --append-system-prompt(-file), --resume, stream-json. --bare는 훅·MCP·CLAUDE.md 자동 로드 생략(CI 재현성), ANTHROPIC_API_KEY 필요.
- pattern: CLI 프로바이더(서브프로세스)
- applicability: 매우 높음. 현재 CodexCliVisualBriefProvider(--output-schema)와 동일한 형태라 ClaudeCliProvider를 수십 줄로 추가 가능(UTF-8 stdin 명시는 Windows에서 동일하게 필요). 프롬프트 파일을 --append-system-prompt-file로 넘기고 스키마 강제.
- evidence: docs 2026-09-02 확인. v2.1.205+에서 잘못된 --json-schema는 시작 시 오류.
- caveat: format 키워드는 주석으로만 취급(검증 안 함). 기본 권한 모드는 Manual이라 파일 쓰기 등은 --allowedTools/--permission-mode 지정 필요.

### Dynamic Workflows (docs + Cookbook 08)
- url: https://code.claude.com/docs/en/workflows
- what: Claude가 작성한 JS 스크립트가 수십~수백 서브에이전트를 오케스트레이션: agent(prompt,{schema,label,model}), parallel([...]), pipeline(items, stage…), phase(). 동시 16, 런당 1,000 에이전트, parallel/pipeline 4,096항목 상한, 결과는 스크립트 변수에 유지, 일시정지·재개, .claude/workflows/에 저장해 /<name>으로 재사용, args로 입력. fan-out 시 동일 프리픽스 캐시 공유(5초 스태거). Cookbook 08: 투자자 업데이트 사실검증 = EXTRACT(10 claims 구조화) → VERIFY(claim당 1 에이전트 병렬) → SKEPTIC(확인된 판정마다 반박) → REPORT, 약 $3.29·2.5분.
- pattern: 코드가 계획을 쥔 fan-out + 회의적 검증
- applicability: 높음(중장기). claim inventory 검증(claim당 에이전트+회의자), 110샷 브리프 생성→규칙 검증→회의자 검토, 110장 채점 fan-out. claude -p/Agent SDK에서는 Workflow 툴 허용 규칙 필요.
- evidence: docs 2026-09-02 확인(모든 유료 플랜·API 접근, Bedrock/Vertex/Foundry). Cookbook claude_agent_sdk/08_Dynamic_workflows.ipynb 최근 커밋 2026-08-03, claude-agent-sdk v0.2.90+, Python 3.11+.
- caveat: 토큰 사용량이 단일 에이전트보다 크게 늘어남(노트북 2~4달러). 스크립트에서 파일시스템·셸 직접 접근 불가, import 불가. 먼저 작은 슬라이스(10샷)로 비용 측정 권고.

### Claude Code GitHub Actions (claude-code-action)
- url: https://code.claude.com/docs/en/github-actions
- what: @claude 멘션 인터랙티브 모드와 prompt 입력 자동화 모드(스케줄 cron 포함). anthropic_api_key / claude_code_oauth_token / OIDC 연합 인증, claude_args로 --model·--max-turns·--allowedTools 전달, 스킬/플러그인 실행(/code-review). PR 리뷰를 인라인 코멘트로 게시.
- pattern: CI 이벤트 기반 에이전트 실행(PR 요약·리뷰)
- applicability: 낮음~중간. 현재 D:/module은 git 저장소가 아니고 파이프라인이 로컬 Chrome CDP·TTS 서버·사람 승인에 묶여 있어 GitHub Actions에서 실행 불가. 도입한다면 스키마·계약 YAML·승인 JSON만 버전관리하는 저장소에서 '승인 JSON·fact report 변경 PR 요약/규칙 위반 리뷰' 정도.
- evidence: GitHub API 2026-09-02: anthropics/claude-code-action 8,775★, 2,112 fork, pushed 2026-09-01. docs 2026-09-02 확인.
- caveat: 공개 저장소 fork PR은 시크릿 미제공. GitHub Actions 분 + API 토큰 이중 과금.

### Cost optimization (docs + Cookbook)
- url: https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence
- what: 레버 순서: 프롬프트 캐싱(에이전트 루프 2.7~5.3x, 캐시 읽기 80%+ 목표) → 캐시 TTL 선택 → 입력 트리밍(이미지 리사이즈, 툴 지연 로딩) → Batch 50% → 프롬프트 감사(14%) → effort 스윕(30~75%) → 실패만 상위 effort 재실행 → 모델 업그레이드 → 태스크 예산 → 다중 모델(advisor/orchestrator). 완료 작업당 비용으로 비교. usage 필드 기반 비용 계산 코드 제공. Cookbook cost_optimization: Opus high→low 59% 절감, Sonnet medium+캐시 83% 절감, 이미지 4,088→928토큰 77% 절감, Haiku 서브에이전트+Sonnet 결정자 90% 절감.
- pattern: 비용 설계 순서
- applicability: 매우 높음. 우리 편당 비용 설계 근거. 특히 (1) 이미지 다운스케일, (2) 채점을 Batch, (3) 대본만 Opus 5·나머지 Sonnet 5, (4) 판정 경계 사례만 상위 모델 재실행.
- evidence: docs·Cookbook cost_optimization/cost_optimization.ipynb 2026-09-02 확인(가격표: Fable 5 $10/$50, Opus 5 $5/$25, Sonnet 5 $2/$10, Haiku 4.5 $1/$5).
- caveat: 벤치마크 수치는 코딩·검색 작업 기준, 한국어 장문 생성 품질은 우리 eval로 직접 측정 필요.

### 모델 가격표 (docs Pricing)
- url: https://platform.claude.com/docs/en/about-claude/pricing
- what: per MTok: Fable 5.1 $10/$50(캐시 읽기 $0.25), Fable 5 $10/$50(읽기 $1), Opus 5·4.8·4.7·4.6 $5/$25(읽기 $0.5), Sonnet 5 $2/$10(읽기 $0.2, 도입가가 정가로 확정), Sonnet 4.6 $3/$15, Haiku 4.5 $1/$5. 5m 쓰기 1.25x, 1h 쓰기 2x. Batch 50%. 1M 컨텍스트 전 구간 동일 단가(장문 프리미엄 없음). Claude 4.7+ 토크나이저는 같은 텍스트에 약 30% 더 많은 토큰.
- pattern: 단가 기준
- applicability: 편당 비용 추정 기준. 1편 추정(한국어 1자≈0.8~1.0토큰 가정, 추정): 대본 25,000자 1회 = Opus 5 $1.2~1.6 / Sonnet 5 $0.5 / Fable 5.1 $2.3~2.8 / Haiku $0.23; 5단계 순차+캐시 = Opus 5 $1.5~1.8. 브리프 110샷(10샷 단위 11회+캐시) = Opus 5 $3.1(Batch $1.6) / Sonnet 5 $1.25(Batch $0.65); 샷별 110회는 Opus 5 $5.9. 이미지 채점 110장(2,691토큰+텍스트 3K/장, 출력 300) = Opus 5 $3.0(Batch $1.5, 1456×819 다운스케일 $2.4) / Sonnet 5 $1.2(Batch $0.6) / Haiku 4.5 $0.7(Batch $0.35) / Fable 5.1 $5.8. 대본 QA 판정 = Opus 5 $0.43 / Sonnet 5 $0.17 / Fable 5.1 $0.85. 재사용 판정 30후보 = Opus 5 $1.0 / Sonnet 5 $0.4. 편당 합계: 혼합(대본 Opus 5+나머지 Sonnet 5, 캐시+Batch) $3.5~4.5, 전부 Opus 5 동기·무캐시 $9~12, 전부 Sonnet 5+Batch 약 $2, 전부 Fable 5.1 $14~20 (모두 추정).
- evidence: docs 2026-09-02 확인. 한국어 토큰 비율은 공식 수치 없음(웹 검색: 한글은 문자 단위 토큰화, 영어 대비 약 2.36x 밀도 보고) → 추정 표시. 실측은 무료 count_tokens 엔드포인트(모델별 토크나이저 반영) 권장.
- caveat: thinking 토큰은 출력 과금(adaptive, effort로 조절). Fable 5.1은 30일 데이터 보존 필수·Priority Tier 없음.

### Token counting (docs)
- url: https://platform.claude.com/docs/en/build-with-claude/token-counting
- what: client.messages.count_tokens(model, system, messages, tools) 무료, 이미지·PDF·툴 포함 가능, RPM 5,000~20,000. 대상 모델 ID로 세어야 함(4.7+ 토크나이저 약 +30%).
- pattern: 예산 실측
- applicability: 높음. 도입 전 EP01(한글 20,228자)·EP03 대본과 flow_image_prompts.json(112건, 제출 프롬프트 평균 1,241자)으로 한국어·영어 혼합 토큰 비율을 실측해 위 추정치를 보정.
- evidence: docs 2026-09-02 확인.
- caveat: 캐시 로직은 반영 안 됨(추정치).

### Cookbook: JSON mode (prefill) — 채택 금지 항목
- url: https://platform.claude.com/cookbook/misc-how-to-enable-json-mode
- what: assistant prefill('Here is the JSON:{')·stop sequence·XML 태그로 JSON 추출. 2024-03 게시, 모델 claude-opus-4-1.
- pattern: 프롬프트 기반 JSON(구식)
- applicability: 낮음(반면교사). 4.6+·Opus 5·Sonnet 5·Fable에서 assistant prefill은 400 에러(claude-api 스킬 명시). 구조화 출력으로 대체.
- evidence: 호스팅 페이지 2026-09-02 확인; prefill 제거 사실은 claude-api 스킬 'Prefill removed' 항목.
- caveat: 레시피 자체는 prefill 제거를 언급하지 않음.

### Cookbook: Generate test cases / Tool evaluation
- url: https://platform.claude.com/cookbook/misc-generate-test-cases
- what: {{VARIABLE}} 템플릿에서 변수 추출→메타프롬프트로 현실적 테스트 입력 합성(Sonnet 4.6, temp 1.0), 생성 예시를 다음 생성 가이드로 재투입. tool_evaluation은 evaluation.xml 태스크로 툴 설명 품질·정확도(7/8)·호출 수 리포트.
- pattern: 합성 eval 세트 생성
- applicability: 중간. 브리프 프롬프트·채점 루브릭의 회귀 테스트 입력(다양한 내레이션 문장·금지 패턴 포함)을 합성해 104개 회귀 테스트를 확장.
- evidence: 호스팅 페이지 2026-09-02 확인.
- caveat: 합성 입력은 실제 사료 분포와 다를 수 있어 실 에피소드 샘플과 혼합.

### Compaction / Context editing (claude-api 스킬·docs)
- url: https://platform.claude.com/docs/en/build-with-claude/compaction
- what: 서버측 compaction(베타 compact-2026-01-12, 기본 150K 트리거)이 긴 대화 앞부분을 요약; context editing(clear_tool_uses)은 오래된 툴 결과 제거. 응답 content 전체를 그대로 다시 넣어야 함.
- pattern: 이전 회차 컨텍스트 압축
- applicability: 중간. '세계관 바이블+이전 회차로 다음 장' 패턴에서 이전 장 전문 대신 요약을 넣는 것이 원칙이며, 다회 에이전트 세션(Agent SDK·워크플로)에서만 compaction 의미 있음. 단일 호출 순차 생성은 코드가 요약/아웃라인을 관리하는 편이 캐시에 유리.
- evidence: claude-api 스킬 Compaction 섹션·live-sources URL 2026-09-02 확인.
- caveat: 베타. 텍스트만 뽑아 붙이면 compaction 상태가 유실됨.

## patterns

- **안정 프리픽스 캐싱(바이블·사료·스타일 가이드 → 캐시, 가변 입력은 뒤)** (대본 생성(5단계 순차), 시각 브리프(샷별/10샷 단위), 이미지 채점(루브릭+참조 이미지), 재사용 판정): tools→system→messages 순으로 바이트 단위 프리픽스 매칭. 페르소나 계약·스타일 가이드·claim inventory·규칙표를 system 앞에 고정하고 cache_control 1회, 단계/샷/이미지별 가변 내용은 마지막 브레이크포인트 뒤에. 캐시 읽기 0.1x(Fable 5.1 0.025x), 배치에서는 1h TTL. [seen in: docs prompt-caching, Cookbook misc/prompt_caching.ipynb, docs optimizing-for-cost-and-intelligence, Dynamic workflows fan-out 캐시 공유]
- **Outline-to-Book 순차 확장 = prompt chaining + 코드 게이트** (대본 생성(compile_narrative_outline.py → build_expanded_script.py 흐름에 그대로 대응), 대본 QA): 아웃라인(5단계 비율·문장 예산) 생성 → 단계별 확장(각 단계 출력이 다음 입력, 사이에 문장 길이·구조 비율·claim 결속을 코드로 검증) → 문장 다듬기. 이전 장 전문 대신 요약/아웃라인을 넘겨 컨텍스트와 캐시 유지. 각 단계는 structured outputs로 스키마 보장. [seen in: Cookbook patterns/agents/basic_workflows.ipynb (chain), Anthropic 'Building effective agents' (2024-12-19), docs long context prompting]
- **LLM-as-judge(루브릭 + 추론 후 판정 + 다른 모델) 및 evaluator-optimizer 루프** (대본 QA(5단계 구조·28자 중앙값·페르소나·claim 결속), 시각 브리프 QA, 생성 후 의미 채점): <rubric>과 입력·출력을 함께 주고 <thinking> 후 Likert/이진/enum으로 판정, 생성 모델과 다른 모델로 채점. NEEDS_IMPROVEMENT면 피드백을 붙여 재생성, 상한 후 사람에게 REVIEW_REQUIRED. 결정적 지표(문장 길이, 비율)는 코드로. [seen in: docs test-and-evaluate/develop-tests, Cookbook misc/building_evals.ipynb, Cookbook patterns/agents/evaluator_optimizer.ipynb, Cookbook summarization evaluation (llm_eval.py, promptfoo)]
- **스키마 추출 → 결정론 규칙 엔진(모델은 사실 필드만, 판정은 코드)** (생성 후 의미 채점(verify_visual_assets.py 앞단), 재사용 판정(build_semantic_image_reuse_plan.py 후보 채점), OCR 교차검증): 비전+output_config json_schema로 이미지에서 타입 필드(글자 존재, 인물 수, 마스코트 존재, 시대·장소 일치도, 소품 목록)만 추출하고, 모델 호출 없는 엔진이 approve/flag/block/needs_review를 3값 논리로 판정해 감사 추적을 남김. [seen in: Cookbook capabilities/content_moderation guide, docs structured-outputs, Cookbook tool_use/vision_with_tools.ipynb]
- **저가 워커 fan-out + 상위 모델 종합/재판정(orchestrator-workers, sub-agents, dynamic workflows)** (시각 브리프 110샷, 이미지 채점 110장, claim 사실 검증): Haiku 4.5/Sonnet 5 워커가 샷별·이미지별 작업을 병렬 처리하고, 경계 사례·실패만 Opus 5(또는 높은 effort)로 재실행. 코드(스크립트)가 계획을 쥐고 결과는 변수에 유지, 최종 보고만 컨텍스트로. 회의자(skeptic) 단계로 확인 판정을 재검증. [seen in: Cookbook patterns/agents/orchestrator_workers.ipynb, Cookbook multimodal/using_sub_agents.ipynb, Cookbook claude_agent_sdk/08_Dynamic_workflows.ipynb, docs workflows, docs cost optimization '실패만 상위 effort 재실행']
- **Batch API + 캐시 중첩으로 비실시간 단계 50% 절감** (이미지 채점, 시각 브리프 전체 생성, 재사용 후보 판정, 회귀 eval): 사람 승인 대기 중 돌아가는 대량 단계를 배치로 제출(custom_id=shot_id), 동일 cache_control 블록을 모든 요청에 포함, 1h TTL. 비전·구조화 출력·thinking 모두 배치 지원. [seen in: docs batch-processing, Cookbook misc/batch_processing.ipynb, docs pricing]
- **CLI/SDK 프로바이더 어댑터(claude -p --json-schema 또는 Agent SDK query()+output_format)** (대본 생성·시각 브리프 provider, 사실 검증(파일 읽기 필요 시 Agent SDK)): 기존 antigravity-cli/codex-cli/json-file 프로바이더와 같은 인터페이스로 Claude를 붙이고, structured_output을 기존 JSON Schema 검증기에 통과시킴. ResultMessage.total_cost_usd / usage로 편당 비용 감사. 단순 생성 단계는 Messages API + structured outputs가 더 싸고 단순. [seen in: docs headless, docs agent-sdk overview/python/structured-outputs, claude-api 스킬 'Start simple' 및 Tool Runner vs Agent SDK 구분]
- **근거 인용 우선(citations / quote-first) → claim-evidence 결속** (사실 검증(verify_script_facts.py), claim inventory 구축): 사료를 document 블록으로 상단 배치, citations 활성화로 cited_text·char_location을 받아 대본 문장별 근거 span을 자동 결속. 구조화 출력과 병용 불가하므로 인용 호출과 JSON 정리 호출 분리. [seen in: docs citations, Cookbook misc/using_citations.ipynb, docs long context prompting]
- **구조화 출력으로 prefill/JSON-mode 대체** (모든 JSON 산출 단계(대본, 브리프, 채점, 재사용 판정, 사실 보고서)): output_config.format json_schema 또는 messages.parse(Pydantic)로 API 레벨 스키마 보장. 미지원 키워드(minLength/maxLength/minimum/maximum, 재귀, additionalProperties≠false)는 SDK가 제거·description 이관 후 원본 스키마로 재검증. Fable 5.1은 tool_choice 강제 불가. [seen in: docs structured-outputs, Cookbook tool_use/extracting_structured_json.ipynb, Cookbook misc/how_to_enable_json_mode.ipynb(구식, 채택 금지)]