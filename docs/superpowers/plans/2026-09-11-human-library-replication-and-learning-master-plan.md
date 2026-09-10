# '인류의 서재' 역공학 기반 오리지널 재생성·학습 마스터 실행 계획서

- **문서 버전**: 2.0 (2026-09-11 Round 2 검증 갱신판)
- **목표**: '인류의 서재' Top 3 영상에서 추상적인 제작 메커니즘을 계측하고, 1위 영상의 주제와 핵심 사실을 바탕으로 **원문·원본 에셋을 복사하지 않는 오리지널 다큐멘터리**를 NOLLAM으로 반복 재생성하여 품질 개선 루프를 구축한다.
- **계획 상태**: 분석·계약 초안은 존재한다. TTS, Flow 이미지, 영상 클립, 최종 MP4, 학습 실험은 미완료다.
- **대상 분석 증거**: `D:\module\audit\human_library_top3_reverse_engineering_audit\`
- **외부 입력**: `C:\Users\shs\.gemini\antigravity\brain\ca607435-c42c-414e-93bd-29c240db06c4\implementation_plan.md`, `walkthrough.md`
- **관련 감사**: [`2026-09-11-human-library-replication-codebase-workflow-skill-audit.md`](D:/module/bible/docs/superpowers/reviews/2026-09-11-human-library-replication-codebase-workflow-skill-audit.md)

## 0. 먼저 고정하는 사실과 용어

### 0.1 검증된 현재 기준선

| 항목 | 현재 실측값 | 계획에서의 사용법 |
|---|---:|---|
| 원시 VTT/ASR 큐 | 406개 | `raw_cue_count`로만 기록. 문장 수로 부르지 않는다. |
| 롤업 중복 제거 후 논리 문장 | 135개 | `logical_sentence_count` 및 TTS 입력 단위 |
| 순수 글자 수 | 4,937자 | 대본 통계. 원본/정제 알고리즘 해시와 함께 보존 |
| 정제 대본의 CPS | 5.079 | 오디오 계획의 참고값. 실제 TTS 측정치가 최종 권위 |
| 장면 매니페스트 런타임 | 972.11s | 오디오·자막·영상의 실측 기준값 |
| 장면 수 | 40개 | 고정 불변식이 아니라 초기 실험 가설 |
| 장면 분포 | Opening 3 / Tier 1 7 / Tier 2 12 / Tier 3 18 | 현재 계약 초안의 기준. 대본·오디오 결과에 따라 변경 가능 |

현재 물리적으로 존재하는 것은 다음 JSON 3종뿐이다.

- `D:\module\bible\human_archive\runs\human_library_replica\rank1_race_adaptation\script\master_script_clean.json`
- `D:\module\bible\human_archive\runs\human_library_replica\rank1_race_adaptation\metadata\scenes_manifest.json`
- `D:\module\bible\human_archive\runs\human_library_replica\rank1_race_adaptation\metadata\shot_composition_plan.json`

WAV, 이미지, 클립, ASS, 마스터 MP4가 없으므로 Phase 4 이후를 완료로 표시하지 않는다.

### 0.2 독창성·출처 경계

- 허용 범위: 훅의 기능, 질문-대비-증거-역설 구조, 컷 길이 분포, 정보 밀도, 색·렌즈의 일반적 미학, 모션 패밀리, 자막 안전영역 등 **추상적 제작 규칙의 계측과 학습**.
- 금지 범위: 원본 영상의 대본·문장·자막·음성·이미지·썸네일·편집 타임라인을 그대로 재현하거나 시청자가 공식 영상으로 오인할 정도의 1:1 복제.
- 모든 공개용 대본은 동일한 사실을 사용하더라도 새 문장으로 작성하고, 사실마다 출처·확신도·검토 상태를 보존한다.
- `video_id`는 분석 출처 식별자이지 복제 콘텐츠의 원본 바인딩으로 사용하지 않는다. `source_reference`와 `original_content_hash`를 분리한다.

## 1. 목표 아키텍처

```text
source VTT/API evidence
  -> raw-cue de-rollup report + source hashes
  -> original fact inventory + original Korean script
  -> human_library_replica_contract_v1 (canonical adapter)
  -> audio-derived pacing planner
  -> 48kHz stereo narration + roomtone/BGM mix
  -> Flow image requests (one shot, one card, one completion)
  -> visible-first opening + beat-aware motion renderer
  -> ASS subtitles + canonical mux
  -> physical postflight + release manifest + artifact SHA chain
  -> approved sample feature vector + experiment report
