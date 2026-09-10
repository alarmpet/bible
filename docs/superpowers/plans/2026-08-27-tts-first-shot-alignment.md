# TTS-First Shot Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable, episode-neutral pipeline that synthesizes approved narration by sentence, derives shots from measured audio time, obtains schema-constrained visual briefs through Codex CLI, and emits a hash-bound `shot_alignment_manifest.json`.

**Architecture:** Keep timing deterministic and model-independent: sentence TTS produces the authoritative clock, a pure planner creates immutable shot spans, and Codex CLI may enrich only the visual meaning fields. A final assembler validates source anchors and sequence constraints, then derives the legacy shot/audio views needed by downstream renderers without re-synthesizing speech.

**Tech Stack:** Python 3.12+, pytest, JSON Schema 2020-12, PyYAML, Jinja2, FFmpeg/ffprobe, Supertonic3 provider, Codex CLI `exec --output-schema`

**Spec:** `docs/superpowers/specs/2026-08-27-narration-aligned-visual-workflow-design.md`

## Global Constraints

- Profile ID is exactly `narration_aligned_hybrid_v1`.
- Shot bounds are `min=9.0`, `target=10.5`, `max=12.0`, `hard_max=15.0` seconds.
- A shot contains at most two whole sentences; a sentence over 12 seconds is split only at declared segment or clause boundaries.
- Sentence audio is authoritative; shot planning never re-synthesizes or time-stretches it.
- Every source sentence or clause span is covered exactly once and in order.
- Required semantic anchors must resolve to approved narration text or claim inventory source spans.
- Host ratio is 8–12%, host scenes are never consecutive, and at least seven non-host shots separate host scenes.
- Build-local `source/shot_contract_v5.json` is canonical for v5; legacy parent contracts are read-only fallbacks.
- Tests must use fixture/fake providers and must not invoke network services or a real Codex session.

---

### Task 1: Add Versioned Pacing and Alignment Contracts

**Files:**
- Create: `human_archive/config/visual_pacing_profiles.yaml`
- Create: `human_archive/schemas/sentence_audio_manifest.schema.json`
- Create: `human_archive/schemas/shot_timing_manifest.schema.json`
- Create: `human_archive/schemas/visual_brief_manifest.schema.json`
- Create: `human_archive/schemas/shot_alignment_manifest.schema.json`
- Create: `human_archive/tests/test_narration_alignment_contracts.py`

**Interfaces:**
- Consumes: existing `lib.schema_validation.load_schema(path)` and `validate_json(instance, schema)`.
- Produces: four JSON Schema boundaries and the named YAML profile consumed by Tasks 2–5.

- [ ] **Step 1: Write failing schema/profile tests**

```python
from pathlib import Path
import json
import pytest
import yaml

from lib.schema_validation import load_schema, validate_json

ROOT = Path(__file__).resolve().parents[1]


def test_hybrid_profile_has_approved_exact_limits():
    data = yaml.safe_load((ROOT / "config" / "visual_pacing_profiles.yaml").read_text(encoding="utf-8"))
    profile = data["narration_aligned_hybrid_v1"]
    assert (profile["min_shot_sec"], profile["target_shot_sec"], profile["max_shot_sec"]) == (9.0, 10.5, 12.0)
    assert profile["hard_max_shot_sec"] == 15.0
    assert (profile["host_ratio_min"], profile["host_ratio_max"]) == (0.08, 0.12)
    assert profile["host_min_non_host_gap"] == 7


def test_sentence_audio_schema_rejects_missing_script_hash():
    schema = load_schema(ROOT / "schemas" / "sentence_audio_manifest.schema.json")
    with pytest.raises(ValueError, match="script_sha256"):
        validate_json({"schema_version": 1, "episode_id": "HA002", "sentences": []}, schema)


def test_alignment_schema_requires_semantic_anchors_and_motion_profile():
    schema = load_schema(ROOT / "schemas" / "shot_alignment_manifest.schema.json")
    invalid = {
        "schema_version": 1,
        "episode_id": "HA002",
        "script_sha256": "A",
        "sentence_audio_sha256": "B",
        "shots": [{"shot_id": "ha002_v5_shot_001", "order": 1}],
    }
    with pytest.raises(ValueError, match="semantic_anchors|motion_profile"):
        validate_json(invalid, schema)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `pytest human_archive/tests/test_narration_alignment_contracts.py -v`

Expected: FAIL because the YAML profile and schemas do not exist.

- [ ] **Step 3: Create the exact pacing profile**

```yaml
narration_aligned_hybrid_v1:
  min_shot_sec: 9.0
  target_shot_sec: 10.5
  max_shot_sec: 12.0
  hard_max_shot_sec: 15.0
  max_sentences_per_shot: 2
  host_ratio_min: 0.08
  host_ratio_max: 0.12
  host_min_non_host_gap: 7
  max_same_mode_streak: 2
  max_evidence_streak: 1
  motif_window_shots: 10
  max_motif_occurrences_per_window: 2
  cold_open_pilot_shots: 12
  cold_open_pilot_max_sec: 120.0
  coverage_pilot_shots: 8
  max_policy_auto_retries: 2
