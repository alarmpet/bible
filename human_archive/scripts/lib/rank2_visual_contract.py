# -*- coding: utf-8 -*-
"""Shared visual contract for the Rank 2 candidate renderer.

This module deliberately keeps planning decisions separate from FFmpeg.  The
planner emits an auditable edit graph; the renderer only consumes that graph.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image


MOTION_GRAMMAR: tuple[dict[str, Any], ...] = (
    {
        "motion_family": "establish",
        "transformation": "wide_establishing",
        "start_zoom": 1.03,
        "end_zoom": 1.08,
        "start_cx": 0.50,
        "end_cx": 0.47,
        "start_cy": 0.47,
        "end_cy": 0.45,
        "start_rotation": 0.0,
        "end_rotation": 0.0,
    },
    {
        "motion_family": "push",
        "transformation": "push_in",
        "start_zoom": 1.04,
        "end_zoom": 1.14,
        "start_cx": 0.48,
        "end_cx": 0.50,
        "start_cy": 0.46,
        "end_cy": 0.42,
        "start_rotation": 0.0,
        "end_rotation": 0.35,
    },
    {
        "motion_family": "lateral_reveal",
        "transformation": "pan_right",
        "start_zoom": 1.08,
        "end_zoom": 1.08,
        "start_cx": 0.42,
        "end_cx": 0.58,
        "start_cy": 0.45,
        "end_cy": 0.45,
        "start_rotation": 0.0,
        "end_rotation": 0.0,
    },
    {
        "motion_family": "evidence_macro",
        "transformation": "macro_detail",
        "start_zoom": 1.12,
        "end_zoom": 1.28,
        "start_cx": 0.52,
        "end_cx": 0.53,
        "start_cy": 0.42,
        "end_cy": 0.39,
        "start_rotation": 0.0,
        "end_rotation": -0.25,
    },
    {
        "motion_family": "pull",
        "transformation": "pull_out",
        "start_zoom": 1.14,
        "end_zoom": 1.04,
        "start_cx": 0.52,
        "end_cx": 0.50,
        "start_cy": 0.42,
        "end_cy": 0.46,
        "start_rotation": 0.0,
        "end_rotation": 0.0,
    },
    {
        "motion_family": "lateral_reveal",
        "transformation": "pan_left",
        "start_zoom": 1.08,
        "end_zoom": 1.08,
        "start_cx": 0.58,
        "end_cx": 0.42,
        "start_cy": 0.45,
        "end_cy": 0.45,
        "start_rotation": 0.0,
        "end_rotation": 0.0,
    },
)


V3_CALM_MOTION_GRAMMAR: tuple[dict[str, Any], ...] = (
    {
        "motion_family": "calm_establish",
        "transformation": "wide_establishing",
        "start_zoom": 1.02,
        "end_zoom": 1.04,
        "start_cx": 0.50,
        "end_cx": 0.50,
        "start_cy": 0.46,
        "end_cy": 0.46,
        "start_rotation": 0.0,
        "end_rotation": 0.0,
    },
    {
        "motion_family": "calm_push",
        "transformation": "push_in",
        "start_zoom": 1.04,
        "end_zoom": 1.10,
        "start_cx": 0.50,
        "end_cx": 0.50,
        "start_cy": 0.45,
        "end_cy": 0.45,
        "start_rotation": 0.0,
        "end_rotation": 0.0,
    },
    {
        "motion_family": "calm_pan_right",
        "transformation": "pan_right",
        "start_zoom": 1.06,
        "end_zoom": 1.06,
        "start_cx": 0.46,
        "end_cx": 0.54,
        "start_cy": 0.45,
        "end_cy": 0.45,
        "start_rotation": 0.0,
        "end_rotation": 0.0,
    },
    {
        "motion_family": "calm_evidence",
        "transformation": "macro_detail",
        "start_zoom": 1.08,
        "end_zoom": 1.15,
        "start_cx": 0.50,
        "end_cx": 0.50,
        "start_cy": 0.44,
        "end_cy": 0.44,
        "start_rotation": 0.0,
        "end_rotation": 0.0,
    },
    {
        "motion_family": "calm_pull",
        "transformation": "pull_out",
        "start_zoom": 1.10,
        "end_zoom": 1.05,
        "start_cx": 0.50,
        "end_cx": 0.50,
        "start_cy": 0.45,
        "end_cy": 0.45,
        "start_rotation": 0.0,
        "end_rotation": 0.0,
    },
    {
        "motion_family": "calm_pan_left",
        "transformation": "pan_left",
        "start_zoom": 1.06,
        "end_zoom": 1.06,
        "start_cx": 0.54,
        "end_cx": 0.46,
        "start_cy": 0.45,
        "end_cy": 0.45,
        "start_rotation": 0.0,
        "end_rotation": 0.0,
    },
)


V3_PACING_POLICY: dict[str, Any] = {
    "visible_cut_budget": (420, 480),
    "first_10s_max_cuts": 4,
    "first_30s_max_cuts": 10,
    "hook_motion_per_cut": 1,
    "hook_duration_sec": (1.4, 2.5),
    # 455 visible cuts over 1,440 seconds imply a ~3.16s median. Longer
    # explanatory holds are represented as internal reframes, not extra cuts.
    "body_duration_sec": (3.0, 5.0),
    "max_zoom_delta": 0.08,
    "max_pan_delta": 0.10,
    "max_rotation_delta": 0.20,
}


def build_v3_pacing_policy() -> dict[str, Any]:
    """Return an immutable-by-copy pacing policy for the calm V3 candidate."""
    return {
        key: (tuple(value) if isinstance(value, tuple) else value)
        for key, value in V3_PACING_POLICY.items()
    }


def annotate_cut_contract(
    cut: Mapping[str, Any],
    lineage: Mapping[str, Sequence[str]],
    *,
    visual_beat: str,
    motion_profile: Mapping[str, Any],
    transition_in: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a cut record with all provenance and encoded-edit metadata."""
    required = ("sentence_ids", "cue_ids", "claim_ids")
    missing = [name for name in required if not lineage.get(name)]
    if missing:
        raise ValueError(f"{cut.get('cut_id', '<unknown>')}: missing lineage {missing}")
    result = dict(cut)
    result.update(
        {
            "sentence_ids": list(lineage["sentence_ids"]),
            "cue_ids": list(lineage["cue_ids"]),
            "claim_ids": list(lineage["claim_ids"]),
            "visual_beat": str(visual_beat),
            "motion_profile": dict(motion_profile),
            "transition_in": dict(transition_in),
        }
    )
    return result


