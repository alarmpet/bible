Flow automation`n`nSee flow_automation/README.md for installation, Generate Missing, Resume, recovery codes, and uninstall instructions.`n`n# Human Archive — 20분 시네마틱 다큐멘터리 파이프라인 (놀람파일 / 쉽선비)

**Human Archive**는 AI 기반 롱폼 다큐멘터리 자동화 제작 시스템입니다.

- **1순위 메인 프로필**: `nollam_file_v1` (**놀람파일 / NOLLAM FILE**) — '인류의 서재' 벤치마크 기반 20분 롱폼(1200초) 포토리얼리스틱 시네마틱 다큐멘터리 (호스트 아바타 0%, 7구간 시간 감쇠 페이싱, Claude 4-Step 대본 체인, Midjourney v6.1 / Flux.1 시네마틱 B-roll).
- **2순위 레거시 서브 프로필**: `doodle_seonbi_v1` (**갓쓴 스틱맨 쉽선비**) — 조선 역사 두들 다큐멘터리 (호스트 캐릭터 합성 8~12%).

상세 설계 및 마스터 플랜: `docs/superpowers/plans/2026-09-02-human-archive-retention-pacing-autonomy-master-plan.md` (v2.1)

## 1. 환경 설정
```bash
python -m pip install -r human_archive/requirements.lock.txt
```

## 2. 표준 에피소드 제작 명령

### 1단계: 근거 스냅샷 및 Claim 인벤토리 생성
```powershell
python human_archive/scripts/build_source_snapshots.py --ledger human_archive/sources/pompeii_ep01_source_ledger.json --output human_archive/runs/ep01_pompeii_v2/source/source_snapshot_manifest_v2.json
python human_archive/scripts/build_claim_inventory.py --ledger human_archive/sources/pompeii_ep01_source_ledger.json --sources human_archive/runs/ep01_pompeii_v2/source/source_snapshot_manifest_v2.json --output human_archive/runs/ep01_pompeii_v2/source/claim_inventory_v2.json
```

### 2단계: 대본 생성 및 사실/페르소나 역검증
```powershell
python human_archive/scripts/generate_verified_script.py --contract human_archive/templates/documentary_contract.yaml --claims human_archive/runs/ep01_pompeii_v2/source/claim_inventory_v2.json --sources human_archive/runs/ep01_pompeii_v2/source/source_snapshot_manifest_v2.json --output human_archive/runs/ep01_pompeii_v2/source/script_seonbi_v2.json
python human_archive/scripts/verify_script_facts.py --script human_archive/runs/ep01_pompeii_v2/source/script_seonbi_v2.json --claims human_archive/runs/ep01_pompeii_v2/source/claim_inventory_v2.json --sources human_archive/runs/ep01_pompeii_v2/source/source_snapshot_manifest_v2.json --report human_archive/runs/ep01_pompeii_v2/source/fact_check_report_v2.json
python human_archive/scripts/validate_seonbi_persona.py --script human_archive/runs/ep01_pompeii_v2/source/script_seonbi_v2.json --report human_archive/runs/ep01_pompeii_v2/source/persona_report_v2.json
```

### 3단계: 샷 계약 컴파일 및 렌더링
```powershell
python human_archive/scripts/compile_shot_contract.py --shot-plan human_archive/runs/ep01_pompeii_rebuild_v2/source/shot_plan.yaml --script human_archive/runs/ep01_pompeii_v2/source/script_seonbi_v2.json --claims human_archive/runs/ep01_pompeii_v2/source/claim_inventory_v2.json --fact-report human_archive/runs/ep01_pompeii_v2/source/fact_check_report_v2.json --persona-report human_archive/runs/ep01_pompeii_v2/source/persona_report_v2.json --fact-approval human_archive/runs/ep01_pompeii_v2/source/approvals/fact_approval.json --shot-plan-approval human_archive/runs/ep01_pompeii_rebuild_v2/source/approvals/shot_plan_approval.json --output human_archive/runs/ep01_pompeii_v2/source/shot_contract.json
```

