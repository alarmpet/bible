# scripts.md — 검증 코드 (현대 v12)

챕터 후 `check_chapter_lite`. 합본 후 `check_final_modern`.  
등급: **BLOCK** = 즉시 1회 보정 / **WARN** = 기록·선택 수정 / 문체 = 측정만.

## 분량 티어 v2

단일 진실 원천은 `config/duration_matrix.yaml`이다. 기본은 `standard` 25~45분이며 100분은 `special` 또는 `anthology` 승인 대상이다.

| 키 | 분 | 구조 |
|---|---:|---|
| quick | 15~25 | 한 관계·한 선택 |
| standard | 25~45 | 주 플롯 + 얕은 보조선 |
| deep | 45~70 | 독립 욕망 보조선 1~2개 |
| special | 80~120 | 승인된 대형 단일 이야기 |
| anthology | 총 80~120 | 25~35분 이야기 3편 |

문자 수 바닥을 맞추기 위한 자동 패딩은 금지한다. `require_story_material(text, minimum_chars)`가 부족하면 `INSUFFICIENT_STORY_MATERIAL`을 발생시킨다.

```python
from modern.story_quality import duration_bounds, load_yaml

config = load_yaml("modern/config/duration_matrix.yaml")
minutes = duration_bounds(config, "standard")  # (25, 45)
```

## 공통 유틸

```python
import re
from collections import Counter

def split_lines(text):
    return [l.strip() for l in text.split("\n") if l.strip()]

def is_dialogue(line):
    return line.startswith('"') or line.startswith("\u201c")

def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]

def get_narration_only(text):
    return [l for l in split_lines(text) if not is_dialogue(l)]

def char_count(text):
    return len(text)
```

## BLOCK: 허구 고지

```python
FICTION_MARKERS = [
    "실제 인물·기관·사건과 무관한 창작물",
    "실제 인물·기관·사건과 무관",
    "허구 고지",
]

def check_fiction_disclaimer(*docs: str):
    blob = "\n".join(docs)
    ok = any(m in blob for m in FICTION_MARKERS)
    return (ok, [] if ok else ["BLOCK: 허구 고지 누락"])
```

## BLOCK/WARN: 사극 시대 누수

```python
ERA_BANNED = [
    r"대감", r"마님", r"아씨", r"소저", r"원님", r"사또", r"나으리",
    r"전하", r"상감", r"중전", r"한양", r"관아", r"포도청", r"사약",
    r"유배", r"과거\s*급제", r"어사", r"노비", r"머슴", r"기생",
    r"상투", r"\b갓\b", r"도포", r"저고리", r"치맛자락", r"가마",
    r"옛날\s*옛적", r"옛적", r"하옵", r"이옵", r"사옵", r"느니라",
    r"옥패", r"어명", r"주상",
]

# 허용: <!-- era_allow --> ... <!-- /era_allow --> 또는 [era_allow]...[/era_allow]
ALLOW_BLOCK = re.compile(
    r"<!--\s*era_allow\s*-->.*?<!--\s*/era_allow\s*-->|\[era_allow\].*?\[/era_allow\]",
    re.S | re.I,
)

def strip_era_allow(text: str) -> str:
    return ALLOW_BLOCK.sub(" ", text)

def check_era_leak(text: str):
    body = strip_era_allow(text)
    hits = []
    for p in ERA_BANNED:
        for m in re.finditer(p, body):
            hits.append(m.group(0))
    # 나레이션 위주 경고; 대사 안 사극 어휘도 기본 WARN
    if not hits:
        return (True, [], "OK")
    return (False, hits[:20], "WARN")  # 스모크에선 수정 권고. 다수면 사용자 보고
```

## WARN: 현대 앵커 (몰아넣기 방지)

