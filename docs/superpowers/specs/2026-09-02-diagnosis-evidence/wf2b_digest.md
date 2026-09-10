

# channel video-automation-oss

## summary
조사일 2026-09-02. GitHub의 faceless/다큐/explainer 자동 생성 파이프라인 22건(저장소 README 직접 열람 19건 + 블로그/평가 라이브러리)을 검토했다. 핵심 관찰: (1) 샷 분할은 거의 전부 'TTS 오디오 실측 길이 우선(TTS-first)'이며, 문장/절 단위 대본 → 오디오 길이 → 샷 길이로 흐른다(clawvid, spoonstill, storyboard-ai). 시간 고정 분할은 스톡영상형(MoneyPrinterTurbo)에서만 보인다. (2) 대본↔이미지 프롬프트는 예외 없이 LLM 구조화 출력(JSON scene plan: narration·visual_prompt·duration·effects)이 유일한 계약 문서이며, 상위 프로젝트(OpenMontage 55.5k★, ViMax 12.2k★)는 scene_plan을 사람 승인 게이트로 고정한 뒤 에셋을 생성한다. (3) 이미지 프로바이더는 API(fal.ai/Replicate/Gemini) 추상화가 표준이고 브라우저 자동화는 Google Flow 전용 도구(gflow-cli 140★, google-flow-browser-mcp 49★)가 따로 존재하며 '실제 Chrome 영속 프로필 + CDP + 단일 작업 큐 + 폴링 + 실패 시 즉시 중단(exit code)' 패턴을 공유한다. (4) 생성 후 품질 검증: CLIP 텍스트-이미지 정합 점수는 StoryBoard-Generator(CLIP 정합+이미지 간 일관성 코사인), ai-video-editor(CLIP ViT-B/32 + Qwen2.5-VL 1~10점 채점 → 속도 티어), OpenMontage(video_understand: CLIP/BLIP-2, README 기재)에서 확인됐고, 범용 채점기는 t2v_metrics의 VQAScore(600★, Qwen2.5-VL 기반, CLIPScore보다 구성 정확도 우수)와 imscore(PickScore/ImageReward/HPSv2/VQAScore 통합)가 있다. VLM 프레임 QA는 claude-faceless-shorts-creator(Claude 비전으로 렌더 PNG 검수)에서 실전 적용. (5) 모션/페이싱: '연속 샷 동일 모션 금지'(stevecv get_varied_motions), '슬라이드쇼 위험 6차원 점수로 렌더 차단'(OpenMontage), '강도 곡선 0~100 + 아크 프리셋 + 피크 씬 단독 파일럿 렌더'(reelforge, 한국어 우선), '롱→쇼트→쇼트→포즈→임팩트 리듬'(visual-skills)이 우리 5단계 구조(훅→균열→증거→절정→통찰)에 직접 매핑 가능하다. (6) 사람 개입: OpenMontage는 proposal/script/scene_plan/assets/publish 5개 게이트를 '강제'하고 비용 $0.50 초과마다 승인, rushindrasinha는 '초안 훅·사실 주장' 검토를 유일 핵심 체크포인트로 명시, ContentMachine은 씬당 4변형 중 사람이 선택. 우리 파이프라인에 가장 실익이 큰 도입안: (a) 시각 브리프를 수작업 규칙표에서 JSON scene_plan(문장ID·visual_prompt·shot_type·motion·reference_entity) 구조화 출력으로 전환하고 생성 전 lint, (b) OCR/pHash QA 뒤에 VQAScore(또는 CLIP) 정합 점수와 VLM 채점을 붙여 사람 승인 대기열을 상위 후보로 축소, (c) 씬당 2~4변형 생성 후 점수 기반 best-of-n, (d) Ken Burns 모션을 5단계 구조 강도 곡선과 '연속 동일 모션 금지' 규칙으로 자동 배정, (e) Google Flow CDP 계층에 gflow-cli식 '제출 전 기록·실패 즉시 중단·선택자 자동 탐색'을 이식. 주의: 한국어 문장을 CLIP에 직접 넣는 사례는 없었고(영문 프롬프트 기준), 한국어 정합은 영문 visual_prompt 대비 채점 또는 Qwen-VL 계열 VQAScore로 우회해야 한다(추정). 스타 수·날짜는 GitHub 페이지 표기 기준(API는 rate limit로 실패).

## items

### MoneyPrinterTurbo (harry0703)
- url: https://github.com/harry0703/MoneyPrinterTurbo
- what: 주제/키워드 → LLM 대본 → TTS → 스톡/AI 영상 소재 매칭 → 자막 → MoviePy/FFmpeg 렌더. 숏폼 중심이나 REST/CLI/에이전트 인터페이스 제공. 확인일 2026-09-02.
- pattern: 샷 분할: 사용자 설정 '片段时长(세그먼트 길이)' 기반 시간 분할, 오디오 길이를 채울 때까지 소재를 이어붙임. 대본↔소재: LLM이 '소재 검색 키워드 추출'(구조화 프롬프트 생성이 아니라 검색어). 프로바이더: Pexels/Pixabay/Coverr API + AI 영상(WaveSpeed, Seedance, OFox, MiniMax) + OpenAI 호환 이미지 API, 로컬 업로드. 자막: TTS 타임스탬프(edge) 또는 Whisper. 품질 검증·모션 규칙·페이싱 규칙 없음. 사람 개입: WebUI에서 대본·소재·음성 단계별 수정.
- applicability: 프로바이더 추상화(스톡·AI영상·이미지 API를 한 인터페이스로) 구조는 참고 가치. 우리 다큐형(문장 단위 생성 이미지)과는 매칭 철학이 다름(키워드 검색형). 페이싱·QA 도입 근거로는 부적합.
- evidence: README 표기 119.7k★; 최근 커밋 2026-09-02('feat(material): default OFox vendor pinning'). MIT. 릴리스 페이지는 v1.3.5(2024-08-22)까지만 표시.
- caveat: 세그먼트 분할 규칙 상세는 README에 없음(코드 미확인). 인증 없음·서드파티 업로드 서비스 등 보안 이슈 지적됨.

### ShortGPT (RayVentura)
- url: https://github.com/RayVentura/ShortGPT
- what: LLM 지향 편집 마크업(EDL/JSON)으로 편집 단계를 블록화한 숏폼/롱폼 자동화 프레임워크. 확인일 2026-09-02.
- pattern: 'Editing Markup Language + JSON'으로 편집 스텝을 LLM이 이해·수정 가능한 블록으로 분해. 소재: Pexels API, Bing 이미지 검색(LLM 키워드 추출). TTS: ElevenLabs/EdgeTTS. 품질 검증·모션 규칙 없음.
- applicability: '편집 결정 리스트(EDL)를 LLM 친화 JSON으로 두고 사람이 수정' 아이디어만 참고. 사실상 개발 정체.
- evidence: README 표기 7.9k★, 1.1k fork; stable 브랜치 최근 커밋 2025-02-10('add Gemini API key support') → 약 19개월 미갱신.
- caveat: 정체 상태이므로 코드 의존 도입은 비권장.

### OpenMontage (calesthio)
- url: https://github.com/calesthio/OpenMontage
- what: Claude Code/Cursor/Codex 등 코딩 에이전트를 오케스트레이터로 쓰는 12개 제작 파이프라인(Animated Explainer, Documentary Montage 등), 100+ Python 툴, YAML 파이프라인 매니페스트, Remotion 합성. 확인일 2026-09-02.
- pattern: 단계: research → proposal → script → scene_plan → assets → edit → compose. scene_plan은 duration·visual_prompt·narration 필드의 구조화 산출물. 프로바이더: 15+ 이미지 API를 7차원 점수(task fit 30%, 품질 20%, 제어 15%, 신뢰성 15%, 비용 10%, 지연 5%, 연속성 5%)로 자동 선택하고 대안·신뢰도를 감사 로그에 기록. 품질: 'Video Understand — CLIP/BLIP-2 vision-language analysis' 툴, 6차원 '슬라이드쇼 위험 점수'(반복·장식적 시각·약한 모션·샷 의도·타이포 과의존·근거 없는 시네마틱 주장)가 critical이면 렌더 차단, 렌더 후 ffprobe·4지점 프레임 추출(블랙프레임/깨진 오버레이)·오디오 레벨·자막 존재 검사 실패 시 게시 보류. 사람 개입: 'Human approval gates are enforced, not suggested' — proposal/script/scene plan/assets/publish 5게이트 + 비용 $0.50 초과 시 건별 승인, Backlot 보드에 씬별 컨택트시트(테이크·프롬프트·비용·품질점수). 모션: Remotion spring 애니메이션 이미지 씬, 다큐 몽타주는 Archive.org/NASA/Wikimedia에서 CLIP 검색 가능한 코퍼스를 만들어 실사 클립을 검색.
- applicability: 우리 파이프라인과 구조가 가장 유사(에이전트 CLI 오케스트레이션 + 강제 승인 게이트). 도입 후보: (1) scene_plan JSON 계약, (2) 슬라이드쇼 위험 점수 개념을 Ken Burns 단조로움 검출에 이식, (3) 게이트를 5개로 통합·비용 임계값 승인, (4) 렌더 후 자동 셀프리뷰(블랙프레임·자막 존재).
- evidence: README 표기 55.5k★, 6.9k fork; 최근 커밋 2026-08-22(#507 'feat/cjk-caption-support' 병합 — CJK 자막 지원 추가). 릴리스 태그 없음. tools/ 하위에 analysis/ 디렉터리 존재 확인.
- caveat: video_understand의 CLIP/BLIP-2 입출력·임계값은 README 문구만 확인, docs/tools.md는 404. 실제 채점 로직은 코드 열람 필요(추정). 명시적 페이싱 알고리즘은 문서화되지 않음.

### ContentMachine (Saganaki22)
- url: https://github.com/Saganaki22/ContentMachine
- what: 주제 → 실제 역사 이야기 4개 제안 → 씬 계획 → 씬당 이미지 4변형 → 이미지-투-비디오 → TTS → 메타데이터/썸네일까지 다큐 스타일 롱폼 준비 파이프라인(Node/React). 확인일 2026-09-02.
- pattern: 대본→샷: LLM이 '스마트 페이싱' 샷 리스트를 생성하되 길이를 영상 모델 제약(LTX-2 Pro 6/8/10s, Kling v3 3~15s)에 맞춰 사전에 고정(model-aware duration). 대본↔프롬프트: 씬 계획에서 LLM 구조화 출력, 7단계 시스템 프롬프트(스토리 선택·씬 계획·이미지 프롬프트·비디오 프롬프트·나레이션·메타데이터·썸네일)를 사용자가 편집 가능, 잘린 JSON 자동 복구. 씬당 4변형(establishing/intimate/detail/atmospheric) 생성 후 사람이 선택, 재생성 이력 화살표로 탐색. 캐릭터 레퍼런스 이미지를 매 요청에 첨부하되 '의상·포즈는 씬별, 외형만 고정'. 프로바이더: Replicate/fal.ai/Gemini API. 자동 QA 없음(429 지수 백오프 재시도만). 비용 4:30 다큐 약 $28.
- applicability: '씬당 샷타입 4변형 → 사람 선택' 및 '캐릭터 외형 고정, 의상·포즈 씬별 가변' 규칙은 우리 역사 인물 일관성에 직접 적용 가능. 사실 검증 없이 LLM이 이야기를 고르는 점은 우리 claim inventory 방식과 반대이므로 도입 불가.
- evidence: README 표기 108★, 26 fork, Apache-2.0; 최근 커밋 2026-03-02('Fix ReferenceError: autoSaveSession…').
- caveat: 나레이션이 시각 생성 뒤에 씬별로 생성됨(우리 TTS-선행 구조와 순서 반대). 씬 JSON 필드 상세는 README에 없음.

### ViMax (HKUDS)
- url: https://github.com/HKUDS/ViMax
- what: Director·Screenwriter·Producer·Video Generator 에이전트가 대본→스토리보드→캐릭터→영상까지 처리하는 에이전틱 영상 생성(Python, MIT). 확인일 2026-09-02.
- pattern: 스토리보드: 씬 파싱 → 샷 설계(앵글·전환·페이싱) → 샷별 레퍼런스 이미지 정렬, 카메라 연속성 추적. 일관성: 캐릭터 외형·환경 '자동 일관성 검증(Consistency Validation)' + 실패 시 더 강한 LLM으로 재시도. 프로바이더: Google Nano Banana/GPT Image 2(OpenRouter) 이미지, Veo/Seedance 영상 — 모두 API. 사람 개입: Agent Loop TUI/Web UI에서 계획·수정·렌더 제어, 산출물(대본·스토리보드) 검수, 렌더 체크포인트·세션 재개.
- applicability: '실패 시 상위 모델로 승격 재시도'와 '렌더 체크포인트/세션 재개'는 우리 장시간 배치(18~20분, 수백 샷)에 유용. 캐릭터 일관성 검증 로직은 인물 다큐에 참고.
- evidence: README 표기 12.2k★, 1.8k fork; 최근 커밋 2026-07-29, v1.2.0 Web UI 릴리스 2026-07-20.
- caveat: 일관성 검증이 비전 모델 채점인지 규칙 기반인지 README에서 불명(추정: VLM 기반).

### storyboard-ai (yogendra-yatnalkar)
- url: https://github.com/yogendra-yatnalkar/storyboard-ai
- what: 주제 → 리서치 → 대본 → Director Agent 씬 분할 → 화이트보드 스타일 이미지 → SAM3 컨투어 드로잉 애니메이션 → Gemini TTS → 자막. 확인일 2026-09-02.
- pattern: 핵심 차별점: '실존 인물·랜드마크 등 실세계 개체는 씬마다 웹에서 레퍼런스 이미지를 자동 검색해 이미지 생성기에 함께 입력'하여 구조적 정확성 확보. 타이밍: 라인아트 드로잉 애니메이션을 '나레이션 오디오 길이에 맞춰 늘리거나 조여' 추가 생성 비용 없이 길이 맞춤. 프로바이더: Gemini-3-pro-image, Veo-3.1(API). 품질 검증·사람 개입 없음.
- applicability: 우리 역사 인물·유물·지도 샷에 '레퍼런스 이미지 자동 검색 → 프롬프트 첨부' 단계를 시각 브리프에 추가하면 고증 오류(복식·건축) 감소 기대. 드로잉 애니메이션 길이 스트레칭은 Ken Burns 길이 맞춤과 동일 원리.
- evidence: README 표기 160★; 최근 커밋 2026-07-01('standalone execution support… without SAM3'), v1 2026-06-14.
- caveat: Google Flow 브라우저 경로에서는 레퍼런스 이미지 첨부 UI 자동화가 추가로 필요(추정).

### claude-faceless-shorts-creator (hassancs91)
- url: https://github.com/hassancs91/claude-faceless-shorts-creator
- what: Claude Code 스킬(/make-short 등 5개)로 대본→beats.json→Remotion TSX 합성→ElevenLabs 단어 타임스탬프 자막→렌더까지 수행하는 숏폼 공장. 확인일 2026-09-02.
- pattern: 대본→샷: 6비트 문법 'HOOK(프레임0=썸네일) → SETUP → QUIZ → REVEAL → TWIST → LOOP'로 script.md + beats.json 생성 후 Claude가 타임라인 구성. 캐릭터: character.json + 레퍼런스 PNG로 고정. 자막: ElevenLabs가 합성 시 단어별 타임스탬프 반환. 품질: 'Claude가 폰 스케일 PNG를 프레임 단위로 렌더해 비전으로 분석'하는 자체 시각 QA 게이트.
- applicability: 우리 '5단계 구조'를 beats.json 같은 명시적 비트 스키마로 강제하고, 렌더 프레임을 Claude 비전으로 검수하는 방식은 Ken Burns·자막 렌더 후 QA에 그대로 적용 가능(비용은 샘플링 프레임으로 제어).
- evidence: README 표기 201★, MIT; 최근 커밋 2026-08-18(docs). topics 페이지 'Updated Aug 18, 2026'.
- caveat: 숏폼(60초 내) 전제. 롱폼에서는 비트 문법을 5단계 비율(0~10%/10~30%/…)로 재정의해야 함.

### youtube-shorts-pipeline / Verticals (rushindrasinha)
- url: https://github.com/rushindrasinha/youtube-shorts-pipeline
- what: 뉴스 리서치 → 대본(60~90초) → Gemini Imagen b-roll 3장 → TTS → Whisper 단어 타임스탬프 → ffmpeg Ken Burns 조립 → 업로드. 확인일 2026-09-02.
- pattern: 대본 단계가 '나레이션 텍스트 + b-roll 이미지 프롬프트'를 함께 출력(니치 프로필이 시각 어휘 결정). 프로바이더: Gemini Imagen API, 실패 시 단색 'fallback frame'으로 파이프라인 중단 방지. 모션: ffmpeg Ken Burns zoom/pan. 사람 개입: 'The most important human checkpoint is the draft: hook, factual claims, and whether the video has a real reason to exist' — 초안 검토를 유일 핵심 게이트로 명시, 새 니치는 --dry-run.
- applicability: '생성 실패 시 폴백 프레임 삽입 후 진행'은 우리 Flow 생성 실패 샷을 플레이스홀더로 채워 렌더를 막지 않고 후속 재생성하는 전략으로 적용. 사람 게이트를 '훅·사실 주장' 초안 단계에 집중하는 원칙도 우리 검증 단계와 일치.
- evidence: README 표기 2.3k★; 최근 커밋 2026-06-09(v3.1.0, edge-tts 7.x 범프). 커밋 공동저자 Claude.
- caveat: 영상당 이미지 3장이라 샷 분할 논리는 사실상 없음. Ken Burns 파라미터·방향 교대 규칙 미문서화.

### clawvid (neur0map)
- url: https://github.com/neur0map/clawvid
- what: OpenClaw 에이전트용 숏폼 CLI: TTS 우선 → 오디오 길이로 타이밍 산출 → fal.ai 이미지/영상/SFX/BGM → Remotion 16:9·9:16 합성. 확인일 2026-09-02.
- pattern: 샷 분할·타이밍: 'TTS-first' — 씬별 narration을 먼저 합성하고 '실측 오디오 길이'를 씬 길이로 채택(+패딩), ffmpeg adelay로 씬 시작점에 나레이션 배치. 씬 JSON 스키마: id, type(image|video), narration, image_generation{model, prompt}, video_generation{model, duration, negative}, sound_effects[], effects[](vignette, kenburns, grain, glitch…), timing{}(자동 계산). 프로바이더: fal.ai 단일 게이트웨이(Kling Image v3 $0.028, Nano Banana Pro $0.15 레퍼런스). QA: Sharp로 치수·포맷·무결성 검사, analysis.ts 존재. 사람 개입: 에이전트가 사전 질문 후 전자동.
- applicability: 우리 '실측 샷 타이밍' 단계와 동일 철학. 씬 JSON에 effects 배열로 모션을 선언하는 방식은 우리 시각 브리프 스키마에 motion 필드로 흡수 가능.
- evidence: README 표기 22★, 97 tests; 최근 커밋 2026-02-14('frame chaining for seamless video continuity').
- caveat: 소규모·베타. 이미지-문장 정합 채점은 없음.

### reelforge (gongnyang, 한국어 우선)
- url: https://github.com/gongnyang/reelforge
- what: 브리프 → 나레이션·자막·씬 편집 가능한 숏/롱폼을 결정론적 HTML/GSAP 렌더로 만드는 '에이전트 네이티브 영상 공장', 무키(keyless) 스택, 한국어 우선. 확인일 2026-09-02.
- pattern: 페이싱: D2 Arc 단계에서 '강도 0~100 곡선 + 아크 프리셋(ramp, double-peak, cliff, steady-pulse) + 비트 그리드'로 씬 강도를 설계하고 D3 라우팅 결정표가 검증된 31개 안무(모션) 갤러리에서 씬별 기법을 배정. 프롬프트가 아니라 검증 통과 '조각(fragment)'을 keep/mutate 계약으로 재사용. QA 2단계: 렌더 전 direction-lint(RF-DIR-001~008: 문법·슬롯 예산·아크 일관성·전환 인접성), 렌더 후 strip QC(blank·저대비·모션 정지 자동 스캔 + 수동 검토) 실패 씬은 사유 첨부 후 재설계(씬당 최대 2회). '파일럿 게이트: 피크 씬 1개 단독 렌더가 통과해야 전체 진행'.
- applicability: 우리 5단계 구조를 강도 곡선(훅 고밀도→균열→증거→절정 피크→통찰 하강)으로 수치화하고, Ken Burns 기법을 검증된 갤러리에서 결정표로 배정하는 방식 도입 가능. '피크 씬 먼저 렌더해 검수' 게이트는 18~20분 배치 낭비 방지에 효과적. 한국어 타이포·자막 규칙 참고.
- evidence: topics 페이지 81★, 'Updated Jul 30, 2026'; 최근 커밋 2026-07-30(CC0 BGM 교체), README 3개 국어.
- caveat: 쇼케이스는 12씬 22.9초로 롱폼 실증 없음. 이미지 프로바이더 명시 없음('키리스' 스택). LLM 프롬프트 생성이 아닌 결정론적 기법 라우팅이라 우리 생성 이미지 파이프라인과는 결합 방식이 다름.

### video-podcast-maker (Agents365-ai)
- url: https://github.com/Agents365-ai/video-podcast-maker
- what: 코딩 에이전트(Claude Code/OpenClaw/OpenCode)가 SKILL.md로 주제 → 리서치 → 대본 → 11개 TTS 백엔드 → Remotion 4K 합성 → 게시까지 구동하는 5~10분 나레이션 영상 도구. 확인일 2026-09-02.
- pattern: 대본 분할: podcast.txt를 [SECTION:xxx] 블록으로 나누고 각 섹션에 훅·전환 포함. 페이싱 규칙: '중국어 약 280자/분, 영어 약 150단어/분', 5~10분 = 1,400~2,800자. 시각: 사용자 파일·스톡(assetseeker)·AI 정지 이미지(imagencn)·AI B-roll(videogencn)·Hyperframes 오버레이, 자산별 라이선스·출처 매니페스트 기록. 사람 개입: '약한 대본은 4K 쓰레기를 렌더한다' — TTS 전 수동 대본 검토 필수, Remotion Studio 프리뷰, 4K 렌더 명시 확인.
- applicability: 우리 벤치마크(28자 중앙값 × 12.7문장/분 ≈ 356자/분)와 비교 가능한 분당 글자 페이싱 규칙의 선례. 자산 출처 매니페스트는 사료 이미지·생성 이미지 혼용 시 필요.
- evidence: topics 페이지 1.6k★; v5.2.1, 최근 커밋 2026-08-01('update pipeline diagram to current 11-step workflow').
- caveat: 이미지-문장 정합 자동 채점 없음. README에 '아직 성숙하지 않음' 명시.

### StoryBoard-Generator (Gunnika)
- url: https://github.com/Gunnika/StoryBoard-Generator
- what: 장문 서사를 TextTiling으로 씬 분할 → DistilBART-xsum 한 줄 요약을 이미지 프롬프트로 → Stable Diffusion 생성 → CLIP 평가하는 비지도 스토리보드 파이프라인(학술 프로젝트). 확인일 2026-09-02.
- pattern: 샷 분할: 문장 기반 토픽 분할(TextTiling). 일관성: 첫 이미지 독립 생성, 이후 이미지는 '프롬프트 유사도가 가장 높은 기존 이미지'에 조건화. 평가: (1) CLIP 텍스트-이미지 정합 점수, (2) 이미지 임베딩 쌍별 코사인 평균으로 '코히런시 점수'.
- applicability: 'CLIP 정합 점수 + 인접 이미지 스타일 코히런시 점수' 두 지표를 우리 QA에 그대로 정의 가능(쉽선비 두들 스타일 이탈 검출에 코히런시 점수 유용).
- evidence: README 표기 14★; 최근 커밋 2024-01-03. 소규모·미유지.
- caveat: 영문 텍스트 전제. 한국어 문장은 번역 또는 영문 visual_prompt 기준 채점 필요(추정).

### ai-video-editor (mazsola2k)
- url: https://github.com/mazsola2k/ai-video-editor
- what: 실사 푸티지를 VLM으로 '보고' 흥미도 분류 → 속도 램핑·컷 편집하는 파이프라인(Linux/CUDA). 확인일 2026-09-02.
- pattern: 2초마다 프레임 샘플링 → Qwen2.5-VL-7B가 캡션 + 품질 1~10점 + 분류. CLIP ViT-B/32로 텍스트-이미지 크로스모달 매칭, ResNet-50으로 지각 유사도. 점수→속도 티어(Interesting 1.0x / Moderate 2x / Low 4x / Boring 6x·제외 / Skip), 9~10점은 '쇼케이스' 티저(최대 45초). 오디오 무음(≤-35dB, ≥3s) + 프레임 정지(픽셀차 0.02)면 boring 강등.
- applicability: 'VLM 1~10 채점 + CLIP 정합 + 임계값 티어'를 우리 생성 이미지 QA에 이식: 예) VQA/CLIP 정합 하위 20%는 자동 재생성, 상위만 사람 승인. 로컬 Qwen2.5-VL-7B는 한국어 프롬프트도 처리 가능(추정).
- evidence: README 표기 60★, v1.2.0 'Last Updated: April 11, 2026'; 최근 커밋 2026-04-11.
- caveat: 실사 편집용이라 생성 이미지 정합 판정은 우리가 프롬프트 재설계 필요.

