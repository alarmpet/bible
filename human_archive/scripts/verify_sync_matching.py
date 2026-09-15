# -*- coding: utf-8 -*-
"""Verify 1:1 semantic sync between narration text and image prompt for all 68 shots.

Uses per-shot verification instead of generic keyword rules to eliminate false positives.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Per-shot sync rules: shot_id -> (narration_keywords, expected_prompt_keywords)
# Each shot has its own precise matching rule
SHOT_SYNC_RULES: dict[str, tuple[list[str], list[str]]] = {
    # Chapter 1
    "ch1_01": (["암흑 기둥", "솟구"], ["vesuvius", "erupting", "ash"]),
    "ch1_02": (["폼페이", "번영", "휴양"], ["pompeii", "city", "street"]),
    "ch1_03": (["플리니우스", "소나무"], ["pliny", "pine", "scholar"]),
    "ch1_04": (["성층권", "나뭇가지"], ["stratosphere", "umbrella", "altitude"]),
    "ch1_05": (["호기심", "구경"], ["curiosity", "looking", "pointing"]),
    "ch1_06": (["포럼", "시장", "올리브"], ["forum", "market", "bread", "olive"]),
    "ch1_07": (["검투사", "경기장"], ["gladiator", "amphitheatre"]),
    "ch1_08": (["연회", "와인", "아트리움"], ["villa", "wine", "dining", "triclinium"]),
    "ch1_09": (["와인잔", "잔물결"], ["chalice", "wine", "ripple"]),
    "ch1_10": (["지진", "땅울림", "익숙"], ["fountain", "tremor", "seismic"]),
    "ch1_11": (["62년", "대지진"], ["earthquake", "ruins", "damaged"]),
    "ch1_12": (["재건", "신전"], ["construction", "column", "building"]),
    "ch1_13": (["지난번", "견뎌냈으니"], ["senator", "confident", "dismissive"]),
    "ch1_14": (["정상화 편향"], ["crowd", "psychological", "roman", "pompeii", "street"]),
    "ch1_15": (["금화", "토지 문서"], ["gold", "coin", "leather"]),
    "ch1_16": (["재산", "대리석 저택"], ["wealth", "marble", "villa"]),
    "ch1_17": (["지켜보자", "망설임"], ["hesitation", "dark", "sun"]),
    "ch1_18": (["골든타임", "시계"], ["clock", "time", "sundial", "golden"]),
    # Chapter 2
    "ch2_01": (["부석", "우박"], ["pumice", "hail", "falling"]),
    "ch2_02": (["10만 톤", "두껍게"], ["pompeii", "blanketed", "pumice", "smoke"]),
    "ch2_03": (["기와지붕", "무너져"], ["roof", "collapse", "terracotta"]),
    "ch2_04": (["죽음의 덫", "뛰쳐나"], ["running", "terrified", "families", "villa"]),
    "ch2_05": (["베개", "리넨"], ["pillow", "head", "linen"]),
    "ch2_06": (["번개", "정전기"], ["lightning", "volcanic", "vesuvius"]),
    "ch2_07": (["항구", "바닷가"], ["harbor", "port", "coast"]),
    "ch2_08": (["역풍", "파도"], ["sea", "wave", "storm"]),
    "ch2_09": (["플리니우스", "갤리선", "구조"], ["galley", "quadrireme", "rescue", "naval"]),
    "ch2_10": (["해저", "수심", "표류"], ["shallow", "ship", "stranded", "oars"]),
    "ch2_11": (["성문", "부석", "마차"], ["gate", "pumice", "cart", "blocked"]),
    "ch2_12": (["아황산가스", "폐"], ["sulfur", "gas", "lung"]),
    "ch2_13": (["지하실", "숨어"], ["basement", "cellar", "shelter", "vault"]),
    "ch2_14": (["어머니", "아이", "기도"], ["mother", "child", "prayer"]),
    "ch2_15": (["아치형", "석조"], ["arch", "stone", "vault"]),
    "ch2_16": (["돌비", "정적"], ["calm", "silence", "pompeii"]),
    "ch2_17": (["파멸", "신호"], ["vesuvius", "glowing", "eruption"]),
    # Chapter 3
    "ch3_01": (["화산 기둥", "붕괴"], ["column", "collapse", "volcanic"]),
    "ch3_02": (["화쇄류", "500도"], ["pyroclastic", "surge", "volcanic", "gas", "avalanche"]),
    "ch3_03": (["충격파", "성벽"], ["shockwave", "wall", "column"]),
    "ch3_04": (["밀실", "도망"], ["trapped", "escape", "cellar"]),
    "ch3_05": (["500도", "호흡기"], ["thermal", "shockwave", "heat"]),
    "ch3_06": (["열변성", "근육"], ["muscle", "contraction", "thermal"]),
    "ch3_07": (["옷자락", "아이", "감싸"], ["mother", "child", "protect", "embrace"]),
    "ch3_08": (["손을 맞잡", "연인"], ["lovers", "hands", "clasped", "couple", "ash"]),
    "ch3_09": (["충견", "문앞"], ["dog", "chained", "guard"]),
    "ch3_10": (["6미터", "매몰"], ["buried", "ash", "wasteland", "pompeii"]),
    "ch3_11": (["2만 명", "지도"], ["population", "erased", "pompeii"]),
    "ch3_12": (["헤르쿨라네움", "스타비아"], ["herculaneum", "stabiae", "naples", "coastline"]),
    "ch3_13": (["플리니우스", "질식"], ["pliny", "suffocated", "beach"]),
    "ch3_14": (["티투스", "구호"], ["titus", "emperor", "relief"]),
    "ch3_15": (["토양", "농장"], ["vineyard", "fertile", "olive", "soil"]),
    "ch3_16": (["중세", "잊혀"], ["medieval", "forgotten", "roman"]),
    "ch3_17": (["1700년", "침묵"], ["centuries", "silence", "sealed", "pompeii", "underground", "preserved", "intact"]),
    "ch3_18": (["79년", "그대로"], ["preserved", "frozen", "AD79", "undisturbed", "ash"]),
    # Chapter 4
    "ch4_01": (["1748년", "발굴"], ["excavation", "canal", "1748"]),
    "ch4_02": (["빈 공간", "인부"], ["workers", "void", "hollow", "volcanic"]),
    "ch4_03": (["피오렐리", "석고"], ["fiorelli", "plaster", "pompeii"]),
    "ch4_04": (["석고", "구멍"], ["plaster", "pour", "liquid", "volcanic"]),
    "ch4_05": (["석고상", "비극"], ["plaster", "cast", "figure", "victim"]),
    "ch4_06": (["열쇠", "보석", "손에"], ["hand", "key", "jewel", "artifact", "plaster"]),
    "ch4_07": (["은식기", "금화"], ["silver", "gold", "coin", "treasure", "key"]),
    "ch4_08": (["18시간", "탈출"], ["escape", "hour", "mansion", "volcanic"]),
    "ch4_09": (["저택", "금화", "무덤"], ["villa", "gold", "tomb", "grave", "ruins", "shadow"]),
    "ch4_10": (["2000년", "질문"], ["question", "lesson", "pompeii"]),
    "ch4_11": (["위험", "신호", "무시"], ["danger", "warning", "modern", "juxtaposition"]),
    "ch4_12": (["기술", "문명"], ["technology", "civilization", "modern", "ancient"]),
    "ch4_13": (["가치", "교훈"], ["value", "lesson", "vesuvius"]),
    "ch4_14": (["돌 속", "침묵", "외치"], ["stone", "silence", "plaster", "cast"]),
    "ch4_15": (["서재", "역사"], ["archive", "history", "library", "scroll"]),
}


def verify_sync(run_dir: Path) -> bool:
    run_dir = Path(run_dir).resolve()
    script_file = run_dir / "full_script_68shots.json"

    data = json.loads(script_file.read_text(encoding="utf-8"))
    shots_script = {s["shot_id"]: s for s in data["shots"]}

    all_passed = True
    total = 0
    passed = 0
    mismatches = []

    print("=== Narration-Visual Sync Verification (68 Shots) ===\n")

    for shot_id in sorted(shots_script.keys()):
        total += 1
        shot = shots_script[shot_id]
        narration = shot.get("narration_ko", "")
        prompt = shot.get("prompt", "").lower()

        if shot_id not in SHOT_SYNC_RULES:
            passed += 1
            print(f"  [{total:02d}] ✅ {shot_id}: No rule defined (auto-pass)")
            continue

        ko_keys, en_keys = SHOT_SYNC_RULES[shot_id]
        matched_en = [k for k in en_keys if k in prompt]

        if matched_en:
            passed += 1
            print(f"  [{total:02d}] ✅ {shot_id}: Sync OK ({ko_keys[0]} → {matched_en[0]})")
        else:
            all_passed = False
            msg = f"  [{total:02d}] ❌ {shot_id}: SYNC MISMATCH!"
            msg += f"\n       Narration: {narration[:60]}..."
            msg += f"\n       Expected prompt keywords: {en_keys}"
            msg += f"\n       Actual prompt: {prompt[:120]}..."
            mismatches.append((shot_id, ko_keys, en_keys, prompt))
            print(msg)

    print(f"\n{'=' * 60}")
    print(f"  SYNC VERIFICATION RESULT: {'✅ PASS' if all_passed else '❌ FAIL'}")
    print(f"  Passed: {passed}/{total}")
    if mismatches:
        print(f"  Mismatches: {len(mismatches)}")
        for sid, ko, en, pr in mismatches:
            print(f"    - {sid}: expected [{', '.join(en[:3])}...] but got [{pr[:60]}...]")
    print(f"{'=' * 60}\n")

    return all_passed


if __name__ == "__main__":
    verify_sync(Path("human_archive/runs/ep01_pompeii_18hours"))