```

- [ ] **Step 4: Create strict schemas**

Require these exact per-row fields:

```text
sentence_audio_manifest top level:
schema_version, episode_id, script_sha256, master_audio, total_duration_sec,
gap_sec, sentences

sentence_audio_manifest.sentences[]:
sentence_id, order, chapter, beat, tts_text, start_sec, end_sec,
duration_sec, audio_file, provenance

shot_timing_manifest top level:
schema_version, episode_id, script_sha256, sentence_audio_sha256,
profile_id, timing_sha256, shots

shot_timing_manifest.shots[]:
shot_id, order, chapter, start_sec, end_sec, duration_sec,
sentence_spans, claim_ids, boundary_reason

visual_brief_manifest top level:
schema_version, episode_id, script_sha256, timing_sha256,
provider, model, brief_manifest_sha256, briefs

visual_brief_manifest.briefs[]:
shot_id, narration_digest, visual_mode, semantic_anchors, focal_subject,
action, place, era, shot_scale, camera, foreground, midground, background,
continuity_group, reference_asset_ids, prop_motifs, text_overlay_policy,
overlay_items, motion_profile, safety_treatment

shot_alignment_manifest top level:
schema_version, episode_id, script_sha256, sentence_audio_sha256,
timing_sha256, brief_manifest_sha256, profile_id, alignment_sha256, shots

shot_alignment_manifest.shots[]:
all timing fields + all visual brief fields + visual_role, host_mode,
novelty_signature, source_sentence_spans
```

Use `additionalProperties: false` for new row objects so misspelled contract fields fail at the boundary. Constrain `visual_mode` to the eight modes in the approved spec and constrain `motion_profile` to `reenactment_push`, `place_sweep`, `route_pan`, `diagram_reveal`, `artifact_close_push`, `analogy_pan`, `atmosphere_drift`, `host_hinge`.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `pytest human_archive/tests/test_narration_alignment_contracts.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add human_archive/config/visual_pacing_profiles.yaml human_archive/schemas/sentence_audio_manifest.schema.json human_archive/schemas/shot_timing_manifest.schema.json human_archive/schemas/visual_brief_manifest.schema.json human_archive/schemas/shot_alignment_manifest.schema.json human_archive/tests/test_narration_alignment_contracts.py
git commit -m "feat: define narration-aligned visual contracts"
```

### Task 2: Build the Authoritative Sentence Audio Timeline

**Files:**
- Create: `human_archive/scripts/lib/sentence_audio_timeline.py`
- Create: `human_archive/scripts/build_sentence_audio_master.py`
- Create: `human_archive/tests/test_sentence_audio_timeline.py`
- Modify: `human_archive/tests/test_audio_timeline_v2.py`

**Interfaces:**
- Consumes: approved script dict, `ToneFixtureProvider` or `SupertonicHttpProvider`, `get_wav_duration()`, `normalize_master_audio()`.
- Produces: `build_sentence_audio_master(script_path: Path, build_dir: Path, audio_mode: str, tts_url: str | None, gap_sec: float = 0.35) -> Path`; pure `build_sentence_rows(sentences: list[dict], durations: dict[str, float], gap_sec: float) -> list[dict]`; `validate_sentence_timeline(script: dict, manifest: dict) -> list[str]`.

- [ ] **Step 1: Write pure failing timeline tests**

```python
from lib.sentence_audio_timeline import build_sentence_rows, validate_sentence_timeline


def _sentence(sid, order, text):
    return {"sentence_id": sid, "order": order, "chapter": 1, "beat": "body", "tts_text": text}


def test_sentence_rows_use_measured_duration_and_gap():
    sentences = [_sentence("S1", 1, "첫 문장"), _sentence("S2", 2, "둘째 문장")]
    rows = build_sentence_rows(sentences, {"S1": 4.0, "S2": 5.0}, gap_sec=0.35)
    assert rows[0]["start_sec"] == 0.0
    assert rows[0]["end_sec"] == 4.0
    assert rows[1]["start_sec"] == 4.35
    assert rows[1]["end_sec"] == 9.35


