from __future__ import annotations

import random

from PIL import Image

from lib.flow_generation_state import adaptive_cooldown, canvas_is_busy, validate_download_evidence


def test_canvas_busy_gate_detects_progress_and_spinners() -> None:
    assert canvas_is_busy("렌더링 42%", 0)
    assert canvas_is_busy("완료", 1)
    assert not canvas_is_busy("완료", 0)


def test_adaptive_cooldown_has_required_bands_with_injected_rng() -> None:
    rng = random.Random(7)
    assert 14.0 <= adaptive_cooldown(1, False, rng=rng) <= 17.0
    assert 25.0 <= adaptive_cooldown(1, True, rng=rng) <= 28.0
    assert 30.0 <= adaptive_cooldown(10, False, rng=rng) <= 35.0


def test_download_evidence_requires_file_and_matching_sha(tmp_path) -> None:
    path = tmp_path / "SHOT_001.jpg"
    Image.new("RGB", (1920, 1080), (12, 24, 36)).save(path, quality=92)
    import hashlib

    row = {
        "status": "COMPLETED",
        "file_path": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }
    assert validate_download_evidence(row, path, min_bytes=1)
    assert not validate_download_evidence(row | {"sha256": "B" * 64}, path, min_bytes=1)


def test_download_evidence_rejects_wrong_physical_dimensions(tmp_path) -> None:
    path = tmp_path / "SHOT_002.jpg"
    Image.new("RGB", (1280, 720), (12, 24, 36)).save(path, quality=92)
    import hashlib

    row = {
        "status": "COMPLETED",
        "file_path": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "width": 1920,
        "height": 1080,
    }
    assert not validate_download_evidence(row, path, min_bytes=1)


def test_download_evidence_rejects_corrupt_image_with_matching_sha(tmp_path) -> None:
    path = tmp_path / "SHOT_003.jpg"
    path.write_bytes(b"not-a-jpeg" * 3_000)
    import hashlib

    row = {
        "status": "COMPLETED",
        "file_path": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "width": 1920,
        "height": 1080,
    }
    assert not validate_download_evidence(row, path, min_bytes=1)
