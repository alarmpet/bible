# 구약 힐링 영상 제작 매뉴얼

이 문서는 작업 전 확인용 기준이다. **단일 적용 기준은 `bible_healing/config/media_rules_lock.json`이다.** `final_render_policy.json`·`healing_caption_policy.json`은 lock과 동기화되어야 한다. 최종 렌더 전에는 preflight를 통과해야 한다.

## 고정된 최종 자막 방식

- 롱폼용 균형 2줄 자막을 사용한다.
- 한 줄 목표 14~18자, hard 최대 20자, 한 화면 최대 2줄이다.
- 어절과 문장 의미 단위에서 나누고, 조사·어미 중간 분할을 금지한다. 자막이 화면을 덮지 않도록 하단 중앙에 고정한다.
- 음성 세그먼트의 실제 시작·종료 시각을 사용한다. 장면 전체 시각을 반복 사용하지 않는다.
- 글꼴·크기·외곽선·위치는 전체 영상에서 고정한다 (본문 96px, 성경 100px, outline 6, shadow 3, marginV 90).
- 자막 교체는 한 단어씩 흘려보내지 않고, 짧은 구절 단위로 한다.

## 화자와 성경 본문

- 화자는 `narrator`와 `scripture` 두 종류만 허용한다.
- narrator = **M2 warm @ 0.95**, total_step 10, 쉼 0.25초, 남성 따뜻한 해설 톤. 기준 샘플은 `D:\module\bible\human_archive\audits\supertonic3_male_voice_samples_2026-08-31\M2_warm.wav`이다.
- scripture = **M4 @ 0.86** (10% 감속으로 차분한 낭독 템포), total_step 10, 쉼 0.35초, 동일 화자 간격 0.40초, 피치 **-10%** (`asetrate=24000*0.90`, atempo 없음, lowpass 6000, EQ 180+3 / 120+2). 체감 속도 약 0.77. 기준 샘플은 `D:\module\bible\bible_healing\assets\voice_refs\scripture_M4_ref.wav`이다.
- 성경은 절(마침표)마다 따로 합성한다. `max_chunk_length` 90, 어절 중간 절단 금지.
- 성경 본문에서 괄호 설명, 곡 제목, `다윗의 시`, `영장으로`, `셀라`, 느낌표·물음표를 제거한다.
- TTS 입력의 숫자는 한글로 읽힌다 (`1814년`→`천팔백십사년`). 자막은 숫자를 그대로 둔다.
- 합성 후 엔진 앞뒤 정적을 자른다. 같은 화자 간격 0.40초(숨 쉴 틈 확보), 장면·화자 전환 0.6초는 조립 단계에서 넣는다.
- SuperTonic HTTP 서버(`http://127.0.0.1:3093`)가 켜져 있어야 합성한다. 꺼져 있으면 폴백하지 않고 중단하며, 서버 기동 후 재시도한다. CosyVoice 등 새 TTS는 설치하지 않는다.
- 서버 기동: `powershell -File bible_healing/scripts/start_supertonic3_server.ps1`
- M1/M3/M4/M5는 이 운영 프로필의 기본 나레이터로 사용하지 않는다. 성경 본문은 기존 규칙대로 M4를 사용한다. 자세한 표는 `MEDIA_RULES.md`와 `media_rules_lock.json`.

## 우측 상단 주제 표시 정책

우측 상단에는 매 자막마다 제목을 띄우지 않고, 장면 또는 큰 주제가 바뀔 때만 성경 권/장/절(`- 시편 4편 -`, `- 시편 27편 1-5절 -`, `- 잠언 6장 5절 -`) 또는 주제 라벨(`- 오프닝 -`, `- 잠들기 전 마음이 멈출 때 -`)을 표시한다.

- 현재 읽고 있는 구절/주제 확인용 지속 라벨이며 본문 자막(하단 2줄)과 분리된 Layer 1이다.
- 크기는 **하단 본문 자막 크기의 약 70%인 70px (1080p 기준)**로 시인성 있게 표시한다.
- 자막 스타일: `Style: Chapter,Malgun Gothic,70,&H00E8E0D0,&H00E8E0D0,&H00000000,&H90000000,0,0,0,0,100,100,0,0,1,3,2,9,120,120,90,1`
- 주제나 구절이 바뀔 때 문구만 교체하고, 영상에서 깜빡이지 않고 지속적으로 유지한다 (연속된 씬 병합 유지).
- YouTube 업로드 설명에는 별도로 `00:00`부터 챕터 타임스탬프를 작성한다. 영상 안의 라벨과 플랫폼 챕터는 함께 사용한다.