```python
def check_modern_anchor(intro_and_ch1: str):
    """첫 구간에서 연도/지명/직업 신호가 있는지, 한 문장에 과밀하지 않은지."""
    year = bool(re.search(r"20\d{2}년|\d{2}년\s*(겨울|봄|여름|가을)", intro_and_ch1))
    place = bool(re.search(
        r"(서울|부산|인천|대구|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주|"
        r"아파트|병원|회사|편의점|고시원|공장|학교|구청|경찰서|요양)",
        intro_and_ch1,
    ))
    job = bool(re.search(
        r"(직원|간호사|기사|사장|과장|보호사|교사|형사|기자|알바|계약직|의사|변호사)",
        intro_and_ch1,
    ))
    warnings = []
    if not (year or place):
        warnings.append("WARN: 첫 구간에 연도·장소 앵커 약함")
    if not job:
        warnings.append("WARN: 첫 구간에 직업·역할 신호 약함")
    # 몰아넣기: 연도+지명+직업+금액/시각 등이 한 짧은 문장에 겹칠 때만
    for s in split_sentences(intro_and_ch1):
        if len(s) >= 100:
            continue
        has_year = bool(re.search(r"20\d{2}", s))
        has_place = bool(re.search(r"[가-힣]+(구|동|시|군)", s))
        has_job = bool(re.search(r"(직원|간호사|사장|기사|과장|보호사|교사|형사)", s))
        has_extra = bool(re.search(r"\d+\s*(억|만\s*원|원|층|호|시\s*\d|:\d{2})", s))
        if has_year and has_place and has_job and has_extra:
            warnings.append(f"WARN: 앵커 몰아넣기 의심: {s[:40]}...")
            break
    return (len(warnings) == 0, warnings)
```

## WARN~BLOCK: 증거 회수

```python
def check_proof_payoff(text: str, evidence_rows: list[dict]):
    """
    evidence_rows: {name, function_setup, function_pressure, function_payoff, is_core}
    function_* 는 본문 등장 여부 bool (작성기/수동 태깅).
    """
    warns, blocks = [], []
    for e in evidence_rows:
        name = e.get("name", "")
        if name and name not in text:
            msg = f"증거 '{name}' 본문 미등장"
            (blocks if e.get("is_core") else warns).append(msg)
            continue
        funcs = [e.get("function_setup"), e.get("function_pressure"), e.get("function_payoff")]
        if e.get("is_core") and not e.get("function_payoff"):
            blocks.append(f"BLOCK: 핵심 증거 '{name}' 회수(페이오프) 없음")
        elif e.get("is_core") and sum(bool(x) for x in funcs) < 2:
            warns.append(f"WARN: 핵심 증거 '{name}' 설정·압박·회수 분화 부족")
    ok = len(blocks) == 0
    return (ok, blocks, warns)
```

## WARN: 인물 의사결정 샘플 (말버릇 키워드 대체)

```python
def check_decision_voice_sample(notes: str):
    """
    자동 완전자단 어려움 → 작성 후 체크리스트 문자열 검사.
    notes에 'P1_scene', 'P2_scene' 등 수동 확인 마크 권장.
    """
    if "VOICES_OK" in notes:
        return (True, [])
    return (True, ["WARN: 주요 3인 의사결정 패턴 2장면 샘플 수동 확인 필요"])
```

## 기존 경량 검사 (유지)

```python
def check_hanja(text):
    m = re.findall(r"[\u4e00-\u9fff]", text)
    return (len(m) == 0, m)

def check_quotes_balanced(text):
    # 간단: 한국어 기본 따옴표 쌍
    c = text.count("\u201c") - text.count("\u201d")
    d = text.count('"') % 2
    ok = c == 0 and d == 0
    return (ok, [] if ok else ["따옴표 짝 불일치"])

def remove_meta(text):
    patterns = [
        r"^\[.*?\]\s*\w*$",
        r"^챕터\s*\d+.*$",
        r"^제\s*\d+\s*장.*$",
        r"^---+$",
        r"^\*\*\*+$",
    ]
    out = []
    for line in text.split("\n"):
        if not any(re.match(p, line.strip()) for p in patterns):
            out.append(line)
    t = "\n".join(out)
    return re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", "", t)

def check_dialogue_ratio(text):
    dialogues = re.findall(r"\u201c[^\u201d]+\u201d|\"[^\"]+\"", text)
    ratio = sum(len(d) for d in dialogues) / max(len(text), 1)
    # 측정만
    return (True, [f"MEASURE: 대사 비중 {ratio*100:.1f}% (목표 40%, 참고 35%+)"])
```

