# 구약 힐링 전체 미디어 파이프라인 고정 계획 (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Revision:** 2026-08-13 v2. 코드·실물 ASS·voice_map·SuperTonic 엔진·문서 대조 후 재작성. v1은 설정 잠금만 다루고, 화난 억양·한국어 자막 줄바꿈·오래된 WAV 재사용을 빠뜨렸다.

**Goal:** 남성 성경 낭독이 끝까지 같은 M4 저음·평안 톤으로 유지되고, 자막이 한국어 어절 경계의 2줄로 읽히며, 문서·설정·실제 실행이 하나의 lock만 따르게 한다.

**Architecture:** `bible_healing/config/media_rules_lock.json`을 유일한 정책 원본으로 둔다. 공통 `sanitize_script()` → 절 단위 TTS → `audio_filter` 후처리 → provenance 있는 WAV만 concat → 한국어 어절 자막 → D: 렌더 → preflight/postflight. 기존 `scene_*.wav`, `scene_*_synced.mp4`, `--skip-existing`, 과거 M5 잡, 수동 ASS 헤더는 입력으로 쓰지 않는다.

**Tech Stack:** Python 3.14, SuperTonic3 (`C:\Users\amd\supertonic3-local-tts-20260517-r4\supertonic3-local-tts`), FFmpeg/ffprobe, JSON, ASS, pytest, PowerShell.

## Global Constraints

- 화자는 `narrator`, `scripture`만 허용한다. 제3 화자·캐릭터 금지.
- narrator = F5, speed 0.95, total_step 8, silence 0.24.
- scripture = M4, speed 0.72, pitch -8%, silence 0.65. `total_step`은 공식 권장 5~12 안에서 A/B 후 lock에 기록한다. **24를 기본값으로 유지하지 않는다.**
- scripture `max_chunk_length`는 90. 엔진에 200자를 통째로 넘기지 않는다.
- TTS 입력에서 `! ！ !? ❗ ? ？` 전부 마침표. `<laugh> <breath> <sigh>` 금지.
- `(...)` `（...）` 제목·셀라·영장·현악·스미닛·저자 표기는 음성·자막에서 제거.
- 자막: 최대 2줄, 한 줄 목표 14~18자, hard 20자, `\N`로 두 줄. 조사·어미·단어 중간 분할 금지.
- 자막 타이포: Malgun Gothic Bold, 본문 96px, 성경 100px, outline 6, shadow 3, marginV 90, WrapStyle 0, ScaledBorderAndShadow yes.
- 배경: `pingpong-1min` 12개 MP4, `setpts=3*PTS` (0.333배속).
- 최종: `D:\bible_healing_ep01\final`. 임시: `D:\bible_healing_ep01\work`.
- `--skip-existing`와 기존 `scene_*_synced.mp4` 오디오는 본편 입력 금지.
- preflight 또는 postflight 실패 시 배포 금지.

---

## 2026-08-13 실측 원인 (v1이 놓친 것)

사용자 증상 세 가지는 서로 다른 버그가 겹친 결과다. “설정을 M4로 고치면 끝”이 아니다.

### A. 목소리가 자꾸 바뀐다

| # | 실측 | 파일 |
|---|---|---|
| A1 | 문서가 서로 다른 보이스를 가르친다. `HANDOFF.md`는 **F5@0.95 / M5@0.85**와 **F3/M2**를 동시에 적는다. | `bible_healing/HANDOFF.md:27`, `:87` |
| A2 | `build_full_job.py`가 yaml의 `audio_filter`를 **빈 문자열로 덮어쓰고** notes에 `F5/M5`를 남긴다. | `bible_healing/scripts/build_full_job.py:48-53` |
| A3 | 현재 full `voice_map.json`은 M4이지만 `audio_filter`가 비어 있고 `max_chunk_length`가 200이다. | `hermes_jobs/full/voice_map.json` |
| A4 | `tts_multi_voice.py`는 `audio_filter`를 읽기만 하고 FFmpeg에 적용하지 않는다. pitch -8%가 사라진다. | `modern/scripts/tts_multi_voice.py:187-197` |
| A5 | `--skip-existing`가 예전 M5/필터 없는 WAV를 그대로 쓴다. 새 lock과 다른 목소리가 한 영상에 섞인다. | `tts_multi_voice.py:167-169` |
| A6 | `rebuild_authoritative_full_audio.py`는 `scene_*.wav`만 glob한다. 보이스·해시·대본 검증이 없다. | `bible_healing/scripts/rebuild_authoritative_full_audio.py` |
| A7 | 과거 잡이 그대로 남아 있다. `voice_smoke_M3`, prelock manifest의 M5, `scene_*_synced.mp4` 136개. | `hermes_jobs/` |
| A8 | 게이트가 한 잡에 하드코딩되어 있다. `final_render_preflight.py`는 `actual_first3min_pause_split`만 본다. `media_rules_preflight.py`는 full job만 본다. | 두 preflight |
| A9 | 단일 오케스트레이터/워크플로가 없다. 에이전트가 예전 렌더 스크립트를 골라 다른 보이스로 다시 뽑는다. | `.grok/workflows` 없음, 렌더 스크립트 20개+ |