## 배경영상 고정 규칙

- 최종영상 배경은 반드시 `bible_healing/assets/movie-sample/pingpong-1min`의 1분 MP4를 사용한다.
- `scene_*_flow.jpg`, `bg_*.jpg`, 정지 이미지, 단색 plate는 최종 배경으로 사용 금지.
- 12개 1분 앰비언트 MP4를 순환 사용하고, 단일 촛불 영상만 반복하지 않는다.
- **배경 재생 속도**: `setpts=10*PTS`로 **0.1배속 초슬로우 모션**을 적용하여 촛불, 물결 등이 매우 은은하고 고요한 앰비언트 모션을 유지한다.
- **배경 전환 주기**: 각 배경 영상은 **정확히 1분(60초)마다 다음 샘플로 순환 전환**된다 (각 영상의 0.1배속 60초 구간 순차 렌더링).
- 렌더 시작 전 `final_background_preflight.py`를 통과해야 한다.

## 전체 배포영상 필수 검사 규칙

- 전체 배포영상에는 `subtitles-full-audio-aligned.ass` 본문 자막을 반드시 번인한다.
- 챕터 표시만 있고 본문 자막이 없는 영상은 최종본으로 인정하지 않는다.
- 최종 음성 길이와 자막 마지막 타임코드는 0.5초 이내로 일치해야 한다.
- 기존 자막 파일을 다른 전체 영상에 복사하지 않는다. 음성·자막·영상이 동일 작업 산출물인지 확인한다.
- 장면 manifest에 없는 추가 음성 구간이 있으면 배포하지 않고 원본을 먼저 대조한다.

## 작업 전·최종 검사

```powershell
python bible_healing/scripts/final_background_preflight.py
python bible_healing/scripts/final_render_preflight.py
```

## [쉽선비 / Human Archive] v5/v6 내레이션 정렬형 제작 매뉴얼

이 섹션의 실제 TTS 기반 동적 샷 절차가 신규 에피소드 정본이다. 기존 `full-v4-*`, 대표 8장, 대본 글자 수 기반 샷, 호스트 15~25% 절차는 레거시 빌드 재현에만 사용한다. EP02 v6 재개 전에는 `docs/solutions/integration-issues/ep02-v6-reuse-first-tts-codex-visual-brief-recovery-2026-08-28.md`의 현재 상태와 stop gate를 먼저 확인한다.

### 1. 고정 순서와 역할 정책

표준 순서는 다음과 같다.

```text
승인 대본 → 실제 Supertonic3 문장 TTS → 실측 샷 타이밍
→ 구체 의미 브리프·Flow 요청 → 이중 파일럿 → 전체 이미지
→ OCR·중복·연속성·해시 QA → 최신 전체 사람 승인
→ 25 CFR 모션 → 문장 자막 → 최종 렌더 → postflight
```

- 샷 수는 45개로 고정하지 않는다. 실제 문장 음성의 9~12초 목표와 최대 15초 규칙으로 계산한다.
- 역할은 `host_explainer`, `historical_reconstruction`, `evidence_object`, `diagram_metaphor`, `atmosphere`다.
- 쉽선비는 호스트 장면에만 전체 8~12%, 최소 7샷 간격으로 배치한다.
- 호스트 배경에는 사람·손·신체 일부가 없어야 한다. 승인된 `doodle_seonbi_v1.png`만 후처리 합성하며 완전한 갓·얼굴·몸통·소매·깃·허리끈을 유지한다.
- 비호스트에는 쉽선비·검은 갓 마스코트·발표자·카메라 응시 인물을 금지한다.
- AI 이미지에는 연도·숫자·글자·캡션·간판·인장·말풍선·워터마크·서비스 마크를 생성하지 않는다.
- 한글 semantic anchor와 범용 fallback은 생성 전 FAIL이다. 새 내레이션에 구체 장면 규칙이 없으면 생성하지 않는다.

