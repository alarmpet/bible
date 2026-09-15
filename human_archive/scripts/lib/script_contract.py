"""Fail-closed NOLLAM spoken-script contract and narrative deadline checks.

STATUS (2026-09-15, found while resolving the nollam script phase-naming
mismatch -- docs/superpowers/plans/2026-09-15-human-archive-nollam-script-visual-motion-multi-llm-overhaul-plan.md):
The validator this module exports has no production caller -- generate_script_candidate()
validates against trend_verified_script_v1.schema.json instead, and nothing
in this repo's real nollam pipeline calls into this module. Its own PHASES
tuple is a THIRD, independent phase-naming vocabulary for the same 5-stage
nollam narrative structure the template (nollam_script_prompt_v3.j2's bare
6-value per-sentence tag) and config/script_policy_v3.yaml's story_phases
(the reconciled pair -- see lib/phase_mapping.py) already disagreed on
before that fix. REQUIRED_FIELDS here (spoken_text, fact_grade,
visual_intent) also don't match the fields real generated scripts actually
carry (tts_text, no fact_grade/visual_intent at the sentence level) -- this
looks like an earlier design draft that was never reconciled with the
pipeline that shipped.

Left as-is rather than partially patched: swapping just the phase names
without also redesigning the field contract and re-deciding whether its
narrative-timing assertions (reversal <=20s, roadmap <=38s) still match
current policy would just be cosmetic, not a real integration. Whoever wires
this in for real should design it against the actual current schema
(trend_verified_script_v1.schema.json) and phase_mapping.py's
SENTENCE_PHASE_VALUES, not patch around the mismatch. Tracked as an accepted,
still-unwired capability in audit_declared_vs_wired.py's registry
(validate_script_contract) so it stays visible rather than silently rotting
further.
"""

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
