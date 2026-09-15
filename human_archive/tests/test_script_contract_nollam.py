from __future__ import annotations

import pytest

from lib.script_contract import validate_script_contract


def _sentence(index: int, phase: str, *, beat: str = "body", start: float | None = None) -> dict:
    return {
        "sentence_id": f"S{index:03d}",
        "order": index,
        "spoken_text": f"검증 가능한 서사 문장 {index}입니다.",
        "display_text": f"검증 가능한 서사 문장 {index}입니다.",
        "phase": phase,
        "claim_ids": [],
        "fact_grade": "A",
        "visual_intent": "cinematic evidence",
        "beat": beat,
        "start_sec": 0.0 if start is None else start,
        "end_sec": 4.0 if start is None else start + 4.0,
    }


def _valid_script() -> dict:
    phases = ["phase_1_hook", "phase_2_mechanism", "phase_3_crisis", "phase_4_discovery", "phase_5_reflection"]
    sentences = [_sentence(1, phases[0], beat="hook", start=0.0), _sentence(2, phases[0], beat="reversal", start=4.0)]
    sentences += [_sentence(index, phases[(index - 1) // 2], start=float(index * 4)) for index in range(3, 11)]
    sentences[1]["start_sec"] = 12.0
    sentences[1]["end_sec"] = 16.0
    sentences[2]["beat"] = "roadmap"
    sentences[2]["start_sec"] = 24.0
    sentences[2]["end_sec"] = 28.0
    return {"episode_id": "TEST", "target_duration_sec": 1200, "sentences": sentences}


def test_valid_nollam_script_contract_passes() -> None:
    result = validate_script_contract(_valid_script())
    assert result["sentence_count"] == 10
    assert result["phase_counts"]["phase_5_reflection"] == 2


@pytest.mark.parametrize("field", ["spoken_text", "display_text", "phase", "claim_ids", "fact_grade", "visual_intent"])
def test_required_sentence_fields_fail_closed(field: str) -> None:
    script = _valid_script()
    script["sentences"][0].pop(field)
    with pytest.raises(ValueError, match=field):
        validate_script_contract(script)


def test_missing_early_reversal_fails_closed() -> None:
    script = _valid_script()
    script["sentences"][1]["beat"] = "body"
    with pytest.raises(ValueError, match="reversal"):
        validate_script_contract(script)