### B. 남자 목소리가 읽다가 화난 억양이 난다

느낌표 하나 때문이 아니다. SuperTonic3는 문장부호·호격·긴 청크 중간 절단에서 감정을 올린다.

| # | 실측 | 근거 |
|---|---|---|
| B1 | 대본 원문에 호격+느낌표가 남아 있다. `인생들아 !`, `내 영혼아 !`, `너는 하나님을 바라라 !`, `바랄지어다 !` | `script_segments.json`, `script_readable.md:18` |
| B2 | 물음표도 그대로다. `네 하나님이 어디 있느뇨 ?`, `누구뇨` | 같은 대본. `clean_for_tts()`는 `?`를 바꾸지 않음 |
| B3 | 표제·셀라가 한 덩어리로 합성된다. `(다윗의 시. 영장으로 현악에 맞춘 노래)`, `(셀라)` | scene 5 원문 |
| B4 | `scripture_tts_prep.py`의 절 단위 확장(`max_len=90`)이 **호출되지 않는다**. TTS는 `scenes.json` 통짜 텍스트를 넣는다. | `tts_multi_voice.py:174` vs `scripture_tts_prep.py:142` |
| B5 | scene 5는 시편 4편 전체가 **52.8초 한 파일**. `max_chunk_length=200`이라 엔진이 문장 중간에서 자른다. 잘린 다음 조각이 명령/호격으로 다시 시작하면 화난 억양처럼 들린다. | `scene_audio_manifest.json` scene 5 |
| B6 | `total_step: 24`는 공식 README 권장 5~12 밖이다. 로컬 래퍼 LIMITS는 1~100이라 실행만 된다. 과한 step이 억양을 키울 수 있어 A/B가 필요하다. | SuperTonic README; `supertonic3_engine.py:221` |
| B7 | 엔진 `sanitize_tts_text()`는 제어문자만 지운다. `!` `?` `(셀라)`를 건드리지 않는다. | `supertonic3_engine.py:111-123` |
| B8 | 표현 태그 차단이 없다. | 공식 API: `<laugh> <breath> <sigh>` |
| B9 | 현재 잠긴 `scene_5.wav`는 정제 전 원문 해시로 만들어졌다. 정제기를 만들어도 `--skip-existing`이면 화난 원본이 남는다. | manifest sha256 `bb20cec3...` |

### C. 자막이 사람이 읽기 좋게 안 나온다

실물 `subtitles-full-audio-aligned.ass`가 증거다.

```
불을 껐는데, 머릿속은 아직 환한
밤이 있습니다.
...
(다윗의 시. 영장으로 현악에 맞춘
노래) 내 의의 하나님이여, 내가
...
여기사 나의 기도를 들으소서 인생들아
! 어느 때까지 나의 영광을 변하여
구하겠는고 (셀라) 여호와께서 자기를
```

| # | 실측 | 파일 |
|---|---|---|
| C1 | `chunks()`가 **영어 공백 split**이다. 한국어는 `환한 / 밤이`, `내일 / 해야`, `해내지 / 않아도`처럼 어절 중간에서 끊긴다. 한 토큰이 20자를 넘으면 그대로 한 줄이 되어 화면을 넘긴다. | `build_full_audio_aligned_ass.py:28-39` |
| C2 | 2줄 `\N`이 없다. 이벤트마다 1줄. WrapStyle 0이라 넘치면 잘린다. | 같은 파일 header |
| C3 | 표제·셀라·느낌표가 자막에 그대로 있다. `chunks()`의 괄호 정규식이 현재 ASS에는 적용되지 않았거나, 생성 후 원문이 다시 들어갔다. | ASS L34-46 |
| C4 | 글자 크기 충돌: ASS 72px, `healing_caption_policy.json` 96/100, 이전 계획 108/112, `final_render_policy.json` 72, lock은 크기 없음. | 4개 파일 |
| C5 | 글자 수 충돌: lock 14~18/20, caption policy 24, HANDOFF 12, Hermes splitter 기본 12/16. | 4개 파일 |
| C6 | 시간은 장면 전체에 글자 수 비례 배분이다. 실제 절 단위 발화와 어긋난다. 시편 한 장이 52초면 자막이 음성보다 앞서거나 뒤처진다. | `build_full_audio_aligned_ass.py:42-44` |
| C7 | ASS 경로가 두 개다. `build_ass_from_cues.py`(정책 96px)와 `build_full_audio_aligned_ass.py`(하드코딩 72px). 최종 렌더는 후자를 태운다. | `render_authoritative_full.py:4` |
| C8 | `caption_split_hermes.py`도 영어 단어 분할이다. 긴 한글 어절을 `word[i:i+max]`로 자른다. | `caption_split_hermes.py:69-70` |

