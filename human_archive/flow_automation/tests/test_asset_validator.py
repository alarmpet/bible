from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from PIL import Image

from flow_automation.native_host.asset_validator import validate_asset
from flow_automation.native_host.job_store import compile_job


@pytest.fixture
def valid_job(himalaya_manifest: Path, episode_dir: Path) -> dict[str, object]:
    job = compile_job(himalaya_manifest, episode_dir, "https://labs.google/fx/ko/tools/flow/project/p1", "HIMALAYA-v1")
    for index, row in enumerate(job["shots"], 1):
        row.update({"card_id": f"CARD-{index}", "attempt": 1, "download_id": f"download-{index}"})
    return job

@pytest.fixture
def downloads_root(valid_job: dict[str, object]) -> Path:
    path = Path(str(valid_job["output_dir"]))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _shot(job: dict[str, object], shot_id: str) -> dict[str, object]:
    for row in job["shots"]:  # type: ignore[index]
        if row["shot_id"] == shot_id:
            return row
    raise AssertionError(f"missing shot fixture: {shot_id}")



def _binding(job: dict[str, object], shot_id: str, original_filename: str) -> dict[str, object]:
    shot = _shot(job, shot_id)
    values = {"job_id": job["job_id"], "shot_id": shot_id, "prompt_sha256": shot["prompt_sha256"], "attempt": shot["attempt"], "card_id": shot["card_id"], "media_identity": f"media-{shot_id}", "download_id": shot["download_id"], "original_filename": original_filename}
    return {"expected": dict(values), "observed": dict(values)}
def _write_image(path: Path, size: tuple[int, int], image_format: str = "PNG") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=(32, 96, 160)).save(path, format=image_format)
    return path


def _copy_file(source: Path, destination: Path) -> Path:
    destination.write_bytes(source.read_bytes())
    return destination


def _read_manifest(downloads_root: Path) -> dict[str, object]:
    path = downloads_root / "approved_asset_manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_valid_png_moves_to_approved_and_records_provenance(
    valid_job: dict[str, object], downloads_root: Path
) -> None:
    chrome_path = _write_image(downloads_root / "flow-card.png", (3840, 2160))

    result = validate_asset(valid_job, "SHOT_001", chrome_path, downloads_root, [], binding=_binding(valid_job, "SHOT_001", chrome_path.name))

    shot = _shot(valid_job, "SHOT_001")
    approved_path = Path(str(result.approved_path))
    assert result.status == "ACCEPTED"
    assert result.code == "OK"
    assert result.mime_type == "image/png"
    assert result.width == 1920
    assert result.height == 1080
    assert approved_path.name == shot["expected_filename"]
    assert approved_path.exists()
    assert not chrome_path.exists()
    assert result.rejected_path is None

    with Image.open(approved_path) as image:
        assert image.size == (1920, 1080)

    sidecar = approved_path.with_suffix(".json")
    assert sidecar.exists()

    manifest = _read_manifest(downloads_root)
    assert manifest["job_id"] == valid_job["job_id"]
    assert manifest["output_dir"] == str(downloads_root)
    assert len(manifest["assets"]) == 1
    entry = manifest["assets"][0]
    assert entry["shot_id"] == "SHOT_001"
    assert entry["prompt_sha256"] == shot["prompt_sha256"]
    assert entry["approved_path"] == str(approved_path)
    assert entry["original_filename"] == "flow-card.png"
    assert entry["mime_type"] == "image/png"
    assert entry["width"] == 1920
    assert entry["height"] == 1080
    assert entry["sha256"] == result.sha256
    assert result.sha256 == hashlib.sha256(approved_path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    ("case", "code"),
    [
        ("corrupt", "IMAGE_DECODE_FAILED"),
        ("zero", "EMPTY_FILE"),
        ("partial", "PARTIAL_DOWNLOAD"),
        ("wrong_ratio", "INVALID_ASPECT_RATIO"),
    ],
)
def test_invalid_asset_is_rejected(
    valid_job: dict[str, object], downloads_root: Path, case: str, code: str
) -> None:
    chrome_path = downloads_root / {
        "corrupt": "broken.png",
        "zero": "empty.png",
        "partial": "still-downloading.crdownload",
        "wrong_ratio": "square.png",
    }[case]
    if case == "corrupt":
        chrome_path.write_bytes(b"not-an-image")
    elif case == "zero":
        chrome_path.write_bytes(b"")
    elif case == "partial":
        chrome_path.write_bytes(b"partial-download")
    else:
        _write_image(chrome_path, (1000, 1000))

    result = validate_asset(valid_job, "SHOT_001", chrome_path, downloads_root, [], binding=_binding(valid_job, "SHOT_001", chrome_path.name))

    rejected_path = Path(str(result.rejected_path))
    assert result.status == "REJECTED"
    assert result.code == code
    assert result.approved_path is None
    assert rejected_path.exists()
    assert rejected_path.parent.name == "rejected"
    assert rejected_path.with_suffix(".json").exists()

    manifest_path = downloads_root / "approved_asset_manifest.json"
    assert not manifest_path.exists()


