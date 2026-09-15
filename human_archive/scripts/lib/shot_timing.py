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


def _resolve_nollam_decay_zones(zones_cfg, total_duration_sec: float):
    """Resolve config/visual_pacing_profiles.yaml's nollam_decay_20m zone list
    against the *actual measured* episode duration, not a nominal 1200s target
    -- matching plan_shot_timing()'s own audio-driven, measured-not-estimated
    philosophy. The first five zones use fixed absolute seconds as declared in
    the YAML; late_body/outro are declared relative to the real end
    (end_offset_from_end_sec, with start_sec: -1 as an explicit "computed
    dynamically" sentinel on outro).
    """
    resolved = []
    for zone in zones_cfg:
        raw_start = zone.get("start_sec")
        # start_sec: -1 (or absent) is the "compute my start dynamically" sentinel
        # -- only the curve's last zone (outro) uses it, meaning "start
        # end_offset_from_end_sec seconds before the real end". That field is
        # then already spent describing this zone's START, not its end, so its
        # own END must be the measured episode end itself (offset 0), not a
        # second read of the same end_offset_from_end_sec value. Reusing it for
        # both used to resolve outro to the empty range [total-90, total-90),
        # which only ever produced a sensible zone because _zone_bounds_at()
        # falls back to the last zone in the list for any unmatched query --
        # true for every t >= total-90, masking the bug (see
        # test_pacing_scheduler_zone_source_of_truth.py's regression test).
        is_dynamic_start = raw_start is None or raw_start < 0
        if is_dynamic_start:
            start = total_duration_sec - float(zone["end_offset_from_end_sec"])
            end = total_duration_sec
        else:
            start = raw_start
            end_offset = zone.get("end_offset_from_end_sec")
            if end_offset is not None:
                end = total_duration_sec - float(end_offset)
            else:
                end = zone.get("end_sec")
                if end is None:
                    end = total_duration_sec
        resolved.append({**zone, "start_sec": float(start), "end_sec": float(end)})
    return resolved


def _zone_bounds_at(resolved_zones, time_sec: float):
    for zone in resolved_zones:
        if zone["start_sec"] <= time_sec < zone["end_sec"]:
            return zone
    return resolved_zones[-1]


class NollamDecayTimingProfile:
    """Time-varying shot-length bounds for a decay-curve pacing profile
    (e.g. nollam_decay_20m), resolved from config/visual_pacing_profiles.yaml's
    zone list. Exposes the same bounds shape as ShotTimingProfile via
    bounds_for(time_sec) so plan_shot_timing() can treat a flat profile and a
    zoned one uniformly (see 2026-09-15 overhaul plan Task 7 -- this replaces
    the previous behavior of plan_shot_timing() only ever accepting a single
    flat profile for the whole episode, which made channel profiles like
    nollam_decay_20m's 7-stage decay curve unusable at the real production
    entry point even though the curve itself was already fully defined in
    config).
    """

    def __init__(self, profile_id: str, zones_cfg, total_duration_sec: float):
        self.profile_id = profile_id
        self._zones = _resolve_nollam_decay_zones(list(zones_cfg), float(total_duration_sec))

    def bounds_for(self, time_sec: float) -> ShotTimingProfile:
        zone = _zone_bounds_at(self._zones, time_sec)
        return ShotTimingProfile(
            min_shot_sec=float(zone["min_shot_sec"]),
            target_shot_sec=float(zone["target_shot_sec"]),
            max_shot_sec=float(zone["hard_max_shot_sec"]),
            hard_max_shot_sec=float(zone["hard_max_shot_sec"]),
            max_sentences_per_shot=int(zone["max_sentences_per_shot"]),
        )


def _bounds_for(profile, time_sec: float) -> ShotTimingProfile:
    bounds_for = getattr(profile, "bounds_for", None)
    return bounds_for(time_sec) if bounds_for is not None else profile


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
    profile_id="narration_aligned_hybrid_v1",
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

        # Bounds are resolved once per shot from the shot's own start time, so a
        # time-varying (zoned) profile like nollam_decay_20m applies the right
        # stage of the decay curve; a flat profile just returns itself.
        active_bounds = _bounds_for(profile, start_sec)

        while (
            next_index < len(sentences)
            and len(rows) < active_bounds.max_sentences_per_shot
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

            if preferred and current_duration >= active_bounds.min_shot_sec:
                boundary_reason = "preferred"
                break
            if candidate_duration <= active_bounds.target_shot_sec or (
                current_duration < active_bounds.min_shot_sec
                and candidate_duration <= active_bounds.hard_max_shot_sec
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
        "profile_id": getattr(profile, "profile_id", profile_id),
        "timing_sha256": timing_sha,
        "shots": shots,
    }