def blend_transition_frame(
    previous: np.ndarray, current: np.ndarray, progress: float
) -> np.ndarray:
    """Blend two equal-size RGB frames with a clamped linear alpha."""
    if previous.shape != current.shape:
        raise ValueError("transition frames must have identical shapes")
    alpha = max(0.0, min(1.0, float(progress)))
    mixed = previous.astype(np.float32) * (1.0 - alpha) + current.astype(np.float32) * alpha
    return np.rint(mixed).astype(np.uint8)


def build_rank2_lineage(
    normalized_bundle: Mapping[str, Any],
    normalized_script: Mapping[str, Any],
    canonical_manifest: Mapping[str, Any],
) -> dict[str, dict[str, list[str]]]:
    """Build and validate the shot-level SSOT lineage index.

    Missing sentence, cue, or claim references fail closed.  A renderer must
    never invent a visual relationship that cannot be traced to the script.
    """
    sentences = {str(s["sentence_id"]): s for s in normalized_script.get("sentences", [])}
    mappings = canonical_manifest.get("sentence_mappings", {})
    cues = {str(c["cue_id"]): c for c in canonical_manifest.get("cues", [])}
    result: dict[str, dict[str, list[str]]] = {}

    for shot in normalized_bundle.get("shots", []):
        shot_id = str(shot["shot_id"])
        sentence_ids = [str(x) for x in shot.get("sentence_spans", [])]
        if not sentence_ids:
            raise ValueError(f"{shot_id}: sentence_spans is empty")
        missing_sentences = [sid for sid in sentence_ids if sid not in sentences]
        if missing_sentences:
            raise ValueError(f"{shot_id}: missing sentence references {missing_sentences}")

        cue_ids: list[str] = []
        for sid in sentence_ids:
            mapped = mappings.get(sid, [])
            if isinstance(mapped, Mapping):
                mapped = mapped.get("cue_ids", [])
            cue_ids.extend(str(x) for x in mapped)
        cue_ids = list(dict.fromkeys(cue_ids))
        missing_cues = [cid for cid in cue_ids if cid not in cues]
        if missing_cues:
            raise ValueError(f"{shot_id}: missing cue references {missing_cues}")
        if not cue_ids:
            raise ValueError(f"{shot_id}: no canonical cues mapped")

        claim_ids: list[str] = []
        for sid in sentence_ids:
            claim_ids.extend(str(x) for x in sentences[sid].get("claim_ids", []))
        claim_ids = list(dict.fromkeys(claim_ids))
        if not claim_ids:
            raise ValueError(f"{shot_id}: no claim references")

        result[shot_id] = {
            "sentence_ids": sentence_ids,
            "cue_ids": cue_ids,
            "claim_ids": claim_ids,
        }
    return result