def test_timeline_rejects_missing_or_overlapping_sentence():
    script = {"sentences": [_sentence("S1", 1, "첫 문장"), _sentence("S2", 2, "둘째 문장")]}
    manifest = {"sentences": [{"sentence_id": "S1", "order": 1, "start_sec": 0.0, "end_sec": 5.0}]}
    errors = validate_sentence_timeline(script, manifest)
    assert any("S2" in error and "missing" in error.lower() for error in errors)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `pytest human_archive/tests/test_sentence_audio_timeline.py -v`

Expected: FAIL with import error for `lib.sentence_audio_timeline`.

- [ ] **Step 3: Implement the pure timeline library**

```python
def build_sentence_rows(sentences, durations, gap_sec=0.35):
    rows = []
    cursor = 0.0
    ordered = sorted(sentences, key=lambda item: (int(item["order"]), str(item["sentence_id"])))
    for index, sentence in enumerate(ordered):
        sentence_id = str(sentence["sentence_id"])
        duration = round(float(durations[sentence_id]), 3)
        start = round(cursor, 3)
        end = round(start + duration, 3)
        rows.append({
            "sentence_id": sentence_id,
            "order": int(sentence["order"]),
            "chapter": int(sentence.get("chapter", 1)),
            "beat": str(sentence.get("beat", "body")),
            "tts_text": str(sentence["tts_text"]),
            "start_sec": start,
            "end_sec": end,
            "duration_sec": duration,
            "audio_file": f"{sentence_id}.wav",
        })
        cursor = end + (gap_sec if index + 1 < len(ordered) else 0.0)
    return rows
```

`validate_sentence_timeline()` must compare ordered IDs exactly, require positive duration, require `end_sec > start_sec`, reject overlap, and confirm `round(end-start, 3) == duration_sec` within 0.02 seconds.

- [ ] **Step 4: Implement sentence-first synthesis**

`build_sentence_audio_master.py` must:

1. load and hash the script;
2. synthesize one WAV per sentence into `build_dir / "audio" / "sentences"`;
3. measure each WAV with ffprobe;
4. concatenate with a 0.35-second fixture gap;
5. normalize to `build_dir / "master_audio_48k.wav"`;
6. write and schema-validate `build_dir / "sentence_audio_manifest.json"` atomically;
7. include each TTS provider provenance object without modification.

Expose this exact CLI:

```powershell
python human_archive/scripts/build_sentence_audio_master.py --script human_archive/runs/ep02_jang_huibin/full-v5-001/source/script_candidate.json --build human_archive/runs/ep02_jang_huibin/full-v5-001 --audio-mode supertonic3 --tts-url http://127.0.0.1:3093
```

- [ ] **Step 5: Add a fixture integration test**

```python
import json

from build_sentence_audio_master import build_sentence_audio_master


def test_build_sentence_audio_master_with_fixture_provider(tmp_path):
    script_path = tmp_path / "script_candidate.json"
    script_path.write_text(json.dumps({
        "episode_id": "HA-TEST",
        "sentences": [
            {"sentence_id": "S1", "order": 1, "chapter": 1, "beat": "hook", "tts_text": "첫 문장입니다"},
            {"sentence_id": "S2", "order": 2, "chapter": 1, "beat": "body", "tts_text": "둘째 문장입니다"},
        ],
    }, ensure_ascii=False), encoding="utf-8")
    build_dir = tmp_path / "build"
    master = build_sentence_audio_master(script_path, build_dir, audio_mode="fixture", tts_url=None)
    manifest = json.loads((build_dir / "sentence_audio_manifest.json").read_text(encoding="utf-8"))
    assert master.exists()
    assert len(manifest["sentences"]) == 2
    assert manifest["script_sha256"]
    assert manifest["total_duration_sec"] >= manifest["sentences"][-1]["end_sec"]
```

- [ ] **Step 6: Run focused tests and verify GREEN**

Run: `pytest human_archive/tests/test_sentence_audio_timeline.py human_archive/tests/test_audio_timeline_v2.py -v`

Expected: PASS; the existing shot-first `build_audio_master_v2.py` test remains green for legacy builds.

- [ ] **Step 7: Commit**

```bash
git add human_archive/scripts/lib/sentence_audio_timeline.py human_archive/scripts/build_sentence_audio_master.py human_archive/tests/test_sentence_audio_timeline.py human_archive/tests/test_audio_timeline_v2.py
git commit -m "feat: synthesize authoritative sentence audio timeline"
```

### Task 3: Plan Shot Timing from Measured Audio

**Files:**
- Create: `human_archive/scripts/lib/shot_timing.py`
- Create: `human_archive/scripts/plan_narration_shots.py`
- Create: `human_archive/tests/test_shot_timing.py`

