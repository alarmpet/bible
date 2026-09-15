# -*- coding: utf-8 -*-
"""Semantic Key Visual Subject Extractor for Korean Documentary Narrations.
Replaces naive character-count slicing (narration[:50]) with semantic entity
and keyword extraction to produce accurate, documentary-grade visual prompts.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

# High-priority visual entity patterns for documentary subjects
DOMAIN_VISUAL_PATTERNS = [
    # Maya & Ancient Civilizations
    (r"(?:라이다|lidar)", "LiDAR laser aerial scanning pulses penetrating thick tropical rainforest canopy, revealing hidden ancient stone structures underneath"),
    (r"(?:석순|산소 동위원소|지질 데이터)", "Close-up geological stalagmite cross-section inside deep limestone cave, mineral isotope layers, scientific macro detail"),
    (r"(?:저수조|아구아다|aguada|바닥이.*갈라|말라비틀)", "Vast ancient stone reservoir completely dried out, cracked mud ground resembling turtle shell, severe drought, parched earth"),
    (r"(?:신전.*불태|신왕|약탈|폭동|봉기)", "Dramatic low-angle view of grand ancient stone pyramid temple, dark smoke rising in background, intense cinematic chiaroscuro shadows"),
    (r"(?:대탈출|정글.*매몰|밀림.*묻|녹색 바다)", "Ancient overgrown stone temple ruins engulfed by massive dense tropical jungle vines and banyan roots, atmospheric volumetric mist"),
    (r"(?:스마트 시티|도로망|피라미드|천문)", "Majestic aerial view of monumental ancient Mayan stone pyramids rising above ocean of tropical rainforest canopy, golden sunrise"),
    (r"(?:증발|하룻밤.*사라|감쪽같이)", "Mysterious abandoned ancient Mayan stone city in dense misty jungle, silent empty courtyards, overgrown vines, eerie solitude"),
    (r"(?:자연의 한계|침묵의 경고|성찰|기후 위기)", "Philosophical contemplation view of ancient moss-covered weathered stone carving ruins, moody cinematic dusk light, epic silence"),

    # Mongol & Eurasian Steppe
    (r"(?:참|örtöö|파이자와|정보망)", "13세기 몽골 제국 파발마(Örtöö) 역참 망, 말을 탄 전령이 모래바람을 가르며 달리는 유라시아 대초원"),
    (r"(?:테무진|칭기즈|칭기즈칸)", "Chinggis Khaan and nomadic cavalry overlooking vast Eurasian steppe, historical leather armor, atmospheric wind"),
    (r"(?:비사|원조비사|사료|집사)", "Ancient weathered historical manuscript parchment, Mongolian script in black ink, historical archival document"),

    # Climate & Science / GLOF
    (r"(?:빙하호|glof|빙하.*붕괴)", "Catastrophic glacial lake outburst flood raging through high altitude Himalayan valley, massive moraine wall breach"),
    (r"(?:모레인|자연 제방|퇴적)", "Unstable massive lateral moraine dam composed of loose rock and glacial till holding back turquoise meltwater"),
    (r"(?:피크 워터|수자원 위기)", "Aerial drone view of receding glacier tongue with meltwater channels cutting through dry gravel riverbeds"),
    (r"(?:세이시|지진파|산사태)", "Massive rock and ice avalanche crashing down 4000-meter sheer granite cliff into glacial lake, kinetic tsunami wave"),

    # JWST & Universe
    (r"(?:제임스 웹|jwst|망원경)", "James Webb Space Telescope in deep black space at Sun-Earth L2 orbit, reflective gold hexagonal mirrors, cosmic backdrop"),
    (r"(?:괴물 은하|초기 은하|빅뱅)", "Massive ancient red spiral galaxy glowing in cosmic dawn 13.5 billion years ago, deep astronomical field"),

    # Economics & Currency
    (r"(?:교초|지폐|원나라.*화폐)", "Ancient Yuan dynasty paper money (Jiaochao) printed on mulberry bark paper, royal seals, historical artifact insert"),
    (r"(?:튤립|네덜란드.*구근)", "Exquisite rare striped Semper Augustus tulip flower in ornate 17th century Dutch vase, dramatic chiaroscuro Rembrandt lighting"),
]


def extract_key_visual_subject(narration: str, protagonist: str = "", default_genre: str = "history") -> Dict[str, Any]:
    """Extract key visual subject and compile focused documentary prompt tokens."""
    text = narration.strip()
    
    # 1. Domain-specific pattern matching
    matched_subjects = []
    matched_keywords = []

    for pattern, eng_desc in DOMAIN_VISUAL_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            matched_subjects.append(eng_desc)
            m = re.findall(pattern, text, flags=re.IGNORECASE)
            matched_keywords.extend(m)

    if matched_subjects:
        # Use primary matched visual description
        primary_subject = matched_subjects[0]
        secondary_subject = matched_subjects[1] if len(matched_subjects) > 1 else None
        compiled = f"{primary_subject}"
        if secondary_subject:
            compiled += f", {secondary_subject}"
        return {
            "source_text": text,
            "compiled_subject": compiled,
            "matched_keywords": list(set(matched_keywords)),
            "match_confidence": 0.95
        }

    # 2. General morphological noun / subject heuristics
    # Extract significant nouns (length >= 2, strip particles)
    tokens = re.findall(r"[가-힣a-zA-Z0-9]+", text)
    stopwords = {"에서", "으로", "에게", "부터", "까지", "하고", "하고는", "그리고", "하지만", "그런데", "이것은", "그것은", "우리가", "말이죠"}
    filtered_nouns = [t for t in tokens if len(t) >= 2 and t not in stopwords]

    # Contextual subject construction
    noun_summary = " ".join(filtered_nouns[:4])
    if default_genre == "history":
        compiled = f"Authentic historical documentary scene depicting {noun_summary}, weathered period textures, authentic atmospheric depth"
    else:
        compiled = f"Scientific documentary visual showing {noun_summary}, realistic environmental terrain, natural atmospheric perspective"

    return {
        "source_text": text,
        "compiled_subject": compiled,
        "matched_keywords": filtered_nouns[:4],
        "match_confidence": 0.75
    }