def choose_motion_profile(
    shot_index: int,
    cut_index: int,
    cut_count: int,
    *,
    pacing: str = "v2",
) -> dict[str, Any]:
    """Choose a deterministic shot-local profile with a visible trajectory.

    The shot index selects a visual grammar family and the local cut index
    selects a complementary beat.  It is intentionally independent of the
    absolute global cut number, preventing a 837-cut modulo loop.
    """
    if shot_index < 0 or cut_index < 0 or cut_count <= 0 or cut_index >= cut_count:
        raise ValueError("invalid shot-local motion coordinates")
    if pacing not in {"v2", "v3_calm"}:
        raise ValueError(f"unknown pacing policy: {pacing}")
    grammar = V3_CALM_MOTION_GRAMMAR if pacing == "v3_calm" else MOTION_GRAMMAR
    profile = dict(grammar[(shot_index + cut_index) % len(grammar)])
    profile["easing"] = "cosine_s"
    profile["visual_beat"] = "context" if cut_index == 0 else "evidence"
    profile["local_cut_index"] = cut_index
    profile["local_cut_count"] = cut_count
    profile["pacing"] = pacing
    profile["max_zoom_delta"] = round(abs(profile["end_zoom"] - profile["start_zoom"]), 6)
    profile["max_pan_delta"] = round(
        max(
            abs(profile["end_cx"] - profile["start_cx"]),
            abs(profile["end_cy"] - profile["start_cy"]),
        ),
        6,
    )
    profile["max_rotation_delta"] = round(
        abs(profile["end_rotation"] - profile["start_rotation"]), 6
    )
    return profile


def transition_for_boundary(
    *, previous_shot: str, next_shot: str, previous_index: int, pacing: str = "v2"
) -> dict[str, Any]:
    """Return a bounded transition policy for one encoded boundary."""
    if previous_shot == next_shot:
        return {"type": "hard_cut", "frames": 0}
    if pacing == "v3_calm":
        # One restrained transition roughly every fifth shot boundary.  The
        # rest remain clean hard cuts so the transition itself never becomes
        # the subject of the documentary.
        choices = (
            {"type": "hard_cut", "frames": 0},
            {"type": "hard_cut", "frames": 0},
            {"type": "hard_cut", "frames": 0},
            {"type": "hard_cut", "frames": 0},
            {"type": "dissolve", "frames": 6},
        )
    elif pacing == "v2":
        choices = (
            {"type": "match_cut", "frames": 4},
            {"type": "dissolve", "frames": 8},
            {"type": "whip_pan", "frames": 6},
            {"type": "hard_cut", "frames": 0},
        )
    else:
        raise ValueError(f"unknown pacing policy: {pacing}")
    return dict(choices[previous_index % len(choices)])


