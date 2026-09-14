# -*- coding: utf-8 -*-
"""Fail-closed physical checks for the Human Library exact release bundle."""

from __future__ import annotations

import hashlib
import re
import struct
from pathlib import Path
from typing import Any

from PIL import Image


ASS_TIME_RE = re.compile(r"^(\d+):(\d{2}):(\d{2})\.(\d{2})$")


def _ass_time_to_seconds(value: str) -> float:
    match = ASS_TIME_RE.match(value.strip())
    if not match:
        raise ValueError(f"invalid ASS time: {value!r}")
    hours, minutes, seconds, centiseconds = (int(part) for part in match.groups())
    return hours * 3600.0 + minutes * 60.0 + seconds + centiseconds / 100.0


def audit_ass_strict(path: Path, *, target_duration_sec: float | None = None) -> dict[str, Any]:
    """Audit an ASS file for non-overlapping, strictly one-line events."""
    path = Path(path)
    errors: list[str] = []
    events: list[tuple[float, float, str]] = []

    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except Exception as exc:
        return {
            "status": "FAIL",
            "dialogue_events": 0,
            "zero_start_events": 0,
            "overlap_events": 0,
            "multiline_events": 0,
            "errors": [f"ASS read failed: {exc}"],
        }

    for line_number, line in enumerate(lines, start=1):
        if not line.startswith("Dialogue:"):
            continue
        fields = line[len("Dialogue:") :].split(",", 9)
        if len(fields) != 10:
            errors.append(f"line {line_number}: malformed Dialogue field count")
            continue
        try:
            start = _ass_time_to_seconds(fields[1])
            end = _ass_time_to_seconds(fields[2])
        except ValueError as exc:
            errors.append(f"line {line_number}: {exc}")
            continue
        if end <= start:
            errors.append(f"line {line_number}: non-positive interval")
        # ASS stores centiseconds; allow one centisecond of terminal quantization.
        if target_duration_sec is not None and end > target_duration_sec + 0.011:
            errors.append(f"line {line_number}: end exceeds target duration")
        events.append((start, end, fields[9]))

    zero_starts = sum(start <= 0.0 for start, _, _ in events)
    overlap_events = sum(
        events[index][0] < events[index - 1][1]
        for index in range(1, len(events))
    )
    multiline_events = sum(r"\N" in text for _, _, text in events)

    if zero_starts:
        errors.append(f"{zero_starts} event(s) start at or before 0 seconds")
    if overlap_events:
        errors.append(f"{overlap_events} overlapping event boundary(ies)")
    if multiline_events:
        errors.append(f"{multiline_events} event(s) contain ASS newline\\N")

    return {
        "status": "PASS" if not errors else "FAIL",
        "dialogue_events": len(events),
        "zero_start_events": zero_starts,
        "overlap_events": overlap_events,
        "multiline_events": multiline_events,
        "errors": errors,
    }