### D. 워크플로·문서가 파이프라인을 다시 깨뜨린다

- 프로젝트 `.grok/workflows` 없음. 본편 실행이 “어떤 스크립트를 고르느냐”에 달려 있다.
- `CLAUDE.md` 후반부가 깨진 인코딩이다. 에이전트가 잘못된 규칙을 읽는다.
- `MEDIA_RULES.md` / `manual.md`는 M4를 말하지만 `HANDOFF.md`가 M5/F3를 말해 에이전트가 HANDOFF를 따르면 보이스가 다시 바뀐다.
- `media_rules_lock.json`에 total_step, max_chunk, audio_filter, 자막 px, skip-existing 금지가 없다.
- `voice_provenance.schema.json`은 `voice, speed, pitch, source_scene_count, audio_sha256`만 있어 화난 원문 해시·필터 적용 여부를 막지 못한다.

---

## File map

**Create**

- `bible_healing/scripts/sanitize_script.py` — TTS/자막 공통 정제
- `bible_healing/scripts/subtitle_layout.py` — 한국어 2줄 분할
- `bible_healing/scripts/apply_audio_filter.py` — pitch/EQ/loudness
- `bible_healing/scripts/verify_voice_provenance.py`
- `bible_healing/scripts/verify_authoritative_audio.py`
- `bible_healing/scripts/run_full_media_pipeline.py` — 유일한 본편 오케스트레이터
- `bible_healing/tests/test_script_sanitization.py`
- `bible_healing/tests/test_subtitle_layout.py`
- `bible_healing/tests/test_voice_lock.py`
- `bible_healing/tests/test_media_rules_gate.py`

**Modify**

- `bible_healing/config/media_rules_lock.json`
- `bible_healing/config/voice_provenance.schema.json`
- `bible_healing/config/healing_caption_policy.json`
- `bible_healing/config/final_render_policy.json`
- `bible_healing/config/voice_healing.yaml`
- `modern/scripts/tts_multi_voice.py`
- `bible_healing/scripts/build_full_job.py`
- `bible_healing/scripts/build_full_audio_aligned_ass.py`
- `bible_healing/scripts/build_cues_from_manifest.py`
- `bible_healing/scripts/rebuild_authoritative_full_audio.py`
- `bible_healing/scripts/media_rules_preflight.py`
- `bible_healing/scripts/media_rules_postflight.py`
- `bible_healing/scripts/pack_to_hermes.py`
- `MEDIA_RULES.md`, `manual.md`, `CLAUDE.md`, `D_DRIVE_OUTPUT_POLICY.md`, `bible_healing/HANDOFF.md`

**Do not use as production input**

- `hermes_jobs/full/scene_*_synced.mp4`
- `hermes_jobs/full/scene_audio_manifest.prelock.*`
- `hermes_jobs/voice_smoke_*`
- `upload_package/final-ep01-full.mp4` 오디오
- `--skip-existing`로 살아남은 정제 전 WAV

---

## Interfaces

이후 태스크는 이 이름만 사용한다.

```python
# bible_healing/scripts/sanitize_script.py
from dataclasses import dataclass

@dataclass(frozen=True)
class SanitizedText:
    original: str
    tts: str
    display: str          # 화면 자막. tts와 동일 본문, 문장부호만 읽기용
    removed: list[str]    # 잘린 표제/셀라/태그

def sanitize_script(text: str) -> SanitizedText: ...
def assert_no_emotion_triggers(text: str) -> None: ...

# bible_healing/scripts/subtitle_layout.py
@dataclass(frozen=True)
class CaptionBlock:
    lines: list[str]      # 1~2개, 각 <= 20자
    text: str             # "줄1\\N줄2" 또는 한 줄

def split_korean_caption(text: str, target_min: int = 14, target_max: int = 18, hard_max: int = 20, max_lines: int = 2) -> list[CaptionBlock]: ...
def pack_two_lines(phrases: list[str]) -> list[CaptionBlock]: ...

# bible_healing/scripts/apply_audio_filter.py
def apply_scripture_filter(src: Path, dst: Path, pitch_percent: float = -8.0) -> dict: ...
```

