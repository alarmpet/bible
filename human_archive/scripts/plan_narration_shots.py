from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from lib.shot_timing import NollamDecayTimingProfile, ShotTimingProfile, plan_shot_timing

_HUMAN_ARCHIVE_ROOT = Path(__file__).resolve().parents[1]
_CHANNEL_PROFILES_PATH = _HUMAN_ARCHIVE_ROOT / "config" / "channel_profiles.yaml"
_PACING_PROFILES_PATH = _HUMAN_ARCHIVE_ROOT / "config" / "visual_pacing_profiles.yaml"


def resolve_pacing_profile_id(explicit_profile: str | None, channel_profile_id: str | None = None) -> str:
    """An explicit --profile always wins (keeps rebuilds of old legacy builds
    reproducible). Otherwise read pacing_profile_id off the active channel
    profile instead of hardcoding narration_aligned_hybrid_v1 for every
    channel -- nollam_file_v1's config/channel_profiles.yaml entry declares
    nollam_decay_20m, the 7-stage decay curve Sep2's master plan specified but
    this entry point never actually used (2026-09-15 overhaul plan Task 7).
    """
    if explicit_profile:
        return explicit_profile
    data = yaml.safe_load(_CHANNEL_PROFILES_PATH.read_text(encoding="utf-8")) or {}
    profiles = data.get("profiles", {})
    pid = channel_profile_id or data.get("default_profile_id")
    profile = profiles.get(pid, {})
    return str(profile.get("pacing_profile_id") or "narration_aligned_hybrid_v1")


def build_timing_profile(pacing_profile_id: str, total_duration_sec: float):
    """A flat profile (narration_aligned_hybrid_v1) applies the same shot-length
    bounds to the whole episode. A zoned profile (nollam_decay_20m) declares
    seven time-relative zones in visual_pacing_profiles.yaml -- resolved here
    against total_duration_sec measured from the real TTS audio, not a nominal
    target, matching this pipeline's "measured, not estimated" philosophy.
    """
    cfg = yaml.safe_load(_PACING_PROFILES_PATH.read_text(encoding="utf-8"))[pacing_profile_id]
    if "zones" in cfg:
        return NollamDecayTimingProfile(pacing_profile_id, cfg["zones"], total_duration_sec)
    return ShotTimingProfile(
        cfg["min_shot_sec"],
        cfg["target_shot_sec"],
        cfg["max_shot_sec"],
        cfg["hard_max_shot_sec"],
        cfg["max_sentences_per_shot"],
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", type=Path, required=True)
    ap.add_argument("--audio", type=Path, required=True)
    ap.add_argument(
        "--profile",
        default=None,
        help="Pacing profile id (e.g. nollam_decay_20m, narration_aligned_hybrid_v1). "
        "Defaults to the active channel profile's pacing_profile_id.",
    )
    ap.add_argument(
        "--channel-profile",
        default=None,
        help="Channel profile id to resolve --profile from when --profile is omitted "
        "(defaults to channel_profiles.yaml's default_profile_id).",
    )
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--claims", type=Path)
    ap.add_argument("--shot-id-prefix")
    args = ap.parse_args()

    script = json.loads(args.script.read_text(encoding="utf-8"))
    audio = json.loads(args.audio.read_text(encoding="utf-8"))
    claims = json.loads(args.claims.read_text(encoding="utf-8")) if args.claims and args.claims.exists() else {}

    pacing_profile_id = resolve_pacing_profile_id(args.profile, args.channel_profile)
    total_duration_sec = max((float(row["end_sec"]) for row in audio["sentences"]), default=0.0)
    profile = build_timing_profile(pacing_profile_id, total_duration_sec)

    result = plan_shot_timing(
        script, audio, claims, profile,
        shot_id_prefix=args.shot_id_prefix,
        profile_id=pacing_profile_id,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