### 2. Chrome CDP 연결

기존 Chrome이 디버그 포트를 점유하거나 일반 프로필에 붙는 경우 사용자가 작업을 저장하고 창을 직접 닫은 후 별도 프로필로 시작한다. `Stop-Process`는 관련 없는 Chrome 세션까지 종료하므로 현재 턴의 명시적 사용자 승인 없이 에이전트가 실행하지 않는다. `Start-Process` 인자에 마크다운 링크나 백슬래시 이스케이프를 넣지 않는다.

```powershell
# 사용자 명시 승인 뒤에만 전체 Chrome 강제 종료
Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue
Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList '--remote-debugging-port=9222','--remote-allow-origins=*','--user-data-dir="C:\Users\shs\.chrome_debug_ep02"','https://labs.google/fx/tools/image-fx'
curl.exe http://127.0.0.1:9222/json/version
```

정식 자산 필드는 `file_path`와 `card_id`다. 파일명·SHA-256·20KB 이상 바이트·양수 해상도·카드 ID가 모두 있어야 `COMPLETED`이며, `SUBMITTED`는 실행 중 중간 상태다.

### 3. v5/v6 실행 명령

```powershell
$build = 'human_archive/runs/ep02_jang_huibin/full-v6-001'
$script = "$build/source/script_candidate.json"
$claims = "$build/source/claim_inventory_v2.json"
$sources = "$build/source/source_snapshot_manifest_v2.json"
$factReport = "$build/source/fact_check_report_v2.json"
$personaReport = "$build/source/persona_report_v2.json"
$factApproval = "$build/source/approvals/fact_review_approval_v1.json"

# 실제 음성 → 타이밍
curl.exe http://127.0.0.1:3093/health
python human_archive/scripts/build_sentence_audio_master.py --script $script --build $build --audio-mode supertonic3 --tts-url http://127.0.0.1:3093
python human_archive/scripts/plan_narration_shots.py --script $script --audio "$build/sentence_audio_manifest.json" --claims $claims --profile narration_aligned_hybrid_v1 --output "$build/shot_timing_manifest.json"

# 의미 브리프 → 프롬프트 사전검사
# 현재 fact review 문구를 사람이 명시 승인한 경우에만 기록한다.
python human_archive/scripts/record_fact_review_approval.py --script $script --fact-report $factReport --persona-report $personaReport --claims $claims --sources $sources --output $factApproval --reviewer-id <human-reviewer-id> --approval-source explicit_user_confirmation_in_antigravity_thread
python human_archive/scripts/generate_visual_briefs.py --script $script --timing "$build/shot_timing_manifest.json" --claims $claims --sources $sources --fact-report $factReport --persona-report $personaReport --fact-approval $factApproval --provider antigravity-cli --response-output "$build/visual_brief_response_v1.json" --output "$build/visual_brief_manifest.json" --prompts "$build/flow_image_prompts.json"
python human_archive/scripts/build_image_request_manifest_v5.py --build $build
python human_archive/scripts/validate_image_requests.py --build $build

# 의미 재사용 계획 → 사람 검토 승인 → dry-run → 실제 물질화
$sourceBuild = 'human_archive/runs/ep02_jang_huibin/full-v5-001'
$reusePlan = "$build/image_reuse_plan.json"
$reuseApproval = "$build/image_reuse_review_approval.json"
python human_archive/scripts/build_semantic_image_reuse_plan.py --source-build $sourceBuild --target-build $build --output $reusePlan
# review_candidate 전부를 사람이 판단하고 현재 plan/request SHA 결속 승인 파일을 만든 뒤에만 아래 두 명령 실행
python human_archive/scripts/materialize_semantic_image_reuse.py --source-build $sourceBuild --target-build $build --plan $reusePlan --review-approval $reuseApproval --dry-run
python human_archive/scripts/materialize_semantic_image_reuse.py --source-build $sourceBuild --target-build $build --plan $reusePlan --review-approval $reuseApproval

# 콜드오픈 12 + 커버리지 8 이중 파일럿
python human_archive/scripts/generate_flow_batch.py --build $build --pilot --model "Nano Banana 2" --cdp http://127.0.0.1:9222
python human_archive/scripts/build_contact_sheet.py --build $build --pilot-set cold_open --output "$build/pilot_cold_open_contact_sheet.jpg"
python human_archive/scripts/build_contact_sheet.py --build $build --pilot-set coverage --output "$build/pilot_coverage_contact_sheet.jpg"
python human_archive/scripts/verify_visual_assets.py --build $build

# 파일럿 명시 승인 후 전체 생성
python human_archive/scripts/generate_flow_batch.py --build $build --all --model "Nano Banana 2" --cdp http://127.0.0.1:9222
python human_archive/scripts/build_contact_sheet.py --build $build --output "$build/contact_sheet.jpg"
python human_archive/scripts/verify_visual_assets.py --build $build

# 최신 전체 연락시트 명시 승인 후 실제 승인자 ID로만 기록
python human_archive/scripts/record_visual_approval.py --build $build --reviewer-id <approved-reviewer-id>
python human_archive/scripts/verify_visual_assets.py --build $build

# 모션·문장 자막·렌더·검증
python human_archive/scripts/build_motion_clips_v2.py --build $build
python human_archive/scripts/build_subtitles_v2.py --build $build
python human_archive/scripts/render_episode_v2.py --build $build --output "$build/candidate/HA002-full-v6-001.mp4"
python human_archive/scripts/postflight_release.py --input "$build/candidate/HA002-full-v6-001.mp4" --report "$build/release_report.json" --duration-mode full
```