### t2v_metrics / VQAScore (linzhiqiu)
- url: https://github.com/linzhiqiu/t2v_metrics
- what: 텍스트-이미지/영상 정합을 VQA 형식('이 이미지가 텍스트를 보여주나?' 확률)으로 채점하는 라이브러리. v3.1은 Qwen2.5-VL/Qwen3-VL/GPT-4o/Gemini 지원, CLIPScore·ImageReward·PickScore도 포함. 확인일 2026-09-02.
- pattern: scorer = t2v_metrics.VQAScore(model='qwen2.5-vl-7b'); scorer(images=[...], texts=[...]). 후보 이미지 랭킹(best-of-n)만으로 사람 정합 평가를 개선, 구성·속성 결합·공간관계에서 CLIPScore/PickScore/ImageReward보다 2~3배 효과(저자 주장). Google DeepMind Imagen3/4, ByteDance, NVIDIA 채택.
- applicability: 우리 '이미지-문장 일치 점수 자동화'의 1순위 후보. 씬당 2~4장 Flow 생성 → VQAScore로 랭킹 → 상위 1장만 사람 승인. 소형 qwen3-vl-2b로 VRAM 절감 가능.
- evidence: README 표기 600★; 최근 커밋 2026-06-05(v3.1 release 병합). 'Most models require 40GB+ GPUs'.
- caveat: GPU 요구 큼(소형 모델 대안). 한국어 텍스트 직접 입력 정확도는 미검증(Qwen 계열은 다국어라 가능성 높음, 추정).

### imscore (RE-N-Y)
- url: https://github.com/RE-N-Y/imscore
- what: PickScore, ImageReward, HPSv2/v3, VQAScore, CLIPScore, MPS, CycleReward, EvalMuse, LAION Aesthetic 등을 단일 인터페이스로 제공하는 미분 가능 이미지 보상 함수 모음. 확인일 2026-09-02.
- pattern: model = SiglipPreferenceScorer.from_pretrained('RE-N-Y/pickscore-siglip'); model.score(pixels, [prompt]). HF에서 모델 자동 다운로드, transformers<5 필요.
- applicability: 정합(VQAScore/CLIP)과 미학(HPS/Aesthetic)을 한 번에 계산해 '정합 임계값 + 미학 상위'로 필터하는 복합 QA 구현에 편리.
- evidence: README 표기 119★; 최근 커밋 2026-03-30(transformers<5 고정).
- caveat: 연구용 라이브러리, 파이프라인 통합 예시는 없음.

### clipscore (jmhessel, EMNLP 2021)
- url: https://github.com/jmhessel/clipscore
- what: 참조 캡션 없이 CLIP 코사인 유사도로 이미지-텍스트 정합을 채점하는 원조 구현(python clipscore.py candidates.json image_dir/). 확인일 2026-09-02.
- pattern: CLIPScore = w·max(cos(img, txt), 0) (w=2.5). 문자 그대로의 캡션에서 사람 판단과 높은 상관, RefCLIPScore는 참조 캡션 병용.
- applicability: 가장 가볍고 CPU에서도 가능한 기준선. Flow 생성 직후 OCR/pHash와 같은 계층에 CLIPScore 하한선(예: 0.6 미만 자동 재생성)을 두는 저비용 출발점.
- evidence: README 표기 251★, 25 fork, 31 commits(최근 날짜 미표시).
- caveat: 영어 CLIP 전제, 다국어는 multilingual-CLIP 대체 필요(추정). 구성·속성 결합 판정은 VQAScore보다 약함.