**Interfaces:**
- Consumes: approved script, sentence audio manifest, claim inventory, named profile from `visual_pacing_profiles.yaml`.
- Produces: `load_pacing_profile(path: Path, profile_id: str) -> ShotTimingProfile`; `plan_shot_timing(script: dict, audio_manifest: dict, claims: dict, profile: ShotTimingProfile) -> dict`; `build_dir / "shot_timing_manifest.json"`.

- [ ] **Step 1: Write failing timing tests**

```python
import pytest

from lib.shot_timing import ShotTimingProfile, plan_shot_timing

PROFILE = ShotTimingProfile(9.0, 10.5, 12.0, 15.0, 2)


def test_planner_combines_short_sentences_but_not_past_max():
    script = {"episode_id": "HA002", "sentences": [
        {"sentence_id": "S1", "order": 1, "chapter": 1, "beat": "body", "tts_text": "하나"},
        {"sentence_id": "S2", "order": 2, "chapter": 1, "beat": "body", "tts_text": "둘"},
        {"sentence_id": "S3", "order": 3, "chapter": 1, "beat": "body", "tts_text": "셋"},
    ]}
    audio = {"script_sha256": "SCRIPT", "sentences": [
        {"sentence_id": "S1", "start_sec": 0.0, "end_sec": 4.0},
        {"sentence_id": "S2", "start_sec": 4.35, "end_sec": 9.35},
        {"sentence_id": "S3", "start_sec": 9.70, "end_sec": 19.70},
    ]}
    result = plan_shot_timing(script, audio, {}, PROFILE)
    assert [s["sentence_spans"][0]["sentence_id"] for s in result["shots"]] == ["S1", "S3"]
    assert [span["sentence_id"] for span in result["shots"][0]["sentence_spans"]] == ["S1", "S2"]
    assert result["shots"][0]["duration_sec"] == 9.35


def test_chapter_and_reversal_force_boundaries():
    script = {"episode_id": "HA002", "sentences": [
        {"sentence_id": "S1", "order": 1, "chapter": 1, "beat": "body", "tts_text": "기존 설명입니다"},
        {"sentence_id": "S2", "order": 2, "chapter": 1, "beat": "body", "tts_text": "그런데 기록은 달랐습니다"},
        {"sentence_id": "S3", "order": 3, "chapter": 2, "beat": "body", "tts_text": "다음 장의 설명입니다"},
    ]}
    audio = {"script_sha256": "SCRIPT", "sentences": [
        {"sentence_id": "S1", "start_sec": 0.0, "end_sec": 5.0},
        {"sentence_id": "S2", "start_sec": 5.35, "end_sec": 10.35},
        {"sentence_id": "S3", "start_sec": 10.70, "end_sec": 15.70},
    ]}
    result = plan_shot_timing(script, audio, {}, PROFILE)
    assert [shot["shot_id"] for shot in result["shots"]] == [
        "ha002_v5_shot_001", "ha002_v5_shot_002", "ha002_v5_shot_003"
    ]


def test_every_source_character_span_is_covered_once():
    text = "가" * 44
    script = {"episode_id": "HA002", "sentences": [{
        "sentence_id": "S1", "order": 1, "chapter": 1, "beat": "body", "tts_text": text,
        "segments": [
            {"char_start": 0, "char_end": 21, "claim_id": "C1"},
            {"char_start": 21, "char_end": 44, "claim_id": "C1"},
        ],
    }]}
    audio = {"script_sha256": "SCRIPT", "sentences": [
        {"sentence_id": "S1", "start_sec": 0.0, "end_sec": 22.0}
    ]}
    result = plan_shot_timing(script, audio, {"claims": [{"claim_id": "C1"}]}, PROFILE)
    spans = [span for shot in result["shots"] for span in shot["sentence_spans"]]
    assert [(s["char_start"], s["char_end"]) for s in spans] == [(0, 21), (21, 44)]
    assert max(shot["duration_sec"] for shot in result["shots"]) <= 15.0
```

- [ ] **Step 2: Run tests and verify RED**

Run: `pytest human_archive/tests/test_shot_timing.py -v`

Expected: FAIL with import error for `lib.shot_timing`.

- [ ] **Step 3: Implement the profile and boundary scorer**

```python
@dataclass(frozen=True)
class ShotTimingProfile:
    min_shot_sec: float
    target_shot_sec: float
    max_shot_sec: float
    hard_max_shot_sec: float
    max_sentences_per_shot: int


TRANSITION_PREFIXES = ("그런데", "하지만", "그렇다면", "결국", "문제는", "반면")


def is_preferred_boundary(previous, current):
    return (
        previous.get("chapter") != current.get("chapter")
        or previous.get("beat") != current.get("beat")
        or str(current.get("tts_text", "")).lstrip().startswith(TRANSITION_PREFIXES)
        or claim_ids(previous) != claim_ids(current)
    )
```

