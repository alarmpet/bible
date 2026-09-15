"""Fail-closed NOLLAM spoken-script contract and narrative deadline checks."""

from __future__ import annotations

from collections import Counter
from typing import Any

REQUIRED_FIELDS = ("spoken_text", "display_text", "phase", "claim_ids", "fact_grade", "visual_intent")
PHASES = (
    "phase_1_hook",
    "phase_2_mechanism",
    "phase_3_crisis",
    "phase_4_discovery",
    "phase_5_reflection",
)


def validate_script_contract(script: dict[str, Any]) -> dict[str, Any]:
    sentences = script.get("sentences")
    if not isinstance(sentences, list) or not sentences:
        raise ValueError("script sentences must be a non-empty list")
    orders = [int(row.get("order", -1)) for row in sentences]
    if orders != list(range(1, len(sentences) + 1)):
        raise ValueError("sentence order must be contiguous from 1")

    for sentence in sentences:
        for field in REQUIRED_FIELDS:
            if field not in sentence:
                raise ValueError(f"sentence missing required field: {field}")
        if not str(sentence["spoken_text"]).strip() or not str(sentence["display_text"]).strip():
            raise ValueError(f"empty spoken/display text: {sentence.get('sentence_id')}")
        if sentence["phase"] not in PHASES:
            raise ValueError(f"unknown phase: {sentence['phase']}")
        if not isinstance(sentence["claim_ids"], list):
            raise ValueError("claim_ids must be a list")

    if sentences[0]["phase"] != "phase_1_hook" or sentences[0].get("beat") != "hook":
        raise ValueError("first sentence must be the phase_1_hook hook")
    reversal = [row for row in sentences if row.get("beat") == "reversal"]
    if not reversal or float(reversal[0].get("start_sec", 9999)) > 20.0:
        raise ValueError("first narrative reversal must begin within 20 seconds")
    roadmap = [row for row in sentences if row.get("beat") == "roadmap"]
    if not roadmap or float(roadmap[0].get("start_sec", 9999)) > 38.0:
        raise ValueError("narrative roadmap must begin within 38 seconds")

    phase_counts = Counter(str(row["phase"]) for row in sentences)
    return {"sentence_count": len(sentences), "phase_counts": dict(phase_counts)}