### 4단계: 실측 포스트플라이트 및 릴리스 승격
```powershell
python human_archive/scripts/postflight_release.py --input human_archive/runs/ep01_pompeii_v2/full-v2-001/candidate/HA001-full-v2-001.mp4 --contract human_archive/templates/documentary_contract.yaml --build human_archive/runs/ep01_pompeii_v2/full-v2-001 --report human_archive/runs/ep01_pompeii_v2/full-v2-001/release_report.json
python human_archive/scripts/release_episode.py --candidate human_archive/runs/ep01_pompeii_v2/full-v2-001/candidate/HA001-full-v2-001.mp4 --report human_archive/runs/ep01_pompeii_v2/full-v2-001/release_report.json --approval human_archive/runs/ep01_pompeii_v2/full-v2-001/approvals/release_approval.json --final human_archive/runs/ep01_pompeii_v2/full-v2-001/final/final_pompeii_ep01_v2.mp4
```

## 3. 데이터 보존 정책
- 생성된 대용량 미디어 파일(MP4, WAV, JPG)은 Git 저장소에 커밋하지 않습니다.
- 모든 스키마, 계약 YAML, Claim Ledger, 스냅샷 Manifest, QA 보고서 및 승인 JSON(작은 메타데이터)만 엄격하게 버전 관리합니다.
# 에피소드 제작 표준 — v5/v6 내레이션 정렬형

신규 에피소드의 정본 순서는 다음과 같습니다.

```text
승인 대본 → 실제 Supertonic3 문장 TTS → 실측 샷 타이밍
→ 구체 의미 브리프·Flow 요청 → 의미 재사용 계획·사람 승인·물질화
→ 콜드오픈 12 + 커버리지 8 파일럿
→ 전체 이미지 → OCR·중복·연속성·해시 QA → 최신 전체 사람 승인
→ 25 CFR 모션 → 문장 자막 → 렌더 → postflight
```

- 샷 수는 45개나 글자 수로 고정하지 않고 실제 음성의 9~12초 목표, 최대 15초 규칙으로 산정합니다.
- 쉽선비는 `host_explainer`에만 전체 8~12%, 최소 7샷 간격으로 사용합니다. Flow가 캐릭터를 새로 그리지 않고 사람이 없는 배경에 승인된 `doodle_seonbi_v1.png`를 합성합니다.
- 비호스트에는 발표자·검은 갓 마스코트·쉽선비를 넣지 않습니다.
- AI 이미지에는 글자·숫자·연도·캡션·간판·인장·워터마크·서비스 마크를 넣지 않습니다.
- 한글 semantic anchor, `narration-specific subject`, `depict directly`, 범용 궁중 행동은 Flow 실행 전 차단합니다. 구체 장면 규칙이 없는 내레이션은 fail-closed입니다.
- `image_request_manifest.contract_sha256`는 정확한 `flow_image_prompts.json` 파일 SHA-256입니다.
- 새 내레이션의 의미 브리프에는 `--provider antigravity-cli` 또는 `--provider json-file`을 명시합니다. Antigravity Agent가 생성과 검증을 오케스트레이션하며, provider를 생략한 fallback은 생산용으로 사용하지 않습니다.
- `image_reuse_plan.json`은 결정 계획일 뿐 이미지 파일이나 `asset_manifest.json`을 만들지 않습니다. `materialize_semantic_image_reuse.py`가 현재 source/target 계약 SHA와 사람 승인 SHA를 검증한 뒤 `images/reused/`와 활성 자산 행을 원자 생성합니다. dry-run과 실제 물질화가 끝나기 전에는 Flow 파일럿을 시작하지 않습니다.
- review candidate 승인 JSON은 자동화가 만들지 않습니다. 사람이 모든 후보를 `reuse` 또는 `generate_new`로 판단해야 하며, stale 승인·호스트 불일치·source 파일 SHA 불일치·같은 요청의 기존 자산 충돌은 모두 fail-closed입니다.
- stale 자산은 교체 생성 전에 `asset_history`와 `rejected_visual_variants/`로 보존합니다.
- `flow_batch_report` PASS는 다운로드 무결성일 뿐입니다. 자동 콘텐츠 PASS, 파일럿 승인, 최신 전체 연락시트 승인은 서로 다른 게이트입니다.
- 정책 거절과 OCR 실패를 같은 재시도 경로로 처리하지 않습니다. OCR은 일반 OCR-safe 1회, ultra-minimal 1회 뒤 직접 크롭 검토로 전환하며 실제 서비스 마크는 항상 재생성합니다.
- `tone_fixture` 음성은 테스트 전용입니다. 실제 TTS 뒤 타이밍·요청 해시가 바뀌면 영향 샷을 다시 생성하고 승인합니다.

