# '인류의 서재' 역공학·복제 학습 파이프라인 코드베이스/워크플로우/스킬 심층 감사

- **감사일**: 2026-09-11
- **범위**: 외부 `implementation_plan.md`, 외부 `walkthrough.md`, 저장소 마스터 계획서, 실제 복제 계약 산출물, NOLLAM 실행기·샷/오디오/프롬프트/렌더/릴리스 모듈, 전역 미디어 스킬
- **판정**: **분석·계약 산출물은 부분 완료. 실제 복제 영상 제작과 학습 루프는 미착수. 원 계획서의 “1:1 완벽 복제” 및 “Phase 1~2 완료” 표현은 정정 필요.**
- **갱신 계획서**: [`2026-09-11-human-library-replication-and-learning-master-plan.md`](D:/module/bible/docs/superpowers/plans/2026-09-11-human-library-replication-and-learning-master-plan.md)

## 1. 감사 대상과 증거

### 1.1 외부 문서

| 대상 | 확인 결과 |
|---|---|
| `C:\Users\shs\.gemini\antigravity\brain\ca607435-c42c-414e-93bd-29c240db06c4\implementation_plan.md` | 존재하며 Top 3 역공학, 1위 영상 40샷·973초 제작 계획을 기술한다. “1:1 복제”와 사용자 승인 대기 문구가 남아 있다. |
| `C:\Users\shs\.gemini\antigravity\brain\ca607435-c42c-414e-93bd-29c240db06c4\walkthrough.md` | 존재하며 Phase 1~2 완료 및 계약 테스트 3건 통과를 보고한다. 그러나 실제 WAV·이미지·클립·MP4의 존재 증거는 제시하지 않는다. |
| `D:\module\audit\human_library_top3_reverse_engineering_audit\` | 3개 제안서, 상호 비판 매트릭스, 합의문 5개가 존재한다. 이는 분석 합의의 증거이지 렌더 결과의 증거는 아니다. |

### 1.2 저장소 실물

확인한 디렉터리:

`D:\module\bible\human_archive\runs\human_library_replica\rank1_race_adaptation\`

현재 파일은 아래 JSON 3종뿐이다.

| 파일 | 실제 크기 | SHA-256 | 역할 |
|---|---:|---|---|
| `script/master_script_clean.json` | 34,618 bytes | `acc8c4f44677bfb4e51a1616302206aa9e535382c5ff231e269de1286f16eddb` | 정제 대본 계약 초안 |
| `metadata/scenes_manifest.json` | 44,306 bytes | `9197a31dddc19d87c4dd6d479349632d839c2ad27011cd38a7d039f23170b70c` | 40개 장면 타임라인 초안 |
| `metadata/shot_composition_plan.json` | 34,862 bytes | `47da7a11e7cd34ea08c0af6dce644a0f1957a4aaecaad27dc3e3ea175b6ee635` | 40개 프롬프트/모션 초안 |

해당 디렉터리에는 현재 `*.wav`, `*.mp4`, `*.m4a`, `*.png`, `*.jpg`, `*.jpeg`, `*.webp`, `*.ass`, `*.srt`가 없다. 따라서 외부 walkthrough의 “Phase 1~2 에셋 구축 완료”는 **계획·메타데이터 에셋 완료**로 범위를 줄여 기록해야 한다.

## 2. 수치·타임라인 교차 검증

### 2.1 자막 큐와 논리 문장의 구분

- 원본 분석 문서의 `406개`는 원시 VTT/ASR 큐 수로 기술되어 있다.
- 실제 `master_script_clean.json`은 `total_sentences=135`이며, 각 항목에 `sentence_id`, `start`, `end`, `duration`, `text`만 있다.
- 파일 헤더 수치는 `total_chars_no_space=4937`, `true_cps=5.079`, `total_duration_sec=972.11`이다.
- 따라서 `406개 문장`이라는 표현은 잘못이며, 앞으로는 **406 raw cues → 135 logical narration sentences**라고 표기해야 한다.
- 원시 자막 롤업 중복 제거 자체는 유효한 분석 가설이지만, 원본 VTT·단어 타임스탬프·정제 알고리즘의 해시와 재현 명령을 별도 provenance로 묶지 않으면 “정확히 2배”를 릴리스 불변식으로 사용할 수 없다.

### 2.2 실제 장면 분포

`scenes_manifest.json`의 `scenes`를 합산한 결과:

| 구간 | 개수 | 실제 합계 | 실제 평균 | 실제 범위 |
|---|---:|---:|---:|---|
| Opening | 3 | 11.00s | 3.667s | 3.0 / 3.5 / 4.5s |
| Tier 1 | 7 | 34.00s | 4.857s | 4.8~5.0s |
| Tier 2 | 12 | 215.00s | 17.917s | 17~18s |
| Tier 3 | 18 | 712.11s | 39.562s | 36.11~42s |
| **합계** | **40** | **972.11s** | — | — |

계획서의 `Tier 1 97초 / Tier 2 195초 / Tier 3 681초`는 현재 실물 매니페스트와 일치하지 않는다. 40개 샷 자체와 3/7/12/18 개수는 일치하지만, 타임라인 설명은 위 실측값으로 교체해야 한다. 자체 `start/end` 필드 기준으로 인접 장면의 gap/overlap은 발견되지 않았다.

### 2.3 대본·장면의 의미적 정합성

현재 장면 3개 Opening은 같은 `narration_text`를 반복해 넣고, 실제 문장-장면 span 또는 `sentence_ids`를 기록하지 않는다. 즉 장면이 “어떤 문장을 책임지는지”를 자동으로 역검증할 수 없다. 이는 자막·TTS·영상 컷이 서로 다른 텍스트를 사용할 수 있는 구조적 위험이다.

## 3. 코드베이스 대조 결과

### 3.1 현재 계약 산출물과 기존 파이프라인의 스키마가 다르다 — P0

복제 초안과 기존 모듈은 다음처럼 서로 다른 필드명을 사용한다.

| 의미 | 복제 초안 | 기존 canonical 경로 |
|---|---|---|
| 장면 ID | `id` | `shot_id` |
| 장면 길이 | `dur` | `duration_sec` 또는 `scene_duration` |
| 시작/끝 | `start`, `end` | `start_sec`, `end_sec` 또는 `scene_start`, `scene_end` |
| 내레이션 | `text`, `narration_text` | `tts_text`, `display_text`, `narration` |
| 문장 연결 | 없음 | `sentence_ids` / `sentence_spans` |
| 시각 앵커 | `prompt` 문자열 | `visual.subject/place/era/action` |
| 모션 | `motion`, `motion_type` | planner의 `effect_id`, `axis`, `phases`, renderer의 canonical motion |

영향받는 코드:

- `human_archive/scripts/plan_narration_shots.py`는 오디오 매니페스트를 요구하고 문장에 `order`가 있어야 한다. 현재 복제 대본에는 `order`가 없다.
- `human_archive/scripts/compile_shot_contract.py`는 `sentence_ids`, `display_text`, `tts_text`, approval/fact inventory를 전제로 한다. 현재 복제 초안으로는 빈 텍스트 또는 빈 샷 계약이 만들어질 수 있다.
- `human_archive/scripts/validate_shot_contract.py`는 `visual.subject/place/era/action`을 요구한다. 현재 `shot_composition_plan.json`에는 해당 구조가 없다.
- `human_archive/scripts/run_neanderthal_full_pipeline.py`는 `EP_DIR`가 네안데르탈인 런으로 고정되어 있어 human-library 디렉터리를 입력으로 받지 않는다.

**개선 방향**: 필드명 별칭을 여러 모듈에 흩뿌리지 말고, `human_library_replica_contract_v1`을 canonical schema로 정하고 `normalize_replica_bundle.py` 한 곳에서만 변환한다. 변환 결과에는 원본 파일 SHA, 문장 span, 시각 앵커, 모션 프로파일, 오디오/이미지/클립 경로를 모두 포함한다.

### 3.2 테스트가 “파일 형식”만 확인하고 제작 가능성을 확인하지 않는다 — P0

`human_archive/tests/test_human_library_replica_contracts.py`는 3개 테스트가 통과하지만 다음을 검증하지 않는다.

- `scenes_manifest`의 `id` 유일성: 테스트는 `shot_id`를 세지 않아 `[None]` 중복을 놓친다.
- 장면의 시작/끝 연속성, duration 합계와 마지막 end의 일치.
- 135개 문장이 적어도 한 장면에 한 번씩 연결되는지, 중복/누락되는지.
- 장면 텍스트와 대본 해시의 일치.
- 실제 WAV/이미지/클립/ASS/MP4 파일이 존재하고 0바이트가 아닌지.
- 프롬프트와 실제 다운로드한 이미지의 prompt hash가 일치하는지.
- 계획된 `motion_type`이 renderer의 실제 canonical motion으로 실행됐는지.
- 첫 프레임 가시성, freeze, 오디오-비디오 parity, 자막 범위.

현재 테스트는 절대 경로 `D:\module\bible\...`를 하드코딩하므로 다른 checkout/CI에서 재사용되지 않는다. `pytest` fixture와 `REPLICA_ROOT` 환경변수 또는 저장소 기준 상대 경로로 바꿔야 한다.

### 3.3 모션 플래너·렌더러에는 좋은 기반이 있지만 human-library 계약으로 연결되지 않았다 — P1

현재 `cinematic_effect_planner.py`에는 visible-first opening, beat-aware family/axis, biphasic/tri-phasic 변환, fail-closed `resolve_render_motion`이 있다. `run_neanderthal_full_pipeline.py`의 현재 렌더 경로도 이 resolver를 사용한다.

그러나 다음 문제가 남아 있다.

- `cinematic_editing_director.py`의 모듈 docstring, `calculate_variable_shot_budget`, `split_script_by_variable_pacing`, `plan_variable_pacing_effects` 설명에는 첫 장면 Bare-Tip이 여전히 헌법처럼 적혀 있다. 실제 visible-first 코드와 문서가 충돌한다.
- human-library 초안의 `motion_type`을 planner profile로 변환하는 adapter가 없다. 따라서 `tri_phasic`, `biphasic_ken_burns`가 실제 phase별 trajectory로 렌더됐다는 증거가 남지 않는다.
- Tier 1의 빠른 전환이 단순한 짧은 클립 반복으로 끝날 수 있다. 컷별 focal anchor, reframe, transition, frame-difference를 기록해야 한다.
- Tier 3의 긴 샷은 한 장의 이미지에 단순 zoom만 적용하면 지루함이 커진다. 35% ambient drift → 35% approach/reframe → 30% focal lock의 phase와 최소 변화량을 물리적으로 측정해야 한다.

### 3.4 프롬프트·에셋 계약의 fail-closed 범위가 부족하다 — P1

`asset_contract.py`는 `FLOW_IMAGE`, `BARETIP_VIDEO`, `HYPERFRAMES_VIDEO`와 Opening의 Bare-Tip 금지를 제공한다. 그러나 `aligned_prompt_compiler.py`는 `visual_mode`에 `bare_tip` 문자열이 들어가기만 하면 `BARETIP_VIDEO`로 분류한다. `order`, `scene_role`, `asset_id`, `source_kind`를 동시에 확인하는 정책이 필요하다.

Google Flow 스킬의 1-shot-1-completion·기존 카드 오염 방지·이미지 모드 고정·유료 비디오 전환 차단 규칙은 유효하다. 다만 복제 계획에는 “실제 생성 요청 ID, 카드 URL, 다운로드 파일 SHA, 실패/재시도 횟수, 모델/프롬프트 버전”을 매니페스트에 남기는 항목이 없었다.

### 3.5 릴리스 postflight가 복제 번들을 직접 감사하지 않는다 — P1

`postflight_release.py`는 릴리스 영상의 geometry, 25fps, BT.709, loudness, subtitle 범위, manifest video SHA, mirror SHA, first-frame visibility 등을 확인하는 좋은 기반이 있다. 하지만 human-library 계획에 필요한 다음 바인딩은 별도 구현이 필요하다.

- replica contract SHA → shot plan SHA → asset request SHA → downloaded asset SHA → clip SHA → final MP4 SHA 체인.
- 장면별 expected start/end와 실제 concat segment의 start/end.
- 계획 모션과 decoded frame motion의 대응.
- 3-cut opening의 실제 컷 경계와 첫 0.5초 시각 밀도.
- TTS 원본과 padded/master WAV의 sample rate, channel, sample count, roomtone 구간.
- `release_manifest_v5.json`의 “true” boolean을 재계산된 측정치로 대체.

## 4. 워크플로우·스킬 대조

### 4.1 잘 맞는 규칙

- `cinematic-hybrid-editing-director`: 첫 장면 visible-first 3-cut, 하단 18% 보호, beat-aware motion, anti-monotony 방향이 현재 요구와 맞다.
- `google-flow-media-generation`: 한 프로젝트/한 샷/한 완료, 기존 카드 차집합, 유료·다른 미디어 타입으로의 조용한 전환 금지 원칙이 재현성에 적합하다.
- `flow-batch-orchestrator`: 순차 생성, adaptive cooldown, 실패 복구, watermark/error-card 방지 규칙이 유효하다.
- `tri-model-creative-engine`: 독립 제안서, 상호 비판, 디스크 감사 체인을 남기도록 한다.
- `hyperframes`: 비디오·애니메이션 작업의 필수 진입점이다. 현재 FFmpeg/PIL canonical renderer와 역할을 구분해, 프리뷰/검증은 HyperFrames 경로를 따르고 최종 배치는 canonical renderer를 사용하거나 한 경로로 단일화해야 한다.

### 4.2 보완해야 할 규칙

1. “복제”를 원문·원본 이미지·원본 편집의 1:1 복사로 정의하면 저작권·콘텐츠 독창성·채널 혼동 위험이 생긴다. **학습 대상은 훅의 기능, 정보 밀도, 컷 길이 분포, 감정 곡선, 시각적 역할 배분 같은 추상적 제작 메커니즘으로 제한**하고, 공개 배포 대본·이미지·음성은 독자적으로 생성한다.
2. 삼사 점수 `99.92`는 모델 합의 점수이지 YouTube 유지율의 인과 증거나 학술 사실의 최종 검증이 아니다. 각 주장에 1차 문헌/신뢰 가능한 출처와 confidence를 붙이고, 불확실한 서사는 자동으로 보수적 문구를 선택해야 한다.
3. 현재 계획은 “973초로 맞추기”가 먼저다. 런타임은 음성·문장 span에서 계산하며, 972.11초 같은 실측값을 우선한다. 빈 구간을 만들어 목표값을 맞추지 않는다.
4. 조회수는 선택·관찰 지표일 뿐 품질의 원인 변수로 사용하지 않는다. 재생성 학습은 사람 평가, 시청 지속 proxy, 자막 가독성, 음성 자연스러움, 모션 정지율을 별도 측정한다.
5. Flow/TTS는 외부 상태와 비용이 발생할 수 있으므로 자동 재시도 횟수·비용 상한·중단 조건을 매니페스트에 남긴다. 사용자가 계속 진행을 요청했더라도 유료 action을 조용히 승인하는 규칙으로 해석하지 않는다.

## 5. 우선순위 결함 목록

| ID | 등급 | 결함 | 조치 |
|---|---|---|---|
| HL-001 | P0 | 원시 큐 406과 논리 문장 135 혼용 | 용어·계산·계약을 분리하고 source extraction report 추가 |
| HL-002 | P0 | human-library JSON과 canonical shot/audio 계약 불일치 | 단일 normalize adapter와 schema validation 추가 |
| HL-003 | P0 | 40개 계약 테스트가 실제 렌더 산출물을 검증하지 않음 | asset/clip/audio/render/postflight tier 테스트 추가 |
| HL-004 | P0 | scene `id` 중복 검증 누락 | `shot_id` canonicalization과 uniqueness/continuity gate 추가 |
| HL-005 | P1 | 실제 WAV·이미지·클립·영상 미생성 | Phase 4~8을 미완료로 유지하고 실물 gate 후 승격 |
| HL-006 | P1 | director 문서의 Bare-Tip opening 잔재 | visible-first 정책으로 docstring/skill/test 정합화 |
| HL-007 | P1 | prompt/asset/download/render provenance 체인 부재 | request/asset/clip/final SHA chain 추가 |
| HL-008 | P1 | fact source와 모델 합의 점수의 과신 | claim inventory, source URL/DOI, confidence, review status 추가 |
| HL-009 | P1 | 973초 고정 목표가 실제 오디오보다 우선 | audio-derived duration과 허용 범위 정책으로 교체 |
| HL-010 | P2 | 절대 경로 테스트와 하위 디렉터리 실행 취약성 | repo-relative fixture, root test command, discovery policy 추가 |

## 6. 결론

현재 결과는 **Top 3 분석 증거 + 1위 대상의 대본/장면/프롬프트 계약 초안**까지는 유효하다. 그러나 실제 제작 파이프라인이 이 계약을 소비하지 않고, 물리 미디어도 없으므로 “같은 생성 작업을 완료했고 학습했다”고 보고할 수 없다.

갱신 마스터 계획은 다음을 순서대로 강제한다.

1. 분석 수치·원본 provenance·독창성 경계를 잠근다.
2. 135개 논리 문장을 canonical schema로 변환한다.
3. 대본 기반으로 3/7/12/18 분포를 재계산하고, 필요하면 40개를 바꿀 수 있게 한다.
4. TTS → Flow → motion renderer → subtitle/mux를 실제 파일로 연결한다.
5. 계획값이 아닌 decoded media와 SHA 체인으로 검증한다.
6. 승인된 재생성 샘플만 다음 prompt/motion/pacing 학습에 사용한다.

이 감사에서 직접 수정한 소스 코드는 없다. 다음 구현은 갱신 계획서의 Gate 0~9를 순서대로 실행해야 한다.