```

### 1.1 코드 연결 지점

| 단계 | 기존 코드/스킬 | 필요한 연결 |
|---|---|---|
| 대본·샷 | `human_archive/scripts/plan_narration_shots.py`, `lib/shot_timing.py` | 135문장 schema adapter와 audio manifest 입력 추가 |
| 계약 | `compile_shot_contract.py`, `validate_shot_contract.py`, `schemas/shot_contract.schema.json` | human-library canonical schema와 `sentence_spans` 지원 |
| 오디오 | `lib/tts_provider.py`, `assemble_scene_audio_master.py`, `verify_audio_timeline_qa.py` | 실제 TTS만 허용, 샷별 WAV·sample count·roomtone provenance 기록 |
| 프롬프트·Flow | `lib/aligned_prompt_compiler.py`, `lib/asset_contract.py`, Flow routes, Flow skills | `asset_id`, request hash, download hash, scene role, 비용/재시도 기록 |
| 모션 | `lib/cinematic_effect_planner.py`, `lib/cinematic_editing_director.py`, `smooth_subpixel_motion_engine.py` | `RenderMotionProfile`와 human-library `motion_type`의 단일 adapter |
| 렌더·mux | `run_neanderthal_full_pipeline.py`의 공통 로직, `CinematicEditingDirector` | 고정 Neanderthal `EP_DIR`에서 episode input/output 분리 |
| QA·릴리스 | `postflight_release.py`, `lib/media_probe.py` | 계획값이 아닌 decoded frame/audio와 모든 SHA를 재계산 |
| 스킬 | `cinematic-hybrid-editing-director`, `google-flow-media-generation`, `flow-batch-orchestrator`, `tri-model-creative-engine`, `hyperframes` | visible-first·원샷 생성·증거 중심 합의·미디어 QA 순서 정합화 |

## 2. 페이싱·대본·구조 설계

### 2.1 5막 구조를 “분석 가설”로 사용

1. **Act 1 / 0~약 75초**: 상식 전복 → 양극단 수치 → 생존 질문 → 결론의 역설 씨앗.
2. **Act 2 / 약 75~270초**: 이동·지리·환경 압력과 선택의 규칙.
3. **Act 3 / 약 270~585초**: 신체·고산·식생활 적응 사례를 비교 증거로 전개.
4. **Act 4 / 약 585~825초**: 감염병·유전자·생존의 역설을 절정으로 끌어올림.
5. **Act 5 / 약 825~972.11초**: 0.1% 차이와 공통 조상으로 감정적 여운을 만든다.

막의 시간은 정답이 아니라 대본의 claim density와 음성 beat에 따라 ±20% 조정한다. 시간을 맞추기 위한 무음 패딩이나 반복 문장을 허용하지 않는다.

### 2.2 빠른 도입부에서 느린 후반부로의 실행 규칙

초안 매니페스트의 현재 실측 분포는 다음과 같다.

| 구간 | 목표 역할 | 초안 실측 |
|---|---|---:|
| Opening | 3-cut visible-first: context → subject → evidence | 0~11.00s, 3.0/3.5/4.5s |
| Tier 1 | 훅 후속 대비·수치·짧은 punchline | 11~45s, 7개, 평균 4.857s |
| Tier 2 | 원인·사례 설명, biphasic reframe | 45~260s, 12개, 평균 17.917s |
| Tier 3 | 증거 추적·반전·철학적 여운, tri-phasic 내부 변화 | 260~972.11s, 18개, 평균 39.562s |

각 샷에는 `beat_type`, `claim_ids`, `sentence_spans`, `focal_anchor`, `transition_out`, `motion_profile`을 반드시 기록한다. 30초 이상 샷은 최소 3 phase의 변화량을 가져야 하며, 단순 고정 프레임을 Ken Burns라고 부르지 않는다.

### 2.3 오프닝 정책

- 첫 화면은 빈 화면·Bare-Tip·화이트보드 선화가 아니다.
- `SHOT_001`을 3개의 독립 asset으로 저장하고, 첫 프레임부터 실제 피사체의 edge/coverage를 물리 측정한다.
- `BARETIP_VIDEO`는 `scene_role != opening_group`이고 `order > 1`이며 설명용 인서트일 때만 선택 가능하다.
- `FLOW_IMAGE`와 `HYPERFRAMES_VIDEO`는 모두 `asset_contract.py`를 통과해야 한다.

## 3. 실행 단계와 체크리스트

### Phase 0 — 증거 잠금·실행 환경·provenance

- [ ] 외부 두 문서와 audit 5개 파일의 실제 경로·크기·SHA-256을 `source_evidence_manifest.json`에 기록한다.
- [ ] 원시 큐 406, 논리 문장 135, 4,937자, 972.11초를 별도 필드로 정규화한다.
- [ ] `source_reference`, `source_snapshot_sha256`, `original_script_sha256`, `plan_sha256` 필드를 분리한다.
- [ ] 공개 배포는 오리지널 문장·신규 이미지·신규 음성만 허용한다는 정책 파일을 저장한다.
- [ ] Flow/TTS 외부 서비스의 포트·계정·비용·재시도 제한을 preflight에 등록한다.

**Gate 0 — Evidence/Originality Gate**

- 입력 증거 5개와 외부 문서의 hash 목록이 존재한다.
- 406/135 용어가 보고서·계획·테스트에서 혼용되지 않는다.
- 원문 복사본이 공개 산출물 입력으로 연결되지 않고, original script provenance가 존재한다.
- 실패 시 후속 생성·외부 호출을 시작하지 않는다.

### Phase 1 — 대본 디컨볼루션·팩트 인벤토리·원문 대체

- [ ] VTT 롤업 제거기를 deterministic 함수로 고정하고 입력/출력 큐 수와 텍스트 hash를 저장한다.
- [ ] 135개 논리 문장에 `sentence_id`, `order`, `start_sec`, `end_sec`, `tts_text`, `display_text`, `claim_ids`를 부여한다.
- [ ] 공개용 오리지널 대본을 같은 사실·새 문장으로 작성한다. 현재 `text`를 그대로 TTS에 보내지 않는다.
- [ ] CCR5-Δ32, EPAS1, LCT, ALDH2 등 각 과학 주장에 출처 URL/DOI, 사실 상태, uncertainty, reviewer를 기록한다.
- [ ] 긴 문장을 `split_sentence_by_semantic_clause` 규칙으로 분리하되 문법 단위·의미 단위를 보존한다.

**Gate 1 — Script/Fact Gate**

- 문장 ID가 유일하고 order가 연속이다.
- 모든 문장이 하나 이상의 shot span에 정확히 한 번 연결되며, 누락·중복·겹침이 보고되지 않는다.
- display/TTS 텍스트가 빈 값이 아니고, 자막과 TTS용 정규화 규칙이 다르면 hash가 각각 남는다.
- 고위험 과학 주장에 출처와 confidence가 없다면 Fail-Closed다.

### Phase 2 — canonical human-library 계약 adapter

- [ ] `human_library_replica_contract_v1` schema를 추가한다.
- [ ] `id/dur/start/end`를 `shot_id/duration_sec/start_sec/end_sec`로 변환하는 로직을 단일 `normalize_replica_bundle.py`에 둔다.
- [ ] `narration_text`를 장면에 복사하지 말고 `sentence_spans`로 원본 문장과 연결한다.
- [ ] prompt를 `visual.subject/place/era/action`, `look_type`, `negative_prompt`, `safe_zone`으로 구조화한다.
- [ ] 기존 `compile_shot_contract.py`·`validate_shot_contract.py`가 normalized bundle을 소비하도록 adapter 입력 테스트를 추가한다.
- [ ] 절대 경로 테스트를 제거하고 repo-relative fixture 또는 `REPLICA_ROOT`를 사용한다.

**Gate 2 — Contract/Schema Gate**

- schema validation, hash validation, ID uniqueness, sentence coverage, time continuity가 모두 통과한다.
- canonical bundle에서 40개는 권장값일 뿐이며, 실제 오디오 기반 결과가 바뀌면 plan revision으로 기록된다.
- 기존 NOLLAM Neanderthal 고정 경로를 오염시키지 않고 human-library run directory를 명시적으로 선택한다.

### Phase 3 — 오디오 기반 동적 씬 분할

- [ ] `plan_narration_shots.py`에 normalized script와 sentence-audio manifest를 입력한다.
- [ ] 장면 경계는 문장 중간이 아니라 semantic clause·beat·claim boundary 중 안전한 지점에서만 결정한다.
- [ ] 0~45초 rapid, 45~260초 context, 이후 deep 구간을 시간 비율이 아니라 대본/오디오의 실제 누적 시간으로 계산한다.
- [ ] 3/7/12/18 분포를 baseline으로 기록하되, hard-coded 40-shot forcing을 금지한다.
- [ ] 각 샷의 duration budget, sentence span, claim density, beat, transition, motion profile을 하나의 manifest에 저장한다.

**Gate 3 — Pacing Gate**

- 첫 11초가 3-cut이고 첫 프레임이 visible-first다.
- 실제 대본 span이 장면 경계와 일치하고, gap/overlap이 0.01초 허용치 안이다.
- Tier 1 평균 컷 길이가 Tier 2보다 짧고, Tier 2가 Tier 3보다 짧다.
- 연속 3개 이상의 동일 look/motion family가 없고 10-shot window의 family 다양성 기준을 만족한다.

### Phase 4 — SuperTonic3 M2 오디오 제작

- [ ] sentence-level TTS를 실제 SuperTonic3 서비스에서 생성한다. 서비스가 없으면 dummy tone으로 승격하지 않고 중단한다.
- [ ] 각 WAV의 sample rate 48kHz, channel stereo, sample count, duration, text hash를 기록한다.
- [ ] 문장·샷 사이 roomtone 0.35~0.50초를 실제 sample 단위로 합성하고, 임의의 전역 0.38초 padding을 권위값으로 고정하지 않는다.
- [ ] BGM은 내레이션 구간 ducking과 sidechain gain curve를 저장한다. 목표 loudness는 실제 `media_probe` 결과로 확인한다.
- [ ] master audio의 총 길이를 장면 manifest와 역바인딩한다.

**Gate 4 — Audio Gate**

- 모든 샷 WAV가 존재하고 0바이트가 아니며 문장 hash와 일치한다.
- master audio가 48kHz stereo이고, 샘플 기반 합계와 ffprobe duration 차이가 0.04초 이하이다.
- roomtone gap, clipping, true peak, integrated loudness가 프로파일 범위 안이다.
- 오디오 없이 다음 Flow/렌더 단계로 넘어가지 않는다.

### Phase 5 — Google Flow 오리지널 이미지 생성

- [ ] 40개는 초기 요청 수일 뿐이며 실제 normalized shot 수와 동일하게 생성한다.
- [ ] 한 프로젝트, 한 shot, 한 카드, 한 completion을 유지한다.
- [ ] 첫 장면은 `context_wide → subject_action → evidence_detail` 3개 visible-first 이미지로 생성한다.
- [ ] 영문 prompt는 35mm documentary look, 피사체·시대·장소·행동, negative prompt, 하단 18% 자막 보호를 구조화한다.
- [ ] `request_id`, prompt hash, card URL, download time, file SHA, dimensions, failure/retry, spend/credit indicator를 저장한다.
- [ ] Flow가 video generation, 유료 action, 다른 미디어 타입으로 전환하면 중단 상태로 기록한다.

**Gate 5 — Asset Gate**

- 모든 승인 이미지가 실제 파일이고 0바이트가 아니며 1920x1080 또는 명시된 변환 이력을 가진다.
- opening 이미지에는 `BARETIP_VIDEO`가 없고, 첫 프레임 visibility가 decoded frame으로 통과한다.
- prompt hash와 asset manifest hash가 일치한다.
- error card, watermark, text/logo, stale card 혼입이 없다.

### Phase 6 — 모션 프로파일·클립 렌더링

- [ ] `motion_type`을 문자열 if/else로 분산하지 않고 `resolve_render_motion` 단일 adapter에 통과시킨다.
- [ ] planner profile의 family, axis, focal anchor, phases, transition을 clip sidecar에 기록한다.
- [ ] Tier 1은 3~5초 visible reframe/cut grammar로 설계한다. 짧은 시간에 같은 이미지가 정지하지 않도록 컷·축·focal anchor를 바꾼다.
- [ ] Tier 2는 2단계 biphasic Ken Burns와 설명 beat의 전환을 결합한다.
- [ ] Tier 3는 35% ambient drift → 35% approach/reframe → 30% focal lock의 tri-phasic motion을 구현한다.
- [ ] 모든 클립을 1920x1080, 25fps CFR, no-audio canonical intermediate로 렌더한다.
- [ ] `cinematic_editing_director.py`의 Bare-Tip opening docstring/legacy 설명을 visible-first 정책과 일치시킨다.

**Gate 6 — Render/Motion Gate**

- 모든 planned motion이 실제 renderer motion과 1:1로 sidecar에 기록된다.
- Tier별 decoded frame difference와 freeze 검사가 통과한다.
- 30초 이상 클립에 3 phase 경계와 변화량이 존재한다.
- 연속 동일 motion/axis 위반, subtitle safe-area 침범, 첫 장면 Bare-Tip이 하나라도 있으면 Fail-Closed다.

### Phase 7 — 자막·mux·스트림 parity

- [ ] normalized display text로 52pt Pretendard ASS를 생성하고 한 줄 36자·최대 2줄·하단 safe zone을 검증한다.
- [ ] 영상 concat 전에 video-only duration과 master audio duration을 측정한다.
- [ ] `-shortest`를 사용하지 않고, `|T_video - T_audio| <= 0.040s` pre-mux와 `<=0.050s` final stream parity를 확인한다.
- [ ] FFmpeg 명령, codec, color tags, audio bitrate, subtitle file SHA를 sidecar에 저장한다.
- [ ] final output과 deployment mirror를 byte/SHA 단위로 비교한다.

**Gate 7 — Mux/Parity Gate**

- decoded video/audio stream, subtitle last cue, expected timeline의 끝점이 모두 허용 범위다.
- video SHA, audio SHA, contract SHA, shot/asset/clip SHA가 release manifest에 바인딩된다.
- 하나라도 측정 불가하면 boolean을 임의로 `true`로 기록하지 않는다.

### Phase 8 — 물리 postflight·승격

- [ ] `postflight_release.py`에 human-library contract validator를 연결한다.
- [ ] first frame edge density/coverage/focal bbox를 실제 decoded frame으로 계산한다.
- [ ] 25-frame sliding MAE로 freeze를 검사하되, opening cut boundaries와 Tier 3 phase boundaries도 별도 측정한다.
- [ ] duration, dimensions, CFR, BT.709, loudness, subtitle range, mirror SHA를 재계산한다.
- [ ] `release_manifest_human_library_v1.json`과 사람이 읽는 `release_report.md`를 생성한다.
- [ ] 검증된 candidate만 `D:\module\output\`으로 승격한다. 기존 V4/V5 Neanderthal output은 덮어쓰지 않는다.

**Gate 8 — Release Gate**

- 모든 물리 검사가 PASS이고 final MP4·mirror가 존재하며 0바이트가 아니다.
- manifest의 hash와 실제 파일 hash가 일치한다.
- 각 shot의 expected asset, clip, text, motion, time binding을 추적할 수 있다.
- 실패한 candidate는 release로 표시하지 않고 `rejected/`에 이유와 hash를 남긴다.

### Phase 9 — 반복 재생성·학습 루프

- [ ] 모든 run에 `experiment_id`, `parent_run_id`, deterministic seed, code SHA, skill policy SHA, model/prompt version을 기록한다.
- [ ] 다음 feature vector를 추출한다: hook latency, cut density, shot duration quantiles, tier boundary, sentence CPS, caption density, pause/roomtone, loudness, motion family/axis 분포, decoded MAE, visual coverage, subtitle violations, human quality ratings.
- [ ] 한 실험에서는 변수 하나만 바꾼다(예: opening cut length, Tier 3 phase ratio, prompt look, subtitle density).
- [ ] baseline/variant를 script-audio, visual, motion, final QA 네 층으로 비교한다.
- [ ] 조회수는 인과 품질 점수로 사용하지 않는다. retention proxy와 사람 평가를 분리하고, 가능하면 동일 주제의 A/B 비교로 해석한다.
- [ ] 사람이 승인한 PASS 샘플만 prompt/motion/pacing optimizer의 학습 데이터로 편입한다. 실패·보류·출처 불명 샘플은 자동 학습에서 제외한다.
- [ ] `learning_report.json`에 개선/퇴행/불확실성을 모두 기록하고 다음 계획 revision으로 승격한다.

**Gate 9 — Learning Gate**

- baseline과 variant의 입력·코드·모델·seed·출력이 재현 가능하다.
- 변경 변수가 하나로 식별되고, 개선 지표와 guardrail 지표를 함께 보고한다.
- 사람 승인과 자동 QA가 모두 PASS한 샘플만 canonical learning set에 추가된다.
- 학습 결과가 원본 문장/원본 에셋 복제를 유도하지 않는지 originality audit가 통과한다.

## 4. 테스트 계획

### 4.1 새로 추가할 테스트

- `test_human_library_schema_adapter.py`: 필드 변환, required field, hash, source/original 분리.
- `test_human_library_timeline.py`: scene ID, sentence span coverage, gap/overlap, tier monotonicity.
- `test_human_library_asset_provenance.py`: request/prompt/download/asset SHA chain.
- `test_human_library_audio_contract.py`: 48k stereo, roomtone, sample count, master parity.
- `test_human_library_render_binding.py`: planned profile → canonical renderer, no silent fallback.
- `test_human_library_postflight.py`: decoded frame visibility, motion, freeze, subtitle, mirror hash.
- `test_learning_run_reproducibility.py`: experiment metadata, one-variable diff, approved-only ingestion.

### 4.2 검증 명령

```powershell
Set-Location D:\module\bible
python -m py_compile human_archive/scripts/lib/*.py human_archive/scripts/*.py
python -m pytest human_archive/tests/test_human_library_replica_contracts.py -q
python -m pytest -m "not media_heavy" -q
python human_archive/scripts/validate_human_library_bundle.py --run-root D:\module\bible\human_archive\runs\human_library_replica\rank1_race_adaptation
python human_archive/scripts/postflight_release.py --input D:\module\bible\human_archive\runs\human_library_replica\rank1_race_adaptation\releases\candidate\final.mp4 --build D:\module\bible\human_archive\runs\human_library_replica\rank1_race_adaptation\releases\candidate --report D:\module\bible\human_archive\runs\human_library_replica\rank1_race_adaptation\releases\candidate\release_report.json --duration-mode full
git diff --check
```

현재는 마지막 두 명령의 human-library 전용 validator와 실제 candidate가 없으므로 구현 전 실행 불가 상태다. 계획 실행 시 명령을 추가한 뒤 실행한다.

## 5. 완료 기준

- **Code**: 변경 모듈 `py_compile` 통과.
- **Test**: 관련 신규 테스트와 루트 non-media suite Exit Code 0.
- **Integrity**: 실제 WAV·이미지·클립·ASS·MP4가 0바이트가 아니고 manifest/mirror SHA가 일치.
- **Media**: 48kHz stereo, final parity ≤0.050s, 25fps CFR, 1920x1080, BT.709, loudness·subtitle·first-frame·freeze gate 통과.
- **Narrative**: 도입부의 빠른 컷과 후반부의 느린 내부 모션이 실제 decoded timeline에서 확인되고, 문장-장면-자막 span이 일치.
- **Learning**: 실험 ID·seed·코드/스킬 hash·평가 feature vector·사람 승인 기록이 존재하며 approved-only learning set에 등록.
- **Memory**: `D:\module\TASK.md`, `PROGRESS.md`, `PROJECT_MEMORY.md`, `DECISIONS.md`, `ERRORS.md`가 실제 상태와 일치.

## 6. 현재 상태와 다음 실행 순서

현재 완료로 인정하는 것은 Top 3 분석 증거와 3종 계약 초안, 해당 계약 테스트 3건뿐이다. 다음 순서는 **Gate 0 → Phase 1 → Gate 1 → Phase 2 → Gate 2**이며, 이 다섯 단계가 통과되기 전에는 TTS/Flow 비용이 발생하는 호출을 시작하지 않는다. 이후에는 작은 파일럿(Opening 11초 + Tier 1 일부)으로 Gate 3~6을 먼저 검증하고, 통과한 뒤 전체 972.11초 candidate를 생성한다.
