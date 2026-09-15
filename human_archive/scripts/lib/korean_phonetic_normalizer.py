# -*- coding: utf-8 -*-
"""Hardened Korean phonetic normalizer for SuperTonic3 M2 documentary TTS."""
from __future__ import annotations
import re

_SINO_DIGITS = ["영", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]


def sino_int(n: int) -> str:
    """Read a non-negative integer in Sino-Korean (천팔백십사)."""
    if n < 0:
        return "마이너스 " + sino_int(-n)
    if n == 0:
        return "영"
    parts: list[str] = []
    units = [
        (100000000, "억"),
        (10000, "만"),
        (1000, "천"),
        (100, "백"),
        (10, "십"),
    ]
    rest = n
    for value, name in units:
        qty, rest = divmod(rest, value)
        if qty == 0:
            continue
        if qty == 1 and value >= 10:
            parts.append(name)
        else:
            parts.append(sino_int(qty) + name)
    if rest:
        parts.append(_SINO_DIGITS[rest])
    return "".join(parts)


def robust_normalize_korean_tts(text: str) -> str:
    """Convert written text with digits, English acronyms, and units into natural Korean speech."""
    if not text:
        return text
    out = text

    # 1. Strip visual English glosses in parentheses: e.g. 사빙(Dead Ice) -> 사빙
    out = re.sub(r"\(([A-Za-z\s]+)\)", "", out)

    # 2. Acronyms & Specific Geological Terms
    out = re.sub(r"GLOF(?=[^a-zA-Z]|$)", "글로프", out)
    out = re.sub(r"ICIMOD(?=[^a-zA-Z]|$)", "아이씨아이엠오디", out)

    # 2b. Kilometers: 80km -> 팔십 킬로미터
    out = re.sub(r"(\d{1,3}(?:,\d{3})+|\d+)\s*km(?=[^a-zA-Z0-9]|$)", lambda m: f"{sino_int(int(m.group(1).replace(',', '')))} 킬로미터", out)

    # 3. Percentages: e.g. 65% -> 육십오 퍼센트
    out = re.sub(r"(\d+(?:\.\d+)?)\s*%", lambda m: f"{sino_int(int(float(m.group(1))))} 퍼센트", out)

    # 4. Decimals & Units: e.g. 3.0 -> 삼 점 영, 3.4m -> 삼 점 사 미터, 1.5배 -> 일 점 오 배, 0.5도 -> 영 점 오 도
    def _read_decimal(m: re.Match) -> str:
        int_val = sino_int(int(m.group(1).replace(",", "")))
        frac_str = " ".join(_SINO_DIGITS[int(d)] for d in m.group(2))
        return f"{int_val} 점 {frac_str}"

    out = re.sub(r"(\d{1,3}(?:,\d{3})+|\d+)\.(\d+)\s*m(?=[^a-zA-Z0-9]|$)", lambda m: f"{_read_decimal(m)} 미터", out)
    out = re.sub(r"(\d{1,3}(?:,\d{3})+|\d+)\.(\d+)\s*(배|도|초|퍼센트|미터)", lambda m: f"{_read_decimal(m)} {m.group(3)}", out)
    out = re.sub(r"(\d{1,3}(?:,\d{3})+|\d+)\.(\d+)", _read_decimal, out)

    # 4b. Metric Distances with Korean Postpositions: 5,000m의 -> 오천 미터의
    out = re.sub(r"(\d{1,3}(?:,\d{3})+|\d+)\s*m(?=[^a-zA-Z0-9]|$)", lambda m: f"{sino_int(int(m.group(1).replace(',', '')))} 미터", out)
    out = re.sub(r"(\d{1,3}(?:,\d{3})+|\d+)\s*미터", lambda m: f"{sino_int(int(m.group(1).replace(',', '')))} 미터", out)

    # 5. Centuries: 21세기 -> 이십일세기
    out = re.sub(r"(\d+)\s*세기", lambda m: f"{sino_int(int(m.group(1)))}세기", out)

    # 6. Large Compound Numerals: 2억 4천만 -> 이억 사천만, 5억 명 -> 오억 명, 20억 -> 이십억
    out = re.sub(r"(\d+)\s*억\s*(\d+)\s*천만", lambda m: f"{sino_int(int(m.group(1)))}억 {sino_int(int(m.group(2)))}천만", out)
    out = re.sub(r"(\d+)\s*억\s*명", lambda m: f"{sino_int(int(m.group(1)))}억 명", out)
    out = re.sub(r"(\d+)\s*억", lambda m: f"{sino_int(int(m.group(1)))}억", out)

    # 7. Units of Time & Years: 10분 -> 십 분, 10년 -> 십 년, 2024년 -> 이천이십사 년, 6개월 -> 육 개월
    out = re.sub(r"(\d+)\s*분", lambda m: f"{sino_int(int(m.group(1)))} 분", out)
    out = re.sub(r"(\d+)\s*개월", lambda m: f"{sino_int(int(m.group(1)))} 개월", out)
    out = re.sub(r"(\d+(?:,\d+)?)\s*년", lambda m: f"{sino_int(int(m.group(1).replace(',', '')))} 년", out)
    out = re.sub(r"(\d+)\s*도(?=[^a-zA-Z0-9]|$)", lambda m: f"{sino_int(int(m.group(1)))} 도", out)

    # 8. Ordinals & Counters: 제3의 -> 제삼의, 10대 -> 십대
    out = re.sub(r"제(\d+)의", lambda m: f"제{sino_int(int(m.group(1)))}의", out)
    out = re.sub(r"(\d+)대\s*거대", lambda m: f"{sino_int(int(m.group(1)))}대 거대", out)
    out = out.replace("2만 5천 개", "이만 오천 개").replace("2만 5천", "이만 오천")

    # 9. Generic Integers Catch-all (Unicode safe)
    out = re.sub(r"(?<!\d)(\d{1,3}(?:,\d{3})+|\d+)(?!\d)", lambda m: sino_int(int(m.group(1).replace(",", ""))), out)
    
    return re.sub(r"\s+", " ", out).strip()