`record_fact_review_approval.py`는 fact report의 FAIL·unsupported·forbidden·conflict가 모두 0이고 모든 review 사유가 정확히 승인 문구 차이이며 persona `overall_status`가 `PASS`일 때만 동작한다. review의 `sentence_id`는 비어 있지 않은 문자열이어야 하고 `segment_index`·`review_required_count`는 bool·문자열·실수에서 변환하지 않은 정수여야 한다. raw fact report는 수정하지 않는다. 승인 파일은 script/fact/persona/claims/sources SHA와 정확한 review-set에 결속되며, 같은 입력 재실행은 byte/mtime을 바꾸지 않고 stale·변조 파일은 덮어쓰지 않는다. `generate_visual_briefs.py`는 이 다섯 fact gate 인자를 필수로 요구하고 출력 manifest v2에 승인 SHA를 남긴다.

`--provider codex-cli`는 전송 텍스트 범위를 설명하고 사용자가 **별도로 외부 전송을 승인한 뒤에만** 실행한다. 사실 문구 승인은 외부 전송 승인이 아니다. 승인 전에는 검토된 응답 파일을 `--provider json-file --response <reviewed-response.json>`로 사용하되 fact gate 인자를 생략하지 않는다. provider를 생략해 fallback을 사용하지 않는다. `image_reuse_plan.json`은 계획만 기록한다. 재사용은 전용 materializer로만 실행하고, review candidate 승인 파일을 자동 생성하거나 임시 복사 명령으로 우회하지 않는다. source/target 계약 SHA, 승인 SHA, 실제 이미지 SHA가 모두 맞고 dry-run·실행이 통과해야 Flow 파일럿으로 이동한다.

### 4. 실패 장면 복구

정책 위반과 OCR 실패는 별도 생명주기로 처리한다.

- 정책 거절: 동일 프롬프트 반복·계정 변경 금지. 첫 자동 재시도는 `safe_rephrase`, 두 번째는 모드별 `safe_abstraction`, 그 다음은 `REVIEW_REQUIRED`다.
- OCR 실패: 일반 OCR-safe 1회, ultra-minimal 1회 뒤 직접 크롭 검토로 전환한다.
- 실제 글자·워터마크·서비스 마크는 예외 승인하지 않고 재생성한다.
- 사물 곡선 등을 문자로 읽은 확정 오탐만 현재 이미지 SHA와 OCR findings SHA에 결속해 기록한다.
- 프롬프트 해시가 바뀐 과거 자산은 생성 전에 `asset_history`와 `rejected_visual_variants/`로 보존한다.