Use a forward greedy group with a one-step lookahead: combine only when the current shot is below 9.0 seconds, the next sentence keeps the span at or below 12.0 seconds, the count remains at or below two, and no preferred boundary is crossed.

- [ ] **Step 4: Implement long-sentence clause splitting**

Use declared `segments[]` first. If no usable segments exist, split at Korean clause punctuation `,`, `;`, `—` and transition tokens. Allocate audio time by non-whitespace character proportion, preserve the exact `[char_start, char_end)` coverage, and reject a sentence over 15 seconds when no legal split exists.

- [ ] **Step 5: Implement the CLI and schema/hash binding**

Expose:

```powershell
python human_archive/scripts/plan_narration_shots.py --script human_archive/runs/ep02_jang_huibin/full-v5-001/source/script_candidate.json --audio human_archive/runs/ep02_jang_huibin/full-v5-001/sentence_audio_manifest.json --claims human_archive/runs/ep02_jang_huibin/full-v5-001/source/claim_inventory_v2.json --profile narration_aligned_hybrid_v1 --output human_archive/runs/ep02_jang_huibin/full-v5-001/shot_timing_manifest.json
```

The output must include `script_sha256`, `sentence_audio_sha256`, `profile_id`, and a canonical `timing_sha256`. Abort before writing if the audio manifest's script hash differs from the loaded script.

- [ ] **Step 6: Run tests and verify GREEN**

Run: `pytest human_archive/tests/test_shot_timing.py human_archive/tests/test_narration_alignment_contracts.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add human_archive/scripts/lib/shot_timing.py human_archive/scripts/plan_narration_shots.py human_archive/tests/test_shot_timing.py
git commit -m "feat: plan shots from measured narration time"
```

### Task 4: Generate Schema-Constrained Visual Briefs with Codex CLI

**Files:**
- Create: `human_archive/templates/narration_visual_brief_prompt.j2`
- Create: `human_archive/scripts/lib/visual_brief_provider.py`
- Create: `human_archive/scripts/generate_visual_briefs.py`
- Create: `human_archive/tests/test_visual_brief_provider.py`

**Interfaces:**
- Consumes: shot timing manifest, approved script excerpts, claim inventory, visual brief JSON Schema.
- Produces: `VisualBriefProvider.generate(prompt: str, output_schema_path: Path) -> dict`; `CodexCliVisualBriefProvider`; `JsonFileVisualBriefProvider`; `build_dir / "visual_brief_manifest.json"`.

- [ ] **Step 1: Write failing provider invocation tests**

```python
from pathlib import Path
import pytest

from lib.visual_brief_provider import CodexCliVisualBriefProvider, JsonFileVisualBriefProvider


def write_schema(tmp_path):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(
        '{"type":"object","required":["schema_version","briefs"],"properties":{"schema_version":{"const":1},"briefs":{"type":"array"}}}',
        encoding="utf-8",
    )
    return schema_path


def test_codex_provider_uses_schema_ephemeral_read_only_and_no_shell(tmp_path):
    calls = []
    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        output = Path(args[args.index("--output-last-message") + 1])
        output.write_text('{"schema_version":1,"briefs":[]}', encoding="utf-8")
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    schema_path = write_schema(tmp_path)
    provider = CodexCliVisualBriefProvider(repo_root=tmp_path, runner=fake_run)
    provider.generate("PROMPT", schema_path)
    args, kwargs = calls[0]
    assert args[:2] == ["codex", "exec"]
    assert ["--ephemeral", "--sandbox", "read-only"] == args[2:5]
    assert "--output-schema" in args and "--output-last-message" in args
    assert kwargs["input"] == "PROMPT"
    assert kwargs["shell"] is False


def test_codex_provider_surfaces_nonzero_exit_stderr(tmp_path):
    def failed_run(args, **kwargs):
        return type("Result", (), {"returncode": 7, "stdout": "", "stderr": "authentication failed"})()
    provider = CodexCliVisualBriefProvider(repo_root=tmp_path, runner=failed_run)
    with pytest.raises(RuntimeError, match="authentication failed"):
        provider.generate("PROMPT", write_schema(tmp_path))


def test_codex_provider_rejects_malformed_json(tmp_path):
    def malformed_run(args, **kwargs):
        output = Path(args[args.index("--output-last-message") + 1])
        output.write_text("not-json", encoding="utf-8")
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    provider = CodexCliVisualBriefProvider(repo_root=tmp_path, runner=malformed_run)
    with pytest.raises(ValueError, match="JSON"):
        provider.generate("PROMPT", write_schema(tmp_path))


def test_json_file_provider_schema_validates_fixture(tmp_path):
    response_path = tmp_path / "response.json"
    response_path.write_text('{"schema_version":1}', encoding="utf-8")
    provider = JsonFileVisualBriefProvider(response_path)
    with pytest.raises(ValueError, match="briefs"):
        provider.generate("IGNORED", write_schema(tmp_path))
```