def count_wav_sample_frames(path: Path) -> int:
    """Count interleaved PCM sample frames from the RIFF data chunk."""
    path = Path(path)
    with path.open("rb") as handle:
        header = handle.read(12)
        if len(header) != 12 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
            raise ValueError("not a RIFF/WAVE file")

        channels: int | None = None
        block_align: int | None = None
        data_bytes: int | None = None
        while True:
            chunk_header = handle.read(8)
            if not chunk_header:
                break
            if len(chunk_header) != 8:
                raise ValueError("truncated RIFF chunk header")
            chunk_id, chunk_size = struct.unpack("<4sI", chunk_header)
            chunk_data = handle.read(chunk_size)
            if len(chunk_data) != chunk_size:
                raise ValueError(f"truncated RIFF chunk: {chunk_id!r}")
            if chunk_size % 2:
                handle.seek(1, 1)
            if chunk_id == b"fmt ":
                if chunk_size < 16:
                    raise ValueError("invalid fmt chunk")
                _, channels, _, _, block_align, _ = struct.unpack(
                    "<HHIIHH", chunk_data[:16]
                )
            elif chunk_id == b"data":
                data_bytes = chunk_size

    if channels is None or block_align is None or data_bytes is None:
        raise ValueError("WAV is missing fmt or data chunk")
    if channels <= 0 or block_align <= 0:
        raise ValueError("invalid WAV channel/block alignment")
    if data_bytes % block_align:
        raise ValueError("WAV data chunk is not aligned to sample frames")
    return data_bytes // block_align


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def validate_plate_manifest(
    plates: list[dict[str, Any]],
    *,
    expected_count: int | None = None,
    expected_dimensions: tuple[int, int] = (2304, 1296),
) -> dict[str, Any]:
    """Require physically bound, hashed, dimensioned, unique plate assets."""
    errors: list[str] = []
    hashes: list[str] = []
    if expected_count is not None and len(plates) != expected_count:
        errors.append(f"expected {expected_count} plates, got {len(plates)}")

    for index, plate in enumerate(plates, start=1):
        label = str(plate.get("plate_id") or f"plate[{index}]")
        raw_path = plate.get("path")
        if not raw_path:
            errors.append(f"{label}: path is required")
            continue
        path = Path(str(raw_path))
        if not path.is_file() or path.stat().st_size <= 0:
            errors.append(f"{label}: path does not point to a non-empty file")
            continue
        declared_sha = str(plate.get("sha256") or "").upper()
        if not declared_sha:
            errors.append(f"{label}: sha256 is required")
        actual_sha = _sha256_file(path)
        hashes.append(actual_sha)
        if declared_sha and declared_sha != actual_sha:
            errors.append(f"{label}: sha256 mismatch")
        try:
            with Image.open(path) as image:
                actual_dimensions = image.size
        except Exception as exc:
            errors.append(f"{label}: image decode failed: {exc}")
            continue
        if actual_dimensions != expected_dimensions:
            errors.append(
                f"{label}: dimensions {actual_dimensions[0]}x{actual_dimensions[1]} "
                f"!= {expected_dimensions[0]}x{expected_dimensions[1]}"
            )
        if plate.get("width") != expected_dimensions[0] or plate.get("height") != expected_dimensions[1]:
            errors.append(f"{label}: declared width/height do not match required dimensions")

    unique_content_count = len(set(hashes))
    if len(hashes) != unique_content_count:
        errors.append("duplicate plate content hash detected")
    return {
        "status": "PASS" if not errors else "FAIL",
        "plate_count": len(plates),
        "unique_content_count": unique_content_count,
        "errors": errors,
    }


