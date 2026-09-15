from __future__ import annotations

from pathlib import Path
from typing import Sequence


def validate_pilot_inputs(
    scenes: Sequence[dict],
    available_images: Sequence[Path],
) -> None:
    """Reject incomplete or ambiguous pilot inputs before FFmpeg is invoked."""
    scene_ids = [str(scene["shot_id"]) for scene in scenes]
    duplicate_ids = sorted({shot_id for shot_id in scene_ids if scene_ids.count(shot_id) > 1})
    if duplicate_ids:
        raise ValueError(f"duplicate shot IDs in pilot scenes: {', '.join(duplicate_ids)}")

    image_by_id = {path.stem: path for path in available_images}
    missing = [shot_id for shot_id in scene_ids if shot_id not in image_by_id]
    if missing:
        raise ValueError(
            f"missing {len(missing)} images; pilot requires {len(scene_ids)} unique images: "
            + ", ".join(missing)
        )

    if len(image_by_id) < len(scene_ids):
        raise ValueError(
            f"pilot requires {len(scene_ids)} unique images, but only {len(image_by_id)} are available"
        )