---

### Task 1: Lock을 실제 실패 원인까지 확장하고 문서 충돌을 끊는다

**Files:**
- Modify: `bible_healing/config/media_rules_lock.json`
- Modify: `bible_healing/config/voice_provenance.schema.json`
- Modify: `bible_healing/config/healing_caption_policy.json`
- Modify: `bible_healing/config/final_render_policy.json`
- Modify: `bible_healing/HANDOFF.md`, `MEDIA_RULES.md`, `manual.md`, `CLAUDE.md`

- [ ] **Step 1: lock JSON을 아래 필드로 교체한다.** `total_step`은 Task 4 A/B 전까지 `pending_ab`로 두고, A/B 후 숫자로 고정한다.

```json
{
  "version": 2,
  "voice": {
    "narrator": {"voice": "F5", "speed": 0.95, "total_step": 8, "silence_seconds": 0.24, "audio_filter": ""},
    "scripture": {
      "voice": "M4",
      "speed": 0.72,
      "pitch": -8,
      "silence_seconds": 0.65,
      "total_step": "pending_ab",
      "total_step_candidates": [8, 10, 12],
      "forbidden_total_step": [24],
      "max_chunk_length": 90,
      "audio_filter": "asetrate=24000*0.92,aresample=24000,atempo=1.087,highpass=f=65,lowpass=f=8500,equalizer=f=250:t=q:w=1:g=1.5"
    }
  },
  "speakers": ["narrator", "scripture"],
  "tts": {
    "engine": "supertonic3",
    "skip_existing_forbidden": true,
    "require_sanitize": true,
    "require_verse_split": true,
    "forbid_expression_tags": ["<laugh>", "<breath>", "<sigh>"],
    "punctuation_to_period": ["!", "！", "!?", "❗", "?", "？"]
  },
  "captions": {
    "max_lines": 2,
    "target_chars_per_line": [14, 18],
    "max_chars_per_line": 20,
    "split_priority": ["sentence_end", "clause_end", "eojel"],
    "forbid_mid_josa": true,
    "forbid_mid_eomi": true,
    "remove_parenthetical_text": true,
    "fontName": "Malgun Gothic",
    "fontSizePx_narrator": 96,
    "fontSizePx_scripture": 100,
    "outlinePx": 6,
    "shadowPx": 3,
    "marginV_px": 90,
    "marginL_px": 100,
    "marginR_px": 100
  },
  "background": {
    "directory": "bible_healing/assets/movie-sample/pingpong-1min",
    "required_count": 12,
    "duration_seconds": 60,
    "speed": 0.333,
    "still_images_forbidden": true
  },
  "storage": {
    "final_root": "D:\\bible_healing_ep01\\final",
    "work_root": "D:\\bible_healing_ep01\\work"
  },
  "release_gates": {
    "duration_delta_seconds": 0.5,
    "require_first_caption_matches_first_script": true,
    "require_authoritative_audio": true,
    "require_no_selah_or_bang_in_ass": true,
    "require_no_mid_eojel_split": true
  }
}
```

- [ ] **Step 2: `healing_caption_policy.json`의 `maxLineChars`/`maxDisplayCharacters`를 20으로, `fontSizePx_1080p`를 96으로 맞춘다.** `final_render_policy.json`의 `font_size_1080p`도 96으로 맞춘다. 24자·72px를 남기지 않는다.

- [ ] **Step 3: `HANDOFF.md` 보이스 표를 F5/M4로 바꾸고 F3/M2/M5 줄을 삭제한다.** 상단에 “구 보이스 문서. `media_rules_lock.json`이 우선”을 적는다.

- [ ] **Step 4: `CLAUDE.md` 깨진 한글(59행 이후)을 복구하고, 작업 전 확인 목록 1번에 `media_rules_lock.json`을 넣는다.**

- [ ] **Step 5: Commit**

```powershell
git add bible_healing/config/media_rules_lock.json bible_healing/config/healing_caption_policy.json bible_healing/config/final_render_policy.json bible_healing/HANDOFF.md MEDIA_RULES.md manual.md CLAUDE.md
git commit -m "fix: lock voice/caption fields and retire F5/M5 HANDOFF"
```

---

### Task 2: 화난 억양을 만드는 입력을 테스트로 먼저 죽인다

**Files:**
- Create: `bible_healing/tests/test_script_sanitization.py`
- Create: `bible_healing/scripts/sanitize_script.py`

**Interfaces:** `sanitize_script(text) -> SanitizedText`