### gflow-cli (ffroliva)
- url: https://github.com/ffroliva/gflow-cli
- what: Google Flow(Veo/Imagen) 비공식 CLI: 영속 Playwright Chrome 프로필로 t2i/t2v/i2v/r2v·캐릭터·업스케일·배치·다중 씬 manifest(gflow movie) 수행, 출력은 로컬/S3/GCS. 확인일 2026-09-02.
- pattern: 브라우저 프로바이더 견고성: 'Google이 Playwright 번들 Chromium을 거부'하므로 실제 Chrome 필수, HTTP 직접 전송은 reCAPTCHA로 차단. '재제출하지 않고 구분된 exit code로 즉시·명확히 실패'(예: exit 23 = 선택자 드리프트). 배치 항목을 '제출 전에 로컬 기록'해 크레딧 이중 소모 방지. 이미지 생성은 크레딧 무료, Veo 영상만 과금.
- applicability: 우리 Google Flow CDP 자동화의 직접 비교 대상. '제출 전 원장 기록 → 결과 매칭', '선택자 드리프트 전용 실패 코드', 'MCP 서버 병행 제공' 3가지를 이식하면 배치 안정성 향상.
- evidence: README 표기 140★, develop 브랜치 1,555 commits; 최근 커밋 2026-09-02(#633, #632 — 공동저자 claude).
- caveat: 비공식 도구로 Flow UI 변경 시 파손 위험(README도 selector drift를 상정). 이용약관 리스크는 사용자 판단.

### google-flow-browser-mcp (TMSSS05)
- url: https://github.com/TMSSS05/google-flow-browser-mcp
- what: CDP(포트 9222) 우선·Playwright 보조로 Google Flow를 제어하는 MCP 서버(15+ 툴: flow_generate_image(Nano Banana Pro/2, Imagen 4, 레퍼런스 이미지 지원), flow_create_character, flow_use_grid_architect 배치 샷, flow_discover_ui 등). 확인일 2026-09-02.
- pattern: 세션: 기존 Chrome 프로필 로그인 재사용, expectedAccount 검증, 비밀번호 미저장. 완료 감지: 5초 간격 × 최대 120회 폴링(약 5분). 단일 작업 큐로 병렬 충돌 방지, 캡차/검증 화면이면 정지, actionDelayMs 800ms 안티디텍션 지연. flow_discover_ui가 버튼/입력 요소를 매핑해 선택자 맵을 자동 갱신. 영상 생성은 '생성 버튼 직전에 멈춤'으로 크레딧 보호.
- applicability: 우리 CDP 계층에 'UI 자동 탐색으로 선택자 맵 갱신', '계정 일치 검증', '단일 큐 + 폴링 상한', '레퍼런스 이미지 첨부 툴' 설계를 참고. Claude Code에서 MCP로 노출하면 시각 브리프→생성 호출을 에이전트가 직접 수행 가능.
- evidence: README 표기 49★; 최근 커밋 2026-05-31(감지 시스템 수정 3건).
- caveat: 소규모·최근 3개월 미갱신. Flow UI 변경 추적 지속 필요.

### visual-skills (smixs)
- url: https://github.com/smixs/visual-skills
- what: 에이전트용 '영화 감독' 스킬: 드라마투르기(Murch 6법칙, 블로킹, 몽타주) + Seedance/Kling/Veo/Nano Banana 2/GPT Image 2 프롬프트 문법. 확인일 2026-09-02.
- pattern: 스토리보드 행 14필드(프레이밍·구도·카메라·움직임 이유·시선 흐름·길이·컷 타입·사운드·조명·앵커 5종). 프롬프트 생성 전 품질 게이트 2종: 6점 드라마투르기 체크와 '3디테일 감사'(환경 압력·미세 동작·모티프 각 1개) — 실패 프롬프트는 출력하지 않음. 리듬: 'long → shorter → shorter → pause → impact', 15/30/60/90초 비트 구조. 모델 선택: Nano Banana 2(실존 장소·극단 비율·저비용 배치), GPT Image 2(밀집 텍스트·브랜드).
- applicability: 시각 브리프 스키마에 shot_type·camera·motion_reason·anchor 필드를 추가하고, 생성 전 lint로 '고증 개체 1·행동 1·모티프 1' 조건을 검사하는 규칙형 게이트를 도입 가능. 우리 절정 구간(70~90%)에 '롱→쇼트→포즈→임팩트' 리듬 배정.
- evidence: README 표기 242★; 최근 갱신 2026-08-04(Seedance 2.5 레퍼런스 추가).
- caveat: 실사·시네마틱 지향. 두들 스타일 다큐에는 필드 축소 필요.

### spoonstill (VijaysinghPuwar) + Ken Burns 자동화 기법(stevecv 블로그)
- url: https://github.com/VijaysinghPuwar/spoonstill
- what: (정지 이미지 + 나레이션) 쌍을 '나레이션 경계에서 컷'하며 Ken Burns 모션으로 MP4를 만드는 Rust/FFmpeg 배치 렌더러(001.jpg↔001.m4a/txt 이름 매칭 또는 순서 매칭, project.yaml·scenes.csv). 보조 출처: stevecv 블로그 https://stevecv.com/blog/ken-burns-effect-automated-video-production.html — zoompan z='min(zoom+0.001,1.5)', d=250, 4개 프리셋(zoom_in/zoom_out/pan_l2r/pan_r2l), get_varied_motions()로 '연속 샷 동일 모션 금지', concurrent.futures 병렬 렌더, 원본은 출력 해상도의 1.33배 이상(2560×1440). 확인일 2026-09-02.
- pattern: 샷 길이 = 해당 나레이션 길이(문장 기반 컷), 각 정지 이미지에 느린 줌 또는 팬, 자막은 FFmpeg가 아닌 자체 드로잉. Ken Burns 방향 교대 제약.
- applicability: 우리 Ken Burns 단계에 '직전 샷과 다른 모션 타입 강제', '원본 해상도 여유 확보', '샷별 병렬 렌더' 규칙을 명시적으로 넣을 근거.
- evidence: spoonstill 0★, master 55 commits, topics 페이지 'Updated Aug 2026', 프리뷰 빌드(M2 완료). stevecv 블로그는 GitHub 코드 미공개.
- caveat: 둘 다 소규모/개인 프로젝트. 페이싱(초반 고밀도) 규칙은 없음.

### Autotube (Hritikraj8804)
- url: https://github.com/Hritikraj8804/Autotube
- what: n8n 워크플로로 주제 → 대본(hook/content/CTA) → Pollinations.ai/Z-Image 이미지 → OpenTTS → MoviePy(Ken Burns 줌·크로스페이드·텍스트 오버레이) → YouTube 업로드. 확인일 2026-09-02.
- pattern: 대본 섹션 단위로 이미지 생성, MoviePy Ken Burns. 품질 검증·사람 승인 없음(전자동).
- applicability: n8n 노코드 오케스트레이션 예시로만 참고. QA 부재는 반면교사.
- evidence: README 표기 64★, 13 fork, 18 commits(날짜 미표시).
- caveat: 30초 숏폼 전용.

### Awesome-Evaluation-of-Visual-Generation (ziqihuangg)
- url: https://github.com/ziqihuangg/Awesome-Evaluation-of-Visual-Generation
- what: 시각 생성 평가 지표·모델·시스템(VBench++, MLLM-as-a-Judge, VQAScore 등) 목록. 확인일 2026-09-02(검색 결과에서 확인, README 세부 미열람).
- pattern: VLM-as-a-Judge: 프롬프트·생성물·루브릭을 사람 평가자와 동일하게 제공하고 체크리스트 기반 채점(VideoScience-Bench 등 2025~2026 논문).
- applicability: 우리 VLM 채점 루브릭(고증·스타일 일치·텍스트 깨짐·문장 핵심 개체 존재) 설계 시 참고 문헌 인덱스.
- evidence: 스타 수·갱신일 미확인.
- caveat: 목록 저장소이므로 직접 코드 없음.

## patterns

- **TTS 선행 실측 타이밍(TTS-first, cut on narration boundaries)** (SuperTonic3 문장 TTS → 실측 샷 타이밍 (현행 유지, 다만 '샷 길이 확정 후 시각 브리프' 순서를 스키마로 고정)): 문장/절 단위 나레이션을 먼저 합성하고 실측 오디오 길이를 샷 길이로 채택. 시간 고정 분할은 스톡영상형에서만 사용. 이미지 생성 전에 씬 길이가 확정되므로 페이싱 검증을 이미지 생성 전에 할 수 있다. [seen in: clawvid, spoonstill, storyboard-ai(애니메이션 길이를 나레이션에 맞춰 스트레칭), MoneyPrinterTurbo(TTS 타임스탬프 자막), video-podcast-maker]
- **JSON scene_plan 단일 계약 + 생성 전 lint** (시각 브리프(현재 에피소드별 수작업 규칙표) → Codex --output-schema/agy 구조화 출력으로 전환, 규칙표는 lint 규칙으로 코드화): 대본↔시각의 유일한 계약을 구조화 JSON(scene_id, sentence_ids, narration, visual_prompt, shot_type, motion, reference_entity, duration)으로 두고, 프롬프트 출력 전 규칙 게이트(3디테일 감사·direction-lint·잘린 JSON 복구)로 검사. 사람 승인은 이 JSON에서 1회. [seen in: OpenMontage scene_plan, clawvid scene JSON(effects 배열), claude-faceless-shorts-creator beats.json, ContentMachine 7단계 프롬프트+JSON repair, visual-skills 14필드 샷카드+품질 게이트, reelforge direction-lint RF-DIR-001~008]
- **이미지-문장 정합 자동 채점(CLIP/VQAScore/VLM 루브릭) → best-of-n 선별** (OCR/pHash QA → 사람 승인 (승인 전 자동 점수 필터 추가; 한국어 문장은 영문 visual_prompt 기준 채점 또는 Qwen-VL 계열 사용, 추정)): 씬당 2~4변형 생성 후 (1) CLIPScore 또는 VQAScore로 visual_prompt/문장 정합 점수, (2) 인접 이미지 임베딩 코사인으로 스타일 코히런시, (3) VLM 1~10 루브릭(고증·텍스트 깨짐·핵심 개체 존재)을 계산해 하위는 자동 재생성, 상위 1장만 사람 승인 대기열에 올림. OCR/pHash와 같은 계층에 배치. [seen in: StoryBoard-Generator(CLIP 정합+코히런시), ai-video-editor(CLIP ViT-B/32 + Qwen2.5-VL 1~10점 티어), OpenMontage video_understand(CLIP/BLIP-2, README 기재), t2v_metrics VQAScore(best-of-n 랭킹), imscore(정합+미학 통합), claude-faceless-shorts-creator(Claude 비전 프레임 QA), ContentMachine(4변형 사람 선택)]
- **실세계 개체 레퍼런스 그라운딩 + 캐릭터 외형 고정/의상·포즈 가변** (시각 브리프(reference_entity 필드) → Google Flow 생성(레퍼런스 첨부 자동화)): 실존 인물·유물·건축은 씬마다 웹 레퍼런스 이미지를 검색해 생성기에 첨부하고, 반복 등장 인물은 character.json+레퍼런스 PNG로 외형만 고정하되 시대 의상·포즈는 씬별 프롬프트에서 결정. [seen in: storyboard-ai(레퍼런스 자동 검색), ContentMachine('외형만 고정'), ViMax(일관성 검증+재시도), clawvid(nano-banana-pro 레퍼런스), google-flow-browser-mcp(flow_generate_image 레퍼런스 이미지·flow_create_character)]
- **강도 곡선 기반 페이싱 + 모션 다양성 제약 + 슬라이드쇼 위험 점수** (페이싱(5단계 구조 0~10/10~30/30~70/70~90/90~100%를 강도 곡선으로 수치화) + Ken Burns 모션 자동 배정 + 렌더 전 단조로움 검사): 영상 전체를 0~100 강도 곡선(아크 프리셋)으로 설계해 구간별 샷 길이·모션 세기를 배정하고, 연속 샷 동일 Ken Burns 모션 금지, 반복·약한 모션·장식적 시각 등 6차원 '슬라이드쇼 위험' 점수가 임계 초과면 렌더 차단. 절정 구간은 '롱→쇼트→쇼트→포즈→임팩트' 리듬. [seen in: reelforge(강도 0~100 + 아크 프리셋 + 비트 그리드), stevecv get_varied_motions(), OpenMontage 슬라이드쇼 위험 6차원, visual-skills 몽타주 리듬, video-podcast-maker(분당 글자 수 규칙)]
- **강제 승인 게이트 5개 + 비용 임계값 + 피크 씬 파일럿 렌더 + 폴백 프레임** (사람 승인 다수 → 게이트 통합(대본 사실검증 후 / scene_plan / 이미지 상위 후보 / 최종 렌더), 절정 구간 파일럿 렌더 우선): proposal/script/scene_plan/assets/publish에서만 사람이 멈추고 나머지는 자동. 비용 $X 초과 작업은 건별 승인. 전체 렌더 전 '피크 씬 1개'를 먼저 완성해 검수(파일럿 게이트). 생성 실패 샷은 플레이스홀더로 채워 렌더를 막지 않고 후속 재생성. [seen in: OpenMontage('enforced, not suggested', $0.50), rushindrasinha(초안 훅·사실 주장이 최우선 체크포인트, fallback frame), reelforge(파일럿 게이트, 씬당 재설계 최대 2회), ViMax(렌더 체크포인트·세션 재개), video-podcast-maker(대본 수동 검토 필수, 4K 렌더 명시 확인)]
- **브라우저 프로바이더 견고성 계층(실 Chrome 영속 프로필 + CDP + 원장 + fail-fast)** (Google Flow(브라우저 CDP 자동화) 이미지 생성 단계): Google Flow 자동화는 실제 Chrome 프로필 로그인 재사용, CDP 9222 연결, 계정 일치 검증, 제출 전 배치 원장 기록(이중 과금 방지), 단일 작업 큐, 5초×120회 폴링 상한, 캡차 감지 시 정지, 선택자 드리프트 전용 exit code, UI 자동 탐색으로 선택자 맵 갱신, MCP 노출로 에이전트 직접 호출. [seen in: gflow-cli, google-flow-browser-mcp, MoneyPrinterTurbo/OpenMontage(API 프로바이더 추상화·점수 기반 선택은 대조군)]


# channel ops-ci-agents

## summary
조사일 2026-09-02. (1) anthropics/claude-code-action(8.8k★, MIT, v1.0.213 2026-09-01)은 `prompt` 입력만 주면 @claude 멘션 없이 pull_request 이벤트로 자동 실행되는 '자동화 모드'를 공식 지원하며, `on.pull_request.paths`로 `runs/**/script*.json`·`*brief*.json`만 트리거하고, `claude_args: --json-schema`로 `steps.<id>.outputs.structured_output`에 검증된 JSON을 받아 후속 스텝에서 게이트(라벨 부착·체크 실패)로 쓸 수 있다. 인라인 코멘트는 `mcp__github_inline_comment__create_inline_comment` 도구를 `--allowedTools`에 명시해야만 동작하고, 기본은 워크플로 로그에만 출력된다. 코드가 아닌 JSON/마크다운 리뷰도 파일 읽기 도구만 있으면 동일하게 동작한다(공식 문서에 '문서 동기화' 용례 명시). (2) Claude Agent SDK(Python 8.0k★, v0.2.151 2026-09-01)와 `claude -p --bare --output-format json --json-schema`는 '생성→스키마 검증→재프롬프트' 루프를 SDK 내부에 내장(`error_max_structured_output_retries`)하고 있어, 현재 우리의 agy/Codex 프로바이더+외부 JSON Schema 검증 구조를 그대로 대체·병행할 수 있다. 다단계(생성→검증→재생성) 오케스트레이션의 공식 레퍼런스는 claude-cookbooks(52.4k★)의 evaluator_optimizer/orchestrator_workers 노트북, claude-agent-sdk-demos(2.7k★)의 Research Agent(서브에이전트 병렬→합성), Ralph Wiggum 플러그인(Stop 훅 기반 반복, --max-iterations)이다. (3) 대본 품질 회귀 테스트는 promptfoo(24.8k★, 최근 커밋 2026-09-02)의 `exec:`/python 프로바이더로 우리 생성 스크립트를 그대로 감싸고 결정적 assert(문장 길이 중앙값·분당 문장 수·5단계 구조 비율)+`llm-rubric`(Anthropic grader 지정 가능)을 섞어 promptfoo-action의 `fail-on-threshold`로 PR을 막는 구성이 가장 즉시 적용 가능. deepeval(18.0k★)의 G-Eval `evaluation_steps`+pytest `assert_test`, ragas(15.6k★)의 AspectCritic(3회 판정 다수결)/RubricsScore도 동급 대안. (4) generator×N+critic+judge는 프레임워크 예제(AutoGen RoundRobin primary+critic 'APPROVE' 종료—단 AutoGen은 유지보수 모드, langgraph-reflection—2026-04-01 아카이브, CrewAI 58k★)보다 2026-03 논문 'When Agents Disagree'(다양한 생성기+judge 선택이 단일 모델 대비 승률 0.810, 합성 방식은 42개 과제 중 0승)과 JETTS(자연어 비평으로 재생성 유도는 비효과, 재순위화는 유효)의 결론이 설계에 더 중요하다: 'N개 생성→pairwise judge로 선택'이 '비평→수정 반복'보다 안정적. 구현체로 jury-arena(6★, 최대 3심사 다수결+Glicko-2), judges 라이브러리(337★, Jury.vote)가 있으나 소규모라 참고용. (5) HITL 축소는 Trust or Escalate(ICLR 2025: 심사자 신뢰도 기반 선택적 신뢰, 인간 동의율 80% 보장하며 약 80%를 자동 처리), 계층화 표본 검토(Galileo: 인간 검증량 최대 85% 절감, Cohen's kappa를 헤드라인 지표로), Braintrust(주당 50~100건, 0~3점 저정밀 척도)로 근거가 있고, 영상 파이프라인 사례로는 OpenMontage(AGPLv3, 최근 커밋 2026-08-22; 제안·대본·씬플랜·에셋·게시 5단계 승인 게이트, '승인 기록 없는 완료'를 체크포인트 writer가 거부)가 우리 artifact_approval_v2.schema.json 구조와 가장 유사하다. 결론: 즉시 도입 우선순위는 ①promptfoo 골든셋 회귀 CI ②claude-code-action 자동 QA 코멘트(대본/브리프 JSON 변경 시) ③Agent SDK 구조화 출력으로 생성·검증 루프 내재화 ④N-생성+judge 선택을 대본 훅(0~10%) 구간에 한정 적용 ⑤judge 점수·kappa 보정 후 예외 승인 전환.

## items

### anthropics/claude-code-action (Claude Code GitHub Action v1)
- url: https://github.com/anthropics/claude-code-action
- what: GitHub Actions 러너 안에서 Claude Code 전체 런타임을 실행하는 공식 액션. `prompt` 입력이 있으면 '자동화 모드'로 @claude 멘션 없이 어떤 GitHub 이벤트(pull_request, schedule 등)에서도 실행되고, 없으면 '대화 모드'로 @claude 멘션에 응답한다. `claude_args`로 `--max-turns`, `--model`, `--allowedTools`, `--json-schema`를 넘길 수 있고, `--json-schema` 사용 시 액션 출력 `steps.<id>.outputs.structured_output`에 검증된 JSON 문자열이 담겨 후속 스텝에서 `fromJSON()`으로 분기할 수 있다. PR 인라인 코멘트는 `--allowedTools "mcp__github_inline_comment__create_inline_comment"`를 명시해야 해당 MCP 서버가 기동된다. `use_sticky_comment`(단일 코멘트 갱신), `classify_inline_comments`, `include_fix_links` 등 코멘트 제어 입력 제공.
- pattern: PR 이벤트 트리거 자동 QA 리뷰 코멘트 + 구조화 출력 게이트
- applicability: 우리 저장소에서 `on.pull_request.paths: ['runs/**/script*.json','runs/**/*brief*.json','schemas/**']`로 필터하고, prompt에 '인류의 서재 5단계 구조 비율·문장 중앙값 28자·12.7문장/분·claim_inventory 인용 누락·페르소나 규칙 위반을 점검하라'를 넣은 뒤 `--json-schema '{"verdict":"pass|warn|fail","issues":[...]}'`로 받아, fail이면 `gh pr edit --add-label needs-human-review` 또는 체크 실패로 연결. 코드가 아닌 JSON/마크다운 파일이라도 Read 도구만 있으면 동일하게 리뷰 가능(공식 README의 '문서 동기화' 용례). CLAUDE.md에 CI 전용 섹션(리뷰 기준·출력 형식)을 두면 매 실행에 반영됨.
- evidence: 확인 2026-09-02: GitHub 페이지 표기 8.8k★, 2.1k forks, MIT, 781 commits. 최근 커밋 2026-09-01 'chore: bump Claude Code to 2.1.258 and Agent SDK to 0.3.258'. 릴리스 페이지 최신 v1.0.213(9월 1일, 연도 미표기—2026으로 추정). docs/usage.md에 자동화 모드 YAML·`structured_output` 출력·`--json-schema` 예제(flaky test 판정) 명시. docs/security.md: 쓰기 권한 사용자만 트리거, 봇은 `allowed_bots` 명시 필요, PR 본문 HTML 주석·보이지 않는 문자 등 프롬프트 인젝션 경로 경고.
- caveat: (a) 기본값은 워크플로 로그 출력이므로 코멘트를 달려면 prompt로 지시하고 코멘트 도구를 허용해야 함. (b) PR 본문·사료 파일 내용이 프롬프트 인젝션 벡터가 됨—우리 사료(sources/)는 외부 텍스트이므로 `--allowedTools`를 Read·인라인코멘트로 최소화하고 Bash/Write 금지 권장. (c) 실행마다 API 토큰+Actions 분 소모: `--max-turns 5~10`, `timeout-minutes`, `concurrency` 설정 필수. (d) 공개 저장소 포크 PR에는 시크릿이 노출되지 않아 실행 안 됨. (e) OAuth 토큰(구독)은 발급자 개인 구독에 묶이므로 조직 공유 시 API 키 권장.

### Claude Code GitHub Actions 공식 문서 (code.claude.com)
- url: https://code.claude.com/docs/en/github-actions
- what: 설치(`/install-github-app` 또는 수동), 대화/자동화 모드 판별 규칙, 트리거 가능 주체(쓰기 권한 사용자·사람 액터), code-review 플러그인을 `prompt: "/code-review:code-review --comment ..."`로 호출하는 예제, 스케줄 실행 예제, 비용 관리(`--max-turns`, 타임아웃, 동시성), GitHub App 권한 표, 클라우드 프로바이더(Bedrock/Vertex/Foundry) 연동.
- pattern: 스킬 기반 리뷰 워크플로 (prompt에 /skill 호출)
- applicability: 우리 저장소 `.claude/skills/script-qa/SKILL.md`에 대본 QA 규칙(5단계 구조, 문장 통계, claim 인용 검사 스크립트 호출)을 스킬로 정의하고, 워크플로 prompt를 `/script-qa --comment`로 호출하면 리뷰 기준을 코드로 버전 관리할 수 있다. 스킬 frontmatter `allowed-tools`로 `Bash(python scripts/audit_episode_quality.py *)`처럼 기존 감사 스크립트 실행을 허용하면 결정적 검사+LLM 판단을 한 코멘트로 합칠 수 있음.
- evidence: 확인 2026-09-02: 공식 문서에 '자동화 모드: prompt 입력이 있으면 멘션 없이 실행, 결과는 기본적으로 워크플로 로그', '`--comment` 없으면 아무것도 게시하지 않음', 'Claude는 드래프트·이미 Claude 코멘트가 있는 PR을 건너뜀' 명시. `--allowedTools`를 claude_args에 반드시 두어야 인라인 코멘트 MCP가 기동된다는 주의문 존재.
- caveat: 스케줄 트리거는 기본 브랜치에서만 실행되고 공개 저장소는 60일 비활성 시 비활성화됨. 리뷰 스킵 규칙(이미 코멘트가 있으면 건너뜀)이 있으므로 synchronize마다 재리뷰를 원하면 sticky comment 방식과 조합 필요.

### Claude Code 헤드리스 모드 (`claude -p`) 공식 문서
- url: https://code.claude.com/docs/en/headless
- what: `claude -p "..."`로 비대화 실행. `--bare`(훅·MCP·CLAUDE.md 자동 로드 생략, CI 권장·향후 기본값 예정), `--output-format json`(result·session_id·total_cost_usd 포함), `--json-schema`(`structured_output` 필드에 검증 JSON, 잘못된 스키마는 시작 시 에러), `--allowedTools`/`--permission-mode dontAsk`, `--resume <session_id>`로 세션 이어가기, stdin 파이프(10MB 상한), 종료코드 0/비0, SIGTERM 시 143.
- pattern: CLI 헤드리스 생성→검증→재개(resume) 루프
- applicability: 현재 `generate_verified_script.py`류가 agy/Codex CLI를 subprocess로 호출하는 구조에 'claude' 프로바이더를 추가하는 최소 변경: `cat claim_inventory.json | claude --bare -p "$PROMPT" --output-format json --json-schema "$(cat schemas/script_v2.schema.json)" --allowedTools Read`. 검증 실패 시 `--resume $session_id`로 '다음 위반 사항을 고쳐라'만 보내면 전체 컨텍스트 재전송 없이 재생성 가능. `total_cost_usd`를 runs/ 메타에 기록해 에피소드당 비용 추적.
- evidence: 확인 2026-09-02: 문서에 `claude -p ... --output-format json --json-schema '...' | jq '.structured_output'` 예제, `session_id=$(claude -p ... | jq -r '.session_id'); claude -p ... --resume "$session_id"` 예제, `--bare`가 '스크립트·SDK 호출 권장 모드이며 향후 -p 기본값' 명시. stdin 10MB 상한, 잘못된 --json-schema는 v2.1.205부터 즉시 에러.
- caveat: JSON Schema는 draft-07 기준이며 `format` 키워드는 주석으로만 취급(검증 안 함)—우리 스키마의 `format`/`pattern` 의존 규칙은 별도 검증기 유지 필요. `--bare`는 OAuth 구독 로그인을 쓰지 않으므로 ANTHROPIC_API_KEY 필요. Windows에서 stdin 처리 이슈는 v2.1.211에서 수정됨(우리 환경 win32이므로 버전 확인).

### anthropics/claude-agent-sdk-python (+ 구조화 출력 문서)
- url: https://github.com/anthropics/claude-agent-sdk-python
- what: Claude Code의 에이전트 루프·도구·권한·서브에이전트를 Python에서 직접 구동하는 SDK. `query()`(단발)와 `ClaudeSDKClient`(양방향·세션). `ClaudeAgentOptions(output_format={"type":"json_schema","schema":...})`로 결과 `ResultMessage.structured_output`에 검증 JSON을 받고, 불일치 시 SDK가 재프롬프트하며 한도 초과 시 `subtype='error_max_structured_output_retries'`. `hooks={'PreToolUse':[HookMatcher(...)]}`로 도구 호출 가로채기, `create_sdk_mcp_server`로 프로세스 내 커스텀 도구, `agents` 옵션으로 서브에이전트 정의, `can_use_tool` 권한 콜백.
- pattern: SDK 내장 스키마 재시도 루프 + 훅 기반 검증기 삽입
- applicability: 대본 생성기를 SDK로 감싸면 '생성→JSON Schema 검증→재생성'이 SDK 내부에서 처리되고, 우리 사실·페르소나 검증기(claim 인용 매칭, 금칙어, 문장 통계)를 `@tool`로 등록해 모델이 제출 전 스스로 호출하게 하거나 `PostToolUse` 훅으로 강제 실행 가능. 시각 브리프 단계도 `doodle_scene_contract.schema.json`을 output_format으로 주면 Codex `--output-schema` 경로와 동일한 계약을 Claude로 재현. Pydantic 모델→`model_json_schema()`로 스키마 단일 소스 유지.
- evidence: 확인 2026-09-02: GitHub 페이지 8.0k★, MIT. 최근 커밋 2026-09-01 'chore: release v0.2.151', 'bump bundled CLI version to 2.1.258'. 구조화 출력 문서(code.claude.com/docs/en/agent-sdk/structured-outputs)에 Python `query(... ClaudeAgentOptions(output_format=...))` 코드, `error_max_structured_output_retries` 서브타입, 'subtype success이나 structured_output이 None인 경우도 실패로 처리' 지침 명시.
- caveat: 구조화 출력이 실패하면 예외가 아니라 결과 메시지 서브타입으로 오므로 반드시 subtype+structured_output 존재 여부를 둘 다 검사해야 함. 깊은 중첩·필수 필드 많은 스키마는 재시도 실패율 상승—문서가 '스키마를 단순하게, 정보가 없을 수 있는 필드는 optional'을 권고. SDK는 번들된 Claude Code CLI 버전에 종속되어 잦은 릴리스(거의 매일)로 핀 고정 필요.

### anthropics/claude-agent-sdk-demos
- url: https://github.com/anthropics/claude-agent-sdk-demos
- what: Agent SDK 공식 데모 모음. Research Agent(요청을 하위 주제로 분해→병렬 리서처 서브에이전트→합성 리포트, 서브에이전트 활동 추적), Resume Generator(웹 검색→정보 조합→.docx 생성의 콘텐츠 파이프라인), AskUserQuestion Previews(HTML 미리보기 카드로 사용자 선택 왕복, `canUseTool` 콜백), Hello World V2(세션 API `send()/stream()`).
- pattern: 오케스트레이터-워커(서브에이전트 병렬)로 다단계 콘텐츠 생성
- applicability: 에피소드 생성을 '개요 작성(오케스트레이터)→5단계 구간별 워커 서브에이전트 병렬 집필→합성·연결부 다듬기' 구조로 재구성할 때 그대로 참조. AskUserQuestion 데모의 미리보기 카드 방식은 우리 '사람 승인' 단계(썸네일·컨택트시트 선택)를 SDK 세션 안에서 처리하는 UI 패턴으로 응용 가능.
- evidence: 확인 2026-09-02: GitHub 페이지 2.7k★, MIT. README 데모 표에 Research Agent 'Breaks requests into subtopics → spawns parallel researcher subagents → synthesizes findings' 명시. 최근 커밋 날짜는 페이지에서 확인 불가(추정: 활발히 유지).
- caveat: 데모는 코드·리서치 도메인이며 '생성→평가→재생성' 폐루프 자체를 보여주는 데모는 없음(폐루프는 cookbook evaluator_optimizer 참조). 긴 한국어 대본(18~20분)을 서브에이전트가 분할 집필하면 톤·문체 일관성이 깨질 수 있어 페르소나 검증 단계가 더 중요해짐.

### anthropics/claude-cookbooks — patterns/agents (Building Effective Agents 구현)
- url: https://github.com/anthropics/claude-cookbooks/tree/main/patterns/agents
- what: Anthropic 엔지니어링 글 'Building Effective Agents'의 최소 구현 노트북: basic_workflows(prompt chaining·routing·parallelization), orchestrator_workers, evaluator_optimizer('한 LLM 호출이 생성하고 다른 호출이 평가·피드백을 주는 루프'), async_multi_agent_orchestration. 글은 evaluator-optimizer를 '명확한 평가 기준이 있고 반복 개선이 측정 가능한 가치를 줄 때', parallelization/voting을 '더 높은 신뢰도를 위해 여러 시도가 필요할 때'로 권고.
- pattern: Evaluator-Optimizer 루프 / Voting(다중 시도)
- applicability: 우리 파이프라인의 '대본 생성→사실·페르소나 검증→재생성'이 정확히 evaluator-optimizer. 노트북 구조대로 evaluator 출력을 `{status: PASS|NEEDS_IMPROVEMENT|FAIL, feedback: [...]}`로 고정하고, generator에 '이전 시도+피드백' 메모리를 넘기며 max_iterations(권장 2~3)를 두면 됨. 훅(0~10%) 문장은 voting 패턴으로 N개 생성 후 선택.
- evidence: 확인 2026-09-02: 저장소 52.4k★, MIT. patterns/agents/README.md에 evaluator_optimizer.ipynb·orchestrator_workers.ipynb 링크. anthropic.com/engineering/building-effective-agents 원문에서 'One LLM call generates a response while another provides evaluation and feedback in a loop' 인용 확인.
- caveat: 노트북은 최소 예제라 재시도 상한·비용 상한·피드백 형식 강제가 없음. JETTS 논문(아래)은 자연어 비평이 재생성 품질을 크게 못 올린다고 보고—피드백은 '위반 규칙 ID+위치+수정 지시' 같은 구조화 형태로 주는 것이 안전.

### Ralph Wiggum / Ralph Loop 플러그인 (anthropics/claude-code plugins)
- url: https://github.com/anthropics/claude-code/blob/main/plugins/ralph-wiggum/README.md
- what: Claude Code Stop 훅으로 세션 종료를 가로채 같은 프롬프트를 다시 주입, 파일·git 변경을 보며 완료 조건(`--completion-promise` 정확 문자열 매칭) 또는 `--max-iterations`까지 반복하는 자율 루프 플러그인. `/ralph-loop "<prompt>" --max-iterations 50 --completion-promise "COMPLETE"`.
- pattern: Stop 훅 기반 '검증 통과까지 반복' 루프
- applicability: 로컬에서 에피소드 한 편을 '검증 스크립트 전부 통과할 때까지 수정'시키는 야간 배치에 적합. 프롬프트에 '`python scripts/audit_episode_quality.py`가 exit 0이면 <promise>COMPLETE</promise> 출력'을 넣고 max-iterations 10 정도로 제한. 단, 저장소 훅으로 구현하면 `claude -p`(비-bare)에서도 실행됨.
- evidence: 확인 2026-09-02: README에 Stop 훅 동작 순서, 옵션(`--max-iterations` 기본 무제한, `--completion-promise` 단일 조건만), '항상 --max-iterations를 안전망으로 사용', '막혔을 때 탈출 논리를 프롬프트에 포함' 경고 명시.
- caveat: 완료 조건이 문자열 매칭이라 모델이 검증 없이 'COMPLETE'를 출력하는 오탐 가능—완료 판정은 반드시 결정적 스크립트 exit code로 대체. 무제한 반복은 비용 폭주 위험. 우리처럼 Windows 환경이면 stop-hook.sh 실행 셸(Git Bash) 확인 필요(추정).

### promptfoo + promptfoo-action
- url: https://github.com/promptfoo/promptfoo
- what: 프롬프트·모델·파이프라인 출력 평가 CLI/라이브러리. `exec:`(임의 명령, stdout을 응답으로) 및 `file://x.py` 파이썬 프로바이더로 자체 파이프라인을 감싸 테스트 가능. assert 유형: contains/regex/javascript/python(결정적) + `llm-rubric`(LLM 판사, `threshold`, assertion 단위 `provider: anthropic:...` 지정, 결과 `{reason, score 0~1, pass}`). CI: `promptfoo eval --fail-on-error`, JSON 결과를 jq로 통과율 계산해 exit 1, `PROMPTFOO_CACHE_PATH`/TTL 캐시. promptfoo-action은 PR 변경 파일 글롭 매칭→평가→'통과/실패 수 요약 코멘트+웹뷰어 링크' 게시, `fail-on-threshold`(필수 통과율 0~100), `no-share`, `workflow-base` 입력.
- pattern: 골든셋 기반 대본 품질 회귀 테스트 CI
- applicability: `tests/promptfoo/script_regression.yaml`에 프로바이더 `exec: python scripts/generate_verified_script.py --provider agy --stdin` 를 두고, 에피소드 5~10편의 claim_inventory를 테스트 케이스로 고정. 결정적 assert(python): 문장 중앙값 25~32자, 12~14문장/분, 5단계 구간 비율(10/20/40/20/10%±5), claim 인용률≥95%, 금칙 표현 0건. `llm-rubric`(Anthropic grader, threshold 0.8): '0~10% 구간이 인지부조화 훅인가', '페르소나(쉽선비/놀람파일) 톤 일치'. promptfoo-action `fail-on-threshold: 90`으로 프롬프트 템플릿·규칙표 PR을 차단.
- evidence: 확인 2026-09-02: 24.8k★, MIT, 최근 커밋 2026-09-02('feat(providers): add grok-4.6 ...'). promptfoo-action 71★, MIT, README에 `fail-on-threshold` '필수 통과율 0~100' 및 PR 요약 코멘트 명시. 공식 문서 custom-script 페이지: exec 프로바이더는 인자로 prompt/options/context JSON을 받고 stdout을 output으로 취급(JSON을 찍어도 문자열). llm-rubric 문서: 기본 판사는 OpenAI 계열이며 `provider: anthropic:claude-...`로 교체 가능.
- caveat: exec 프로바이더는 stdout 전체가 응답이므로 우리 스크립트가 로그를 stdout에 섞으면 오염—결과 JSON만 stdout, 로그는 stderr로. 한국어 루브릭은 판사 모델 성능 편차가 있으니 판사 고정+temperature 0+golden 사례로 kappa 확인 후 임계값 설정. 대본 1편 생성이 수 분·수천 토큰이라 CI마다 전량 재생성은 비쌈—캐시+'프롬프트/규칙표 변경 시에만' paths 필터, 또는 이미 생성된 runs/ 산출물을 입력으로 '평가만' 도는 모드 분리 권장.

### confident-ai/deepeval (G-Eval + pytest CI)
- url: https://github.com/confident-ai/deepeval
- what: pytest 스타일 LLM 평가 프레임워크. `GEval(name, evaluation_steps=[...] 또는 criteria, evaluation_params=[ACTUAL_OUTPUT,...], threshold=0.7, rubric=[score_range 밴드], strict_mode)`로 커스텀 판사 지표 정의, `assert_test(test_case, [metric])`를 `test_*.py`에 쓰고 `deepeval test run test_file.py`를 GitHub Actions 스텝으로 실행하면 임계값 미달 시 빌드 실패. Anthropic 모델을 판사로 쓰는 통합 예제 존재.
- pattern: 골든셋 기반 대본 품질 회귀 테스트 CI(파이썬 네이티브 대안)
- applicability: 우리 코드베이스가 파이썬(scripts/, tests/)이므로 promptfoo(Node)보다 도입 마찰이 적음. `tests/test_script_quality.py`에 `EvaluationDataset`으로 과거 승인된 대본을 골든셋으로 로드하고, G-Eval `evaluation_steps`에 '훅 구간에 통념과 충돌하는 진술이 있는지', '증거 개방 구간에서 claim_inventory ID를 인용하는지' 등을 명시. `rubric` 밴드로 0~10점 중간 몰림 방지, `strict_mode`로 페르소나 금칙 규칙은 이진 판정.
- evidence: 확인 2026-09-02: 18.0k★, Apache-2.0, 최근 커밋 2026-09-02. 공식 가이드 'Regression Testing LLM Systems in CI/CD'에 `deepeval test run` GitHub Actions YAML과 `OPENAI_API_KEY`/`CONFIDENT_API_KEY` 환경변수 안내. G-Eval 문서: criteria와 evaluation_steps는 배타적, evaluation_params는 기준에 언급된 필드만 포함해야 정확.
- caveat: 기본 판사가 OpenAI이며 Anthropic 판사는 커스텀 모델 래퍼로 지정해야 함(문서 확인). Confident AI 클라우드 연동을 유도하는 구조라 로컬 전용으로 쓰려면 결과 저장을 자체 구현. G-Eval은 CoT 기반이라 판사 비용이 promptfoo 단순 루브릭보다 높음(추정).

### ragas (vibrantlabsai/ragas) — AspectCritic / RubricsScore / InstanceRubrics
- url: https://github.com/vibrantlabsai/ragas
- what: 원래 RAG 평가 프레임워크지만 범용 지표 제공: AspectCritic(자연어로 정의한 측면에 대해 이진 판정, 3회 LLM 판정 다수결), SimpleCriteriaScore/DiscreteMetric(0~10 등 커스텀 척도), RubricsScore(1~5 루브릭 일괄 적용), InstanceRubrics(데이터 항목별 다른 루브릭). `evaluator_llm` 주입 방식.
- pattern: 항목별 루브릭(InstanceRubrics)으로 에피소드 맞춤 평가
- applicability: 에피소드마다 다른 '시각 브리프 규칙표'와 '페르소나 규칙'을 InstanceRubrics로 각 테스트 항목에 붙이면, 현재 수작업 규칙표를 평가 데이터로 전환할 수 있음. AspectCritic의 3회 다수결은 한국어 판정 흔들림을 줄이는 데 유용. 사료 기반 대본의 '근거 충실도'는 ragas Faithfulness 지표(응답이 제공 컨텍스트로 뒷받침되는지)로 claim_inventory 대비 검증 가능.
- evidence: 확인 2026-09-02: 15.6k★, Apache-2.0(조직명이 explodinggradients→vibrantlabsai로 표시됨; 리네임 여부는 페이지에서 미확인). 공식 문서 general_purpose 페이지에 AspectCritic '3회 판정 다수결', RubricsScore, InstanceRubrics 코드 예시 확인.
- caveat: RAG 중심 API라 대본 같은 장문 생성물에는 입력 포맷(response/reference/contexts) 매핑이 어색함. 3회 판정은 비용 3배. CI 통합 예제는 deepeval·promptfoo보다 빈약.

### LangGraph 및 langchain-ai/langgraph-reflection
- url: https://github.com/langchain-ai/langgraph-reflection
- what: langgraph-reflection: `create_reflection_graph(main_graph, critique_graph)`로 '메인 에이전트→비평 에이전트→비평이 있으면 메인 재호출, 없으면 종료' 루프를 생성. 예제 2종: LLM-as-judge(정확성·완결성·명료성 평가), Pyright 정적 분석으로 코드 검증 후 오류를 되돌려 수정. LangGraph 본체는 HITL을 `interrupt()`+`Command(resume=)`+체크포인터로 제공하며, 미들웨어의 `when` 술어로 '특정 조건일 때만' 인터럽트(예: 워크스페이스 밖 쓰기만 승인 요구).
- pattern: 그래프 기반 생성-비평 루프 + 조건부 HITL 인터럽트
- applicability: `when` 술어 패턴이 우리 '예외 승인' 설계의 정확한 코드 형태: `when=lambda s: s['judge_score']<0.8 or s['claim_coverage']<0.95`일 때만 `interrupt()`로 사람 승인, 아니면 자동 진행. 체크포인터(SQLite/Postgres)에 상태가 남아 승인 대기 중 프로세스를 내려도 재개 가능—브라우저 CDP로 Flow 이미지를 생성하는 긴 단계에 유리.
- evidence: 확인 2026-09-02: langgraph 40.9k★, MIT. langgraph-reflection 185★, 2026-04-01자로 아카이브(읽기 전용). LangChain 공식 HITL 문서에 `interrupt()`, `Command(resume=)`, '체크포인터 필수', approve/edit/reject/respond 4종 결정, `"when": lambda request: not request.tool_call["args"].get("path","").startswith("/workspace/")` 예제 확인.
- caveat: langgraph-reflection은 아카이브되어 유지보수 중단—개념만 차용하고 직접 구현(수십 줄) 권장. 예제에 최대 반복 횟수 제한이 없음. LangGraph 도입은 의존성 증가가 크므로, 우리처럼 스크립트 순차 실행 구조라면 Agent SDK 훅+체크포인트 JSON 파일로 동일 효과를 얻는 편이 가벼움.

### Microsoft AutoGen(primary+critic) / CrewAI(Flows·human_input)
- url: https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html
- what: AutoGen AgentChat 공식 튜토리얼: `RoundRobinGroupChat([primary_agent, critic_agent], termination_condition=TextMentionTermination("APPROVE"))`로 작성자와 비평가가 번갈아 발화, 비평가가 'APPROVE'를 말하면 종료하는 반영 패턴. CrewAI는 역할 기반 에이전트(Writer/Editor/Reviewer)와 Flows(이벤트 기반 상태 관리·조건 분기), 태스크 `human_input` 옵션으로 사람 승인 삽입.
- pattern: 작성자-비평가 교대 대화 종료 조건
- applicability: 패턴 자체는 우리 '대본→페르소나 검증→재생성'과 동일하나, 우리 검증은 사실 검증 스크립트 등 결정적 도구가 핵심이므로 프레임워크 도입보다 Agent SDK/훅으로 구현하는 편이 적합. CrewAI Flows의 '조건 분기+human_input'은 예외 승인 흐름 설계의 참고 모델.
- evidence: 확인 2026-09-02: AutoGen 60.8k★, MIT/CC-BY-4.0이나 README에 '유지보수 모드—신규 기능 없음, Microsoft Agent Framework로 이전 권고' 명시. CrewAI 58k★, MIT, README에 Flows와 'Having Human input on the execution' 예제 확인. AutoGen 예제는 max_turns 없이 'APPROVE' 문자열에만 의존.
- caveat: AutoGen은 유지보수 모드라 신규 도입 비권장. 문자열 종료 조건은 비평가가 조기에 'APPROVE'를 내는 오탐이 잦음—종료는 결정적 검증 통과로 판정. CrewAI는 OpenAI 중심 기본값이 많아 Claude 연동 시 설정 필요(추정).

### jury-arena / judges 라이브러리 / tourno (generator×N + 다중 판사 토너먼트 구현체)
- url: https://github.com/elementshq/jury-arena
- what: jury-arena: 동일 프롬프트에 두 후보 응답을 생성→LLM 판사가 승/패/무 판정→Elo 또는 Glicko-2(불확실성 추적, 정보량 최대 매칭) 레이팅 갱신, '최대 3개 판사 병렬+다수결', LiteLLM `provider/model` 형식으로 Anthropic 지원, Docker Compose 웹 UI. judges(quotient-ai): 연구 기반 판사 프롬프트 모음+`Jury.vote()`(평균/다양화 집계). tourno(haizelabs): pointwise+pairwise 판사를 라운드로빈/ELO 토너먼트로 합쳐 RL 보상으로 쓰는 연구 코드.
- pattern: N 후보 생성 → pairwise 다중 판사 → 레이팅 선택
- applicability: 에피소드 전체가 아니라 '훅(0~10%) 3~5안', '제목/썸네일 문구', '통찰(90~100%) 결말 2~3안'처럼 짧고 결정적 구간에 적용. 구현은 jury-arena를 그대로 쓰기보다 그 설계(pairwise, 위치 편향 방지 위해 순서 교대, 3판사 다수결, 무승부 허용)를 우리 스크립트로 옮기는 것이 현실적. 판사 프롬프트에 벤치마크 통계(28자 중앙값, 인지부조화 훅 정의)를 명시.
- evidence: 확인 2026-09-02: jury-arena 6★, Apache-2.0, README에 '최대 3 판사 병렬, 다수결', Elo/Glicko-2 설명. judges 337★, Apache-2.0, README에 Jury `.vote()` 및 built-in classifier/grader 목록. tourno 13★, MIT, README에 `--judge-type pointwise|pairwise|mixture`, `--pairwise-alpha`.
- caveat: 세 저장소 모두 스타 수가 작아 장기 유지보수 불확실(참고용). tourno는 RLHF 학습용으로 우리 용도와 거리가 있음. pairwise 판사는 위치 편향·장황함 선호 편향이 알려져 있어 순서 스왑 2회 판정+길이 정규화 필요.

### 논문: When Agents Disagree — The Selection Bottleneck in Multi-Agent LLM Pipelines (arXiv 2603.20324) + JETTS (arXiv 2504.15253)
- url: https://arxiv.org/abs/2603.20324
- what: 2026-03 논문: 210개 테스트(42과제·7범주)에서 '다양한 모델로 N개 생성 후 판사가 선택'이 단일 모델 대비 승률 0.810, 동질 모델 팀은 0.512(우연 수준), '합성(synthesis)' 집계는 판사 패널이 42과제 중 0건에서 베이스라인보다 선호. 집계 품질 임계점(s*)이 다양성의 득실을 가르며 '선택기 품질이 생성기 다양성보다 중요', '약한 모델을 섞으면 비용은 줄고 성능은 오름'. JETTS(2025): 판사는 재순위화에는 결과 보상 모델과 대등하나, 자연어 비평으로 생성기를 개선시키는 데는 '현재 비효과적'.
- pattern: 합성보다 선택(best-of-N + 고품질 판사), 비평 루프의 한계
- applicability: 우리 다중 프로바이더(agy/Codex/Claude)가 이미 '이질적 생성기'이므로 같은 claim_inventory로 각 1안씩 생성→pairwise 판사 선택이 논문 조건과 맞음. 선택 후 '고르지 않은 안의 좋은 문장을 합쳐라'는 합성 단계는 논문상 오히려 해로울 수 있어 기본 비활성. 비평→재생성 반복은 2회 이내로 제한하고, 재생성 지시는 자연어 비평 대신 규칙 ID·위치 기반 구조화 피드백으로.
- evidence: 확인 2026-09-02: arXiv 초록 페이지에서 게재 2026-03-20(개정 2026-07-21), 승률 0.810/0.512, Δ=+0.631, 독립 판사 Spearman ρ=0.90 확인. JETTS 초록: 10개 판사(7B~70B)·8개 생성기, 'natural language critiques are currently ineffective in guiding the generator' 확인.
- caveat: 두 논문 모두 영어·코드/수학/지시수행 도메인 실험이며 한국어 장편 내러티브에 직접 검증된 결과는 아님(일반화는 추정). JETTS는 7B~70B 오픈 모델 판사 기준이라 최신 프런티어 모델 비평 효과는 다를 수 있음.

### Trust or Escalate (ICLR 2025) + LLM 판사 보정·표본 검토 가이드(Galileo, Braintrust)
- url: https://arxiv.org/abs/2407.18370
- what: Trust or Escalate: 판사 모델의 신뢰도를 추정('Simulated Annotators')해 신뢰할 때만 자동 판정하고 나머지는 상위 모델→사람으로 에스컬레이션하는 선택적 평가; 사용자가 지정한 인간 동의율(예: 80%)을 보장하면서 약 80% 커버리지를 저가 모델로 달성. Galileo 가이드: 판사 신뢰도(저·중·고)·주제·최신성·불일치 패턴으로 계층화 표본 추출 시 95% 신뢰 달성에 필요한 인간 검증량이 단순 무작위 대비 최대 85% 감소, Cohen's kappa를 헤드라인 지표로, 주간 골든셋 회귀·월간 전체 보정·판사 모델 교체 직후 즉시 재보정. Braintrust: 주당 50~100건 검토, 저점·사용자 신고·엣지케이스 우선 표본, 0~3 또는 pass/fail 저정밀 척도가 일관성 높음.
- pattern: 신뢰도 임계값 기반 예외 승인 + 계층화 표본 감사 + kappa 보정
- applicability: 현재 '사람 승인 다수' 단계를 3단으로 재편: (1) 결정적 검사 전부 통과+판사 점수≥임계(예: 0.85)+판사 3회 일치 → 자동 승인, (2) 그 외 → 사람 승인(예외), (3) 자동 승인분 중 10% 무작위+저신뢰 상위 5%를 주간 표본 감사. 초기 4~8주는 100% 사람 검토를 유지하면서 판사 판정을 병행 기록해 kappa≥0.6(권장 0.8) 도달한 항목(문장 통계·금칙어·구조 비율)부터 자동화하고, 사실 검증(사료 인용)은 마지막까지 사람 유지. `artifact_approval_v2.schema.json`에 `auto_approved`, `judge_score`, `sampled_for_audit` 필드 추가로 추적.
- evidence: 확인 2026-09-02: arXiv 2407.18370 초록에 'Simulated Annotators', 'guarantee over 80% agreement ... ~80% test coverage' 확인(ICLR 2025 게재는 검색 결과의 proceedings.iclr.cc 링크로 확인). galileo.ai 블로그: '최대 85% 감소, 95% 신뢰', kappa 권고, 주/월/분기 보정 주기. braintrust.dev 기사: '50 to 100 traces per week', '0 to 3 or pass/fail' 척도. 검색 결과 요약에 'kappa>0.6 운영 가능, >0.8 강한 판사' 및 '자동 승인분 5~10% 교차 검토' 언급(출처 futureagi.com 블로그, 2차 자료).
- caveat: 동의율 보장은 보정 세트가 실제 분포를 대표할 때만 유효—에피소드 장르(역사 다큐 vs 트렌드 해설)별로 별도 보정 필요. 사료 사실 오류처럼 비용이 큰 실패는 판사 신뢰도와 무관하게 사람 검토를 유지해야 함(논문도 고위험은 에스컬레이션 전제). 판사 모델 버전 업데이트 시 임계값이 흔들리므로 모델 핀 고정+교체 시 재보정.

### calesthio/OpenMontage (에이전틱 영상 제작 시스템의 승인 게이트 사례)
- url: https://github.com/calesthio/OpenMontage
- what: Claude Code·Cursor·Codex 등 코딩 에이전트를 '영상 제작 스튜디오'로 바꾸는 오픈소스. 12개 파이프라인(Documentary Montage, Animated Explainer, Localization & Dub 등), 7차원 가중 점수(과제 적합 30%·품질 20%·제어 15%·신뢰성 15%·비용 10%·지연 5%·연속성 5%)로 생성 프로바이더 자동 선택, 렌더 후 self-review(ffprobe 검사, 4지점 프레임 추출, 오디오 레벨, 자막 존재 확인), 제안→대본→씬플랜→에셋→게시 5개 사람 승인 게이트, '승인 기록 없이 완료로 표시된 게이트 단계는 체크포인트 writer가 거부'.
- pattern: 체크포인트 파일에 승인 기록을 강제하는 게이트 + 렌더 후 자동 self-review
- applicability: 우리 파이프라인과 단계 구성이 거의 같음(대본→시각 브리프→이미지→모션→자막→FFmpeg). '승인 없는 완료 거부' 규칙을 우리 build_manifest/artifact_approval 스키마에 그대로 적용하고, 렌더 후 self-review(ffprobe 길이·오디오 피크·자막 트랙·4지점 프레임 OCR)를 자동화해 최종 사람 검토를 표본화. 프로바이더 점수표는 Flow vs 대체 이미지 생성기 선택 기준으로 참고. 한국어 자막 지원(CJK caption) 커밋이 있어 자막 렌더 코드 참고 가능.
- evidence: 확인 2026-09-02: GitHub 페이지 표기 55.5k★(페이지 표기값 그대로; 급성장 저장소로 추정), AGPLv3, 448 commits, 최근 커밋 2026-08-22('feat/cjk-caption-support' 등). README에 12 파이프라인 목록, 7차원 가중치, 승인 게이트 5단계, 'checkpoint writer rejects a completed gated stage without recorded approval' 확인.
- caveat: AGPLv3—코드를 우리 파이프라인에 병합하면 배포 시 공개 의무 발생 가능(패턴만 차용 권장). 에이전트 스킬 파일 700+개로 매우 큰 규모라 부분 도입이 어려움. 품질 게이트가 '슬라이드쇼처럼 보이는 렌더 차단' 등 영상 미학 중심이라 대본 사실성 검증은 별도.

### humanlayer/humanlayer (참고: 원본 승인 SDK는 폐기됨)
- url: https://github.com/humanlayer/humanlayer
- what: AI 에이전트의 고위험 함수 호출에 Slack/이메일 승인 워크플로를 강제하는 SDK(`@require_approval` 데코레이터)로 알려진 프로젝트였으나, 현재 저장소는 '여기 코드는 사실상 전부 폐기, humanlayer.com의 재구축본을 써라'는 안내로 코딩 에이전트 IDE로 전환됨.
- pattern: 도구 호출 단위 사람 승인(폐기 사례)
- applicability: 도입 비권장. 동일 기능은 Claude Agent SDK의 `can_use_tool` 권한 콜백·`PreToolUse` 훅, 또는 LangGraph `interrupt()`로 자체 구현하는 것이 안전. 우리 경우 '유튜브 업로드', '승인 파일 덮어쓰기' 같은 비가역 도구에만 승인 콜백을 붙이는 식으로 적용.
- evidence: 확인 2026-09-02: 11.4k★이나 README에 'the code here is pretty much all deprecated' 명시, 저장소는 이슈 아카이브 용도.
- caveat: 스타 수만 보고 채택하면 안 되는 대표 사례. 블로그 검색 결과 중 '11,000+ stars' 언급은 폐기 이전 정보.

## patterns

- **PR 이벤트 자동 QA 코멘트 + 구조화 판정 게이트** (대본 생성 직후 / 시각 브리프 JSON 커밋 시 (사실·페르소나 검증 단계의 1차 자동 리뷰)): `on.pull_request.paths`로 대본/브리프 JSON 변경만 감지→claude-code-action 자동화 모드(prompt)로 규칙 점검→`--json-schema`로 `{verdict, issues[]}` 구조화 출력→후속 스텝에서 라벨 부착·체크 실패·인라인 코멘트. 도구는 Read+인라인코멘트 MCP로 최소화하고 `--max-turns`, timeout, concurrency로 비용 상한. [seen in: anthropics/claude-code-action docs/usage.md(structured_output, 자동화 모드 YAML), code.claude.com/docs/en/github-actions(code-review 스킬 --comment 예제), JSONbored/awesome-claude 리뷰 워크플로 가이드(SHA 핀·권한 최소화)]
- **스키마 검증 재시도 루프의 내재화 (SDK/CLI 구조화 출력)** (대본 생성(현재 agy/Codex/json-file 프로바이더 + 외부 스키마 검증) 및 시각 브리프(Codex --output-schema 경로)): 외부에서 JSON Schema를 검증하고 실패 시 프로세스를 재호출하는 대신, Agent SDK `output_format={'type':'json_schema'}` 또는 `claude -p --json-schema`가 검증 실패를 스스로 재프롬프트하도록 하고, 실패 서브타입(`error_max_structured_output_retries`)과 `structured_output` 부재를 모두 실패로 처리. `--resume session_id`로 컨텍스트 재전송 없이 수정 지시. [seen in: code.claude.com/docs/en/agent-sdk/structured-outputs, code.claude.com/docs/en/headless(--json-schema, --resume), anthropics/claude-agent-sdk-python README]
- **Evaluator-Optimizer 루프(구조화 피드백, 반복 상한, 결정적 검증기 우선)** (대본 생성→사실·페르소나 검증→재생성 루프): 생성기와 평가기를 분리하고 평가 출력을 `{status, feedback[]}`로 고정, 반복 2~3회 상한. 평가는 결정적 스크립트(문장 통계·claim 인용률·금칙어)를 먼저 돌리고 LLM 판사는 그 뒤. 완료 판정은 문자열이 아니라 검증 스크립트 exit code. JETTS 결과에 따라 자연어 비평보다 '규칙 ID+위치+수정 지시' 형태의 피드백 사용. [seen in: anthropics/claude-cookbooks patterns/agents/evaluator_optimizer.ipynb, langchain-ai/langgraph-reflection(아카이브, Pyright 검증 예제), anthropics/claude-code plugins/ralph-wiggum(Stop 훅 반복, --max-iterations), AutoGen RoundRobinGroupChat primary+critic]
- **골든셋 기반 대본 품질 회귀 테스트 CI** (대본 생성 프롬프트/규칙표 변경 시 CI(사실·페르소나 검증 단계의 회귀 방지), 벤치마크 통계 유지): 승인된 과거 에피소드를 골든셋으로 고정하고, 프롬프트 템플릿·규칙표·프로바이더 변경 PR마다 promptfoo `exec:`/python 프로바이더로 생성기를 호출해 결정적 assert(28자 중앙값, 12.7문장/분, 5단계 구간 비율, claim 인용률)+`llm-rubric`(Anthropic 판사, threshold)로 채점, promptfoo-action `fail-on-threshold`로 머지 차단. 캐시로 비용 절감, 또는 기존 산출물 대상 '평가 전용' 모드 분리. [seen in: promptfoo/promptfoo + promptfoo-action(fail-on-threshold, PR 요약 코멘트), confident-ai/deepeval(G-Eval evaluation_steps + pytest assert_test + deepeval test run), vibrantlabsai/ragas(AspectCritic 3회 다수결, InstanceRubrics)]
- **N 후보 생성 → pairwise 다중 판사 선택 (합성 금지, 선택기 품질 우선)** (대본 훅(0~10%)·통찰(90~100%) 구간, 제목/썸네일 문구, 시각 브리프 후보 선택): 이질적 생성기(agy/Codex/Claude)로 같은 입력에 각 1안 생성→순서 스왑한 pairwise 비교를 3판사 다수결로 판정→Elo/Glicko-2 또는 단순 승수로 선택. 논문 근거상 '합성' 집계는 비활성, 판사 프롬프트 품질에 투자. 비용 때문에 훅·결말·제목처럼 짧고 결정적인 구간에 한정. [seen in: arXiv 2603.20324 When Agents Disagree(판사 선택 승률 0.810 vs 합성 0/42), arXiv 2504.15253 JETTS(재순위화 유효, 비평 비효과), elementshq/jury-arena(3판사 다수결, Glicko-2), quotient-ai/judges(Jury.vote), Building Effective Agents parallelization/voting]
- **신뢰도 임계값 기반 예외 승인 + 계층화 표본 감사 + kappa 보정** (사람 승인 다수 단계(대본 승인, 브리프 승인, 이미지 QA 승인, 최종 렌더 승인)와 artifact_approval_v2 스키마): 결정적 검사 전부 통과+판사 점수≥임계+판사 다중 판정 일치 시 자동 승인, 그 외만 사람 승인. 자동 승인분 중 무작위 10%+저신뢰 상위 5%를 주간 표본 감사(0~3 저정밀 척도). 초기엔 100% 사람 검토를 유지하며 판사 판정을 병행 기록, 항목별 Cohen's kappa≥0.6(권장 0.8) 달성 순으로 자동화 전환. 사료 사실성처럼 고비용 실패 항목은 사람 유지. 승인 기록 없는 '완료'는 체크포인트가 거부. [seen in: arXiv 2407.18370 Trust or Escalate(ICLR 2025, 선택적 평가·인간 동의율 보장), galileo.ai 판사 보정 가이드(계층화 표본으로 검증량 최대 85% 절감, kappa), braintrust.dev HITL 기사(주당 50~100건, 저정밀 척도), LangChain HITL 문서(`when` 술어 조건부 interrupt), calesthio/OpenMontage(5단계 승인 게이트, 승인 없는 완료 거부)]
- **CI 보안·비용 가드레일 (프롬프트 인젝션·권한·상한)** (모든 CI 자동화 단계 공통(특히 외부 사료 텍스트를 읽는 대본·검증 단계)): 사료(sources/)·PR 본문은 신뢰할 수 없는 입력으로 취급: `--bare`로 저장소 훅/MCP 자동 로드 차단, `--allowedTools` 최소화(Write/Bash 금지), `allowed_bots` 비활성, 액션 SHA 핀, 포크 PR 실행 차단, `--max-turns`·timeout·concurrency·`total_cost_usd` 기록. `show_full_output` 비활성으로 로그에 사료 원문·키 노출 방지. [seen in: anthropics/claude-code-action docs/security.md, code.claude.com/docs/en/headless(--bare, 워크스페이스 신뢰 경고), JSONbored/awesome-claude 리뷰 워크플로 가이드(SHA 핀, same-repo 조건)]


# MAPPING

## verdict_summary
조사한 4개 채널(GitHub 장편 생성 OSS 22건, Anthropic 공식 자료 27건, 영상 자동화 OSS 22건, CI·에이전트 운영 16건)을 우리 파이프라인 13단계에 대응시킨 결론: (1) 즉시 채택(adopt)할 것은 '대본 본문 생성·아웃라인·대본 자동 QA·시각 브리프·이미지 의미 채점' 5개 단계이며, 공통 수단은 Messages API 구조화 출력(output_config.format=json_schema) + 안정 프리픽스 캐싱(페르소나 계약·claim inventory·스타일 가이드) + Batch API(승인 대기 중 대량 채점)다. 현재 scripts/lib/script_generation.py의 ScriptProvider Protocol(generate(prompt, output_schema))이 이미 '프롬프트 in → 스키마 검증 JSON out'이라 ClaudeApiProvider를 같은 인터페이스로 추가하면 기존 validate_json 게이트가 그대로 유지된다. (2) 적응(adapt)할 것은 사료 수집(STORM 관점 질문+citations), 사실·페르소나 검증(결정론 검사 우선, LLM 판사는 페르소나·구조만, 사료 사실성은 사람 유지), 페이싱(강도 곡선을 visual_pacing_profiles.yaml에 수치화), Flow 생성(gflow-cli식 원장·fail-fast), 재사용 판정(참조 이미지 비교), 승인 게이트(Trust-or-Escalate 3단+kappa 보정), CI(골든셋 회귀는 지금, claude-code-action은 git 리포화 후)다. (3) 거부·보류할 것은 Claude Engineer·Artifacts 클론·마케팅 챗봇 스킬, prefill JSON mode(4.6+에서 400), 합성(synthesis) 집계, RecurrentGPT 장기 메모리(GPL·정체), Dynamic Workflows(비용 미측정), 로컬 퍼플렉시티 개선기(GPU·한국어 신뢰도 낮음)다. (4) 구조상 가장 중요한 발견: 조사한 프로젝트 전부가 소설·영어 전제이며 '사료 claim 결속·한국어 문장 중앙값 28자·TTS 문장 단위 출력'은 아무도 다루지 않으므로, 도입은 코드 복사가 아니라 패턴 이식이어야 하고(autonovel·forsonny는 라이선스 미지정, OpenMontage AGPL, RecurrentGPT GPL), 우리 JSON Schema 검증 체계가 대부분의 OSS보다 엄격하므로 그 위에 Claude를 얹는 방향이 맞다. 편당 API 비용은 권장 혼합(대본 Opus 5 + 브리프·채점 Sonnet 5, 캐시+Batch) 약 $3.5~4.5(추정, 한국어 1자≈0.8~1.0토큰 가정, count_tokens 실측으로 보정 필요). 환경 전제: anthropic SDK 미설치·ANTHROPIC_API_KEY 미설정이므로 `ant auth status` 확인 또는 키 발급이 선행되고, D:/module은 git 저장소가 아니라 CI 계열은 리포화가 선행된다.

## mapping

### (A) 주제·사료 수집 — build_claim_inventory.py / build_source_snapshots.py / lib/narrative_outline.build_story_evidence_packet → ADAPT | STORM '관점 유도 질문→근거 수집→아웃라인' + Anthropic citations(document 블록 char_location) + long-context 문서 상단 배치·quote-first
- current: 사료 스냅샷(source_snapshot_manifest)→claim_inventory.schema.json(claim_id, status SUPPORTED/…, evidence_spans)을 수작업+스크립트로 구축. 관점 다양화나 '통념 균열' 소재 발굴은 사람 몫.
- how: (1) scripts/build_claim_inventory.py에 '--perspective-questions' 단계 추가: 사료 스냅샷을 <documents><document index=…> XML로 system 앞에 놓고(캐시 블록), Claude가 '통념(일반 인식) vs 사료가 뒤집는 사실' 쌍 8~12개를 structured output(새 schemas/perspective_questions_v1.schema.json: question, conventional_belief, contradicting_claim_ids, stage_hint∈{hook,crack,evidence,climax,insight})으로 생성 → 사람이 채택한 것만 claim_inventory.metadata.perspectives에 기록. (2) evidence_spans 자동 결속: lib/fact_verification.verify_script가 쓰는 spans_by_id를 채우기 위해 document 블록에 citations:{enabled:true}로 호출해 cited_text·start_char_index/end_char_index를 source_snapshot의 evidence_spans[span_id]로 저장. citations는 output_config.format과 병용 불가(400)이므로 '인용 호출(자유 텍스트)→코드 파싱→JSON 정리' 2단계로 분리. (3) 초장문 사료만 Cookbook summarization 청킹(2,000자 단위 Haiku→Sonnet 메타요약) 적용, 1M 컨텍스트에 들어가면 통째로.
- claude_features: citations(document 블록, char_location), 1M 컨텍스트, 프롬프트 캐싱(사료 프리픽스), structured outputs(관점 질문), count_tokens(사료 토큰 실측)
- cost: 사료 50K토큰 가정 시 관점 질문 1회 Opus 5 ≈ $0.3, 캐시 후 재호출 ≈ $0.05(추정). citations 호출은 사료 전량 입력이라 에피소드당 1~2회로 제한.
- risk: 위키 문체(STORM)를 그대로 쓰면 다큐 톤과 어긋남 → 관점 질문만 차용. citations는 원문 span 정확도가 높지만 사료 OCR 오류가 있으면 char offset이 어긋남 → span 저장 시 cited_text 일치 검증 필수. 관점 질문이 사료에 없는 '흥미 위주' 통념을 만들 수 있으므로 contradicting_claim_ids가 SUPPORTED claim만 가리키도록 스키마 enum/코드 검증.
- sources: https://github.com/stanford-oval/storm (31.2k★, 최근 커밋 2025-09-30, MIT, 확인 2026-09-02), https://platform.claude.com/cookbook/misc-using-citations (확인 2026-09-02), https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices (long context 절, 확인 2026-09-02), https://platform.claude.com/cookbook/capabilities-summarization-guide (확인 2026-09-02), https://github.com/rahulanand1103/youtube-script-writer (35★, 조사 전/후 2단계 blueprint, 확인 2026-09-02)

### (B) 대본 아웃라인(5단계 구조) — lib/narrative_outline.compile_narrative_outline / validate_promise_answerability / scripts/compile_narrative_outline.py → ADOPT | autonovel gen_outline(% mark·감정 아크·Plants/Payoffs·복선 원장·단어 목표) + story-skills promise-before-payoff 검사 + Claude-Book Starting Point/Ending Hook 유형 + LongWriter 단위별 길이 목표 + structured outputs
- current: CORE_ROLES 순서로 SUPPORTED claim을 1개씩 배정한 core_beats + loop_hook + causal edges를 코드로 생성. % 구간·감정 아크·회수(payoff) 거리·초 단위 목표 필드 없음. 5단계 비율(0~10/10~30/30~70/70~90/90~100%)은 프롬프트 지시에만 의존.
- how: (1) 새 schemas/narrative_outline_v2.schema.json: core_beats[] 각 항목에 stage∈{hook,crack,evidence,climax,insight}, pct_range[start,end], target_sec, target_sentences(=target_sec/60×12.7), emotion_arc{start,end}(−9~+9), info_disclosure_type∈{belief_setup,crack,evidence_open,reversal,insight}, claim_ids, plants[], payoffs[], ending_hook_type∈{cliffhanger,question,revelation,tension}, starting_point(직전 비트 종료 상태). 별도 promise_ledger[]{promise_id, planted_beat, reinforced_beats, payoff_beat}. (2) lib/narrative_outline.validate_narrative_outline에 결정론 검사 추가: pct_range 합이 5단계 비율 ±5%p, payoff_beat>planted_beat(거리≥1비트), hook 비트 loop_hook.question이 climax 이전에 payoff 존재, target_sec 합이 18~20분(1080~1200s). (3) 생성은 Claude structured output: system=[페르소나 계약(config/seonbi_narration_policy.yaml)+벤치마크 규칙 캐시 블록] + user=[claim inventory 요약+관점 질문(A)], output_config.format=json_schema(narrative_outline_v2). minimum/maximum/minLength는 API 미지원이므로 SDK transform 후 기존 validate_json으로 재검증. (4) 훅 비트는 3~5안 생성해 (K)의 pairwise 심판으로 선택.
- claude_features: structured outputs(messages.parse+Pydantic 또는 output_config.format), 프롬프트 캐싱(페르소나·규칙 프리픽스), adaptive thinking + effort high
- cost: 아웃라인 1회 Opus 5 ≈ $0.15~0.3(입력 30K·출력 3K 추정). 훅 5안 추가 ≈ $0.2. 캐시 프리픽스(≥512토큰 Opus 5)로 재시도 시 입력비 0.1x.
- risk: 필드가 많아질수록 structured output 재시도 실패율 상승 → Agent SDK 문서 권고대로 optional 필드 분리. 5단계 비율은 벤치마크 30편 중앙값이므로 에피소드별 편차 허용폭(±5%p)을 config/channel_profiles.yaml에 두고 하드코딩 금지. autonovel 코드는 라이선스 미지정이라 필드 설계만 차용.
- sources: https://github.com/NousResearch/autonovel (1,537★, pushed 2026-03-20, 라이선스 미지정, gen_outline.py, 확인 2026-09-02), https://github.com/danjdewhurst/story-skills (199★, pushed 2026-09-01, MIT, promises/payoff 검사, 확인 2026-09-02), https://github.com/ThomasHoussin/Claude-Book (112★, pushed 2026-01-22, chapter-planner Starting Point/Ending Hook, 확인 2026-09-02), https://github.com/THUDM/LongWriter (1.9k★, 2025-06-24, 단위별 길이 목표, 확인 2026-09-02), https://platform.claude.com/docs/en/build-with-claude/structured-outputs (확인 2026-09-02)

### (C) 대본 본문 생성·확장 — lib/script_generation.py(ScriptProvider/AntigravityCliProvider/OmniRouteProvider/JsonFileProvider, build_prompt_context) / lib/script_expansion.compile_script_expansion / scripts/generate_verified_script.py / build_expanded_script.py → ADOPT | '읽기 전용 바이블 + 파생 상태 카드(≤12KB) 분리 주입'(oh-story/Claude-Book) + '직전 세그먼트 꼬리 + 다음 아웃라인 머리 슬라이딩 창'(autonovel draft_chapter) + Cookbook prompt chaining(단계 사이 코드 게이트) + 안정 프리픽스 캐싱 + structured outputs
- current: --provider antigravity-cli|file|omniroute|llm. build_prompt_context(contract, inventory, snapshots, policy)로 단일 프롬프트를 만들고 provider.generate(prompt, output_schema)→validate_json(verified_script_v2). 에피소드 전체를 한 번에 생성하거나 script_expansion으로 문장 패치. 세그먼트 순차 생성·상태 카드·꼬리 컨텍스트 개념 없음.
- how: (1) lib/script_generation.py에 ClaudeApiProvider(ScriptProvider 구현) 추가: anthropic.Anthropic().messages.create(model, system=[{text: 바이블(페르소나 계약+스타일 가이드+벤치마크 규칙+claim inventory JSON, cache_control ephemeral ttl 1h)}], messages=[{user: 상태 카드 + 아웃라인 비트 + prev_tail}], output_config={format:{type:'json_schema', schema}}, thinking adaptive, stream→get_final_message). 반환 전 기존 validate_json 통과. usage(cache_read_input_tokens 포함)를 runs/<ep>/generation_lineage에 기록. (2) 세그먼트 순차 모드: scripts/generate_verified_script.py에 --mode segmented 추가 → 아웃라인 core_beats를 5단계 순서로 돌며 각 비트마다 호출. 프롬프트 가변부(마지막 브레이크포인트 뒤)에 (a) 상태 카드 7칸: 현재 stage/%·직전 비트 델타 요약 2~3문장·공개 완료 claim_ids·미회수 promise_ids·다음 훅·제약 잠금{target_sec, must_claim_ids, forbidden_expressions}·직전 세그먼트 마지막 3문장(prev_tail) (b) 다음 비트 아웃라인 첫 3줄. 전체 claim_inventory는 캐시 프리픽스에 있으므로 카드에는 ID만. (3) 각 비트 출력은 verified_script_v2의 sentences[] 부분집합(sentence_id, text, claim_ids, stage)이며 compile_script_expansion 경로로 병합·canonical_script_sha256 갱신. (4) 비트 완료 후 델타 요약은 Haiku 4.5 또는 코드(문장 수·claim_ids diff)로 생성해 카드에 반영. (5) 분량 미달 시 자동 패딩 금지: target_sentences 미달 플래그를 올리고 claim inventory에서 미사용 SUPPORTED claim을 제안(oh-story 규칙). (6) 시스템 프롬프트 순서를 '문서(바이블)→지시'로 뒤집어 캐시·품질 동시 확보.
- claude_features: Messages API + structured outputs, 프롬프트 캐싱(4 브레이크포인트, 1h TTL), adaptive thinking·effort, 스트리밍(get_final_message), usage 기반 비용 로그, count_tokens
- cost: 대본 25,000자 1회: Opus 5 ≈ $1.2~1.6, Sonnet 5 ≈ $0.5(추정). 5비트 순차+캐시 시 Opus 5 ≈ $1.5~1.8(캐시 쓰기 1.25x 1회 + 읽기 0.1x 4회). Fable 5.1은 ≈ $2.3~2.8이며 tool_choice 강제 불가·30일 보존 필수라 기본 제외.
- risk: 세그먼트 분할 시 비트 경계 문장 이음새가 TTS(SuperTonic3 문장 단위)에서 부자연스러울 수 있음 → prev_tail 3문장 + '첫 문장은 직전 문장을 받아 시작' 지시 + (D) 경계 검사. 상태 카드가 12KB를 넘으면 캐시 프리픽스 뒤 가변부가 커져 비용 증가 → 카드 크기 검증기. 캐시는 json.dumps(sort_keys=True, ensure_ascii=False) 고정 직렬화가 아니면 조용히 무효화 → cache_read_input_tokens==0 경보. agy/Codex와 동일 프롬프트를 쓰면 Claude 프롬프트 지침(과도한 지시 축소)과 충돌 가능 → 프로바이더별 프롬프트 템플릿 파일 분리.
- sources: https://github.com/NousResearch/autonovel (draft_chapter.py prev_tail 2,000자·다음 장 10줄, 확인 2026-09-02), https://github.com/zenstory-ai/oh-story-claudecode (6,391★, pushed 2026-09-02, MIT, ≤12KB 7칸 카드·_tracking-state.json 프롬프트 제외·패딩 금지, 확인 2026-09-02), https://github.com/ThomasHoussin/Claude-Book (bible 읽기 전용 + state/current, 확인 2026-09-02), https://platform.claude.com/docs/en/build-with-claude/prompt-caching (Opus 5 최소 512토큰·읽기 0.1x, 확인 2026-09-02), https://platform.claude.com/cookbook/patterns-agents-basic-workflows (prompt chaining, 확인 2026-09-02), https://platform.claude.com/docs/en/build-with-claude/structured-outputs (확인 2026-09-02)

### (D) 대본 자동 QA(중복·패딩·훅·리듬) — scripts/audit_episode_quality.py / lib/persona_validation.validate_persona / (신설) lib/script_slop_score.py → ADOPT | autonovel evaluate.py 기계적 slop 스코어(티어별 금지어·문장길이 CV·접속부사·구조 틱, 최대 10점 감점) + 9차원 LLM 심사('AI 장 중앙값 6' 앵커) + Cookbook evaluator-optimizer(PASS/NEEDS_IMPROVEMENT/FAIL+피드백 누적, 상한) + adversarial cut(삭제 후보 JSON, 자동 적용 금지) + docs develop-tests(다른 모델로 채점, 결정 지표는 코드)
- current: audit_episode_quality.py와 persona_validation이 규칙 기반 검사를 수행하나, 반복 n-gram·문장길이 변동계수·접속부사 비율·AI 상투구·분당 문장 수 편차·5단계 비율 이탈을 통합 점수로 내는 무API 게이트와 LLM 심사 이중 구조는 없음.
- how: (1) 신설 lib/script_slop_score.py(무API): 입력 verified_script_v2 → 지표 {sentence_len_median(목표 28자±4), sentence_len_cv(너무 낮으면 감점), sentences_per_min(12.7±1.5, TTS 실측 후 재계산), stage_ratio_dev(5단계 비율 이탈 %p), repeated_ngram_rate(4-gram 재출현), conjunction_start_rate(문장 첫머리 '그런데/하지만/그리고' 비율), ending_pattern_rate('~것이다/~했던 것이다' 연속), tier1_banned(config/seonbi_narration_policy.yaml 금지 표현), tier2_suspicious, telling_patterns('놀랍게도','충격적이게도' 등 감정 명명), not_x_but_y 구조 틱} → 총점 0~10 감점과 위반 위치(sentence_id). audit_episode_quality.py에서 호출해 fact 검증 전에 실행. (2) LLM 심사(Claude, 생성 모델과 다른 모델): schemas/script_quality_review_v1.schema.json {hook_dissonance 1~5, stage_transition 1~5, persona_tone 1~5, evidence_progression 1~5, engagement 1~5, redundancy_flags[], verdict∈{PASS,NEEDS_IMPROVEMENT,FAIL}, feedback[]{rule_id, sentence_ids, instruction}}. system에 루브릭+벤치마크 통계+'평균 AI 대본=3점' 앵커를 캐시, <thinking> 후 판정. (3) evaluator-optimizer 루프: scripts/generate_verified_script.py에 --max-iterations 2. NEEDS_IMPROVEMENT면 feedback[](규칙 ID+문장 ID+수정 지시, 자연어 비평 아님)만 다음 생성 user 턴에 누적 전달, 2회 후 REVIEW_REQUIRED로 사람 회부. (4) 총 길이 초과(실측 타이밍 F에서 되돌아옴) 시 adversarial cut: {quote, sentence_id, type∈FAT|REDUNDANT|OVER_EXPLAIN|GENERIC|TELL, action∈CUT|REWRITE, est_sec} JSON 10~20건을 제안만 하고 correction_action_manifest_v1로 사람 승인 후 script_expansion 패치 적용.
- claude_features: structured outputs(심사 JSON), 프롬프트 캐싱(루브릭), adaptive thinking(판정 전 추론), 모델 분리(생성 Opus 5 → 심사 Sonnet 5 또는 역), Batch(골든셋 재채점)
- cost: 무API 게이트 $0. LLM 심사 1회(입력 30K·출력 2K) Opus 5 ≈ $0.4, Sonnet 5 ≈ $0.17(추정). 루프 2회 상한이면 편당 ≤ $1.
- risk: 한국어 slop 지표는 영어 기준(em-dash 등)을 그대로 못 씀 → 인류의 서재 30편 통계로 임계값을 도출하고 4~8주 kappa 보정 전엔 '경고'만. JETTS 결과상 자연어 비평 재생성은 비효과 → 구조화 피드백 강제. LLM 심사 점수를 자동 차단에 쓰면 오탐으로 재생성 비용 증가 → FAIL만 차단, NEEDS_IMPROVEMENT는 1회 재시도.
- sources: https://github.com/NousResearch/autonovel (evaluate.py slop_score, adversarial_edit.py, 확인 2026-09-02), https://platform.claude.com/cookbook/patterns-agents-evaluator-optimizer (확인 2026-09-02), https://platform.claude.com/docs/en/test-and-evaluate/develop-tests (LLM 채점 원칙, 확인 2026-09-02), https://platform.claude.com/cookbook/misc-building-evals (확인 2026-09-02), https://arxiv.org/abs/2504.15253 (JETTS, 비평 재생성 비효과, 확인 2026-09-02), https://github.com/forsonny/Claude-Code-Novel-Writer (quality-check.sh 구조 지표, 130★, pushed 2026-08-21, 확인 2026-09-02)

### (E) 사실·페르소나 검증 — lib/fact_verification.verify_script → fact_check_report_v2 / lib/persona_validation.validate_persona → persona_report / lib/fact_review_approval.py → ADAPT | story-skills 결정론 연속성 검사기(컴파일러 오류식) + oh-story 생성 전/후 훅 차단 + Cookbook content_moderation('모델은 필드 추출, 판정은 코드') + Claude-Book 리뷰어 3분리(문체/페르소나/연속성) + Trust-or-Escalate(고위험은 사람 유지)
- current: 문장별 claim_ids·evidence_spans 결속을 코드로 검사(unsupported/forbidden/review_required 집계). 페르소나 규칙도 결정론. 사람 fact review 승인(fact_review_approval_v1).
- how: (1) 결정론 검사 확장(코드, API 없음): lib/fact_verification에 '정보 공개 순서' 검사 추가 — 훅 비트에서 claim을 '처음 공개하듯' 서술한 뒤 증거 비트에서 재공개하는 위반, 미회수 promise_id, 이미 공개한 claim의 재공개 표현('사실은 처음 밝히자면' 류 패턴) 탐지. 아웃라인 없이 본문 생성 차단은 generate_verified_script.py 시작부에서 narrative_outline_v2 파일 존재·검증 통과를 요구(oh-story guard-outline-before-prose). (2) 페르소나 LLM 판사(보조): persona_validation 뒤에 Claude structured output {tone_likert 1~5, violations[]{sentence_id, rule_id, quote}, unknown_fields[]}를 붙이되 판정은 validate_persona 코드가 함(모델은 사실 필드만). unknown이면 needs_review. (3) 사료 사실성은 자동 승인 대상에서 제외(사람 fact review 유지). 대신 (A)의 citations로 evidence_spans 자동 채움 → 사람 검토 시간 단축. (4) 재생성 지시는 (D)와 같은 {rule_id, sentence_ids, instruction} 구조. (5) 검증 실패 서브타입 처리: 구조화 출력 실패(structured_output None)도 실패로 취급.
- claude_features: structured outputs(페르소나 필드 추출), citations(근거 span), 프롬프트 캐싱(페르소나 계약), 모델 분리(생성≠채점)
- cost: 결정론 검사 $0. 페르소나 판사 1회 Sonnet 5 ≈ $0.1~0.17(추정). citations 호출은 (A)에서 이미 지불.
- risk: LLM 판사가 사료 사실성을 판단하도록 확장하면 환각 위험이 검증 단계로 들어옴 → 사실성은 claim_ids·evidence_spans 결속 코드 검사만. 페르소나 판사 점수는 kappa≥0.6 확인 전엔 참고용. 사료 원문은 프롬프트 인젝션 벡터(외부 텍스트)이므로 Agent SDK/CLI 경로에서 Write/Bash 도구 금지, Messages API 단일 호출 우선.
- sources: https://github.com/danjdewhurst/story-skills (story validate/continuity, 확인 2026-09-02), https://github.com/zenstory-ai/oh-story-claudecode (guard-outline-before-prose.sh, detect-story-gaps.sh, 확인 2026-09-02), https://platform.claude.com/cookbook/capabilities-content-moderation-guide (스키마 추출→결정론 엔진, 확인 2026-09-02), https://github.com/ThomasHoussin/Claude-Book (리뷰어 3분리·최대 3회, 확인 2026-09-02), https://arxiv.org/abs/2407.18370 (Trust or Escalate, 고위험 에스컬레이션, 확인 2026-09-02), https://github.com/KazKozDev/NovelGenerator (who-knows-what→시청자 기지 정보 추적, 144★, 확인 2026-09-02)

### (F) 샷 분할·페이싱 — lib/shot_timing.plan_shot_timing / ShotTimingProfile / lib/sentence_audio_timeline / config/visual_pacing_profiles.yaml(narration_aligned_hybrid_v1) → ADAPT | TTS-first(clawvid/spoonstill, 현행과 동일) + reelforge 강도 0~100 곡선·아크 프리셋 + visual-skills '롱→쇼트→쇼트→포즈→임팩트' 리듬 + OpenMontage 슬라이드쇼 위험 점수 + video-podcast-maker 분당 글자 규칙
- current: SuperTonic3 문장 TTS 실측 길이 우선(TTS-first) 샷 분할. min/target/max_shot_sec, max_sentences_per_shot 2, max_same_mode_streak 2, host_ratio, motif_window 등 규칙은 있으나 5단계 구조별 강도 곡선·샷 길이 차등은 없음.
- how: (1) config/visual_pacing_profiles.yaml에 stage_pacing 블록 추가: hook{target_shot_sec 7~9, intensity 80}, crack{9~11, 55}, evidence{10~12, 45→65 램프}, climax{6~9, 90, rhythm long-short-short-pause-impact}, insight{11~14, 35}. ShotTimingProfile에 stage별 오버라이드 필드를 두고 plan_shot_timing이 sentences[].stage(B에서 부여)로 프로파일을 선택. (2) 강도 곡선을 shot_timing_manifest에 intensity 필드로 기록해 (L) 모션 세기와 (G) shot_type 배정에 전달. (3) 슬라이드쇼 위험 점수(코드): 연속 동일 shot_type·동일 motion·동일 content_mode 스트릭, 12초 초과 샷 비율, 훅 구간 평균 샷 길이>9초를 합산해 임계 초과 시 shot_plan_approval 전에 경고. (4) LLM 불필요 — 전부 결정론. 길이 초과분은 (D) adversarial cut으로 되돌림.
- claude_features: 없음(결정론). 굳이 쓴다면 강도 곡선 초안을 아웃라인 생성(B) structured output의 emotion_arc에서 파생.
- cost: $0. TTS 실측 후 재계산이므로 API 호출 없음.
- risk: 강도 곡선 수치는 벤치마크 30편에서 실측(분당 문장 수·샷 전환 빈도)해 정하지 않으면 임의값이 됨 → analytics/ 벤치마크 데이터로 stage별 중앙값 산출 후 적용. 훅 구간 샷을 짧게 하면 Flow 이미지 수가 늘어 (H) 비용·승인 부담 증가 → cold_open_pilot_shots 12 한도 유지.
- sources: https://github.com/gongnyang/reelforge (81★, 2026-07-30, 강도 곡선·아크 프리셋·파일럿 게이트, 한국어 우선, 확인 2026-09-02), https://github.com/neur0map/clawvid (TTS-first, 2026-02-14, 확인 2026-09-02), https://github.com/calesthio/OpenMontage (55.5k★ 표기, 2026-08-22, AGPLv3, 슬라이드쇼 위험 6차원, 확인 2026-09-02), https://github.com/smixs/visual-skills (242★, 2026-08-04, 몽타주 리듬, 확인 2026-09-02), https://github.com/Agents365-ai/video-podcast-maker (1.6k★, 2026-08-01, 분당 글자 규칙, 확인 2026-09-02)

### (G) 시각 브리프·프롬프트 컴파일 — scripts/generate_visual_briefs.py(--provider antigravity-cli|fallback|codex-cli|json-file, visual_brief_response_v1.schema.json) / lib/visual_brief_provider.py / lib/prompt_compiler·aligned_prompt_compiler / lib/prompt_lint.lint_image_request / lib/doodle_scene_planner / config/seonbi_visual_policy.yaml + 에피소드별 수작업 규칙표(ep02_visual_scene_catalog.py 등) → ADOPT | OpenMontage/clawvid 'JSON scene_plan 단일 계약 + 생성 전 lint' + visual-skills 3디테일 감사(고증 개체·행동·모티프) + storyboard-ai 레퍼런스 개체 그라운딩 + ContentMachine '캐릭터 외형 고정·의상/포즈 가변' + Cookbook orchestrator-workers/parallel + Batch + 캐싱
- current: CodexCliVisualBriefProvider가 --output-schema로 구조화 출력, Antigravity는 응답 파일 경유. 에피소드별 규칙표를 파이썬 모듈로 수작업 작성. prompt_lint가 금지 패턴 검사.
- how: (1) lib/visual_brief_provider.py에 ClaudeVisualBriefProvider 추가(CodexCliVisualBriefProvider와 동일 generate(prompt, schema_path) 시그니처): system=[seonbi_visual_policy.yaml + 두들 스타일 가이드 + 승인된 시각 규칙표(에피소드 공통부) + 대본 전체 + shot_timing_manifest]를 캐시 블록으로, user=[샷 10개 단위 배치]로 11회 호출, output_config.format=visual_brief_response_v1(배열). --provider claude-api 선택지 추가. (2) 비실시간이면 --batch 플래그로 Message Batches 제출(custom_id=shot_id, 1h TTL 캐시), 결과를 기존 검증기에 통과. (3) visual_brief_response_v1에 필드 추가: shot_type∈{establishing,intimate,detail,atmospheric}, motion_hint, reference_entity[]{name, type∈{person,artifact,place,map}, era}, anchor_details{entity, action, motif}(3디테일 감사). (4) prompt_lint.lint_image_request 확장: anchor_details 3개 미충족·reference_entity 시대 불일치·연속 4샷 동일 shot_type을 오류로. 규칙표의 에피소드 특수 규칙은 config/<ep>_visual_rules.yaml로 옮겨 lint 규칙으로 코드화(수작업 파이썬 모듈 축소). (5) 호스트 마스코트(doodle_seonbi_v1.png)는 Files API file_id로 올려 레퍼런스 설명에 참조(외형 고정, 의상·포즈는 샷별 프롬프트).
- claude_features: structured outputs, 프롬프트 캐싱(대본+정책 프리픽스), Message Batches(50%), Files API(참조 자산), 병렬 호출(첫 응답 후 fan-out으로 캐시 히트)
- cost: 110샷 10샷 단위+캐시: Opus 5 ≈ $3.1(Batch $1.6), Sonnet 5 ≈ $1.25(Batch $0.65)(추정). 샷별 110회 호출은 Opus 5 ≈ $5.9라 배치 단위 유지.
- risk: Flow(브라우저)에는 레퍼런스 이미지 첨부 자동화가 추가로 필요(추정) → 우선 프롬프트 텍스트 그라운딩만. 10샷 단위 배치에서 한 샷 스키마 오류가 전체 재시도로 번짐 → 응답 배열을 샷 단위로 분리 검증하고 실패 샷만 재호출. Batch 24h 지연은 fail-closed 게이트와 충돌 가능 → 파일럿 12+8샷은 동기, 나머지 배치.
- sources: https://github.com/calesthio/OpenMontage (scene_plan 계약·승인 게이트, 확인 2026-09-02), https://github.com/neur0map/clawvid (scene JSON effects 배열, 확인 2026-09-02), https://github.com/smixs/visual-skills (14필드 샷카드·3디테일 감사, 확인 2026-09-02), https://github.com/yogendra-yatnalkar/storyboard-ai (160★, 2026-07-01, 레퍼런스 자동 검색, 확인 2026-09-02), https://github.com/Saganaki22/ContentMachine (108★, 2026-03-02, 외형 고정·4변형, 확인 2026-09-02), https://platform.claude.com/docs/en/build-with-claude/batch-processing (확인 2026-09-02), https://platform.claude.com/docs/en/build-with-claude/files (확인 2026-09-02)

### (H) 이미지 생성 프로바이더 — scripts/google_flow_automation.py / lib/provider_flow.FlowProviderAdapter / capture_flow_image.py / download_flow_images.py / batch_generate_flow_images.py / lib/visual_qa.check_near_duplicates → ADAPT | gflow-cli/google-flow-browser-mcp '실 Chrome 영속 프로필 + CDP + 제출 전 원장 기록 + 단일 큐 + 폴링 상한 + 선택자 드리프트 전용 exit code + UI 자동 탐색' + OpenMontage 7차원 프로바이더 점수(대조군) + rushindrasinha 폴백 프레임
- current: Google Flow를 실제 Chrome CDP로 자동화, 배치 상태 파일(test_flow_batch_state). 단일 프로바이더.
- how: (1) lib/provider_flow.FlowProviderAdapter에 제출 전 원장(runs/<ep>/flow_ledger.jsonl: shot_id, prompt_sha, submitted_at, status)을 기록하고 재시작 시 원장 기준으로 중복 제출 차단(크레딧·시간 이중 소모 방지). (2) 실패 분류 exit code: 23=선택자 드리프트, 24=캡차/검증 화면, 25=계정 불일치(expectedAccount 검증), 26=폴링 상한(5s×120). 드리프트 시 debug_flow_button.py류 탐색 로직을 flow_discover_ui 스타일로 정형화해 선택자 맵(config/flow_selectors.json) 자동 갱신 후보를 출력(자동 적용은 사람 승인). (3) 생성 실패 샷은 플레이스홀더 자산(asset_manifest status=placeholder)으로 채워 렌더를 막지 않고 후속 재생성 큐에 넣되 release_report에서 placeholder 0건을 게시 조건으로. (4) 씬당 2~4변형 생성은 훅·절정 구간(cold_open_pilot 12샷)에 한정해 (I) best-of-n 입력으로. (5) Claude는 이 단계에 직접 관여하지 않음(이미지 생성 API가 아니므로). 향후 API형 대체 프로바이더(fal.ai 등) 추가 시 OpenMontage식 점수표로 선택.
- claude_features: 없음(브라우저 자동화). 선택자 드리프트 진단에만 Agent SDK/Chrome MCP를 사람 감독 하에 사용 가능(later).
- cost: Flow 이미지 생성은 크레딧 무료(gflow-cli README 기준, 영상만 과금) — 비용은 시간·승인 부담. 원장·fail-fast로 재실행 낭비 감소.
- risk: 비공식 자동화라 Flow UI 변경 시 파손(gflow-cli도 selector drift를 상정). 이용약관 리스크는 사용자 판단. 변형 생성을 전체 샷으로 확대하면 승인 대기열이 2~4배로 늘어남 → 파일럿 구간 한정.
- sources: https://github.com/ffroliva/gflow-cli (140★, 2026-09-02 커밋, 원장·exit code·실 Chrome, 확인 2026-09-02), https://github.com/TMSSS05/google-flow-browser-mcp (49★, 2026-05-31, CDP 9222·flow_discover_ui·단일 큐·폴링 5s×120, 확인 2026-09-02), https://github.com/rushindrasinha/youtube-shorts-pipeline (2.3k★, 2026-06-09, fallback frame, 확인 2026-09-02), https://github.com/calesthio/OpenMontage (7차원 프로바이더 점수, 확인 2026-09-02)

### (I) 생성 후 의미 일치·품질 채점 — lib/visual_qa(픽셀 무결성·pHash 근접 중복·validate_visual_evaluation) / lib/visual_content_qa(RapidOCR) / lib/nollam_visual_gate / schemas/visual_semantic_review.schema.json / verify_visual_assets 경로 → ADOPT | Cookbook content_moderation(비전+json_schema로 타입 필드만 추출→결정론 엔진 approve/flag/block/needs_review) + best_practices_for_vision(참조 이미지 few-shot) + sub-agents(저가 워커 fan-out, 경계만 상위 모델) + Batch + VQAScore/CLIP 정합·인접 코히런시(StoryBoard-Generator, t2v_metrics) + claude-faceless(비전 프레임 QA)
- current: OCR로 글자·서비스마크 검출, pHash 중복, 픽셀 무결성. 브리프-이미지 의미 일치(focal_subject/action/place/era/prop_motifs)와 스타일 코히런시는 사람 승인에 의존.
- how: (1) 신설 scripts/score_visual_semantics.py + lib/visual_semantic_scoring.py: 각 이미지(1920×1080→1456×819 다운스케일, 비용 절감)와 브리프를 Claude 비전에 넣고 structured output으로 사실 필드만 추출: {has_text:bool, text_content[], has_watermark, person_count, mascot_present, focal_subject_match∈{yes,partial,no,unknown}, action_match, place_match, era_match, prop_motifs_found[], style_is_doodle∈{yes,no,unknown}, korean_anchor_present, notes}. 루브릭+승인 참조 이미지(doodle_seonbi_v1.png, 연속성 그룹 대표)는 Files API file_id로 system 캐시 블록에. (2) 판정은 코드(lib/visual_semantic_scoring.decide): unknown→needs_review, has_text·watermark·비호스트 mascot_present→block, focal/action/place/era 중 no 1개→flag(재생성), 전부 yes→approve 후보. 결과를 visual_semantic_review.schema.json에 맞춰 저장하고 기존 OCR/pHash 결과와 교차(OCR 검출≠비전 has_text면 needs_review). (3) 실행 모드: 파일럿 12+8샷은 동기(Sonnet 5), 나머지는 Message Batches(custom_id=shot_id). 경계 사례(partial/unknown)만 Opus 5로 재판정. (4) 변형 2~4장이 있는 샷은 pairwise 비교(A/B 위치 스왑 2회)로 best-of-n. (5) 스타일 코히런시(인접 샷 임베딩 코사인)는 로컬 CLIP/pHash 계열로 보조(선택, GPU 없으면 생략).
- claude_features: 비전(고해상도 티어 Opus 5/Sonnet 5, 표준 티어 Haiku 4.5), structured outputs, Files API(참조 이미지), 프롬프트 캐싱(이미지 블록 캐시 가능), Message Batches, 저가 워커+상위 재판정
- cost: 110장: Sonnet 5 ≈ $1.2(Batch $0.6), Opus 5 ≈ $3.0(Batch $1.5, 다운스케일 $2.4), Haiku 4.5 ≈ $0.7(Batch $0.35)(추정). 경계 20% Opus 재판정 추가 ≈ $0.5. Haiku 4.5는 캐시 최소 4,096토큰이라 짧은 루브릭 캐시 불가.
- risk: 비전은 작은 글자·AI 생성 여부 판별에 약함(docs 명시) → OCR/pHash 유지, has_text는 OR 결합. 사람 식별 불가이므로 '역사 인물 고증'은 복식·소품 필드로 우회. 첫 요청 응답 전 병렬 발사하면 캐시 미스 → 1건 선행 후 fan-out. unknown을 통과로 매핑하면 fail-closed가 깨짐 → decide()에서 unknown은 항상 needs_review.
- sources: https://platform.claude.com/cookbook/capabilities-content-moderation-guide (확인 2026-09-02), https://platform.claude.com/docs/en/build-with-claude/vision (1920×1080=2,691토큰, 표준 티어 1,560, 확인 2026-09-02), https://platform.claude.com/cookbook/multimodal-best-practices-for-vision (확인 2026-09-02), https://platform.claude.com/cookbook/multimodal-using-sub-agents (확인 2026-09-02), https://github.com/linzhiqiu/t2v_metrics (600★, 2026-06-05, VQAScore best-of-n, 확인 2026-09-02), https://github.com/Gunnika/StoryBoard-Generator (CLIP 정합+코히런시, 2024-01-03, 확인 2026-09-02), https://github.com/hassancs91/claude-faceless-shorts-creator (201★, 2026-08-18, Claude 비전 프레임 QA, 확인 2026-09-02)

### (J) 재사용 판정 — lib/semantic_image_reuse.plan_semantic_image_reuse / scripts/build_semantic_image_reuse_plan.py / materialize_semantic_image_reuse.py → ADAPT | Cookbook vision few-shot 비교(참조 여러 장+대상) + content_moderation 필드 추출→코드 판정 + jury 다중 판정 다수결(AspectCritic 3회)
- current: 문장 ID·요청 필드 유사성으로 재사용 후보를 코드로 산출(_demote_incompatible_request_pairs), 최종은 사람 승인.
- how: (1) plan_semantic_image_reuse가 낸 후보(약 30건/편) 각각에 대해 Claude 비전 pairwise: [승인 자산 이미지(file_id), 새 브리프 텍스트] → structured output {subject_compatible, era_compatible, place_compatible, prop_conflicts[], continuity_group_match, confidence∈{high,mid,low}}. 판정은 코드: 모두 compatible+high → reuse 승인 후보, prop_conflicts 있음 → 재생성. (2) mid/low는 3회 판정 다수결(temperature 기본, 서로 다른 프롬프트 변형) 후에도 갈리면 사람. (3) 결과를 asset_manifest의 reuse_decision{source_asset_id, judge_fields, decision, auto}에 기록해 lineage 유지(artifact_lineage). Batch로 제출 가능.
- claude_features: 비전 다중 이미지('Image 1:' 라벨), structured outputs, Files API, Batch, 다수결(병렬 3회)
- cost: 30후보 Sonnet 5 ≈ $0.4, Opus 5 ≈ $1.0(추정). 3회 다수결은 갈린 항목만이라 +30% 이내.
- risk: 재사용은 시청자가 '같은 그림 반복'으로 느낄 수 있어 motif_window 규칙(visual_pacing_profiles)을 코드 판정에 반드시 포함. 참조 자산 file_id는 워크스페이스 공유 범위 → 미공개 에피소드 자산은 전용 워크스페이스 키.
- sources: https://platform.claude.com/cookbook/multimodal-best-practices-for-vision (참조 이미지 비교, 확인 2026-09-02), https://platform.claude.com/cookbook/capabilities-content-moderation-guide (확인 2026-09-02), https://github.com/vibrantlabsai/ragas (15.6k★, AspectCritic 3회 다수결, 확인 2026-09-02), https://platform.claude.com/docs/en/build-with-claude/files (확인 2026-09-02)

### (K) 승인 게이트·HITL — lib/approval.validate_approval_freshness / schemas/artifact_approval_v2·shot_plan_approval·visual_approval·fact_review_approval_v1·av_pilot_approval / lib/build_manifest.verify_upstream_hash_freshness → ADAPT | Trust-or-Escalate(신뢰도 기반 선택적 자동 판정, 인간 동의율 보장) + Galileo 계층화 표본·Cohen's kappa + Braintrust 저정밀 척도 + OpenMontage 5게이트·승인 없는 완료 거부·비용 임계 승인 + autonovel reader_panel find_disagreements(갈린 항목만 사람) + reelforge 피크 씬 파일럿 게이트 + N후보 pairwise 심판(When Agents Disagree)
- current: 승인 파일 신선도(상류 해시)를 검증하는 다수의 사람 승인 게이트. 자동 승인·표본 감사·판사 점수 기록 없음.
- how: (1) artifact_approval_v2.schema.json에 선택 필드 추가: auto_approved:bool, judge_model, judge_score, judge_agreement(3회 중 일치 수), sampled_for_audit:bool, human_override. approval.validate_approval_freshness는 auto_approved=true여도 상류 해시 검증을 동일 적용. (2) 3단 정책(config/approval_policy.yaml): 자동 승인 = 결정론 검사 전부 통과 ∧ judge_score≥0.85 ∧ 3회 일치; 예외 승인 = 그 외; 표본 감사 = 자동 승인분 무작위 10% + 저신뢰 상위 5% 주간 검토(0~3 척도). 초기 4~8주는 100% 사람 검토를 유지하며 판사 판정을 병행 기록해 항목별 kappa≥0.6(권장 0.8)부터 자동화. 사료 사실성(fact_review_approval)은 자동화 제외. (3) 훅·통찰·제목 후보 선택: scripts/(신설) select_candidates.py — agy/Codex/Claude 각 1안 + Claude 온도 변형 2안을 pairwise(위치 스왑 2회, 3판사 다수결, Opus 5 심판, 무승부 허용)로 선택하고 갈린 쌍만 사람에게. 합성(좋은 문장 합치기)은 비활성. (4) 시청자 페르소나 패널(역사 애호가/캐주얼/편집자/사료 검증자) JSON 고정 필드 채점은 대본 승인 화면에 '의견 갈린 세그먼트'만 표시. (5) 절정 구간 파일럿(cold_open_pilot 12샷 외에 climax 8샷)을 먼저 렌더해 av_pilot_approval 통과 후 전체 진행(reelforge 파일럿 게이트, 이미 coverage_pilot_shots 8 존재). (6) 승인 기록 없는 완료는 build_manifest가 거부(현 verify_upstream_hash_freshness 확장).
- claude_features: structured outputs(판사 JSON), 병렬 다수결 호출, 프롬프트 캐싱(루브릭), 모델 분리(심판 Opus 5)
- cost: 훅 5안 pairwise 10쌍×2스왑×3판사=60호출, 짧은 입력이라 Opus 5 ≈ $0.6~1.0(추정). 페르소나 패널 4×Sonnet 5 ≈ $0.5. 자동 승인 전환 후 사람 검토 시간 절감이 주된 효과.
- risk: kappa 보정 세트가 장르(역사 다큐 vs 놀람파일 트렌드)별로 달라 채널별 별도 보정 필요. 판사 모델 버전 교체 시 임계값 흔들림 → 모델 ID 핀 고정+교체 시 재보정. 자동 승인이 사료 오류를 통과시키는 사고는 비용이 커서 사실성은 끝까지 사람. pairwise 판사의 위치·장황함 편향 → 스왑+길이 정규화.
- sources: https://arxiv.org/abs/2407.18370 (Trust or Escalate, ICLR 2025, 확인 2026-09-02), https://arxiv.org/abs/2603.20324 (When Agents Disagree, 선택 승률 0.810 vs 합성 0/42, 확인 2026-09-02), https://github.com/NousResearch/autonovel (compare_chapters.py Elo·reader_panel find_disagreements, 확인 2026-09-02), https://github.com/calesthio/OpenMontage (5게이트·승인 없는 완료 거부·$0.50 승인, 확인 2026-09-02), https://github.com/gongnyang/reelforge (피크 씬 파일럿 게이트, 확인 2026-09-02), https://github.com/elementshq/jury-arena (6★, 3판사 다수결·Glicko-2, 참고용, 확인 2026-09-02)

### (L) 모션·렌더 — lib/motion_plan.build_motion_filter / lib/motion_engine_v3.trajectory / build_motion_clips_v3.py / build_subtitles_v2·korean_caption / FFmpeg 렌더 / release_report → LATER | stevecv get_varied_motions(연속 동일 모션 금지) + reelforge 검증된 안무 갤러리·결정표 + OpenMontage 렌더 후 self-review(ffprobe·4지점 프레임·오디오 레벨·자막 존재) + claude-faceless 렌더 프레임 비전 QA
- current: Ken Burns 모션 타입별 FFmpeg 필터·궤적 생성. 모션 다양성·강도 연동 규칙과 렌더 후 자동 셀프리뷰는 제한적.
- how: (1) 지금(결정론, Claude 무관): build_motion_clips_v3.py에 '직전 샷과 다른 motion_type 강제' + (F) intensity→줌 속도/팬 거리 매핑표(config/motion_profiles.yaml) + 원본 해상도 1.33배 확보 검사(media_probe). (2) 렌더 후 셀프리뷰 스크립트: ffprobe 길이=오디오 마스터 길이±0.5s, 오디오 피크/무음 구간, 자막 트랙 존재, 4지점 프레임 추출→OCR(기존 visual_content_qa)로 깨진 자막 검출 → release_report에 기록. (3) 나중: 추출 프레임 8~12장을 Claude 비전에 넣어 {subtitle_legible, subtitle_overlap_with_subject, black_frame, motion_artifact} 필드 추출(Batch). 비용 대비 효과 확인 후 도입.
- claude_features: (later) 비전 프레임 검사, structured outputs, Batch
- cost: 결정론 부분 $0. 프레임 QA 12장 Sonnet 5 ≈ $0.15/편(추정).
- risk: 모션 규칙 변경은 기존 test_motion_engine_v3·test_motion_clips_v2 회귀 테스트와 정합 필요. 프레임 비전 QA는 자막 가독성 판단이 주관적이라 kappa 확인 전 참고용.
- sources: https://stevecv.com/blog/ken-burns-effect-automated-video-production.html (get_varied_motions, 확인 2026-09-02), https://github.com/gongnyang/reelforge (안무 갤러리·strip QC, 확인 2026-09-02), https://github.com/calesthio/OpenMontage (렌더 후 self-review, 확인 2026-09-02), https://github.com/hassancs91/claude-faceless-shorts-creator (프레임 비전 QA, 확인 2026-09-02), https://github.com/VijaysinghPuwar/spoonstill (나레이션 경계 컷, 확인 2026-09-02)

### (M) CI·회귀 테스트·운영 — tests/(80개 pytest, conftest·fixtures) / requirements.lock.txt / (git 저장소 아님, CI 없음) / runs/ 산출물 → ADAPT | promptfoo/deepeval 골든셋 회귀(결정적 assert+llm-rubric, fail-on-threshold) + claude-code-action 자동화 모드(prompt+--json-schema→structured_output 게이트, paths 필터) + headless claude -p --bare + CI 보안 가드레일(--allowedTools 최소, SHA 핀, 포크 PR 차단) + Ralph loop(Stop 훅 반복, 완료는 exit code)
- current: pytest 80파일이 있으나 git·CI 부재. 대본 품질 골든셋 회귀(문장 통계·구조 비율·claim 인용률)는 없음. 프로바이더 비용 추적 없음.
- how: (1) 지금(리포화 전에도 가능): tests/test_script_quality_regression.py — runs/ep01~ep03의 승인 대본을 골든셋 fixture로 고정하고 (D) lib/script_slop_score.py 지표가 임계(중앙값 25~32자, 12~14문장/분, 5단계 비율 ±5%p, claim 인용률≥95%, 금지 표현 0) 안인지 결정적 assert. 프롬프트 템플릿·정책 YAML 변경 시 JsonFileProvider(재생)로 생성기 경로를 통과시켜 스키마·lint 회귀. LLM 루브릭 채점은 --run-llm-eval 옵션(기본 skip, Batch로 주 1회). (2) 리포화 후: human_archive를 git 저장소로 만들고 schemas/·config/·scripts/·tests/·runs/**/script*.json·*brief*.json만 추적(이미지·오디오·사료 원문은 제외 또는 LFS). GitHub Actions에 pytest + promptfoo-action(fail-on-threshold 90)과 claude-code-action 자동화 모드(on.pull_request.paths: runs/**/script*.json, runs/**/*brief*.json, schemas/**, config/*policy*.yaml; prompt='/script-qa --comment'; claude_args '--max-turns 8 --allowedTools Read,mcp__github_inline_comment__create_inline_comment --json-schema {verdict,issues[]}') → verdict=fail이면 needs-human-review 라벨. .claude/skills/script-qa/SKILL.md에 리뷰 기준을 코드로 버전 관리. (3) 비용 감사: 모든 Claude 호출의 usage(input/output/cache_read/cache_creation)를 runs/<ep>/generation_lineage.json에 기록하고 audit_episode_quality가 편당 USD 합산. (4) 보안: 사료·PR 본문은 신뢰 불가 입력 → CI에서는 Write/Bash 금지, 액션 SHA 핀, 포크 PR 차단, show_full_output 비활성. (5) 야간 자율 수정 루프(Ralph)는 완료 판정을 audit_episode_quality exit 0으로 하고 --max-iterations 10.
- claude_features: claude-code-action structured_output(--json-schema), headless claude -p --bare --output-format json, Agent SDK output_format(선택), usage/total_cost_usd 로그, Batch(주간 골든셋 재채점)
- cost: 결정론 회귀 $0. PR당 claude-code-action 1회(입력 40K·max-turns 8) Sonnet 5 ≈ $0.2~0.5 + Actions 분(추정). 주간 LLM 루브릭 골든셋 10편 Batch Sonnet 5 ≈ $1.
- risk: D:/module 전체가 git이 아니며 브라우저 CDP·TTS·승인은 로컬에 묶여 있어 CI는 텍스트 산출물(대본·브리프 JSON·스키마·정책)에만 적용. claude-code-action 오픈 이슈 748건·거의 매일 릴리스 → SHA 핀 필수. `claude -p --bare`는 API 키 필요(구독 OAuth 불가). Windows stdin 이슈는 v2.1.211+ 확인. promptfoo exec 프로바이더는 stdout 전체가 응답이므로 로그는 stderr로.
- sources: https://github.com/anthropics/claude-code-action (8,775★, pushed 2026-09-01, MIT, docs/usage.md structured_output, 확인 2026-09-02), https://code.claude.com/docs/en/github-actions (자동화 모드·스킬 호출, 확인 2026-09-02), https://code.claude.com/docs/en/headless (--bare·--json-schema·--resume, 확인 2026-09-02), https://github.com/promptfoo/promptfoo (24.8k★, 2026-09-02, exec 프로바이더·llm-rubric·promptfoo-action fail-on-threshold, 확인 2026-09-02), https://github.com/confident-ai/deepeval (18.0k★, G-Eval+pytest, 확인 2026-09-02), https://github.com/anthropics/claude-code/blob/main/plugins/ralph-wiggum/README.md (Stop 훅 루프, 확인 2026-09-02), https://github.com/anthropics/claude-agent-sdk-python (8.0k★, v0.2.151 2026-09-01, output_format·error_max_structured_output_retries, 확인 2026-09-02)

## provider_architecture
현재 상태: 대본은 scripts/lib/script_generation.py의 ScriptProvider Protocol(generate(*, prompt, output_schema) → dict, 내부에서 validate_json)을 AntigravityCliProvider(agy subprocess 또는 response_path 재생)·OmniRouteProvider·JsonFileProvider가 구현하고, 시각 브리프는 scripts/lib/visual_brief_provider.py에 별도 Protocol 없이 AntigravityCliVisualBriefProvider·CodexCliVisualBriefProvider(--output-schema)·JsonFileVisualBriefProvider·build_fallback_brief가 generate(prompt, schema_path)로 존재한다. 두 파일의 인터페이스가 미묘하게 다르고(schema dict vs schema_path), 프로바이더 선택이 스크립트별 argparse choices에 하드코딩되어 있으며 비용·토큰 기록이 없다.

통일안(파일 수정은 이 조사 범위 밖이므로 설계만):
1) 공통 계약: scripts/lib/llm_providers.py(신설)에 `class StructuredProvider(Protocol): def generate(self, *, prompt_parts: PromptParts, output_schema: dict, mode: Literal['sync','batch']='sync') -> ProviderResult` 를 두고, PromptParts={stable_prefix: list[str](캐시 대상: 페르소나 계약·정책 YAML·claim inventory·규칙표), variable: str(상태 카드·샷 배치·피드백), images: list[ImageRef]}, ProviderResult={payload: dict, usage: {input, output, cache_read, cache_creation}, cost_usd, provider, model, request_id, session_id}. 기존 script_generation.ScriptProvider와 visual_brief_provider의 generate는 이 계약을 감싸는 얇은 어댑터로 유지해 호출부(generate_verified_script.py, generate_visual_briefs.py)를 깨지 않는다.
2) 구현체: (a) ClaudeMessagesProvider — anthropic SDK messages.create(또는 messages.parse), system=[stable_prefix 블록들에 cache_control ephemeral(ttl 1h)], output_config.format=json_schema(SDK가 minLength/maxLength/minimum/maximum·additionalProperties≠false를 제거하므로 반환 후 반드시 기존 schema_validation.validate_json으로 재검증), thinking adaptive, streaming get_final_message, batch 모드는 messages.batches.create(custom_id=shot_id/beat_id). 이미지가 있으면 vision 블록, 참조 자산은 Files API file_id. (b) ClaudeCliProvider — `claude -p --bare --output-format json --json-schema <schema> --allowedTools Read` subprocess, CodexCliVisualBriefProvider와 동일한 형태(UTF-8 stdin 명시), 파일 읽기·검색이 필요한 검증 단계나 로컬 자율 루프용. --resume session_id로 피드백 재생성. (c) 기존 AntigravityCliProvider·CodexCli·OmniRoute 유지, JsonFileProvider는 테스트·재생·골든셋용 필수 유지. (d) 모든 구현체가 ProviderResult.usage를 반환하고 호출부가 runs/<ep>/generation_lineage.json에 기록(비용 감사, cache_read==0 경보).
3) 단계별 라우팅 설정: config/provider_routing.yaml — stage→{provider, model, effort, mode, fallback_provider}. 기본값: (A) claim 관점 질문·citations=claude-api / (B) 아웃라인=claude-api / (C) 대본 본문=claude-api(기본), agy·codex는 N후보 생성용 대체 생성기 / (D) 심사=claude-api(생성과 다른 모델) / (G) 브리프=claude-api batch / (I) 이미지 채점=claude-api batch / (J) 재사용 판정=claude-api / (E)(F)(H)(L)=결정론 코드 또는 Flow, Claude 미사용 / (K) 심판=claude-api / (M) CI=claude-cli 또는 claude-code-action. 에피소드 단위가 아니라 단계 단위로 선택하고, 스크립트의 --provider는 routing 파일을 덮어쓰는 옵션으로만 남긴다.
4) 프롬프트 템플릿 분리: templates/<stage>/<provider>.md — Claude용은 '문서(바이블)→지시' 순서·과도한 지시 축소, agy/Codex용은 기존 유지. 캐시 안정성을 위해 json.dumps(sort_keys=True, ensure_ascii=False)와 타임스탬프 제거를 PromptParts 빌더에서 강제.
5) 게이트 위치: 프로바이더 호출 전 PreGenerate 훅(아웃라인 존재·검증 통과·상태 카드 크기 ≤12KB), 호출 후 PostGenerate 훅(validate_json → slop score → 결정론 연속성 검사 → LLM 심사 순, 실패 시 구조화 피드백으로 최대 2회 재시도 후 REVIEW_REQUIRED). 이 훅은 Agent SDK 훅이 아니라 우리 파이썬 코드에 두어 프로바이더에 무관하게 동작시킨다.
6) 선행 조건: anthropic SDK 설치(requirements.lock.txt 갱신), `ant auth status`로 자격 확인(없으면 ANTHROPIC_API_KEY), 첫 도입 시 EP01 대본(한글 20,228자)·flow_image_prompts.json으로 count_tokens 실측해 비용 추정치 보정. Agent SDK(claude-agent-sdk)는 파일 탐색이 필요한 검증·CI 자율 루프에만 후순위로 검토하고, 단순 생성·채점은 Messages API가 더 싸고 단순하다(claude-api 스킬 'Start simple' 권고).

## model_routing
원칙: (1) 생성 모델과 심사 모델을 분리(docs develop-tests 권고), (2) 결정 가능한 지표(문장 길이·비율·claim 결속·금지어)는 코드로, LLM은 주관 지표만, (3) 저가 워커 fan-out + 경계 사례만 상위 모델 재판정, (4) 비실시간 대량 단계는 Batch(50%)+캐시 1h TTL, (5) 모델 ID는 날짜 접미사 없이 핀 고정(claude-opus-5, claude-sonnet-5, claude-haiku-4-5)하고 교체 시 kappa 재보정. 아래 가격·비용은 docs Pricing(2026-09-02)과 조사 채널의 추정치(한국어 1자≈0.8~1.0토큰, count_tokens 실측 전)다.

단계별 권장:
- (A) 관점 유도 질문·citations 결속: claude-opus-5, effort high, 편당 1~2회(사료 전량 입력이라 횟수 제한). 초장문 사료 청킹 요약만 claude-haiku-4-5(청크)→claude-sonnet-5(메타).
- (B) 아웃라인: claude-opus-5, adaptive thinking, effort high~xhigh(구조 설계는 품질 민감). 훅 비트 다중 후보는 같은 모델의 온도/프롬프트 변형 + agy/Codex 1안(이질 생성기).
- (C) 대본 본문(5비트 순차): claude-opus-5 기본(편당 ≈ $1.5~1.8 캐시 포함, 추정). 품질 eval에서 동등하면 claude-sonnet-5(≈ $0.5)로 낮추는 것은 사용자 결정 사항이며, 먼저 'Opus 5 effort medium'을 측정하는 편이 캐시 네임스페이스를 하나로 유지하므로 권장. claude-fable-5-1은 tool_choice 강제 불가·30일 보존·Priority Tier 없음·편당 ≈ $2.3~2.8라 기본 제외, 최종 심판·adversarial cut 같은 저빈도 고난도 호출에만 후보(later).
- (D) 대본 자동 QA: 무API slop score 먼저($0). LLM 심사는 생성이 Opus 5이면 claude-sonnet-5로(≈ $0.17), 최종 릴리스 전 1회만 claude-opus-5(≈ $0.4). 델타 요약·상태 카드 갱신은 코드 또는 claude-haiku-4-5.
- (E) 페르소나 필드 추출: claude-sonnet-5(판정은 코드). 사료 사실성은 모델 판정 금지(사람).
- (F)(H)(L): 모델 없음(결정론·Flow).
- (G) 시각 브리프 110샷: claude-sonnet-5 Batch, 10샷 단위+캐시(≈ $0.65). 파일럿 12+8샷은 동기 claude-opus-5(≈ $0.6). lint 실패 샷만 claude-opus-5 재생성.
- (I) 이미지 의미 채점 110장: 1차 claude-sonnet-5 Batch, 1456×819 다운스케일(≈ $0.6); partial/unknown 경계(약 20%)만 claude-opus-5 동기 재판정(≈ $0.5). claude-haiku-4-5(≈ $0.35)는 표준 해상도 티어·캐시 최소 4,096토큰·200K 컨텍스트라 루브릭이 길지 않을 때만.
- (J) 재사용 판정 30후보: claude-sonnet-5(≈ $0.4), 갈린 항목 3회 다수결.
- (K) pairwise 심판·페르소나 패널: 심판은 claude-opus-5(선택기 품질이 생성기 다양성보다 중요, When Agents Disagree), 패널 4인은 claude-sonnet-5.
- (M) CI 리뷰 코멘트: claude-sonnet-5 --max-turns 8(PR당 ≈ $0.2~0.5). 주간 골든셋 LLM 루브릭은 Batch claude-sonnet-5.

편당 합계(추정): 권장 혼합 ≈ $3.5~4.5(대본 Opus 5 + 나머지 Sonnet 5, 캐시+Batch), 전부 Opus 5 동기·무캐시 ≈ $9~12, 전부 Sonnet 5+Batch ≈ $2, 전부 Fable 5.1 ≈ $14~20. 도입 첫 2편은 전 단계 Opus 5로 돌려 품질 상한을 기록한 뒤 단계별로 낮추며 kappa·eval로 확인한다.

## what_not_to_adopt
- Claude Engineer(Doriandarko/claude-engineer, 11,218★): 코드 도구 자기 생성용 CLI이며 2024-12-12 이후 커밋 없음·라이선스 미지정·Claude 3.5 Sonnet 고정. 장편 텍스트 컨텍스트·아웃라인·일관성 기법이 전혀 없고, 같은 역할은 Claude Code/Agent SDK가 공식 지원하므로 도입 이유 없음(확인 2026-09-02).
- Artifacts/챗 UI 클론·마케팅 챗봇 스킬(sergebulaev/youtube-skills 8★, AgriciDaniel/claude-youtube의 SEO·수익화·커뮤니티 포스트 서브스킬): 영어 마케팅 관행 기준의 제목·설명·썸네일 문구 생성이며 사료 검증·장편 일관성·한국어 벤치마크와 무관. claude-youtube의 '훅 유형+위험도 라벨' 아이디어만 (B)에 차용하고 나머지는 제외.
- Cookbook 'JSON mode(prefill)' 레시피(misc/how_to_enable_json_mode): assistant prefill은 Opus 5/Sonnet 5/Fable 5.1 및 4.6+ 전 모델에서 400 에러. structured outputs(output_config.format)로 대체.
- '합성(synthesis)' 집계: N후보의 좋은 부분을 합치는 방식은 When Agents Disagree(arXiv 2603.20324)에서 42과제 중 0건 우위. 선택(pairwise judge)만 채택.
- 자연어 비평→재생성 반복 루프를 3회 이상 돌리는 설계(AutoGen primary+critic 'APPROVE' 문자열 종료 포함): JETTS(arXiv 2504.15253)상 비효과이고 AutoGen은 유지보수 모드. 구조화 피드백(rule_id+sentence_id) 2회 상한으로 대체.
- RecurrentGPT 장기 임베딩 메모리(GPL-3.0, 2024-05 정체, OpenAI 기반): 18~20분 대본은 1M 컨텍스트에 통째로 들어가므로 불필요하며 GPL 전파 위험. 단기 요약 카드 개념만 차용.
- Claude-Book perplexity-improver(로컬 Ministral-3-8B + CUDA): 한국어 소형 모델 퍼플렉시티 신뢰도 낮음(추정)·GPU 의존. 한국어 slop score(D)로 대체.
- Dynamic Workflows(code.claude.com/docs/en/workflows, Cookbook 08): 110샷 fan-out에 적합하나 토큰 사용량이 단일 에이전트보다 크게 늘고(노트북 $2~4/실행) 스크립트 내 파일시스템 접근 불가. 10샷 슬라이스로 비용 측정 전까지 보류(later).
- humanlayer/humanlayer(11.4k★): README에 '코드 사실상 전부 폐기' 명시. 승인 콜백은 Agent SDK can_use_tool/PreToolUse 훅 또는 우리 approval.py로 자체 구현.
- langgraph-reflection(2026-04-01 아카이브)·LangGraph 전체 도입: 의존성 증가 대비 이득 없음. `when` 술어 조건부 인터럽트 개념만 (K)에 반영.
- ContentMachine의 'LLM이 실제 역사 이야기를 고르고 나레이션을 시각 뒤에 생성' 순서: 우리 claim inventory→대본→TTS 선행 구조와 반대이며 사실 검증이 없음. 4변형·외형 고정 규칙만 차용.
- OpenMontage·autonovel·forsonny 코드 직접 병합: 각각 AGPLv3·라이선스 미지정·라이선스 미지정. 패턴만 이식하고 코드는 복사하지 않음.
- MoneyPrinterTurbo/ShortGPT류 스톡 키워드 검색형 소재 매칭: 문장 단위 생성 이미지 파이프라인과 철학이 다르고 ShortGPT는 2025-02 이후 정체.
- 클라이언트 측 CLIPScore(영어 CLIP)를 한국어 문장에 직접 적용: 다국어 미검증. 쓴다면 영문 visual_prompt 대비 또는 Qwen-VL 계열 VQAScore(40GB+ GPU 요구)로 우회하되 Claude 비전 필드 추출(I)이 먼저.

## quick_wins
- [3~4일] scripts/lib/script_generation.py에 ClaudeApiProvider 추가(ScriptProvider 시그니처 유지): anthropic SDK 설치·`ant auth status` 확인 → system 캐시 블록(seonbi_narration_policy.yaml+스타일 가이드+claim_inventory, sort_keys 직렬화) + output_config.format=verified_script_v2 → validate_json 재검증 → usage를 generation_lineage에 기록. generate_verified_script.py --provider claude-api 선택지. 첫 실행 전 count_tokens로 EP01 대본·claim inventory 토큰 실측해 비용표 보정.
- [2~3일] scripts/lib/script_slop_score.py(무API) 신설 + audit_episode_quality.py 연동: 문장 중앙값(28자)·문장길이 CV·분당 문장 수(12.7)·5단계 비율 이탈·4-gram 반복률·접속부사 시작 비율·'~것이다' 연속·금지 표현 티어를 점수화하고 sentence_id 위치를 출력. 인류의 서재 30편 통계로 임계값 도출, tests/test_script_quality_regression.py에 runs/ep01~03 승인 대본을 골든셋으로 고정.
- [2일] schemas/narrative_outline_v2.schema.json + lib/narrative_outline 검증 확장: core_beats에 stage·pct_range·target_sec·emotion_arc·plants/payoffs·ending_hook_type 필드, promise_ledger, 결정론 검사(비율 ±5%p, payoff>plant, 총 1080~1200s). 생성은 Claude structured output, 훅 비트만 3안.
- [3~4일] scripts/score_visual_semantics.py: Flow 산출 PNG를 1456×819로 줄여 Claude 비전+structured output으로 사실 필드만 추출(has_text, mascot_present, focal/action/place/era match, unknown) → 코드가 approve/flag/block/needs_review 판정 → visual_semantic_review.schema.json 저장, OCR/pHash와 OR 결합. 파일럿 20샷 동기(Sonnet 5), 나머지 Batch. 사람 승인 대기열을 approve 후보와 needs_review로 분리.
- [2일] lib/visual_brief_provider.py에 ClaudeVisualBriefProvider(CodexCliVisualBriefProvider와 동일 generate(prompt, schema_path)): 정책·대본·타이밍을 캐시 프리픽스로, 10샷 단위 배열 출력, --batch 옵션. prompt_lint에 anchor_details(개체·행동·모티프) 3디테일 검사와 연속 4샷 동일 shot_type 오류 추가로 에피소드별 수작업 규칙표 의존을 lint 규칙으로 옮기기 시작.