Chrome CDP가 연결되지 않을 때는 사용자가 모든 Chrome 작업을 저장하고 창을 직접 닫은 뒤 별도 프로필을 사용합니다. `Stop-Process`는 관련 없는 Chrome 세션까지 종료하므로 현재 턴의 명시적 사용자 승인 없이 에이전트가 실행하면 안 됩니다.

```powershell
# 사용자 명시 승인 뒤에만 전체 Chrome 강제 종료
Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue
Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList '--remote-debugging-port=9222','--remote-allow-origins=*','--user-data-dir="C:\Users\shs\.chrome_debug_ep02"','https://labs.google/fx/tools/image-fx'
curl.exe http://127.0.0.1:9222/json/version
```

EP02 v6 재개 예시는 다음과 같습니다. 현재 사실 보고서가 `REVIEW_REQUIRED`라면 아래 의미 브리프 명령 전에 먼저 정지 게이트를 해소해야 합니다.

```powershell
$build = 'human_archive/runs/ep02_jang_huibin/full-v6-001'
$script = "$build/source/script_candidate.json"
$claims = "$build/source/claim_inventory_v2.json"
$sources = "$build/source/source_snapshot_manifest_v2.json"
$factReport = "$build/source/fact_check_report_v2.json"
$personaReport = "$build/source/persona_report_v2.json"
$factApproval = "$build/source/approvals/fact_review_approval_v1.json"

curl.exe http://127.0.0.1:3093/health
python human_archive/scripts/build_sentence_audio_master.py --script $script --build $build --audio-mode supertonic3 --tts-url http://127.0.0.1:3093
python human_archive/scripts/plan_narration_shots.py --script $script --audio "$build/sentence_audio_manifest.json" --claims $claims --profile narration_aligned_hybrid_v1 --output "$build/shot_timing_manifest.json"
# 현재 REVIEW_REQUIRED 문구를 사람이 명시 승인한 경우에만:
python human_archive/scripts/record_fact_review_approval.py --script $script --fact-report $factReport --persona-report $personaReport --claims $claims --sources $sources --output $factApproval --reviewer-id <human-reviewer-id> --approval-source explicit_user_confirmation_in_antigravity_thread
python human_archive/scripts/generate_visual_briefs.py --script $script --timing "$build/shot_timing_manifest.json" --claims $claims --sources $sources --fact-report $factReport --persona-report $personaReport --fact-approval $factApproval --provider antigravity-cli --response-output "$build/visual_brief_response_v1.json" --output "$build/visual_brief_manifest.json" --prompts "$build/flow_image_prompts.json"
python human_archive/scripts/build_image_request_manifest_v5.py --build $build
python human_archive/scripts/validate_image_requests.py --build $build
python human_archive/scripts/generate_flow_batch.py --build $build --pilot --model "Nano Banana 2" --cdp http://127.0.0.1:9222
# 이중 파일럿 명시 승인 후
python human_archive/scripts/generate_flow_batch.py --build $build --all --model "Nano Banana 2" --cdp http://127.0.0.1:9222
python human_archive/scripts/build_contact_sheet.py --build $build --output "$build/contact_sheet.jpg"
python human_archive/scripts/verify_visual_assets.py --build $build
# 최신 전체 연락시트 명시 승인 후 실제 승인자 ID로만 기록
python human_archive/scripts/record_visual_approval.py --build $build --reviewer-id <approved-reviewer-id>
python human_archive/scripts/build_motion_clips_v2.py --build $build
python human_archive/scripts/build_subtitles_v2.py --build $build
python human_archive/scripts/render_episode_v2.py --build $build --output "$build/candidate/HA002-full-v6-001.mp4"
python human_archive/scripts/postflight_release.py --input "$build/candidate/HA002-full-v6-001.mp4" --report "$build/release_report.json" --duration-mode full
```