def test_duplicate_file_hash_cannot_serve_two_shots(
    valid_job: dict[str, object], downloads_root: Path
) -> None:
    first_path = _write_image(downloads_root / "first.png", (1920, 1080))
    accepted = validate_asset(valid_job, "SHOT_001", first_path, downloads_root, [], binding=_binding(valid_job, "SHOT_001", first_path.name))

    duplicate_source = _copy_file(
        Path(str(accepted.approved_path)),
        downloads_root / "second.png",
    )
    second = validate_asset(
        valid_job,
        "SHOT_002",
        duplicate_source,
        downloads_root,
        [accepted],
        binding=_binding(valid_job, "SHOT_002", duplicate_source.name),
    )

    manifest = _read_manifest(downloads_root)
    assert accepted.status == "ACCEPTED"
    assert second.status == "REJECTED"
    assert second.code == "DUPLICATE_ASSET_HASH"
    assert len(manifest["assets"]) == 1


def test_asset_outside_download_root_is_rejected(
    valid_job: dict[str, object], downloads_root: Path, tmp_path: Path
) -> None:
    outside_path = _write_image(tmp_path / "outside.png", (1920, 1080))

    result = validate_asset(valid_job, "SHOT_001", outside_path, downloads_root, [], binding=_binding(valid_job, "SHOT_001", outside_path.name))

    assert result.status == "REJECTED"
    assert result.code == "DOWNLOAD_PATH_OUTSIDE_ROOT"
    assert result.approved_path is None
    assert result.rejected_path is None
    assert outside_path.exists()

def test_manifest_matches_schema(valid_job: dict[str, object], downloads_root: Path) -> None:
    source = _write_image(downloads_root / "schema.png", (1920, 1080))
    validate_asset(valid_job, "SHOT_001", source, downloads_root, [], binding=_binding(valid_job, "SHOT_001", source.name))
    schema_path = Path(__file__).parents[1] / "schemas" / "approved_asset_manifest.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(_read_manifest(downloads_root))) == []








def test_binding_is_required_and_filename_bound(valid_job: dict[str, object], downloads_root: Path) -> None:
    source = _write_image(downloads_root / 'actual.png', (1920, 1080))
    missing = validate_asset(valid_job, 'SHOT_001', source, downloads_root, [], binding={})
    assert missing.code == 'MISSING_ASSET_BINDING'
    assert Path(str(missing.rejected_path)).exists()
    source = _write_image(downloads_root / 'actual-2.png', (1920, 1080))
    bad = _binding(valid_job, 'SHOT_001', 'claimed.png')
    mismatched = validate_asset(valid_job, 'SHOT_001', source, downloads_root, [], binding=bad)
    assert mismatched.code == 'ORIGINAL_FILENAME_MISMATCH'



def test_binding_rejects_download_and_media_identity_mismatch(valid_job: dict[str, object], downloads_root: Path) -> None:
    for field in ("download_id", "media_identity"):
        source = _write_image(downloads_root / (field + ".png"), (1920, 1080))
        binding = _binding(valid_job, "SHOT_001", source.name)
        binding["observed"][field] = "mismatch"
        result = validate_asset(valid_job, "SHOT_001", source, downloads_root, [], binding=binding)
        assert result.code == "ASSET_BINDING_MISMATCH"
        assert Path(str(result.rejected_path)).exists()