```powershell
# 정책 거절
python human_archive/scripts/rewrite_policy_rejected_prompt.py --build $build --scene-id <shot_id> --reason provider_policy_rejected
python human_archive/scripts/generate_flow_batch.py --build $build --only <shot_id> --model "Nano Banana 2" --cdp http://127.0.0.1:9222

# OCR 실패: 같은 명령의 두 번째 실행은 ultra-minimal 단계
python human_archive/scripts/rewrite_v5_ocr_failed_prompts.py --build $build --scene-id <shot_id>
python human_archive/scripts/generate_flow_batch.py --build $build --only <shot_id> --model "Nano Banana 2" --cdp http://127.0.0.1:9222
python human_archive/scripts/verify_visual_assets.py --build $build
```

### 5. 승인·렌더 차단 조건

- `flow_batch_report` PASS는 다운로드 무결성일 뿐 시각 승인이 아니다.
- 사실 보고서가 PASS이거나, REVIEW_REQUIRED가 오직 승인 가능한 문구 차이이며 현재 다섯 SHA와 review-set에 결속된 명시적 사람 승인이 있어야 한다. 외부 전송은 별도 승인이다.
- 자동 콘텐츠 PASS, 파일럿 승인, 전체 승인 파일은 서로 대체할 수 없다.
- 전체 승인은 최신 `contact_sheet.jpg`의 모든 현재 샷에 대한 명시적 확인이어야 한다.
- `tone_fixture`가 한 문장이라도 있거나 실제 TTS 후 샷 경계·요청 해시가 달라졌다면 모션을 시작하지 않는다.
- 이미지·요청·OCR·승인 해시 중 하나라도 stale이면 해당 영향 범위를 재검토한다.
- 자막은 같은 빌드의 실제 문장 시작·종료 시각을 사용하고 마지막 큐가 마스터 오디오와 0.5초 이내로 일치해야 한다.

v6 현재 상태, Luna 복구 순서, 외부 전송 범위, 실행기 우회는 `docs/solutions/integration-issues/ep02-v6-reuse-first-tts-codex-visual-brief-recovery-2026-08-28.md`에서 확인한다. v5 자산 생명주기 이력은 `docs/operations/2026-08-27-flow-v5-pilot-state-recovery.md`와 v5 해결 기록을 참고한다.

### 6. EP02 v6 현재 재개 지점 (2026-08-28)

`full-v6-001`의 Codex 2차 시각 브리프 교정본이 전체 게이트를 통과했다. 현재 정본은 112개 요청, 호스트 11개, 직접 묘사 68개(60.71%), `1701` 0건, 제출 prompt 한글 0건이다. OCR-safe 재시도 뒤 `flow_image_prompts.json` SHA-256은 `BC9ECBB5C42A01AA9752A8CFFB7573085EDF81DEF9AA6B6BC5F7751826509EB2`이며 `image_request_manifest.contract_sha256`와 같다.

재사용 계획은 `auto_reuse=8`, `review_candidate=22`, `generate_new=82`다. 22개 재사용 승인을 기록하고 30개를 물질화했다. 이후 파일럿 20/20과 OCR 콘텐츠 PASS를 확인했다. 현재 다음 작업은 최신 콜드오픈·커버리지 연락시트의 사람 승인이다. 승인 전에는 전체 82개 생성·모션·자막·렌더로 진행하지 않는다.

복구 시 주의사항:

- Codex CLI stdin은 UTF-8을 명시한다.
- 반복 모티프 QA는 `prop_motifs`만 센다. 설명문의 추상적 boundary/edge를 시각 소품으로 세지 않는다.
- 실제 반복은 원본 응답을 보존한 뒤 별도 교정본에서 최소 수정하고 `json-file` 공급자로 전체 재검증한다.
- 재사용은 source/target의 visual mode와 role이 모두 호환될 때만 후보로 유지한다.
- Flow `최신 업데이트` dialog가 입력을 막으면 사용자 표시 시작 버튼을 role 기반으로 닫고 hidden을 확인한다.
- OCR-safe `--only` 재생성 뒤에는 `--pilot`을 다시 실행해 `flow_batch_report.json`을 20/20 범위로 복원한다.
