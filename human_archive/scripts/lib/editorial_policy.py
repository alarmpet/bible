# -*- coding: utf-8 -*-
"""Editorial policy and delivery profile validation library."""
from __future__ import annotations

from typing import Any


def load_delivery_profile(profile_id: str, profiles_data: dict[str, Any]) -> dict[str, Any]:
    profs = profiles_data.get("profiles", {})
    if profile_id not in profs:
        raise ValueError(f"Unknown profile '{profile_id}'")
    return profs[profile_id]


def validate_episode_contract(contract: dict[str, Any], profiles_data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    prof_id = contract.get("format_profile", "")
    profs = profiles_data.get("profiles", {})

    if prof_id not in profs:
        errors.append(f"Invalid format_profile '{prof_id}'")
        return errors

    prof = profs[prof_id]
    slogan = contract.get("slogan", "")
    if "3분" in slogan and not prof.get("allow_three_minute_slogan", False):
        errors.append("three-minute slogan requires quick_3m")

    target_dur = contract.get("target_duration_sec", 0)
    min_dur = prof.get("min_duration_sec", 0)
    max_dur = prof.get("max_duration_sec", 99999)
    if not (min_dur <= target_dur <= max_dur):
        errors.append(f"Target duration {target_dur}s out of range [{min_dur}, {max_dur}] for profile '{prof_id}'")

    return errors