# Backward compatibility alias
normalize_korean_phonetic_tts = robust_normalize_korean_tts


if __name__ == "__main__":
    test_cases = [
        ("물은 하늘이 아니라, 해발 5,000m의 산꼭대기에서 터져 나왔습니다.", "오천 미터의"),
        ("수억 톤의 물과 바위가 단 10분 만에 계곡을 집어삼켰습니다.", "단 십 분 만에"),
        ("이것이 바로 과학자들이 경고하던 '보이지 않는 쓰나미', GLOF입니다.", "글로프입니다"),
        ("히말라야는 남극과 북극에 이어 세계에서 세 번째로 얼음이 많은 '제3의 극지'입니다.", "'제삼의 극지'"),
        ("아시아의 10대 거대 강이 모두 이곳에서 시작되어, 무려 20억 인구의 목숨을 먹여 살립니다.", "십대 거대 강", "이십억"),
        ("하지만 최근 10년 동안, 이 거대한 얼음 저장고가 무서운 속도로 녹아내리기 시작했습니다.", "십 년 동안"),
        ("녹아내린 얼음물은 산꼭대기에 2만 5천 개가 넘는 거대한 호수를 만들어냈습니다.", "이만 오천 개"),
        ("사빙(Dead Ice) 현상과 65%의 융해율", "사빙 현상과", "육십오 퍼센트의"),
        ("21세기 문명에 닥칠 위기와 2억 4천만 명", "이십일세기", "이억 사천만"),
        ("당시 지진계에는 규모 3.0 이상의 강력한 지진파가 감지되었습니다.", "규모 삼 점 영 이상의"),
        ("임자 호수의 수위를 3.4m 낮추는 데 성공했죠.", "삼 점 사 미터"),
        ("유량이 1.5배 증가하며 0.5초 만에 붕괴했습니다.", "일 점 오", "영 점 오"),
    ]
    for text, *expected in test_cases:
        res = robust_normalize_korean_tts(text)
        print(f"Original: {text}")
        print(f"Normalized: {res}")
        for exp in expected:
            assert exp in res, f"Expected '{exp}' in '{res}'"
        print(" -> PASS\n")
    print("ALL TESTS PASSED SUCCESSFULLY!")
