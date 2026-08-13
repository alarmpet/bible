# -*- coding: utf-8 -*-
"""Build shot_plan.json for a modern run. Source of truth for packer."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from paths import MODERN_ROOT, run_dir

# Fixed image map for smoke_g1 (order 1..40). Skip 01b alternate.
SMOKE_G1_IMAGES = [
    ("ch1_s01", 1, 1, "images/ch1/ch1_01_meeting_line.jpg", "인트로 퇴사 권고 대사"),
    ("ch1_s02", 1, 2, "images/ch1/ch1_02_fluorescent.jpg", "형광등 깜빡"),
    ("ch1_s03", 1, 3, "images/ch1/ch1_03_envelope_pen.jpg", "봉투와 볼펜"),
    ("ch1_s04", 1, 4, "images/ch1/ch1_04_envelope_hand.jpg", "손이 봉투 모서리"),
    ("ch1_s05", 1, 5, "images/ch1/ch1_05_usb_hook.jpg", "USB 훅"),
    ("ch1_s06", 1, 6, "images/ch1/ch1_06_company_exterior.jpg", "한빛물산 외관"),
    ("ch1_s07", 1, 7, "images/ch1/ch1_07_youjin_intro.jpg", "유진 소개"),
    ("ch1_s08", 1, 8, "images/ch1/ch1_08_desk_monitor.jpg", "모니터와 USB 습관"),
    ("ch1_s09", 1, 9, "images/ch1/ch1_09_gyeongho_late.jpg", "경호 야근 물음"),
    ("ch1_s10", 1, 10, "images/ch1/ch1_10_numbers_habit.jpg", "일단 숫자부터"),
    ("ch1_s11", 1, 11, "images/ch1/ch1_11_partition_siwoo.jpg", "시우 칸막이 동해패키지"),
    ("ch1_s12", 1, 12, "images/ch1/ch1_12_corridor_gicheol.jpg", "기철 복도 서로 좋게"),
    ("ch1_s13", 1, 13, "images/ch1/ch1_13_pen_monitor.jpg", "동해 펜 톡톡"),
    ("ch1_s14", 1, 14, "images/ch1/ch1_14_usb_habit.jpg", "USB 받침 습관"),
    ("ch1_s15", 1, 15, "images/ch1/ch1_15_theme_ramen.jpg", "주제 대사 라면"),
    ("ch1_s16", 1, 16, "images/ch1/ch1_16_input_only.jpg", "입력만 정리"),
    ("ch2_s01", 2, 17, "images/ch2/ch2_01_excel.jpg", "엑셀 이상 누적"),
    ("ch2_s02", 2, 18, "images/ch2/ch2_02_error_mail.jpg", "오류 공문 메일"),
    ("ch2_s03", 2, 19, "images/ch2/ch2_03_resignation.jpg", "퇴사 권고 재대면"),
    ("ch2_s04", 2, 20, "images/ch2/ch2_04_recording.jpg", "녹음 앱"),
    ("ch2_s05", 2, 21, "images/ch2/ch2_05_threat.jpg", "협박 톤 정리"),
    ("ch2_s06", 2, 22, "images/ch2/ch2_06_bus.jpg", "버스 녹취 확인"),
    ("ch3_s01", 3, 23, "images/ch3/ch3_01_two_envelopes.jpg", "합의 두 봉투"),
    ("ch3_s02", 3, 24, "images/ch3/ch3_02_family_threat.jpg", "가족 병원 언급"),
    ("ch3_s03", 3, 25, "images/ch3/ch3_03_convenience.jpg", "편의점 결심"),
    ("ch3_s04", 3, 26, "images/ch3/ch3_04_usb_night.jpg", "야간 USB 회수"),
    ("ch3_s05", 3, 27, "images/ch3/ch3_05_cabinet.jpg", "캐비닛 바인더"),
    ("ch3_s06", 3, 28, "images/ch3/ch3_06_photo_docs.jpg", "서류 사진"),
    ("ch4_s01", 4, 29, "images/ch4/ch4_01_timeline_papers.jpg", "추적 표 작업"),
    ("ch4_s02", 4, 30, "images/ch4/ch4_02_cafe.jpg", "시우 카페 회유"),
    ("ch4_s03", 4, 31, "images/ch4/ch4_03_dining.jpg", "합의금 룸 미끼"),
    ("ch4_s04", 4, 32, "images/ch4/ch4_04_reject_text.jpg", "거절 문자"),
    ("ch4_s05", 4, 33, "images/ch4/ch4_05_family_threat.jpg", "가족 협박 강화"),
    ("ch4_s06", 4, 34, "images/ch4/ch4_06_rooftop.jpg", "옥상 USB"),
    ("ch5_s01", 5, 35, "images/ch5/ch5_01_usb_crisis.jpg", "USB 위기 복구"),
    ("ch5_s02", 5, 36, "images/ch5/ch5_02_timeline.jpg", "타임라인 재구성"),
    ("ch5_s03", 5, 37, "images/ch5/ch5_03_inquiry_table.jpg", "조회 테이블"),
    ("ch5_s04", 5, 38, "images/ch5/ch5_04_phone_reveal.jpg", "녹취 재생"),
    ("ch5_s05", 5, 39, "images/ch5/ch5_05_testimony.jpg", "경호 진술 시우 실토"),
    ("ch5_s06", 5, 40, "images/ch5/ch5_06_ending.jpg", "엔딩 편의점"),
]


def split_units(text: str) -> list[str]:
    """Split into narration/dialogue-ish units without mid-quote cuts."""
    text = text.replace("\r\n", "\n").strip()
    # Keep quoted lines as units; split other prose by sentence end.
    units: list[str] = []
    buf = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        # skip subscribe CTA for TTS body
        if "구독과 좋아요" in line or "지금부터 그 이야기" in line:
            continue
        if line.startswith('"') or line.startswith("\u201c") or line.startswith("'") or line.startswith("‘"):
            if buf:
                units.append(" ".join(buf).strip())
                buf = []
            units.append(line)
            continue
        buf.append(line)
        if re.search(r"[.!?다요죠음]\s*$", line) or len(" ".join(buf)) > 90:
            units.append(" ".join(buf).strip())
            buf = []
    if buf:
        units.append(" ".join(buf).strip())
    return [u for u in units if u]


def load_chapter_units(rd: Path) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for i in range(1, 6):
        p = rd / f"chapter_{i}.txt"
        if p.exists():
            out[i] = split_units(p.read_text(encoding="utf-8"))
        else:
            out[i] = []
    return out


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?다요죠음])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def assign_narration(units: list[str], n_shots: int, high_density: bool = False) -> list[str]:
    """Assign chapter units to n_shots by boundary-preserving pack, not blind equal split.

    high_density (ch1): prefer ~1 short unit per shot; expand units by sentence if needed.
    """
    if not units:
        return [""] * n_shots
    if n_shots == 1:
        return [" ".join(units)]

    # Flatten to smaller pieces for dense chapters
    pieces: list[str] = []
    for u in units:
        if high_density and len(u) > 70 and not (u.startswith('"') or u.startswith("“") or u.startswith("‘")):
            pieces.extend(split_sentences(u) or [u])
        else:
            pieces.append(u)

    if high_density and len(pieces) >= n_shots:
        # sequential 1-ish: first n_shots-1 get one piece each; last gets remainder (trimmed)
        out = []
        for i in range(n_shots - 1):
            out.append(pieces[i])
        rest = pieces[n_shots - 1 :]
        # pack remainder into last shot but keep under ~100 by taking few sentences
        last = []
        for r in rest:
            if sum(len(x) for x in last) + len(r) > 100 and last:
                break
            last.append(r)
        if not last:
            last = [pieces[n_shots - 1]]
        out.append(" ".join(last))
        return out

    # event density (ch2+): sample evenly along chapter timeline.
    # Do NOT dump remainder into the last shot (that produced 3k+ char dumps).
    max_chars = 120
    if len(pieces) <= n_shots:
        out = list(pieces) + [""] * (n_shots - len(pieces))
        # fill empties from nearest prior piece
        for i in range(n_shots):
            if not out[i]:
                out[i] = out[i - 1] if i else (pieces[0] if pieces else "")
        return [str(x)[:max_chars] for x in out]

    out: list[str] = []
    for i in range(n_shots):
        start = int(i * len(pieces) / n_shots)
        end = max(start + 1, int((i + 1) * len(pieces) / n_shots))
        chunk = pieces[start:end]
        picked: list[str] = []
        for u in chunk:
            if picked and sum(len(x) for x in picked) + len(u) + 1 > max_chars:
                break
            picked.append(u)
        if not picked:
            picked = [chunk[0][:max_chars]] if chunk else [""]
        text = " ".join(picked).strip()
        if len(text) > max_chars + 40:
            # hard cap without mid-quote if possible
            text = text[:max_chars].rsplit(" ", 1)[0] or text[:max_chars]
        out.append(text)
    return out


# Fixed dialogue patterns (generic + smoke_g1). Never default all quotes to youjin.
_DIALOGUE_SPEAKER_HINTS: list[tuple[str, tuple[str, ...]]] = [
    ("gicheol", ("정리합시다", "서로 좋게", "서명만", "입력만 하세요", "큰 줄만", "이번 달 안으로 정리", "경력에 흠")),
    ("siwoo", ("페이퍼상", "지금은 속도", "표시는 나중에", "영업 확인", "한 씨 계정", "빠르게 넣어")),
    ("gyeongho", ("잘 몰라", "몸이 먼저", "점심은 챙겨", "형광등 오른쪽", "어제 야근", "나는 말 못")),
    ("youjin", ("숫자부터", "맞추고 싶", "잘 부탁", "거래처 코드", "동해", "표시해 둘", "억울", "엄마", "어머니")),
]


def _speaker_from_context(before: str, after: str, quote: str) -> str:
    """Infer dialogue speaker from nearby narration + line content. No silent youjin default."""
    window = f"{before[-80:]} {after[:80]}"
    q = quote or ""

    # Post-attribution: "…물었습니다" after quote often names speaker before verb.
    if re.search(r"(기철|대표).{0,12}(말|덧붙|웃)", window) or re.search(
        r"(말|웃|덧붙).{0,8}(기철|대표)", window
    ):
        return "gicheol"
    if re.search(r"(경호|대리).{0,12}(물|말|으쓱)", window) or "박경호" in window:
        return "gyeongho"
    if re.search(r"(시우|과장).{0,12}(말|내밀|소리)", window) or "이시우" in window:
        return "siwoo"
    if re.search(r"(유진|한유진).{0,12}(말|대답|고개)", window):
        return "youjin"

    # Pre-attribution in the 40 chars before quote
    pre40 = before[-40:]
    if any(k in pre40 for k in ("대표", "기철", "송기철")):
        return "gicheol"
    if any(k in pre40 for k in ("경호", "대리", "박경호")):
        return "gyeongho"
    if any(k in pre40 for k in ("시우", "과장", "이시우")):
        return "siwoo"
    if any(k in pre40 for k in ("유진", "한유진")):
        return "youjin"

    # Line content lexicon (strong phrases)
    for sid, keys in _DIALOGUE_SPEAKER_HINTS:
        if any(k in q for k in keys):
            return sid

    # Address patterns: "한 씨" is usually spoken TO youjin by others — not youjin herself.
    if "한 씨" in q or "한씨" in q:
        if any(k in q for k in ("페이퍼", "입력", "속도", "정리", "서명", "마감")):
            if "페이퍼" in q or "속도" in q or "입력" in q:
                return "siwoo"
            return "gicheol"
        return "gyeongho"

    # HR-ish lines without name → leave unknown for refine / narrator fallback
    if any(k in q for k in ("창가", "정수기", "휴지", "창고 옆")):
        return "narrator"  # staff; no dedicated voice — keep as narrator read

    return "unknown"


def guess_segments(text: str) -> list[dict]:
    """Split into narrator vs dialogue segments. Never force all quotes to youjin."""
    segs: list[dict] = []
    idx = 0
    for m in re.finditer(r'"([^"]+)"|“([^”]+)”|‘([^’]+)’', text):
        start, end = m.span()
        pre = text[idx:start].strip()
        if pre:
            segs.append({"speaker": "narrator", "text": pre})
        q = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        after = text[end : end + 100]
        speaker = _speaker_from_context(text[max(0, start - 100) : start], after, q)
        # unknown dialogue: keep tagged unknown so QA can block; TTS maps unknown→narrator
        if speaker == "unknown":
            segs.append({"speaker": "unknown", "text": q, "needs_speaker_review": True})
        else:
            segs.append({"speaker": speaker, "text": q})
        idx = end
    tail = text[idx:].strip()
    if tail:
        segs.append({"speaker": "narrator", "text": tail})
    if not segs and text.strip():
        segs = [{"speaker": "narrator", "text": text.strip()}]
    return [s for s in segs if s.get("text")]


def build_smoke_g1(rd: Path) -> dict:
    chapters = load_chapter_units(rd)
    # per-chapter shot counts
    ch_shots = {1: 16, 2: 6, 3: 6, 4: 6, 5: 6}
    narr_by_ch = {
        ch: assign_narration(chapters.get(ch, []), n, high_density=(ch == 1))
        for ch, n in ch_shots.items()
    }
    shots = []
    local_idx = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for scene_id, ch, order, rel, title in SMOKE_G1_IMAGES:
        li = local_idx[ch]
        narration = ""
        if li < len(narr_by_ch[ch]):
            narration = narr_by_ch[ch][li]
        local_idx[ch] = li + 1
        segs = guess_segments(narration)
        segs = refine_speakers(order, segs, narration)
        # split long segments for multi-voice TTS (BLOCK >=111)
        segs = expand_long_segments(segs)
        for i, s in enumerate(segs):
            s["seg_id"] = f"{scene_id}_{i+1:02d}"
        shots.append(
            {
                "scene_id": scene_id,
                "order": order,
                "chapter": ch,
                "title": title,
                "image": rel.replace("\\", "/"),
                "density": "high" if ch == 1 else "event",
                "outputMode": "image",
                "narration": narration,
                "segments": segs,
            }
        )
    return {
        "schema_version": "1.0",
        "run_id": "smoke_g1",
        "total_shots": len(shots),
        "chapter1_high_density": 16,
        "intro_mode": "PRE_ROLL_VIDEO",
        "intro_video": "videos/intro.mp4",
        "shots": shots,
    }


def expand_long_segments(segs: list[dict], limit: int = 100) -> list[dict]:
    out: list[dict] = []
    for s in segs:
        t = s.get("text") or ""
        if len(t) <= limit:
            out.append(s)
            continue
        parts = split_sentences(t)
        if len(parts) <= 1:
            # hard wrap by length at spaces
            while t:
                out.append({"speaker": s["speaker"], "text": t[:limit].rsplit(" ", 1)[0] or t[:limit]})
                t = t[len(out[-1]["text"]) :].strip()
            continue
        buf = []
        for p in parts:
            if buf and sum(len(x) for x in buf) + len(p) > limit:
                out.append({"speaker": s["speaker"], "text": " ".join(buf)})
                buf = [p]
            else:
                buf.append(p)
        if buf:
            out.append({"speaker": s["speaker"], "text": " ".join(buf)})
    return out


def refine_speakers(order: int, segs: list[dict], narration: str) -> list[dict]:
    """Second-pass speaker fixes. unknown → best guess or narrator (never force youjin)."""
    for s in segs:
        t = s.get("text") or ""
        sp = s.get("speaker") or "narrator"
        if sp == "narrator":
            continue
        # lexicon override always wins
        forced = _speaker_from_context(narration, "", t)
        if forced not in ("unknown", "narrator"):
            s["speaker"] = forced
            s.pop("needs_speaker_review", None)
            continue
        if sp == "unknown":
            # Safer for TTS: read as narrator rather than wrong gender voice
            s["speaker"] = "narrator"
            s["speaker_fallback"] = "unknown_to_narrator"
    return segs


def pack_units_fulltext(units: list[str], max_chars: int = 100) -> list[str]:
    """Pack chapter units into scenes without dropping any text."""
    if not units:
        return []
    out: list[str] = []
    buf: list[str] = []
    for u in units:
        u = u.strip()
        if not u:
            continue
        # single unit longer than max: hard-split by sentences then length
        if len(u) > max_chars:
            if buf:
                out.append(" ".join(buf))
                buf = []
            parts = split_sentences(u) or [u]
            for p in parts:
                if len(p) <= max_chars:
                    if buf and sum(len(x) for x in buf) + 1 + len(p) > max_chars:
                        out.append(" ".join(buf))
                        buf = [p]
                    else:
                        buf.append(p)
                else:
                    if buf:
                        out.append(" ".join(buf))
                        buf = []
                    t = p
                    while t:
                        chunk = t[:max_chars]
                        if " " in chunk and len(t) > max_chars:
                            chunk = chunk.rsplit(" ", 1)[0] or chunk
                        out.append(chunk)
                        t = t[len(chunk) :].strip()
            continue
        if not buf:
            buf = [u]
            continue
        if sum(len(x) for x in buf) + 1 + len(u) <= max_chars:
            buf.append(u)
        else:
            out.append(" ".join(buf))
            buf = [u]
    if buf:
        out.append(" ".join(buf))
    return out


def images_by_chapter() -> dict[int, list[tuple[str, str]]]:
    by: dict[int, list[tuple[str, str]]] = {1: [], 2: [], 3: [], 4: [], 5: []}
    for _sid, ch, _order, rel, title in SMOKE_G1_IMAGES:
        by[int(ch)].append((rel.replace("\\", "/"), title))
    return by


# Image filename / title keyword tags for semantic pick (not round-robin).
_IMAGE_TAG_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("meeting", ("서명", "정리해", "권고", "회의", "소회의", "봉투")),
    ("fluorescent", ("형광등", "깜빡")),
    ("envelope", ("봉투", "볼펜", "모서리")),
    ("usb", ("USB", "유에스비", "파일", "키보드 받침")),
    ("company", ("한빛", "공단", "간판", "외벽", "셔터", "주차")),
    ("youjin", ("한유진", "서른", "계약직", "회계")),
    ("desk", ("모니터", "키보드", "책상", "전표", "엑셀")),
    ("gyeongho", ("경호", "대리", "캔커피", "조끼")),
    ("siwoo", ("시우", "과장", "페이퍼", "동해", "칸막이")),
    ("gicheol", ("기철", "대표", "정장", "복도")),
    ("ramen", ("라면", "배신", "숫자부터")),
    ("excel", ("엑셀", "매입", "전표", "코드")),
    ("mail", ("메일", "공문", "오류")),
    ("resignation", ("퇴사", "권고", "서명")),
    ("recording", ("녹음", "앱", "재생")),
    ("threat", ("협박", "합의", "침묵")),
    ("bus", ("버스", "퇴근")),
    ("convenience", ("편의점", "김밥")),
    ("cabinet", ("캐비닛", "바인더", "열쇠")),
    ("cafe", ("카페", "회유")),
    ("dining", ("합의금", "룸", "식사")),
    ("rooftop", ("옥상", "바람")),
    ("hospital", ("병원", "수술", "어머니")),
    ("timeline", ("타임라인", "추적", "표")),
    ("inquiry", ("조회", "테이블")),
    ("testimony", ("증언", "진술")),
    ("ending", ("엔딩", "아침", "어깨")),
]


def pick_image_for_narration(
    narration: str,
    imgs: list[tuple[str, str]],
    prev_rel: str = "",
) -> tuple[str, str, str]:
    """Pick best chapter image by keyword overlap; hold previous if no match (no round-robin)."""
    if not imgs:
        return "images/ch1/ch1_01_meeting_line.jpg", "fallback", "empty"
    text = narration or ""
    best_i = -1
    best_score = 0
    for i, (rel, title) in enumerate(imgs):
        stem = Path(rel).stem.lower()
        blob = f"{stem} {title}"
        score = 0
        for tag, kws in _IMAGE_TAG_RULES:
            if tag in stem or tag in blob:
                hits = sum(1 for k in kws if k in text)
                if hits:
                    score += hits * 2
        # title word overlap
        for tok in re.findall(r"[가-힣]{2,}", title or ""):
            if tok in text:
                score += 1
        if score > best_score:
            best_score = score
            best_i = i
    if best_score <= 0 and prev_rel:
        for rel, title in imgs:
            if rel == prev_rel:
                return rel, title, "hold_prev"
        return imgs[0][0], imgs[0][1], "hold_fallback"
    if best_i < 0:
        return imgs[0][0], imgs[0][1], "default_first"
    return imgs[best_i][0], imgs[best_i][1], f"match_score_{best_score}"


def build_smoke_g1_fulltext(rd: Path, max_chars: int = 100) -> dict:
    """Upload-grade plan: keep entire chapter text; semantic image pick + hold."""
    chapters = load_chapter_units(rd)
    img_by = images_by_chapter()
    shots = []
    order = 0
    coverage = {}
    for ch in range(1, 6):
        units = chapters.get(ch) or []
        narrations = pack_units_fulltext(units, max_chars=max_chars)
        imgs = img_by.get(ch) or [("images/ch1/ch1_01_meeting_line.jpg", "fallback")]
        src_chars = sum(len(u) for u in units)
        packed_chars = sum(len(n) for n in narrations)
        coverage[ch] = {
            "units": len(units),
            "scenes": len(narrations),
            "src_chars": src_chars,
            "packed_chars": packed_chars,
        }
        prev_rel = ""
        for i, narration in enumerate(narrations):
            order += 1
            rel, title, how = pick_image_for_narration(narration, imgs, prev_rel=prev_rel)
            prev_rel = rel
            scene_id = f"ch{ch}_ft{i+1:03d}"
            segs = guess_segments(narration)
            segs = refine_speakers(order, segs, narration)
            segs = expand_long_segments(segs, limit=100)
            for j, s in enumerate(segs):
                s["seg_id"] = f"{scene_id}_{j+1:02d}"
                # TTS safety: unknown must not reach engine as youjin
                if s.get("speaker") == "unknown":
                    s["speaker"] = "narrator"
            shots.append(
                {
                    "scene_id": scene_id,
                    "order": order,
                    "chapter": ch,
                    "title": f"{title} · {i+1}/{len(narrations)}",
                    "image": rel,
                    "density": "high" if ch == 1 else "event",
                    "outputMode": "image",
                    "narration": narration,
                    "segments": segs,
                    "image_assign": how,
                }
            )
    return {
        "schema_version": "1.0",
        "run_id": "smoke_g1",
        "profile": "fulltext_upload",
        "total_shots": len(shots),
        "chapter1_high_density": coverage.get(1, {}).get("scenes"),
        "intro_mode": "PRE_ROLL_VIDEO",
        "intro_video": "videos/intro.mp4",
        "fulltext": True,
        "max_chars_per_scene": max_chars,
        "chapter_coverage": coverage,
        "shots": shots,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="smoke_g1")
    ap.add_argument("--out", default="")
    ap.add_argument(
        "--profile",
        choices=["preview40", "fulltext"],
        default="preview40",
        help="preview40=40 fixed shots (sampled); fulltext=entire chapter text for upload",
    )
    ap.add_argument("--max-chars", type=int, default=100)
    args = ap.parse_args()
    rd = run_dir(args.run)
    if args.run != "smoke_g1":
        raise SystemExit("Only smoke_g1 mapping is built-in for now. Extend SMOKE_G1_IMAGES for new runs.")
    if args.profile == "fulltext":
        data = build_smoke_g1_fulltext(rd, max_chars=args.max_chars)
        default_name = "shot_plan_upload.json"
    else:
        data = build_smoke_g1(rd)
        default_name = "shot_plan.json"
    out = Path(args.out) if args.out else rd / default_name
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    # also bridge copy (upload plan stays separate unless --out points to shot_plan.json)
    bridge = rd / "hermes_bridge"
    bridge.mkdir(exist_ok=True)
    bridge_name = "shot_plan_upload.json" if args.profile == "fulltext" else "shot_plan.json"
    (bridge / bridge_name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    missing = [s["image"] for s in data["shots"] if not (rd / s["image"]).exists()]
    print(f"wrote {out} profile={args.profile} shots={data['total_shots']} missing_images={len(missing)}")
    if data.get("chapter_coverage"):
        print(json.dumps(data["chapter_coverage"], ensure_ascii=False))
    if missing:
        print("MISSING:", missing[:10])


if __name__ == "__main__":
    main()