실측 시편 4편 원문을 fixture로 쓴다. 추상 예시만 넣지 않는다.

- [ ] **Step 1: 실패하는 테스트**

```python
from bible_healing.scripts.sanitize_script import sanitize_script, assert_no_emotion_triggers

PS4 = (
    "(다윗의 시. 영장으로 현악에 맞춘 노래) 내 의의 하나님이여, 내가 부를 때에 "
    "응답하소서 곤란 중에 나를 너그럽게 하셨사오니 나를 긍휼히 여기사 나의 기도를 "
    "들으소서 인생들아 ! 어느 때까지 나의 영광을 변하여 욕되게 하며 허사를 좋아하고 "
    "궤휼을 구하겠는고 (셀라) 여호와께서 자기를 위하여 경건한 자를 택하신 줄 너희가 "
    "알지어다"
)

def test_strips_title_and_selah():
    s = sanitize_script(PS4)
    assert "다윗의 시" not in s.tts
    assert "셀라" not in s.tts
    assert "영장" not in s.tts
    assert "다윗의 시" not in s.display
    assert "셀라" not in s.display

def test_bangs_and_questions_become_periods():
    s = sanitize_script("인생들아 ! 어디 있느뇨 ? 바라라 ！")
    assert "!" not in s.tts and "？" not in s.tts and "?" not in s.tts
    assert "인생들아." in s.tts.replace(" ", "") or "인생들아 ." in s.tts

def test_keeps_scripture_body():
    s = sanitize_script(PS4)
    assert "내 의의 하나님이여" in s.tts
    assert "알지어다" in s.tts

def test_blocks_expression_tags():
    s = sanitize_script("평안히 눕고 <laugh> 자기도 하리니")
    assert "<laugh>" not in s.tts
    assert_no_emotion_triggers(s.tts)

def test_tts_and_display_share_body():
    s = sanitize_script(PS4)
    assert s.tts.replace(".", "").replace(" ", "") == s.display.replace(".", "").replace(" ", "")
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

```powershell
pytest bible_healing/tests/test_script_sanitization.py -v
```

Expected: FAIL — `sanitize_script` 없음.

- [ ] **Step 3: 최소 구현.** `scripture_tts_prep.soften_for_speech`를 호출하지 말고 여기로 모은다. 전각/반각 괄호, `셀라`/`Selah` 단독, `다윗의 시`/`영장으로`/`현악`/`스미닛`/`마스길`/`믹담` 표제, 느낌표·물음표·표현 태그를 처리한다.

```python
BANGS = ["!?", "❗", "！", "!", "？", "?"]
PARENS = re.compile(r"\([^()]*\)|（[^（）]*）")
HEADERS = re.compile(r"(다윗의 시|고라 자손의 시|아삽의 시|영장으로|현악|스미닛|마스길|믹담|셀라|Selah)")
TAGS = re.compile(r"</?(?:laugh|breath|sigh)>", re.I)

def sanitize_script(text: str) -> SanitizedText:
    original = text or ""
    t = PARENS.sub(" ", original)
    t = TAGS.sub(" ", t)
    removed = []
    # 괄호 밖 표제/셀라도 제거
    t = HEADERS.sub(" ", t)
    for mark in BANGS:
        t = t.replace(mark, ".")
    t = re.sub(r"[.]{2,}", ".", t)
    t = re.sub(r"\s+\.", ".", t)
    t = re.sub(r"\s+", " ", t).strip()
    assert_no_emotion_triggers(t)
    return SanitizedText(original=original, tts=t, display=t, removed=removed)
```

- [ ] **Step 4: 테스트 통과 확인**

```powershell
pytest bible_healing/tests/test_script_sanitization.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add bible_healing/scripts/sanitize_script.py bible_healing/tests/test_script_sanitization.py
git commit -m "feat: sanitize scripture punctuation, titles, and selah"
```

---

### Task 3: 한국어 2줄 자막 — 사람이 읽는 단위로 자른다

**Files:**
- Create: `bible_healing/tests/test_subtitle_layout.py`
- Create: `bible_healing/scripts/subtitle_layout.py`

이 태스크가 “자막이 보기 싫다”의 본수정이다. 글자 수만 세는 영어 split을 버린다.

- [ ] **Step 1: 실패하는 테스트.** 실측 ASS에서 깨진 문장을 fixture로 쓴다.

```python
from bible_healing.scripts.subtitle_layout import split_korean_caption

def test_does_not_split_after_adjective():
    blocks = split_korean_caption("불을 껐는데, 머릿속은 아직 환한 밤이 있습니다.")
    joined = [b.text.replace(r"\N", "") for b in blocks]
    assert not any(t.endswith("환한") for t in joined)
    assert any("환한 밤이" in t or "밤이 있습니다" in t for t in joined)

