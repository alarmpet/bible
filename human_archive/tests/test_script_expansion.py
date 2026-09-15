from __future__ import annotations

import copy
import hashlib
import json

import pytest

from lib.script_expansion import (
    apply_script_metadata_patches,
    canonical_script_sha256,
    compile_script_expansion,
)


def _sentence(sentence_id: str, order: int, text: str, *, claim: bool = False) -> dict:
    segment = {
        "kind": "transition",
        "text": text,
        "claim_id": None,
        "evidence_span_ids": [],
    }
    if claim:
        segment = {
            "kind": "fact",
            "text": text,
            "claim_id": "CLM-1",
            "evidence_span_ids": ["SRC-1:SPAN-1"],
        }
    return {
        "sentence_id": sentence_id,
        "order": order,
        "chapter": 1,
        "beat": "body",
        "display_text": text,
        "tts_text": text,
        "segments": [segment],
        "disclosure": None,
    }


def _base() -> dict:
    return {
        "schema_version": 2,
        "episode_id": "HA002",
        "persona": "ship_seonbi",
        "title": "테스트",
        "target_duration_sec": 600,
        "sentences": [
            _sentence("S1", 1, "기존 첫 문장"),
            _sentence("S2", 2, "기존 둘째 문장", claim=True),
        ],
    }


def _claims() -> dict:
    return {
        "claims": [
            {
                "claim_id": "CLM-1",
                "evidence_refs": ["SRC-1:SPAN-1"],
            }
        ]
    }


def _expansion(base: dict) -> dict:
    base_sha = hashlib.sha256(
        json.dumps(base, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": 1,
        "episode_id": "HA002",
        "base_script_sha256": base_sha,
        "target_duration_sec": 1080,
        "blocks": [
            {
                "after_sentence_id": "S1",
                "chapter": 1,
                "sentences": [
                    _sentence("HA002-V6-N001", 999, "추가 해설 문장"),
                    _sentence("HA002-V6-N002", 999, "근거가 있는 추가 문장", claim=True),
                ],
            }
        ],
    }


def test_expansion_preserves_base_sentences_and_inserts_validated_blocks():
    base = _base()
    original = copy.deepcopy(base["sentences"])
    result = compile_script_expansion(base, _claims(), _expansion(base))

    assert [row["sentence_id"] for row in result["sentences"]] == [
        "S1",
        "HA002-V6-N001",
        "HA002-V6-N002",
        "S2",
    ]
    assert [row["order"] for row in result["sentences"]] == [1, 2, 3, 4]
    assert result["target_duration_sec"] == 1080
    assert "claim_id" not in result["sentences"][1]["segments"][0]
    assert "evidence_span_ids" not in result["sentences"][1]["segments"][0]
    preserved = {row["sentence_id"]: row for row in result["sentences"] if row["sentence_id"] in {"S1", "S2"}}
    for old in original:
        current = preserved[old["sentence_id"]]
        assert {key: value for key, value in current.items() if key != "order"} == {
            key: value for key, value in old.items() if key != "order"
        }


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda expansion: expansion["blocks"][0].update(after_sentence_id="missing"), "anchor"),
        (
            lambda expansion: expansion["blocks"][0]["sentences"][1]["segments"][0].update(
                evidence_span_ids=["SRC-OTHER:SPAN-9"]
            ),
            "evidence",
        ),
        (
            lambda expansion: expansion["blocks"][0]["sentences"][0].update(sentence_id="S2"),
            "duplicate",
        ),
    ],
)
def test_expansion_fails_closed_on_stale_or_unsupported_content(mutation, message):
    base = _base()
    expansion = _expansion(base)
    mutation(expansion)

    with pytest.raises(ValueError, match=message):
        compile_script_expansion(base, _claims(), expansion)


def test_metadata_patches_preserve_spoken_text_and_validate_claims():
    compiled = compile_script_expansion(_base(), _claims(), _expansion(_base()))
    original = copy.deepcopy(compiled)
    patches = {
        "schema_version": 1,
        "episode_id": "HA002",
        "input_script_sha256": canonical_script_sha256(compiled),
        "patches": [
            {
                "sentence_id": "S1",
                "segments": [
                    {
                        "kind": "insight",
                        "text": "기존 첫 문장",
                        "claim_id": None,
                        "evidence_span_ids": [],
                    }
                ],
            },
            {
                "sentence_id": "S2",
                "segments": [
                    {
                        "kind": "fact",
                        "text": "기존 둘째 문장",
                        "claim_id": "CLM-1",
                        "evidence_span_ids": ["SRC-1:SPAN-1"],
                    }
                ],
            },
        ],
    }

    result = apply_script_metadata_patches(compiled, _claims(), patches)

    by_id = {row["sentence_id"]: row for row in result["sentences"]}
    original_by_id = {row["sentence_id"]: row for row in original["sentences"]}
    assert by_id["S1"]["tts_text"] == original_by_id["S1"]["tts_text"]
    assert by_id["S1"]["display_text"] == original_by_id["S1"]["display_text"]
    assert by_id["S1"]["segments"][0]["kind"] == "insight"
    assert "claim_id" not in by_id["S1"]["segments"][0]
    assert "evidence_span_ids" not in by_id["S1"]["segments"][0]
    assert by_id["S2"]["segments"][0]["claim_id"] == "CLM-1"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda patches: patches.update(input_script_sha256="0" * 64),
            "stale",
        ),
        (
            lambda patches: patches["patches"][0]["segments"][0].update(
                text="낭독문과 다른 메타데이터 문장"
            ),
            "segment text",
        ),
        (
            lambda patches: patches["patches"][0]["segments"][0].update(
                kind="fact",
                claim_id="CLM-OTHER",
                evidence_span_ids=["SRC-OTHER:SPAN-1"],
            ),
            "unknown claim",
        ),
    ],
)
def test_metadata_patches_fail_closed(mutation, message):
    compiled = compile_script_expansion(_base(), _claims(), _expansion(_base()))
    patches = {
        "schema_version": 1,
        "episode_id": "HA002",
        "input_script_sha256": canonical_script_sha256(compiled),
        "patches": [
            {
                "sentence_id": "S1",
                "segments": [
                    {
                        "kind": "insight",
                        "text": "기존 첫 문장",
                        "claim_id": None,
                        "evidence_span_ids": [],
                    }
                ],
            }
        ],
    }
    mutation(patches)

    with pytest.raises(ValueError, match=message):
        apply_script_metadata_patches(compiled, _claims(), patches)