def audit_visual_anchor_contract(
    records: Sequence[Mapping[str, Any]],
    *,
    required_fields: Sequence[str] = ("place", "subject", "action", "era", "evidence_role"),
) -> dict[str, Any]:
    """Fail closed when a cut has no explicit semantic visual anchors.

    This is a metadata/asset contract, not a claim of pixel-level semantic
    understanding.  Human preview or an approved vision model remains
    required for the final correspondence decision.
    """
    errors: list[str] = []
    reviewed = 0
    for record in records:
        cut_id = str(record.get("cut_id") or record.get("plate_id") or record.get("shot_id") or "<unknown>")
        anchors = record.get("semantic_anchors")
        if not isinstance(anchors, Mapping):
            errors.append(f"{cut_id}: semantic_anchors missing")
            continue
        missing = [field for field in required_fields if not str(anchors.get(field, "")).strip()]
        if missing:
            errors.append(f"{cut_id}: missing semantic anchors {missing}")
        if not record.get("sentence_ids"):
            errors.append(f"{cut_id}: sentence lineage missing")
        if not record.get("claim_ids"):
            errors.append(f"{cut_id}: claim lineage missing")
        reviewed += 1
    return {
        "status": "PASS" if not errors else "FAIL",
        "record_count": len(records),
        "reviewed_count": reviewed,
        "pixel_semantic_verification_required": True,
        "errors": errors,
    }