def test_two_lines_max_and_hard_limit():
    blocks = split_korean_caption(
        "오늘 한 말이 자꾸 돌아오고, 내일 해야 할 일이 벌써 가슴 위에 올라와 있는 밤."
    )
    for b in blocks:
        assert len(b.lines) <= 2
        assert all(len(line) <= 20 for line in b.lines)

def test_does_not_cut_inside_eomi():
    blocks = split_korean_caption("지금은 무언가를 해내지 않아도 됩니다.")
    flat = " ".join(b.text.replace(r"\N", " ") for b in blocks)
    assert "해내지 않아도" in flat
    assert "해내지" not in [b.lines[0] for b in blocks if b.lines[0] == "해내지"]

def test_strips_then_layouts_scripture():
    from bible_healing.scripts.sanitize_script import sanitize_script
    text = sanitize_script("(다윗의 시) 내 의의 하나님이여, 내가 부를 때에 응답하소서").display
    blocks = split_korean_caption(text)
    assert all("(" not in b.text and "다윗" not in b.text for b in blocks)

def test_packs_two_short_phrases_with_n():
    blocks = split_korean_caption("그건 당신이 약해서가 아닙니다.")
    # 한 문장이 20자 이하면 1줄, 넘으면 2줄 \N
    assert all(len(b.lines) in (1, 2) for b in blocks)
```

분할 우선순위 (구현이 이 순서를 지켜야 한다):

1. `. ? ! 。` 문장 끝 (정제한 뒤에는 `.`)
2. `,` `，` 절 끝
3. 어절(공백) 끝
4. 조사 앞이 아니라 **조사·어미를 앞 어절에 붙인 채** 자른다. `은/는/이/가/을/를/에/에서/으로/로/와/과/도/만/부터/까지/께서/이여/여`
5. 그래도 20자를 넘으면 뒤 어절을 다음 줄로. 어절 하나를 절대 `s[i:i+20]`으로 자르지 않는다. 불가피하면 그 어절만 예외로 다음 블록에 단독 배치하고 테스트에 남긴다.

- [ ] **Step 2: 테스트 실패 확인**

```powershell
pytest bible_healing/tests/test_subtitle_layout.py -v
```

- [ ] **Step 3: `split_korean_caption` 구현.** `caption_split_hermes.split_text`를 재사용하지 않는다.

- [ ] **Step 4: 테스트 통과 확인**

- [ ] **Step 5: Commit**

```powershell
git add bible_healing/scripts/subtitle_layout.py bible_healing/tests/test_subtitle_layout.py
git commit -m "feat: Korean eojel-aware two-line captions"
```

---

### Task 4: TTS가 lock을 강제하고, 절 단위로 합성하고, 필터를 실제로 건다

**Files:**
- Modify: `modern/scripts/tts_multi_voice.py`
- Modify: `bible_healing/scripts/build_full_job.py`
- Modify: `bible_healing/scripts/pack_to_hermes.py`
- Create: `bible_healing/scripts/apply_audio_filter.py`
- Create: `bible_healing/scripts/verify_voice_provenance.py`
- Test: `bible_healing/tests/test_voice_lock.py`

**Consumes:** `sanitize_script`, lock JSON
**Produces:** scene WAV + `reports/tts_provenance.json`

- [ ] **Step 1: 실패하는 테스트**

```python
def test_build_full_job_copies_audio_filter(tmp_path, monkeypatch):
    # build_full_job.spk("scripture")["audio_filter"] must equal yaml filter, not ""
    ...

def test_run_job_rejects_non_m4(tmp_path):
    # voice_map scripture voice M5 -> SystemExit

def test_run_job_rejects_skip_existing_when_lock_forbids():
    ...

def test_scripture_is_split_under_90_chars():
    # after sanitize+split, every synthesize text_len <= 90
    ...