- [ ] **Step 2: Run tests and verify RED**

Run: `pytest human_archive/tests/test_visual_brief_provider.py -v`

Expected: FAIL with import error.

- [ ] **Step 3: Implement both providers**

Use `tempfile.TemporaryDirectory()` for the Codex output file and this exact argument order:

```python
args = [
    "codex", "exec",
    "--ephemeral", "--sandbox", "read-only",
    "--output-schema", str(output_schema_path),
    "--output-last-message", str(output_path),
    "--cd", str(self.repo_root),
    "-",
]
completed = self.runner(args, input=prompt, text=True, capture_output=True, shell=False)
```

Parse, schema-validate, and return the JSON. Do not pass `--dangerously-bypass-approvals-and-sandbox`.

- [ ] **Step 4: Write the visual brief prompt template**

The template must include:

- immutable shot IDs, times, narration text, claim IDs and evidence spans;
- the eight allowed modes and their selection rules;
- instruction to retain named people, concrete action, place and era;
- instruction that `evidence_artifact` requires evidence itself to be the narrated subject;
- no invented facts, dialogue, labels, dates or extra people;
- overlay text only when copied from an approved source phrase, always in `overlay_items` and never inside the image prompt;
- reference asset IDs only from the supplied approved asset inventory;
- no style imitation or reference to the benchmark channel in generated prompts;
- exact JSON-only output instruction.

- [ ] **Step 5: Implement the CLI**

```powershell
# 2026-08-28 gate contract: 과거 full-v5 경로를 그대로 복사 실행하지 않는다.
# 현재 build에서 사람이 기록한 fact approval과 PASS persona가 있어야 한다.
$build = '<current-approved-build>'
python human_archive/scripts/generate_visual_briefs.py --timing "$build/shot_timing_manifest.json" --script "$build/source/script_candidate.json" --claims "$build/source/claim_inventory_v2.json" --sources "$build/source/source_snapshot_manifest_v2.json" --fact-report "$build/source/fact_check_report_v2.json" --persona-report "$build/source/persona_report_v2.json" --fact-approval "$build/source/approvals/fact_review_approval_v1.json" --provider json-file --response <reviewed-response.json> --output "$build/visual_brief_manifest.json" --prompts "$build/flow_image_prompts.json"
# codex-cli provider는 사실 문구 승인과 별도의 외부 전송 승인을 받은 뒤에만 사용한다.
```

Also support `--provider json-file --response human_archive/tests/fixtures/visual_brief_response.json` for tests, offline review and a manually prepared Codex/Antigravity response. Validate that returned shot IDs equal timing shot IDs exactly and in order before atomic write.

- [ ] **Step 6: Run tests and verify GREEN**

Run: `pytest human_archive/tests/test_visual_brief_provider.py human_archive/tests/test_narration_alignment_contracts.py -v`

Expected: PASS without starting a real Codex process.

- [ ] **Step 7: Commit**

```bash
git add human_archive/templates/narration_visual_brief_prompt.j2 human_archive/scripts/lib/visual_brief_provider.py human_archive/scripts/generate_visual_briefs.py human_archive/tests/test_visual_brief_provider.py
git commit -m "feat: generate constrained narration visual briefs"
```

### Task 5: Assemble and Validate the Canonical Shot Alignment Manifest

**Files:**
- Create: `human_archive/scripts/lib/visual_modes.py`
- Create: `human_archive/scripts/lib/shot_alignment.py`
- Create: `human_archive/scripts/prepare_narration_aligned_workflow.py`
- Create: `human_archive/tests/test_shot_alignment.py`
- Modify: `human_archive/tests/test_doodle_scene_planner.py`

**Interfaces:**
- Consumes: script, sentence audio, shot timing, visual briefs, pacing profile.
- Produces: `assemble_shot_alignment(timing: dict, briefs: dict, script: dict, claims: dict, profile: dict) -> dict`; `validate_visual_sequence(shots: list[dict], profile: dict) -> list[str]`; `derive_scene_audio_manifest(sentence_audio: dict, alignment: dict) -> dict`; build-local `shot_alignment_manifest.json`, `scene_audio_manifest.json`, `episode_visual_contract_v3.json`, and `source/shot_contract_v5.json`.