def validate_video_probe(
    probe: dict[str, Any],
    *,
    target_frames: int = 29_195,
    target_fps: str = "30/1",
    target_duration_sec: float = 973.166667,
    duration_tolerance_sec: float = 0.033333,
) -> dict[str, Any]:
    """Validate exact video geometry, CFR metadata, frame count, and duration."""
    errors: list[str] = []
    if str(probe.get("codec_name", "")).lower() != "h264":
        errors.append("video codec must be H.264")
    if not str(probe.get("profile", "")).lower().startswith("high"):
        errors.append("video profile must be H.264 High")
    if int(probe.get("width", 0)) != 1920 or int(probe.get("height", 0)) != 1080:
        errors.append("video geometry must be 1920x1080")
    if probe.get("r_frame_rate") != target_fps or probe.get("avg_frame_rate") != target_fps:
        errors.append("video must be 30/1 CFR")
    if int(probe.get("nb_frames", 0)) != target_frames:
        errors.append(f"frame count must be exactly {target_frames}")
    try:
        duration = float(probe["duration"])
    except (KeyError, TypeError, ValueError):
        errors.append("video duration is missing or invalid")
    else:
        if abs(duration - target_duration_sec) > duration_tolerance_sec:
            errors.append("video duration exceeds tolerance")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def validate_audio_probe(probe: dict[str, Any]) -> dict[str, Any]:
    """Validate the clean-scope release audio stream contract."""
    errors: list[str] = []
    if str(probe.get("codec_name", "")).lower() != "aac":
        errors.append("audio codec must be AAC")
    if int(probe.get("sample_rate", 0)) != 48_000:
        errors.append("audio sample rate must be 48000 Hz")
    if int(probe.get("channels", 0)) != 2:
        errors.append("audio must be stereo")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def compute_sha256_chain(entries: list[dict[str, str]]) -> str:
    """Compute a deterministic root over ordered artifact id/hash pairs."""
    payload = "".join(
        f"{entry['artifact_id'].strip()}:{entry['sha256'].strip().upper()}\n"
        for entry in entries
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def validate_manifest_chain(manifest: dict[str, Any]) -> dict[str, Any]:
    """Require ordered chain entries and a matching chain root digest."""
    errors: list[str] = []
    entries = manifest.get("sha256_chain")
    root = str(manifest.get("sha256_chain_root") or "").upper()
    if not isinstance(entries, list) or not entries:
        return {"status": "FAIL", "errors": ["sha256_chain must be a non-empty list"]}
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict) or not entry.get("artifact_id") or not entry.get("sha256"):
            errors.append(f"chain entry {index} requires artifact_id and sha256")
            continue
        artifact_id = str(entry["artifact_id"]).strip()
        sha256 = str(entry["sha256"]).strip().upper()
        if artifact_id in seen:
            errors.append(f"duplicate chain artifact_id: {artifact_id}")
        seen.add(artifact_id)
        normalized.append({"artifact_id": artifact_id, "sha256": sha256})
    if not root:
        errors.append("sha256_chain_root is required")
    elif normalized and root != compute_sha256_chain(normalized):
        errors.append("sha256_chain_root mismatch")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def audit_subcut_montage_plan(
    cuts: list[dict[str, Any]],
    *,
    expected_total_frames: int = 43200,
    expected_min_cuts: int = 800,
    expected_max_cuts: int = 900,
    allow_aba_repeats: bool = False,
) -> dict[str, Any]:
    """Audit ordered subcut montage plan for A/B toggle loops and role progression.

    Enforces Task 5 fail-closed invariants:
    - Total cuts within bounds [expected_min_cuts, expected_max_cuts]
    - Total frames exactly matches expected_total_frames
    - aba_repeat_count == 0 (no A-B-A or B-A-B 2-back toggle loops)
    - Monotonic role progression (no context_wide after detail_evidence within a parent shot)
    """
    errors: list[str] = []
    total_cuts = len(cuts)
    total_frames = sum(int(c.get("frame_count", 0)) for c in cuts)

    if not (expected_min_cuts <= total_cuts <= expected_max_cuts):
        errors.append(f"cut count {total_cuts} out of bounds [{expected_min_cuts}, {expected_max_cuts}]")

    if total_frames != expected_total_frames:
        errors.append(f"total frames {total_frames} != {expected_total_frames}")

    same_parent_adjacent = 0
    same_parent_plate_changes = 0
    aba_repeats = 0
    aba_examples: list[str] = []

    for i in range(1, total_cuts):
        prev = cuts[i - 1]
        curr = cuts[i]
        if curr.get("parent_shot_id") == prev.get("parent_shot_id"):
            same_parent_adjacent += 1
            if curr.get("plate_id") != prev.get("plate_id"):
                same_parent_plate_changes += 1

    for i in range(2, total_cuts):
        c_curr = cuts[i]
        c_prev = cuts[i - 1]
        c_prev2 = cuts[i - 2]
        curr_p = str(c_curr.get("plate_id", ""))
        prev_p = str(c_prev.get("plate_id", ""))
        prev2_p = str(c_prev2.get("plate_id", ""))
        if curr_p and curr_p == prev2_p and curr_p != prev_p:
            aba_repeats += 1
            if len(aba_examples) < 5:
                aba_examples.append(f"cut {i} ({curr_p}) == cut {i - 2} via {prev_p}")

    if aba_repeats > 0 and not allow_aba_repeats:
        errors.append(
            f"detected {aba_repeats} A-B-A / B-A-B toggle loop(s); baseline requires 0. Examples: {'; '.join(aba_examples)}"
        )

    shots_cuts: dict[str, list[dict[str, Any]]] = {}
    for c in cuts:
        shots_cuts.setdefault(str(c.get("parent_shot_id", "")), []).append(c)

    role_reversals = 0
    for shot_id, s_cuts in shots_cuts.items():
        seen_detail = False
        for c in s_cuts:
            role = str(c.get("role", ""))
            plate_id = str(c.get("plate_id", ""))
            if role == "detail_evidence" or plate_id.endswith("_B"):
                seen_detail = True
            elif role == "context_wide" or plate_id.endswith("_A"):
                if seen_detail:
                    role_reversals += 1
                    errors.append(
                        f"shot {shot_id}: role reversal detected (context_wide/Plate A after detail_evidence/Plate B)"
                    )
                    break

    return {
        "status": "PASS" if not errors else "FAIL",
        "total_cuts": total_cuts,
        "total_frames": total_frames,
        "same_parent_adjacent_transitions": same_parent_adjacent,
        "same_parent_plate_changes": same_parent_plate_changes,
        "aba_repeats": aba_repeats,
        "role_reversals": role_reversals,
        "errors": errors,
    }