```

- [ ] **Step 2: `build_full_job.py`에서 `audio_filter: ""`와 notes `F5/M5`를 삭제한다.** yaml 값을 그대로 넣는다. `pack_to_hermes.py`와 동일.

- [ ] **Step 3: `tts_multi_voice.py` 변경**

1. lock을 읽고 narrator/scripture voice·speed가 다르면 `SystemExit`.
2. `--skip-existing`는 lock `skip_existing_forbidden`이면 즉시 실패.
3. 각 segment에 `sanitize_script(text).tts`만 넘긴다. 빈 문자열이면 스킵하지 말고 장면 실패.
4. scripture는 `scripture_tts_prep.split_into_speech_units(sanitized, max_len=90)`로 나눈 뒤 조각마다 합성. 엔진 `max_chunk_length`도 90.
5. scripture WAV에 `apply_scripture_filter()` 적용. asetrate로 -8% 피치 후 atempo로 길이 보정.
6. 조각 사이 무음은 `silence_duration`(0.65). 장면 concat gap도 scripture면 0.65.
7. 각 조각 provenance: `speaker, voice, speed, total_step, max_chunk, text, text_sha256, wav_sha256, filter_applied`.
8. `?` `!`가 남은 텍스트는 합성 전에 `assert_no_emotion_triggers`로 실패.

- [ ] **Step 4: total_step A/B (본편 전에 필수).** 같은 정제 문장 `내 영혼아. 네가 어찌하여 낙망하며 어찌하여 내 속에서 불안하여 하는고.` 로 M4 / 0.72 / silence 0.65 / filter on, step 8·10·12를 `runs/ep01_anxious_night/voice_ab/step_ab/`에 만든다. **화난 억양이 가장 적은 값을 lock `total_step`에 숫자로 기록한다.** 24는 후보가 아니다.

- [ ] **Step 5: 테스트 통과 후 Commit**

```powershell
git commit -m "fix: force M4 lock, verse-level TTS, and pitch filter"
```

---

### Task 5: 기존 화난 음성을 버리고 authoritative 오디오를 다시 만든다

**Files:**
- Modify: `bible_healing/scripts/rebuild_authoritative_full_audio.py`
- Create: `bible_healing/scripts/verify_authoritative_audio.py`

- [ ] **Step 1: `verify_authoritative_audio.py`가 아래를 실패시키게 먼저 짠다.**

- `scene_*.wav` 개수 != `scenes.json` 장면 수
- provenance 없는 WAV
- scripture WAV의 voice != M4 또는 filter_applied != true
- 텍스트 해시에 `!` 원문이 남아 있음
- 경로에 `synced.mp4`, `upload_package`, `prelock`, `audio_partial` 포함

- [ ] **Step 2: rebuild는 verify를 통과한 WAV만 concat한다.** 110개 하드코딩을 장면 수로 바꾼다.

- [ ] **Step 3: 본편 TTS를 skip-existing 없이 재실행한 뒤에만 rebuild한다.** 기존 `scene_5.wav`(원문 `인생들아 !` 해시)는 `audio_pre_sanitize_backup_20260813/`로 옮긴다.

- [ ] **Step 4: Commit**

```powershell
git commit -m "fix: rebuild authoritative audio only from sanitized M4 wavs"
```

---

### Task 6: 자막 생성 경로를 하나로 고정한다

**Files:**
- Modify: `bible_healing/scripts/build_full_audio_aligned_ass.py`
- Modify: `bible_healing/scripts/build_cues_from_manifest.py`
- Modify: `bible_healing/scripts/build_ass_from_cues.py`

- [ ] **Step 1: `build_full_audio_aligned_ass.py`의 `chunks()`를 삭제하고 `sanitize_script` + `split_korean_caption`을 쓴다.**

타이밍: 장면 전체에 글자 수 비례가 아니라, TTS provenance의 **조각 duration**에 맞춰 배분한다. provenance가 있으면 조각 시작~끝에만 그 조각 자막을 넣는다. 없으면 장면 duration을 조각 글자 수 비율로 나누되 테스트로 drift 0.5초를 검사한다.

- [ ] **Step 2: ASS 헤더를 lock 타이포에서만 만든다.** 72px 하드코딩 삭제. `\N` 사용. Scripture/Narrator 스타일 크기 96/100.

- [ ] **Step 3: 생성된 ASS QA**

- `다윗의 시|셀라|영장|\(` 매치 시 실패
- `!` 매치 시 실패
- 한 Dialogue 텍스트에서 `\N` 포함 줄이 2 초과면 실패
- `\N` 제거 후 각 줄 20자 초과면 실패
- 이벤트 시간이 역전이면 실패

- [ ] **Step 4: `build_cues_from_manifest.py`도 같은 splitter를 쓴다.** Hermes 영어 split을 본편 경로에서 제거한다.

- [ ] **Step 5: Commit**

```powershell
git commit -m "fix: single Korean caption path with two-line ASS"
```

---

### Task 7: 게이트를 범용으로 고치고 회귀를 잠근다

**Files:**
- Modify: `bible_healing/scripts/media_rules_preflight.py`
- Modify: `bible_healing/scripts/media_rules_postflight.py`
- Create: `bible_healing/tests/test_media_rules_gate.py`

현재 preflight/postflight는 경로가 박힌 일회용이다. `--job`과 lock을 받게 바꾼다.

- [ ] **Step 1: preflight 실패 케이스**

- voice F3/M3/M5, speed 0.78/0.85
- `audio_filter` 빈 scripture
- `total_step == 24`
- `max_chunk_length > 90`
- 대본/ASS에 `!` `(셀라)` `다윗의 시`
- `--skip-existing` 플래그가 잡 리포트에 있음
- provenance 없음
- 출력 루트가 D:가 아님

- [ ] **Step 2: postflight 실패 케이스**

- H264/AAC 없음, moov 없음
- 첫 자막 != 첫 대본 sanitized (현재 “불을 껐는데”)
- ASS 마지막 시각과 오디오 길이 차이 > 0.5s
- ASS에 표제/셀라/`!`
- 한 줄 20자 초과

- [ ] **Step 3: `final_render_preflight.py`가 가리키는 `actual_first3min_pause_split`를 본편 경로로 바꾸거나, 본편은 `media_rules_preflight.py`만 쓰도록 `CLAUDE.md`를 고친다.**

- [ ] **Step 4: Commit**

```powershell
git commit -m "test: gate stale voices, angry punctuation, and bad captions"
```

---

### Task 8: 본편은 오케스트레이터 한 길로만 실행한다

**Files:**
- Create: `bible_healing/scripts/run_full_media_pipeline.py`

워크플로 파일이 없어서 에이전트가 예전 렌더를 고른다. 이 스크립트가 유일한 본편 진입점이다.

순서 (중간 실패 시 다음 단계 금지):

1. `media_rules_preflight.py --job <full>`
2. `build_full_job.py` (filter 포함 voice_map 재기록)
3. `tts_multi_voice.py --job <full>`  (skip-existing 없음)
4. `verify_voice_provenance.py`
5. `rebuild_authoritative_full_audio.py`
6. `verify_authoritative_audio.py`
7. `build_full_audio_aligned_ass.py`
8. ASS QA (셀라/`!`/20자)
9. `render_authoritative_full.py` → `D:\bible_healing_ep01\final\...`
10. `media_rules_postflight.py <mp4>`

- [ ] **Step 1: 스크립트가 1~10을 subprocess로 실행하고 각 단계 JSON 리포트를 `D:\bible_healing_ep01\work\pipeline\`에 남긴다.**

- [ ] **Step 2: README/`HANDOFF.md`의 본편 명령을 이 스크립트 한 줄로 교체한다.**

```powershell
python bible_healing/scripts/run_full_media_pipeline.py --job bible_healing/runs/ep01_anxious_night/hermes_jobs/full
```

- [ ] **Step 3: Commit**

```powershell
git commit -m "feat: single full-media pipeline entrypoint"
```

---

## Acceptance criteria

청취·화면 기준. 설정만 맞으면 통과가 아니다.

- [ ] 새 provenance에 scripture=M4, speed=0.72, pitch=-8, silence=0.65, filter_applied=true, total_step∈{8,10,12}, max_chunk≤90.
- [ ] 시편 4편 음성에 `(다윗의 시)`, `(셀라)`, `인생들아 !`가 들리지 않는다.
- [ ] `내 영혼아` 다음 억양이 올라가지 않는다. 같은 문장을 step A/B 샘플과 비교해 승인한다.
- [ ] 한 에피소드 안에서 narrator/scripture 보이스 ID가 바뀌지 않는다. skip-existing으로 옛 WAV가 섞이지 않는다.
- [ ] ASS에 `셀라`, `다윗의 시`, `!`, 20자 초과 줄, 어절 중간 절단(`환한`/`밤이`, `해내지` 단독)이 없다.
- [ ] 자막은 최대 2줄, `\N`, 96/100px, 첫 줄 “불을 껐는데”가 첫 음성과 같다.
- [ ] 최종 MP4는 D:에만 있고, 오디오는 새로 만든 authoritative WAV다.
- [ ] `HANDOFF.md`에 M5/F3/M2가 없다.

## 구현 순서

Task 1 → 2 → 3 → 4(A/B 포함) → 5 → 6 → 7 → 8.

2·3은 코드만으로 끝나므로 먼저 잠근다. 4의 A/B 없이 본편 TTS를 돌리지 않는다. 5는 4의 새 WAV 없이 실행하지 않는다.

## 명시적으로 하지 않는 것

- SuperTonic 커스텀 `voice_style_path` 학습. 지금은 정제·청크·필터로 억양을 잡는다. A/B 실패 시에만 후속 계획.
- 자막 자동 축소(폰트 스케일). 길면 줄을 나눈다.
- 과거 M5 본편 재인코딩.
- Hermes 영어 캡션 알고리즘을 본편에 유지.
)