- [ ] **Step 1: Write failing alignment tests**

```python
import pytest

from lib.shot_alignment import (
    assemble_shot_alignment,
    derive_scene_audio_manifest,
    validate_visual_sequence,
)


def profile_fixture():
    return {
        "host_ratio_min": 0.08, "host_ratio_max": 0.12,
        "host_min_non_host_gap": 7, "max_same_mode_streak": 2,
        "max_evidence_streak": 1, "motif_window_shots": 10,
        "max_motif_occurrences_per_window": 2,
    }


def timing_fixture(text="숙종은 조정에 섰다"):
    return {"script_sha256": "SCRIPT", "timing_sha256": "TIMING", "shots": [{
        "shot_id": "ha002_v5_shot_001", "order": 1, "chapter": 1,
        "start_sec": 0.0, "end_sec": 9.35, "duration_sec": 9.35,
        "sentence_spans": [{
            "sentence_id": "S1", "char_start": 0, "char_end": len(text),
            "start_sec": 0.0, "end_sec": 9.35,
        }],
        "claim_ids": [], "boundary_reason": "duration_target",
    }]}


def script_fixture(text="숙종은 조정에 섰다"):
    return {"episode_id": "HA002", "sentences": [{
        "sentence_id": "S1", "order": 1, "chapter": 1,
        "beat": "body", "tts_text": text,
    }]}


def brief_fixture(anchor):
    return {"timing_sha256": "TIMING", "briefs": [{
        "shot_id": "ha002_v5_shot_001", "narration_digest": "조정 장면",
        "visual_mode": "event_reconstruction", "semantic_anchors": [anchor],
        "focal_subject": "King Sukjong", "action": "stands in council",
        "place": "royal council hall", "era": "late Joseon",
        "shot_scale": "wide", "camera": "eye-level",
        "foreground": "minister", "midground": "king", "background": "hall",
        "continuity_group": "sukjong_v1", "reference_asset_ids": ["character_sukjong_v1"],
        "prop_motifs": ["council_mat"], "text_overlay_policy": "renderer_only",
        "overlay_items": [], "motion_profile": "reenactment_push",
        "safety_treatment": "non_graphic",
    }]}


def shots_for_modes(modes):
    return [{
        "shot_id": f"S{index:03d}", "order": index,
        "visual_mode": mode, "host_mode": "full" if mode == "host_chapter_hinge" else "absent",
        "prop_motifs": [f"motif_{index}"], "novelty_signature": f"N{index}",
        "semantic_anchors": [{"anchor_id": f"A{index}", "required": True}],
    } for index, mode in enumerate(modes, 1)]


def sentence_audio_fixture():
    return {
        "script_sha256": "SCRIPT", "master_audio": "master_audio_48k.wav",
        "total_duration_sec": 9.35,
        "sentences": [{
            "sentence_id": "S1", "order": 1, "tts_text": "숙종은 조정에 섰다",
            "start_sec": 0.0, "end_sec": 9.35, "duration_sec": 9.35,
        }],
    }


def alignment_fixture():
    return {"shots": [{
        "shot_id": "ha002_v5_shot_001", "order": 1, "chapter": 1,
        "start_sec": 0.0, "end_sec": 9.35, "duration_sec": 9.35,
        "source_sentence_spans": [{"sentence_id": "S1", "char_start": 0, "char_end": 11}],
    }]}


def test_alignment_rejects_required_anchor_not_found_in_sources():
    briefs = brief_fixture(anchor={
        "anchor_id": "a-1", "kind": "person", "source_text": "세종",
        "visual_token": "King Sejong", "required": True,
    })
    with pytest.raises(ValueError, match="anchor.*source"):
        assemble_shot_alignment(timing_fixture(), briefs, script_fixture(), {}, profile_fixture())


def test_sequence_rejects_object_collapse_and_host_spacing():
    modes = ["evidence_artifact", "evidence_artifact", "host_chapter_hinge", "event_reconstruction", "host_chapter_hinge"]
    errors = validate_visual_sequence(shots_for_modes(modes), profile_fixture())
    assert any("evidence" in error.lower() and "consecutive" in error.lower() for error in errors)
    assert any("host" in error.lower() and "gap" in error.lower() for error in errors)


def test_scene_audio_is_projected_without_resynthesis():
    result = derive_scene_audio_manifest(sentence_audio_fixture(), alignment_fixture())
    assert result["master_audio"] == "master_audio_48k.wav"
    assert result["shots"][0]["startSeconds"] == 0.0
    assert result["shots"][0]["endSeconds"] == 9.35
```

- [ ] **Step 2: Run tests and verify RED**

