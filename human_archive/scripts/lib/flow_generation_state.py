"""Shared, deterministic state predicates for Google Flow generation."""

from __future__ import annotations

import hashlib
import random
import re
from pathlib import Path
from typing import Any

from PIL import Image


def canvas_is_busy(body_text: str, spinner_count: int) -> bool:
    """Return true while progress text or any rendering spinner is present."""
    return bool(re.search(r"\b\d{1,2}%", str(body_text))) or int(spinner_count) > 0


def adaptive_cooldown(
    consecutive_success: int,
    had_error: bool,
    *,
    rng: random.Random | None = None,
) -> float:
    """Return the policy cooldown; RNG injection keeps unit tests reproducible."""
    source = rng or random
    if had_error:
        return round(25.0 + source.uniform(0.0, 3.0), 2)
    if consecutive_success > 0 and consecutive_success % 10 == 0:
        return round(30.0 + source.uniform(0.0, 5.0), 2)
    return round(14.0 + source.uniform(0.0, 3.0), 2)


def validate_download_evidence(
    row: dict[str, Any],
    file_path: Path,
    *,
    min_bytes: int = 20_000,
) -> bool:
    """Validate the physical file and its manifest digest before reuse."""
    if row.get("status") != "COMPLETED" or not file_path.is_file():
        return False
    actual_size = file_path.stat().st_size
    if actual_size < min_bytes or int(row.get("bytes", 0)) != actual_size:
        return False
    expected = str(row.get("sha256", "")).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        return False
    digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
    if digest != expected:
        return False

    # Flow images are normalized to the production canvas before they are
    # recorded as COMPLETED.  Hash/size alone cannot detect a valid-looking
    # non-image payload or a pre-normalization 16:9 frame.
    if file_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
        try:
            with Image.open(file_path) as image:
                image.verify()
            with Image.open(file_path) as image:
                width, height = image.size
        except (OSError, ValueError):
            return False
        if (width, height) != (1920, 1080):
            return False
        declared_width = row.get("width")
        declared_height = row.get("height")
        if declared_width is not None and int(declared_width) != width:
            return False
        if declared_height is not None and int(declared_height) != height:
            return False
    return True