`fact_check_report_v2.json`은 사람 승인 뒤에도 원본 `REVIEW_REQUIRED` 상태를 유지합니다. 승인 overlay가 현재 script/fact/persona/claims/sources SHA와 정확한 review-set을 검증해 effective gate를 PASS로 만듭니다. 이때 persona의 `overall_status`도 반드시 `PASS`여야 하며, review 항목 ID와 count는 강제 형변환 없이 원래 JSON 타입 그대로 검증합니다. recorder를 자동으로 실행하거나 report를 PASS로 편집하지 않습니다. 같은 입력에 대한 recorder 재실행은 무변경 검증이고, artifact가 바뀌면 새 사람 검토 없이는 기존 파일을 덮어쓰지 않습니다.

Antigravity CLI 및 Agent 환경에서는 대본 생성과 비주얼 브리프가 Google Antigravity 런타임 표준에 맞춰 수행됩니다.

정책 거절은 `rewrite_policy_rejected_prompt.py --build $build --scene-id <shot_id> --reason provider_policy_rejected`로 처리합니다. 첫 실행은 safe rephrase, 두 번째는 safe abstraction이며 세 번째 요청은 자동 재생성하지 않고 `REVIEW_REQUIRED`가 됩니다.

운영 상세와 장애 복구는 [`CLAUDE.md`](../CLAUDE.md), [`manual.md`](../manual.md), [EP02 v6 Luna 복구 정본](../docs/solutions/integration-issues/ep02-v6-reuse-first-tts-codex-visual-brief-recovery-2026-08-28.md), [Flow v5 파일럿 기록](../docs/operations/2026-08-27-flow-v5-pilot-state-recovery.md), [EP02 v5 자산 생명주기 해결 기록](../docs/solutions/integration-issues/ep02-v5-flow-visual-pipeline-contract-and-lifecycle-defects-2026-08-28.md)을 따릅니다.

### EP02 v6 현재 상태 (2026-08-28)

외부 Codex 전송 승인과 생성은 완료됐고, 검증된 2차 교정 응답이 정본입니다. 시각 브리프와 Flow 요청은 각각 112개이며 호스트 11개, 직접 묘사 68개(60.71%), `1701` 및 제출 prompt 한글은 0건입니다. 관련 집중 회귀 테스트는 104개가 통과했습니다.

재사용 계획은 자동 8개, 사람 검토 22개, 신규 82개입니다. 22개 재사용 승인과 총 30개 물질화가 완료됐고, 이중 파일럿은 20/20 다운로드 PASS입니다. OCR 차단된 006·013·070은 1차 OCR-safe로 보관·재생성해 콘텐츠 QA PASS를 확인했습니다. 현재 정지 게이트는 최신 두 파일럿 연락시트의 사람 승인입니다. 승인 전 전체 82개 생성을 실행하지 않습니다.

Windows Codex CLI에는 UTF-8 stdin을 명시하고, 10샷 반복 모티프 검사는 실제 생성 소품인 `prop_motifs`만 사용합니다. 원본 모델 응답은 감사용으로 보존하며 교정본은 `--provider json-file`로 전체 사실·시퀀스·prompt QA를 다시 통과해야 합니다.

Flow 프로젝트의 `최신 Flow 업데이트` dialog는 backdrop이 textbox를 가로막으므로 러너가 dialog의 사용자 표시 시작 버튼을 닫고 hidden 상태를 확인합니다. OCR 재시도 `--only` 이후에는 반드시 `--pilot`을 다시 실행해 정식 20/20 보고서를 복원합니다.
### Nollam File

구현 계약은 `docs/superpowers/specs/2026-09-01-nollam-file-trend-explainer-design.md`와 계획서에 있다. `nollam_file_v1`은 opt-in이며 기존 HA/쉽선비 DAG와 분리된다. 실행 전 필수 source capability, M2 warm lock, overlay manifest, 전용 postflight를 확인한다.