Run: `pytest human_archive/tests/test_shot_alignment.py -v`

Expected: FAIL with import error.

- [ ] **Step 3: Implement mode-to-legacy-role compatibility**

```python
MODE_TO_ROLE = {
    "host_chapter_hinge": "host_explainer",
    "event_reconstruction": "historical_reconstruction",
    "place_establishing": "historical_reconstruction",
    "evidence_artifact": "evidence_object",
    "route_map": "diagram_metaphor",
    "mechanism_diagram": "diagram_metaphor",
    "modern_analogy": "diagram_metaphor",
    "atmosphere_transition": "atmosphere",
}


def host_mode_for(visual_mode):
    return "full" if visual_mode == "host_chapter_hinge" else "absent"
```

- [ ] **Step 4: Implement canonical assembly and validation**

For each timing row, join exactly one brief by `shot_id`, copy source spans rather than narration text generated by the model, resolve every required anchor and overlay text against the joined source span or claim source span, reject unknown `reference_asset_ids`, and calculate:

```python
novelty_fields = {
    "visual_mode": shot["visual_mode"],
    "focal_subject": shot["focal_subject"],
    "action": shot["action"],
    "place": shot["place"],
    "shot_scale": shot["shot_scale"],
    "prop_motifs": sorted(shot["prop_motifs"]),
}
shot["novelty_signature"] = compute_object_sha256(novelty_fields)
```

`validate_visual_sequence()` must return all errors in one pass for host ratio, host spacing, same-mode streak, evidence streak, motif window, duplicate novelty signature, timing bounds, and required anchor coverage.

Calculate the top-level hash without a circular dependency:

```python
alignment_without_hash = {key: value for key, value in alignment.items() if key != "alignment_sha256"}
alignment["alignment_sha256"] = compute_object_sha256(alignment_without_hash)
```

- [ ] **Step 5: Implement compatibility projections and CLI**

Expose:

```powershell
python human_archive/scripts/prepare_narration_aligned_workflow.py --script human_archive/runs/ep02_jang_huibin/full-v5-001/source/script_candidate.json --audio human_archive/runs/ep02_jang_huibin/full-v5-001/sentence_audio_manifest.json --timing human_archive/runs/ep02_jang_huibin/full-v5-001/shot_timing_manifest.json --briefs human_archive/runs/ep02_jang_huibin/full-v5-001/visual_brief_manifest.json --claims human_archive/runs/ep02_jang_huibin/full-v5-001/source/claim_inventory_v2.json --profile narration_aligned_hybrid_v1 --build human_archive/runs/ep02_jang_huibin/full-v5-001
```

Write all outputs to the build directory atomically. `source/shot_contract_v5.json` must use the same shot IDs and narration timing; `scene_audio_manifest.json` must reference the existing master and must not create new WAVs.

- [ ] **Step 6: Replace obsolete planner expectations**

Keep legacy `plan_scenes(sentences, claims, target_chars=55)` tests for legacy profile compatibility, but rename the old quota tests with a `legacy_` prefix. Add this source-boundary test to `test_shot_alignment.py`:

```python
from pathlib import Path


def test_v5_workflow_does_not_depend_on_legacy_character_grouper():
    source = (Path(__file__).resolve().parents[1] / "scripts" / "prepare_narration_aligned_workflow.py").read_text(encoding="utf-8")
    assert "doodle_scene_planner" not in source
    assert "_group_sentences" not in source
    assert "target_chars" not in source
```

- [ ] **Step 7: Run the complete alignment suite**

Run:

```powershell
pytest human_archive/tests/test_narration_alignment_contracts.py human_archive/tests/test_sentence_audio_timeline.py human_archive/tests/test_shot_timing.py human_archive/tests/test_visual_brief_provider.py human_archive/tests/test_shot_alignment.py human_archive/tests/test_doodle_scene_planner.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add human_archive/scripts/lib/visual_modes.py human_archive/scripts/lib/shot_alignment.py human_archive/scripts/prepare_narration_aligned_workflow.py human_archive/tests/test_shot_alignment.py human_archive/tests/test_doodle_scene_planner.py
git commit -m "feat: assemble narration-aligned shot manifest"
```

## Plan Acceptance

- [ ] A fixture episode produces sentence audio, timing, visual briefs and final alignment with no network calls.
- [ ] The final alignment validates against its schema and contains every source span exactly once.
- [ ] Timing is derived from measured audio and no shot exceeds 15 seconds.
- [ ] Required anchors cannot be invented or dropped.
- [ ] Host and visual sequence constraints fail before image prompt compilation.
- [ ] Legacy episodes remain readable through the existing v2/v4 path.
