from __future__ import annotations

import copy
import hashlib
import json
from typing import Any


def canonical_script_sha256(script: dict[str, Any]) -> str:
    payload = json.dumps(script, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_new_sentence(
    sentence: dict[str, Any],
    claims: dict[str, dict[str, Any]],
) -> None:
    required = {
        "sentence_id",
        "order",
        "chapter",
        "beat",
        "display_text",
        "tts_text",
        "segments",
    }
    missing = sorted(required - set(sentence))
    if missing:
        raise ValueError(f"new sentence is missing fields: {missing}")
    if not str(sentence["sentence_id"]).strip():
        raise ValueError("new sentence ID is empty")
    if str(sentence["display_text"]) != str(sentence["tts_text"]):
        raise ValueError(f"display/tts mismatch: {sentence['sentence_id']}")
    if not 1 <= len(str(sentence["tts_text"])) <= 65:
        raise ValueError(f"new sentence exceeds 65 characters: {sentence['sentence_id']}")
    segments = sentence.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError(f"new sentence has no segments: {sentence['sentence_id']}")

    for segment in segments:
        kind = str(segment.get("kind", ""))
        if kind not in {"transition", "fact", "analogy", "direct_quote", "insight"}:
            raise ValueError(
                f"unsupported segment kind {kind}: {sentence['sentence_id']}"
            )
        raw_claim_id = segment.get("claim_id")
        claim_id = "" if raw_claim_id in (None, "") else str(raw_claim_id)
        evidence = {
            str(value) for value in (segment.get("evidence_span_ids") or [])
        }
        if kind in {"fact", "direct_quote"} and not claim_id:
            raise ValueError(f"fact segment has no claim: {sentence['sentence_id']}")
        if evidence and not claim_id:
            raise ValueError(f"evidence has no claim: {sentence['sentence_id']}")
        if not claim_id:
            continue
        claim = claims.get(claim_id)
        if not claim:
            raise ValueError(f"unknown claim {claim_id}: {sentence['sentence_id']}")
        allowed_evidence = {str(value) for value in claim.get("evidence_refs", [])}
        if not evidence:
            raise ValueError(f"claim has no evidence: {sentence['sentence_id']}")
        if not evidence <= allowed_evidence:
            raise ValueError(f"unsupported evidence for {claim_id}: {sentence['sentence_id']}")


def _normalize_optional_evidence_fields(
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized = copy.deepcopy(segments)
    for segment in normalized:
        if segment.get("claim_id") is None:
            segment.pop("claim_id", None)
        if not segment.get("evidence_span_ids"):
            segment.pop("evidence_span_ids", None)
    return normalized


def apply_script_metadata_patches(
    script: dict[str, Any],
    claim_inventory: dict[str, Any],
    patch_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Apply evidence metadata corrections without changing spoken script text."""
    if str(patch_manifest.get("episode_id", "")) != str(script.get("episode_id", "")):
        raise ValueError("metadata patch episode ID does not match the script")
    actual_sha = canonical_script_sha256(script)
    if str(patch_manifest.get("input_script_sha256", "")).lower() != actual_sha.lower():
        raise ValueError("metadata patch input script hash is stale")

    result = copy.deepcopy(script)
    rows_by_id = {
        str(row.get("sentence_id", "")): row for row in result.get("sentences", [])
    }
    claims = {
        str(row.get("claim_id", "")): row
        for row in claim_inventory.get("claims", [])
        if row.get("claim_id")
    }
    seen: set[str] = set()
    patches = patch_manifest.get("patches")
    if not isinstance(patches, list) or not patches:
        raise ValueError("metadata patch manifest has no patches")

    for patch in patches:
        unexpected = set(patch) - {"sentence_id", "segments"}
        if unexpected:
            raise ValueError(f"unsupported metadata patch fields: {sorted(unexpected)}")
        sentence_id = str(patch.get("sentence_id", ""))
        if sentence_id in seen:
            raise ValueError(f"duplicate metadata patch: {sentence_id}")
        if sentence_id not in rows_by_id:
            raise ValueError(f"unknown metadata patch sentence: {sentence_id}")
        seen.add(sentence_id)

        candidate = copy.deepcopy(rows_by_id[sentence_id])
        candidate["segments"] = copy.deepcopy(patch.get("segments"))
        for segment in candidate.get("segments") or []:
            if str(segment.get("text", "")) != str(candidate.get("tts_text", "")):
                raise ValueError(
                    f"segment text does not match spoken text: {sentence_id}"
                )
        _validate_new_sentence(candidate, claims)
        rows_by_id[sentence_id]["segments"] = _normalize_optional_evidence_fields(
            candidate["segments"]
        )

    return result


def compile_script_expansion(
    base_script: dict[str, Any],
    claim_inventory: dict[str, Any],
    expansion: dict[str, Any],
) -> dict[str, Any]:
    """Insert validated expansion blocks without rewriting existing sentences."""
    if str(expansion.get("episode_id", "")) != str(base_script.get("episode_id", "")):
        raise ValueError("expansion episode ID does not match the base script")
    actual_base_sha = canonical_script_sha256(base_script)
    if str(expansion.get("base_script_sha256", "")).lower() != actual_base_sha.lower():
        raise ValueError("expansion base script hash is stale")

    base_sentences = list(base_script.get("sentences", []))
    base_ids = [str(row.get("sentence_id", "")) for row in base_sentences]
    if not base_ids or len(base_ids) != len(set(base_ids)):
        raise ValueError("base script sentence IDs are missing or duplicate")
    base_by_id = {str(row["sentence_id"]): row for row in base_sentences}
    claims = {
        str(row.get("claim_id", "")): row
        for row in claim_inventory.get("claims", [])
        if row.get("claim_id")
    }

    blocks_by_anchor: dict[str, list[dict[str, Any]]] = {}
    all_new_ids: set[str] = set()
    for block in expansion.get("blocks", []):
        anchor = str(block.get("after_sentence_id", ""))
        if anchor not in base_by_id:
            raise ValueError(f"unknown expansion anchor: {anchor}")
        if anchor in blocks_by_anchor:
            raise ValueError(f"duplicate expansion anchor: {anchor}")
        if int(block.get("chapter", 0)) != int(base_by_id[anchor].get("chapter", 0)):
            raise ValueError(f"expansion chapter does not match anchor: {anchor}")

        new_rows: list[dict[str, Any]] = []
        for sentence in block.get("sentences", []):
            _validate_new_sentence(sentence, claims)
            sentence_id = str(sentence["sentence_id"])
            if sentence_id in base_by_id or sentence_id in all_new_ids:
                raise ValueError(f"duplicate sentence ID: {sentence_id}")
            if int(sentence["chapter"]) != int(block["chapter"]):
                raise ValueError(f"new sentence chapter does not match block: {sentence_id}")
            all_new_ids.add(sentence_id)
            normalized_sentence = copy.deepcopy(sentence)
            normalized_sentence["segments"] = _normalize_optional_evidence_fields(
                normalized_sentence["segments"]
            )
            new_rows.append(normalized_sentence)
        if not new_rows:
            raise ValueError(f"expansion block has no sentences: {anchor}")
        blocks_by_anchor[anchor] = new_rows

    result = copy.deepcopy(base_script)
    result["target_duration_sec"] = int(expansion["target_duration_sec"])
    combined: list[dict[str, Any]] = []
    for base_sentence in base_sentences:
        combined.append(copy.deepcopy(base_sentence))
        combined.extend(copy.deepcopy(blocks_by_anchor.get(str(base_sentence["sentence_id"]), [])))
    for order, sentence in enumerate(combined, start=1):
        sentence["order"] = order
    result["sentences"] = combined
    return result