def audit_v3_pacing(cuts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Audit visible-cut density and single-axis motion for the V3 candidate."""
    policy = build_v3_pacing_policy()
    errors: list[str] = []
    first_10 = sum(float(c.get("start_sec", 0.0)) < 10.0 for c in cuts)
    first_30 = sum(float(c.get("start_sec", 0.0)) < 30.0 for c in cuts)
    if not (policy["visible_cut_budget"][0] <= len(cuts) <= policy["visible_cut_budget"][1]):
        errors.append(f"visible cut count {len(cuts)} outside {policy['visible_cut_budget']}")
    if first_10 > policy["first_10s_max_cuts"]:
        errors.append(f"first 10s has {first_10} cuts")
    if first_30 > policy["first_30s_max_cuts"]:
        errors.append(f"first 30s has {first_30} cuts")

    overloaded: list[str] = []
    for cut in cuts:
        profile = cut.get("motion_profile", {})
        active = sum(
            abs(float(profile.get(end, 0.0)) - float(profile.get(start, 0.0))) > 1e-6
            for start, end in (
                ("start_zoom", "end_zoom"),
                ("start_cx", "end_cx"),
                ("start_cy", "end_cy"),
                ("start_rotation", "end_rotation"),
            )
        )
        if active > policy["hook_motion_per_cut"]:
            overloaded.append(str(cut.get("cut_id", "<unknown>")))
        if float(profile.get("max_zoom_delta", 0.0)) > policy["max_zoom_delta"] + 1e-6:
            errors.append(f"{cut.get('cut_id', '<unknown>')}: zoom delta exceeds V3 limit")
        if float(profile.get("max_pan_delta", 0.0)) > policy["max_pan_delta"] + 1e-6:
            errors.append(f"{cut.get('cut_id', '<unknown>')}: pan delta exceeds V3 limit")
        if float(profile.get("max_rotation_delta", 0.0)) > policy["max_rotation_delta"] + 1e-6:
            errors.append(f"{cut.get('cut_id', '<unknown>')}: rotation delta exceeds V3 limit")
    if overloaded:
        errors.append(f"multi-transform cuts: {overloaded[:8]}")
    return {
        "status": "PASS" if not errors else "FAIL",
        "cut_count": len(cuts),
        "first_10s_cuts": first_10,
        "first_30s_cuts": first_30,
        "multi_transform_count": len(overloaded),
        "errors": errors,
    }


def detect_baked_in_plate_artifacts(path: str | Path) -> dict[str, Any]:
    """Detect likely provider marks and subtitle-safe-area contamination."""
    image = Image.open(path).convert("RGB")
    image.thumbnail((640, 360), Image.Resampling.BILINEAR)
    arr = np.asarray(image, dtype=np.float32)
    h, w, _ = arr.shape
    bottom = arr[int(h * 0.82) :, :, :]
    bottom_mean = float(bottom.mean())
    band_height = max(1, int(h * 0.08))
    band = arr[h - band_height :, :, :]
    band_mean = float(band.mean())
    band_contrast = float(band.std())

    bottom_band_detected = bool(band_mean < 65.0 and band_contrast < 35.0)
    mark_region = arr[int(h * 0.76) :, int(w * 0.82) :, :]
    mark_mean = float(mark_region.mean())
    mark_contrast = float(mark_region.std())
    # The known Flow artifact is a gray diamond embedded in the dark lower
    # provider band.  Requiring that band avoids mistaking ordinary dark
    # documentary subjects (rocks, trees, night scenes) for a watermark.
    provider_mark_detected = bool(
        bottom_band_detected and mark_mean < 120.0 and mark_contrast > 8.0
    )
    errors: list[str] = []
    if provider_mark_detected:
        errors.append("provider_mark_detected")
    if bottom_band_detected:
        errors.append("baked_in_bottom_band_detected")
    return {
        "status": "PASS" if not errors else "FAIL",
        "path": str(Path(path)),
        "provider_mark_detected": provider_mark_detected,
        "bottom_band_detected": bottom_band_detected,
        "bottom_mean": round(bottom_mean, 3),
        "bottom_band_mean": round(band_mean, 3),
        "bottom_band_contrast": round(band_contrast, 3),
        "errors": errors,
    }


def audit_plate_directory(directory: str | Path, *, expected_count: int) -> dict[str, Any]:
    """Run the clean-plate gate over the exact A/B asset directory."""
    directory = Path(directory)
    paths = sorted(
        p for p in directory.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ) if directory.is_dir() else []
    reports = [detect_baked_in_plate_artifacts(path) for path in paths]
    dirty = [report for report in reports if report["status"] != "PASS"]
    errors: list[str] = []
    if len(paths) != expected_count:
        errors.append(f"plate count {len(paths)} != {expected_count}")
    if dirty:
        errors.append(f"dirty plates {len(dirty)}")
    return {
        "status": "PASS" if not errors else "FAIL",
        "directory": str(directory),
        "plate_count": len(paths),
        "dirty_count": len(dirty),
        "reports": reports,
        "errors": errors,
    }


def prepare_clean_plate_set(
    source_directory: str | Path,
    target_directory: str | Path,
    *,
    output_size: tuple[int, int] = (2304, 1296),
) -> dict[str, Any]:
    """Create a derived 16:9 candidate set with the known lower provider band removed.

    This is a reversible candidate transform, not an inpaint operation.  The
    original Flow files remain untouched and the resulting directory must pass
    the artifact audit before it can be used by the renderer.
    """
    source_directory = Path(source_directory)
    target_directory = Path(target_directory)
    target_directory.mkdir(parents=True, exist_ok=True)
    source_paths = sorted(
        p for p in source_directory.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ) if source_directory.is_dir() else []
    if not source_paths:
        return {"status": "FAIL", "method": "top_safe_crop_16x9", "created": 0, "errors": ["no source plates"]}

    for source in source_paths:
        with Image.open(source) as image:
            image = image.convert("RGB")
            probe = np.asarray(image.resize((320, 180), Image.Resampling.BILINEAR), dtype=np.float32)
            row_mean = probe.mean(axis=(1, 2))
            row_contrast = probe.std(axis=(1, 2))
            dark_rows = (row_mean < 65.0) & (row_contrast < 35.0)
            band_top = next(
                (
                    index for index in range(90, 170)
                    if dark_rows[index : min(180, index + 10)].all()
                ),
                None,
            )
            # A conservative fallback is intentional: three source plates have
            # a textured transition immediately above the otherwise flat band.
            crop_ratio = ((max(1, band_top - 6) / 180.0) if band_top is not None else 0.79)
            crop_h = max(1, int(round(image.height * crop_ratio)))
            crop_w = max(1, int(round(crop_h * 16.0 / 9.0)))
            crop_w = min(crop_w, image.width)
            left = max(0, (image.width - crop_w) // 2)
            crop = image.crop((left, 0, left + crop_w, crop_h))
            clean = crop.resize(output_size, Image.Resampling.LANCZOS)
            clean.save(target_directory / f"{source.stem}.jpg", format="JPEG", quality=95, optimize=True)

    audit = audit_plate_directory(target_directory, expected_count=len(source_paths))
    audit["method"] = "top_safe_crop_16x9"
    audit["source_directory"] = str(source_directory)
    audit["target_directory"] = str(target_directory)
    audit["created"] = len(source_paths)
    return audit
