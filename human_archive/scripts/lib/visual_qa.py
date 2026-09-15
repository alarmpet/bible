# -*- coding: utf-8 -*-
"""Actual pixel-level visual QA and semantic axis evaluation library."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import imagehash
from PIL import Image

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]

REQUIRED_VISUAL_AXES = (
    "semantic_match",
    "historical_subject",
    "host_presence",
    "embedded_text",
    "composition_density",
    "style_profile",
    "dignity",
    "service_mark",
)


def verify_image_pixel_integrity(img_path: Path) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if not img_path.exists():
        return False, [f"Image file does not exist: {img_path}"]

    try:
        with Image.open(img_path) as img:
            img.verify()
        with Image.open(img_path) as img:
            w, h = img.size
            if w != 1920 or h != 1080:
                issues.append(f"Invalid dimensions {w}x{h} (expected 1920x1080)")
    except Exception as e:
        issues.append(f"Image decode failure: {e}")

    return len(issues) == 0, issues


def check_near_duplicates(image_paths: list[Path], max_hamming_dist: int = 6) -> list[tuple[str, str, int]]:
    """Detect near duplicate images using perceptual hashing."""
    hashes = {}
    duplicates = []

    for p in image_paths:
        if not p.exists():
            continue
        try:
            with Image.open(p) as img:
                h = imagehash.phash(img)
                hashes[p.name] = h
        except Exception:
            pass

    names = list(hashes.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            n1, n2 = names[i], names[j]
            dist = hashes[n1] - hashes[n2]
            if dist <= max_hamming_dist:
                duplicates.append((n1, n2, dist))

    return duplicates


def validate_visual_evaluation(scene: dict[str, Any], evaluation: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    axes = evaluation.get("axes", {})
    for axis in REQUIRED_VISUAL_AXES:
        if axis not in axes:
            errors.append(f"missing required visual axis '{axis}'")
        elif axes[axis] not in {"PASS", "NOT_APPLICABLE"}:
            errors.append(f"failed required visual axis '{axis}'")
    if evaluation.get("decision") != "approved":
        errors.append("visual evaluation decision is not approved")
    if scene.get("visual_role") != "host_explainer" and axes.get("host_presence") != "PASS":
        errors.append("host_presence must confirm presenter absence for non-host scenes")
    if axes.get("embedded_text") != "PASS":
        errors.append("embedded_text must pass for every generated base image")
    return errors
