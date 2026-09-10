# 놀람파일 참조 영상 분석 반영 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 인류의서재 참조 영상 KWL8_AnSp2g의 검증 가능한 서사·시각·패키징 패턴만 놀람파일에 흡수하고, 조회수나 과장된 숫자를 성공 공식으로 오인하지 않는 benchmark-aware 운영을 추가한다.

**Reference evidence:** 공개 메타데이터, 자동 한국어 자막, 썸네일, 21개 storyboard frame을 `human_archive/audits/nollam_reference_KWL8_AnSp2g/`에 보존했다. 확인 시점 관측치는 30:34, 111,440 views, 725 likes, 47 comments, 2026-08-31 upload다.

**Spec:** `D:\module\bible\docs\superpowers\specs\2026-09-01-nollam-file-trend-explainer-design.md`

## 적용할 패턴과 금지할 복제

- 적용: 구체적 이상징후 cold open, 기전 설명으로 curiosity loop 회수, 과거 사례를 현재 설명 변수로 연결, 개인·지역에서 세계적 파급으로 확장, 설명란 source stack.
- 최우선 적용: 문장별 semantic intent와 실제 audio timeline을 먼저 잠그고, 그 문장을 이해시키는 visual role·asset·overlay를 1:1로 결속한다.
- 금지: 참조 제목·문장·이미지 복사, `20억 명` 같은 무근거 scale claim, 단일 영상 조회수로 인과 결론, 긴 논문 서지 낭독, 타 채널 footage 재배포.
- Nollam v1 제약 유지: opt-in, 16:9 longform, DAILY/STABLE, M2 warm, manual release, 기존 HA002/legacy DAG 격리.

## 작업 단계

- [ ] **참조 감사 manifest를 고정한다.**
  - Files: `human_archive/audits/nollam_reference_KWL8_AnSp2g/metadata.json`, `KWL8_AnSp2g.ko.vtt`, `KWL8_AnSp2g.jpg`, `storyboard_contact_sheet.jpg`.
  - Add: fetch timestamp, URL/video ID, view/like/comment snapshot, duration, subtitle provenance, storyboard sampling interval, copyright-use=`analysis_only`.
  - Test: `human_archive/tests/test_reference_audit_manifest.py`에서 video ID·관측시각·analysis_only를 검증한다.

- [ ] **Nollam 서사 템플릿에 reference-derived beat를 추가한다.**
  - Files: `human_archive/templates/nollam_file_outline_prompt.j2`, `nollam_file_script_prompt.j2`, `human_archive/scripts/generate_trend_script.py`.
  - Interface: `build_nollam_beats(packet) -> [cold_open, mechanism, paradox, precedent, escalation, consequence]`.
  - Gates: 첫 30초에 사건·질문·보상, 각 숫자에 장소/원인/비교 기준, 마지막에 “그래서 왜 중요한가”.
  - Test: `human_archive/tests/test_reference_derived_beats.py`에서 beat 누락·숫자 scope 누락을 FAIL시킨다.

- [ ] **scale claim과 긴급성 표현을 별도 검증한다.**
  - Files: `human_archive/scripts/lib/trend_fact_gate.py`, `human_archive/schemas/trend_research_packet_v1.schema.json`, `trend_verified_script_v1.schema.json`.
  - Interface: `validate_scale_claim(claim) -> GateResult`; required `metric`, `population_scope`, `as_of_utc`, `calculation_method`, `source_ids`.
  - Rules: 제목·썸네일은 verified scope를 초과할 수 없고, 단일 소셜 신호·모호한 “수십억”은 차단한다.
  - Test: `test_scale_claim_gate.py`에 `20억` 무근거 FAIL, 공식 연구 산정 범위 PASS를 추가한다.

- [ ] **이미지 구성 계약을 beat와 결속한다.**
  - Files: `human_archive/scripts/lib/nollam_visual_gate.py`, `overlay_event_manifest_v1.schema.json`, 신규 `human_archive/scripts/compile_nollam_visual_plan.py`.
  - Interface: `compile_visual_plan(beats, claims) -> visual_plan_v1`.
  - Required visual roles: event scene, mechanism diagram/map, evidence number card, precedent timeline, human-scale consequence, global transfer map. AI base image는 no-glyph, 숫자·라벨은 overlay로만 합성한다.
  - Test: `test_reference_visual_roles.py`에서 각 beat에 role·claim/source ID가 있는지 검증한다.

