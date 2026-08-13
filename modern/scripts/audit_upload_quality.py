# -*- coding: utf-8 -*-
"""Audit upload fulltext shot plan: image-context fit + speaker assignment."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "smoke_g1"


def main() -> None:
    plan = json.loads((RUN / "shot_plan_upload.json").read_text(encoding="utf-8"))
    vm = json.loads((RUN / "hermes_bridge" / "voice_map.json").read_text(encoding="utf-8"))
    shots = plan["shots"]
    print("total_shots", len(shots), "profile", plan.get("profile"))
    print("coverage", json.dumps(plan.get("chapter_coverage"), ensure_ascii=False))

    print("\n=== VOICE MAP ===")
    for sid, conf in (vm.get("speakers") or {}).items():
        print(f"  {sid}: voice={conf.get('voice')} speed={conf.get('speed')}")

    print("\n=== FIRST 24 SCENES ===")
    for s in shots[:24]:
        n = (s.get("narration") or "").replace("\n", " ")
        segs = s.get("segments") or []
        print(
            f"o={s['order']:03d} img={Path(s['image']).name} "
            f"reuse={s.get('image_reuse_index')} title={s.get('title')}"
        )
        print(f"  narr: {n[:100]}")
        for seg in segs:
            print(f"    [{seg.get('speaker')}] {(seg.get('text') or '')[:80]}")

    # image sequence for ch1: consecutive same vs hop
    print("\n=== CH1 IMAGE SEQUENCE ===")
    ch1 = [s for s in shots if int(s["chapter"]) == 1]
    for s in ch1:
        print(f"{s['order']:03d} {Path(s['image']).name}")

    # count image switches per chapter
    print("\n=== IMAGE SWITCH RATE ===")
    by_ch = defaultdict(list)
    for s in shots:
        by_ch[int(s["chapter"])].append(s)
    for ch, lst in sorted(by_ch.items()):
        switches = 0
        for a, b in zip(lst, lst[1:]):
            if a["image"] != b["image"]:
                switches += 1
        uniq = len({s["image"] for s in lst})
        print(f"ch{ch}: scenes={len(lst)} unique_images={uniq} switches={switches} switch_rate={switches/max(1,len(lst)-1):.2f}")

    # speaker stats + suspicious quoted defaults
    spk = Counter()
    male_chars = {"gicheol", "gyeongho", "siwoo"}
    female_on_male_hints = []
    default_youjin_quotes = 0
    for s in shots:
        for seg in s.get("segments") or []:
            sid = seg.get("speaker") or "?"
            spk[sid] += 1
            t = seg.get("text") or ""
            # quotes assigned youjin but context is male role
            if sid == "youjin":
                # heuristic: lines that are clearly gicheol/siwoo style
                if any(k in t for k in ("정리합시다", "서로 좋게", "서명만", "페이퍼상", "지금은 속도", "입력하세요", "입력만")):
                    female_on_male_hints.append((s["order"], sid, t[:60]))
            # quoted dialogue heuristic from guess_segments default
            if re.search(r'["“]', s.get("narration") or "") and sid == "youjin":
                default_youjin_quotes += 1

    print("\n=== SEGMENT SPEAKER COUNTS ===")
    for k, v in spk.most_common():
        voice = (vm.get("speakers") or {}).get(k, {}).get("voice")
        print(f"  {k}: segs={v} voice={voice}")

    print("\n=== SUSPECT: youjin on male-role lines ===")
    for item in female_on_male_hints[:30]:
        print(" ", item)
    print("count", len(female_on_male_hints))

    # M voices all male - user says similar. List gender clusters
    print("\n=== VOICE GENDER CLUSTER ===")
    print("  narrator M2, gicheol M5, gyeongho M3, siwoo M1 = all male SuperTonic presets")
    print("  youjin F2 = only female")
    print("  => 4 male voices may sound similar without filters/speed contrast")

    # keyword match: does image name relate to narration keywords?
    keyword_map = {
        "meeting": ["서명", "정리", "권고", "회의"],
        "fluorescent": ["형광등", "깜빡"],
        "envelope": ["봉투", "볼펜"],
        "usb": ["USB", "유에스비"],
        "company": ["한빛", "공단", "간판", "외벽"],
        "youjin": ["유진", "한유진", "서른"],
        "desk": ["모니터", "키보드", "책상"],
        "gyeongho": ["경호", "대리"],
        "siwoo": ["시우", "과장", "페이퍼", "동해"],
        "gicheol": ["기철", "대표"],
        "ramen": ["라면", "숫자", "배신"],
        "excel": ["엑셀", "전표", "매입"],
        "mail": ["메일", "공문"],
        "recording": ["녹음", "앱"],
        "bus": ["버스"],
        "cafe": ["카페"],
        "rooftop": ["옥상"],
        "ending": ["편의점", "엔딩"],
    }
    fit_ok = fit_bad = 0
    bad_examples = []
    for s in shots[:80]:  # sample early
        img = Path(s["image"]).stem.lower()
        n = s.get("narration") or ""
        matched = False
        for key, kws in keyword_map.items():
            if key in img and any(k in n for k in kws):
                matched = True
                break
        # if no keyword known for image, skip
        known = any(k in img for k in keyword_map)
        if not known:
            continue
        if matched:
            fit_ok += 1
        else:
            fit_bad += 1
            if len(bad_examples) < 15:
                bad_examples.append((s["order"], Path(s["image"]).name, n[:70]))
    print("\n=== IMAGE-NARR KEYWORD FIT (first ~80 with known keys) ===")
    print(f"fit_ok={fit_ok} fit_bad={fit_bad} bad_ratio={fit_bad/max(1,fit_ok+fit_bad):.2f}")
    for ex in bad_examples:
        print(" BAD", ex)

    out = RUN / "reports"
    out.mkdir(exist_ok=True)
    report = {
        "total_shots": len(shots),
        "speaker_counts": dict(spk),
        "female_on_male_hint_count": len(female_on_male_hints),
        "female_on_male_hints": [
            {"order": o, "speaker": sid, "text": t} for o, sid, t in female_on_male_hints[:50]
        ],
        "image_fit_sample": {"ok": fit_ok, "bad": fit_bad, "examples": [
            {"order": o, "image": im, "narr": n} for o, im, n in bad_examples
        ]},
        "root_causes": [
            "fulltext image assignment is round-robin by chapter index, not semantic match to narration",
            "guess_segments defaults quoted dialogue to youjin (F2) when attribution fails",
            "four male SuperTonic voices without strong speed/filter separation sound similar",
            "high scene count (233) with ~40 images causes rapid meaningless cut changes",
        ],
    }
    (out / "upload_quality_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nwrote", out / "upload_quality_audit.json")


if __name__ == "__main__":
    main()
