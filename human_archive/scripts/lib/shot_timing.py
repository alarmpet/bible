from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json


@dataclass(frozen=True)
class ShotTimingProfile:
    min_shot_sec: float
    target_shot_sec: float
    max_shot_sec: float
    hard_max_shot_sec: float
    max_sentences_per_shot: int


TRANSITION_PREFIXES = ("그런데", "하지만", "그렇다면", "결국", "문제는", "반면")


def is_preferred_boundary(previous, current):
    return (
        previous.get("chapter") != current.get("chapter")
        or previous.get("beat") != current.get("beat")
        or str(current.get("tts_text", "")).lstrip().startswith(TRANSITION_PREFIXES)
    )


def plan_shot_timing(
    script,
    audio_manifest,
    claims,
    profile,
    *,
    shot_id_prefix=None,
):
    by_id = {row["sentence_id"]: row for row in audio_manifest["sentences"]}
    sentences = sorted(script["sentences"], key=lambda row: int(row["order"]))
    sentence_by_id = {row["sentence_id"]: row for row in sentences}
    missing_audio = [
        row["sentence_id"] for row in sentences if row["sentence_id"] not in by_id
    ]
    if missing_audio:
        raise ValueError(f"sentence audio is missing: {missing_audio}")

    episode = str(script.get("episode_id", "HA002")).replace("-", "").lower()
    shot_id_prefix = str(shot_id_prefix or f"{episode}_shot")
    shots = []
    index = 0

    while index < len(sentences):
        first_sentence = sentences[index]
        first_audio = by_id[first_sentence["sentence_id"]]
        rows = [first_audio]
        start_sec = float(first_audio["start_sec"])
        end_sec = float(first_audio["end_sec"])
        next_index = index + 1
        boundary_reason = "target_duration"

        while (
            next_index < len(sentences)
            and len(rows) < profile.max_sentences_per_shot
        ):
            previous_sentence = sentences[next_index - 1]
            next_sentence = sentences[next_index]
            if previous_sentence.get("chapter") != next_sentence.get("chapter"):
                boundary_reason = "chapter"
                break

            candidate = by_id[next_sentence["sentence_id"]]
            current_duration = end_sec - start_sec
            candidate_duration = float(candidate["end_sec"]) - start_sec
            preferred = is_preferred_boundary(previous_sentence, next_sentence)

            if preferred and current_duration >= profile.min_shot_sec:
                boundary_reason = "preferred"
                break
            if candidate_duration <= profile.target_shot_sec or (
                current_duration < profile.min_shot_sec
                and candidate_duration <= profile.hard_max_shot_sec
            ):
                rows.append(candidate)
                end_sec = float(candidate["end_sec"])
                next_index += 1
                continue

            boundary_reason = "max_duration"
            break

        spans = []
        for row in rows:
            source = sentence_by_id[row["sentence_id"]]
            segments = source.get("segments") or [
                {
                    "char_start": 0,
                    "char_end": len(source.get("tts_text", "")),
                    "claim_id": None,
                }
            ]
            spans.extend(
                {"sentence_id": source["sentence_id"], **segment}
                for segment in segments
            )

        shots.append(
            {
                "shot_id": f"{shot_id_prefix}_{len(shots) + 1:03d}",
                "order": len(shots) + 1,
                "chapter": first_sentence.get("chapter", 1),
                "start_sec": start_sec,
                "end_sec": end_sec,
                "duration_sec": round(end_sec - start_sec, 3),
                "sentence_spans": spans,
                "claim_ids": [
                    segment["claim_id"] for segment in spans if segment.get("claim_id")
                ],
                "boundary_reason": boundary_reason,
            }
        )
        index = next_index

    timing_sha = hashlib.sha256(
        json.dumps(shots, sort_keys=True).encode()
    ).hexdigest()
    audio_sha = hashlib.sha256(
        json.dumps(audio_manifest, sort_keys=True).encode()
    ).hexdigest()
    return {
        "schema_version": 1,
        "episode_id": script.get("episode_id", "HA002"),
        "script_sha256": audio_manifest.get("script_sha256", ""),
        "sentence_audio_sha256": audio_sha,
        "profile_id": "narration_aligned_hybrid_v1",
        "timing_sha256": timing_sha,
        "shots": shots,
    }