- [ ] **sentence-visual alignment manifest를 핵심 산출물로 추가한다.**
  - Files: 신규 `human_archive/schemas/sentence_visual_alignment_v1.schema.json`, `human_archive/scripts/compile_sentence_visual_alignment.py`, `human_archive/scripts/lib/nollam_visual_gate.py`.
  - Interface: `compile_alignment(script, audio_timeline, visual_plan) -> sentence_visual_alignment_v1`.
  - Required row: `sentence_id`, `audio_start_ms`, `audio_end_ms`, `semantic_intent`, `claim_ids`, `visual_role`, `asset_id`, `why_this_visual`, `source_basis`, `transition_type`, `coverage_score`.
  - Mapping: FACT→evidence/event/map, CAUSAL→diagram/process, CONTEXT→timeline/comparison, REACTION→sampled aggregate, QUOTE→rights-cleared source card, QUESTION/BRIDGE→next-question transition.
  - Gates: semantic coverage ≥0.90, claim-visual mismatch 0, unsupported visual 0, consecutive same asset ≤2, numeric overlay source ID required. Audio timing is measured SuperTonic3 output, never estimated narration duration.
  - Test first: `human_archive/tests/test_sentence_visual_alignment.py`에서 decorative-only asset, 무관 이미지, timing mismatch, source-less number를 FAIL시키고 의미가 맞는 asset을 PASS시킨다.

- [ ] **이미지 생성 요청을 alignment에서 파생한다.**
  - Files: `human_archive/scripts/compile_nollam_visual_plan.py`, `human_archive/scripts/generate_visual_briefs.py` 연동 adapter, 신규 `human_archive/schemas/nollam_visual_request_v1.schema.json`.
  - Required prompt fields: `semantic_intent`, `visual_role`, `claim_ids`, `must_show`, `must_not_show`, `why_this_visual`, no-glyph policy. 기존 자산 자동 재사용은 false로 고정한다.
  - Verify: 생성 결과 asset hash와 request hash가 일치하고, 이미지가 문장 의미를 설명하지 못하면 재생성/FAIL한다.

- [ ] **evidence budget 기반 길이 선택을 추가한다.**
  - Files: `human_archive/scripts/lib/trend_selection.py`, `trend_topic_candidate_v1.schema.json`, `nollam_file_postflight.py`.
  - Implement: 후보 길이 8/15/30분을 내부 평가하되, v1 delivery는 `nollam_file_long`; 근거가 부족하면 긴 영상으로 늘리지 않고 REJECT/DEFER한다.
  - Test: `test_evidence_budget.py`에서 claim 수·독립 출처·visual roles에 따른 길이 상한을 검증한다.

- [ ] **패키징 A/B와 유지율 계측을 수동 파일럿에만 연결한다.**
  - Files: `human_archive/config/trend_publication_policy.yaml`, 신규 `human_archive/schemas/trend_benchmark_snapshot_v1.schema.json`, `human_archive/scripts/record_nollam_benchmark.py`.
  - Metrics: 15s/30s/60s/3m/50% retention, CTR, 평균 시청 지속시간, 댓글 이해 오류.
  - Guardrail: 참조 영상의 조회수는 benchmark snapshot일 뿐 목표치·인과 증거가 아니다. 자동 게시·자동 A/B 변경은 금지한다.
  - Test: `test_benchmark_snapshot.py`에서 관측시각·video ID·metric source가 없으면 FAIL.

- [ ] **private dry run 세 편에 reference pattern을 적용한다.**
  - Files: `human_archive/scripts/run_nollam_dry_run.py`, `human_archive/tests/e2e/test_nollam_private_dry_run.py`.
  - Inputs: IT/tech anomaly, entertainment release anomaly, sports direct_record anomaly.
  - Verify: 첫 30초 beat, source/claim gate, 신규 visual roles, M2 audio, overlay, postflight를 통과하고 외부 게시하지 않는다.

## 완료 조건

- 참조 영상의 공개 사실과 우리 해석이 audit manifest에서 분리된다.
- 새 script가 참조 영상의 문장·이미지·footage를 복사하지 않고 beat 패턴만 재사용한다.
- 무근거 큰 숫자와 제목 escalation은 모두 차단된다.
- 세 카테고리 private dry run이 release-ready까지 도달한다.
- 모든 factual sentence가 실제 오디오 구간과 의미상 설명 가능한 화면 asset으로 연결된다.
- 플랫폼 성과는 공개 파일럿 이후에만 기록하며, 조회수 1건으로 성공을 주장하지 않는다.