## 챕터 라이트

```python
def check_chapter_lite(text, target_chars, tier="normal"):
    floor = DURATION_TIERS[tier]["chapter_floor"]
    tol = DURATION_TIERS[tier]["chapter_tolerance"]
    n = char_count(text)
    issues = []
    blocks = []
    if n < floor:
        issues.append(f"글자수 {n} < 바닥 {floor}")
    if target_chars and abs(n - target_chars) / target_chars > tol and n >= floor:
        issues.append(f"WARN: 목표 {target_chars} 대비 {n}")
    ok_h, han = check_hanja(text)
    if not ok_h:
        blocks.append(f"한자: {han[:5]}")
    ok_q, qiss = check_quotes_balanced(text)
    if not ok_q:
        blocks.append(qiss[0])
    ok_e, ehits, _ = check_era_leak(text)
    warns = [] if ok_e else [f"era_leak: {ehits[:8]}"]
    ok = len(blocks) == 0 and n >= floor
    return (ok, blocks, issues + warns)
```

## 합본 현대

```python
def check_final_modern(
    merged_text: str,
    contract_text: str,
    evidence_rows: list,
    target_chars: int,
    tier: str = "normal",
    voice_notes: str = "",
):
    blocks, warns, measures = [], [], []

    ok_f, f_iss = check_fiction_disclaimer(contract_text, merged_text[:2000])
    if not ok_f:
        blocks.extend(f_iss)

    ok_e, ehits, _ = check_era_leak(merged_text)
    if not ok_e:
        warns.append(f"era_leak {len(ehits)}건: {ehits[:10]}")

    ok_p, p_blocks, p_warns = check_proof_payoff(merged_text, evidence_rows)
    blocks.extend(p_blocks)
    warns.extend(p_warns)

    _, v_warns = check_decision_voice_sample(voice_notes)
    warns.extend(v_warns)

    _, m_ratio = check_dialogue_ratio(merged_text)
    measures.extend(m_ratio)

    n = char_count(merged_text)
    floor = int(target_chars * DURATION_TIERS[tier]["final_floor_ratio"])
    if n < floor:
        blocks.append(f"합본 글자수 {n} < 바닥 {floor}")

    # 고정 마무리
    ending = (
        "다음 영상을 빠르게 만나보시려면 좋아요와 구독을 눌러주세요."
    )
    if ending not in merged_text:
        warns.append("WARN: 고정 마무리 멘트 불일치/누락")

    return {
        "ok": len(blocks) == 0,
        "blocks": blocks,
        "warns": warns,
        "measures": measures,
        "chars": n,
    }
```

## v2 합본 QA CLI

```powershell
python modern/scripts/audit_story_quality.py --text modern/runs/<id>/final.txt --contract modern/runs/<id>/project_contract.yaml --output modern/runs/<id>/qa_report.json
```

- 종료코드 `0`: BLOCK 없음
- 종료코드 `2`: 반복문장·실화성·공개 문구·분량 계약 중 하나 이상 BLOCK
- 정확 반복은 비대사 문장 3회부터 차단하며 의도된 후렴은 계약의 `filler_allowlist`에 사유와 함께 등록한다.
- `TRUE_VERIFIED`와 `TRUE_PERMISSIONED`는 승인된 source packet 없이는 통과하지 않는다.
- 주제 카드·포트폴리오·단서 검사는 `validate_topic_cards`, `audit_portfolio`, `validate_clue_ledger`를 사용한다.

## 실행 원칙

1. BLOCK만 자동 1회 보정. 2회 재작성 금지.  
2. WARN·MEASURE는 보고 후 진행 가능.  
3. 레거시 `대본 sonnet/scripts.md`의 세부 TTS 검사는 합본에서 **선택 호출**(토큰 여유 시).
