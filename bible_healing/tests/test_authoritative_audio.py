# -*- coding: utf-8 -*-
"""Authoritative audio verify + rebuild from sanitized M4 WAVs only."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from rebuild_authoritative_full_audio import rebuild_authoritative_audio  # noqa: E402
from verify_authoritative_audio import (  # noqa: E402
    BACKUP_DIR_NAME,
    backup_unsanitized_wavs,
    verify_authoritative_audio,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _piece(
    *,
    speaker: str,
    scene_order: int,
    text: str = "본문입니다.",
    voice: str | None = None,
    filter_applied: bool | None = None,
    path: str | None = None,
) -> dict:
    if voice is None:
        voice = "M4" if speaker == "scripture" else "F5"
    if filter_applied is None:
        filter_applied = speaker == "scripture"
    return {
        "speaker": speaker,
        "voice": voice,
        "speed": 0.72 if speaker == "scripture" else 0.95,
        "total_step": 10 if speaker == "scripture" else 8,
        "max_chunk": 90 if speaker == "scripture" else 130,
        "text": text,
        "text_sha256": _sha(text),
        "wav_sha256": _sha(f"wav-{scene_order}"),
        "filter_applied": filter_applied,
        "scene_order": scene_order,
        "scene_id": f"s{scene_order}",
        "path": path or f"segments/scene_{scene_order}_unit.wav",
    }


def make_job(
    root: Path,
    *,
    speakers: list[str] | None = None,
    pieces: list[dict] | None = None,
    write_provenance: bool = True,
    write_wavs: bool = True,
    n: int | None = None,
    job_dirname: str = "full",
) -> Path:
    """Build a minimal hermes job under root for unit tests."""
    job = root / "hermes_jobs" / job_dirname
    job.mkdir(parents=True, exist_ok=True)
    if speakers is None:
        n = n or 2
        speakers = ["scripture" if i == 0 else "narrator" for i in range(n)]
    else:
        n = len(speakers)

    scenes = []
    auto_pieces: list[dict] = []
    for i, sp in enumerate(speakers, start=1):
        scenes.append(
            {
                "scene_id": f"s{i}",
                "order": i,
                "segments": [
                    {
                        "speaker": sp,
                        "text": "본문입니다.",
                        "seg_id": f"s{i}_01",
                    }
                ],
                "meta": {"speaker": sp},
            }
        )
        if write_wavs:
            (job / f"scene_{i}.wav").write_bytes(b"RIFF" + b"\x00" * 64)
        auto_pieces.append(_piece(speaker=sp, scene_order=i))

    (job / "scenes.json").write_text(
        json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if write_provenance:
        payload = {
            "ok": True,
            "engine": "supertonic3",
            "pieces": pieces if pieces is not None else auto_pieces,
            "scene_count": n,
        }
        reports = job / "reports"
        reports.mkdir(exist_ok=True)
        (reports / "tts_provenance.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return job


def test_wav_count_mismatch_fails(tmp_path):
    job = make_job(tmp_path, speakers=["narrator", "narrator"], write_wavs=True)
    (job / "scene_2.wav").unlink()
    result = verify_authoritative_audio(job)
    assert result["ok"] is False
    assert any("count" in e.lower() or "개수" in e or "mismatch" in e.lower() for e in result["errors"])


def test_missing_provenance_fails(tmp_path):
    job = make_job(tmp_path, speakers=["narrator"], write_provenance=False)
    result = verify_authoritative_audio(job)
    assert result["ok"] is False
    assert any("provenance" in e.lower() for e in result["errors"])


def test_scripture_wrong_voice_fails(tmp_path):
    pieces = [_piece(speaker="scripture", scene_order=1, voice="M5", filter_applied=True)]
    job = make_job(tmp_path, speakers=["scripture"], pieces=pieces)
    result = verify_authoritative_audio(job)
    assert result["ok"] is False
    assert any("M4" in e or "voice" in e.lower() for e in result["errors"])


def test_scripture_filter_not_applied_fails(tmp_path):
    pieces = [_piece(speaker="scripture", scene_order=1, voice="M4", filter_applied=False)]
    job = make_job(tmp_path, speakers=["scripture"], pieces=pieces)
    result = verify_authoritative_audio(job)
    assert result["ok"] is False
    assert any("filter" in e.lower() for e in result["errors"])


def test_bang_in_text_fails(tmp_path):
    pieces = [
        _piece(
            speaker="scripture",
            scene_order=1,
            text="인생들아 ! 어느 때까지",
            voice="M4",
            filter_applied=True,
        )
    ]
    job = make_job(tmp_path, speakers=["scripture"], pieces=pieces)
    result = verify_authoritative_audio(job)
    assert result["ok"] is False
    assert any("!" in e or "emotion" in e.lower() or "punctuation" in e.lower() for e in result["errors"])


@pytest.mark.parametrize(
    "bad_fragment",
    ["synced.mp4", "upload_package", "prelock", "audio_partial"],
)
def test_forbidden_path_fails(tmp_path, bad_fragment):
    # Job lives under a forbidden path segment
    root = tmp_path / bad_fragment / "ep"
    root.mkdir(parents=True)
    job = make_job(root, speakers=["narrator"])
    result = verify_authoritative_audio(job)
    assert result["ok"] is False
    assert any(bad_fragment in e for e in result["errors"])


def test_clean_job_passes(tmp_path):
    job = make_job(
        tmp_path,
        speakers=["scripture", "narrator", "scripture"],
    )
    result = verify_authoritative_audio(job)
    assert result["ok"] is True
    assert result["errors"] == []
    assert result["scene_count"] == 3
    assert len(result["wavs"]) == 3


def test_rebuild_uses_scenes_json_count_not_110(tmp_path, monkeypatch):
    job = make_job(tmp_path, speakers=["narrator", "narrator", "scripture"])
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        out = Path(cmd[-1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"RIFFOUT")

        class _R:
            returncode = 0

        return _R()

    import rebuild_authoritative_full_audio as reb

    monkeypatch.setattr(reb.subprocess, "run", fake_run)
    monkeypatch.setattr(reb, "ffmpeg_bin", lambda: "ffmpeg")

    info = rebuild_authoritative_audio(job)
    assert info["scenes"] == 3
    assert info["scenes"] != 110
    assert Path(info["output"]).exists()
    # concat list should reference exactly 3 scene wavs plus 2 scene gaps
    work = job / "authoritative_audio_rebuild"
    lst = (work / "scene_audio_concat.txt").read_text(encoding="utf-8")
    assert lst.count("normalized_48k") == 3
    assert lst.count("file ") == 5
    prov_path = work / "voice_provenance.json"
    assert prov_path.is_file()
    prov = json.loads(prov_path.read_text(encoding="utf-8"))
    assert prov["scene_count"] == 3
    assert Path(prov["audio"]).name == "full-authoritative-audio.wav"
    assert prov["sha256"] == hashlib.sha256(b"RIFFOUT").hexdigest()


def test_rebuild_refuses_on_verify_fail(tmp_path, monkeypatch):
    job = make_job(tmp_path, speakers=["scripture"], write_provenance=False)
    ran = {"ffmpeg": False}

    def fake_run(cmd, **kwargs):
        ran["ffmpeg"] = True

        class _R:
            returncode = 0

        return _R()

    import rebuild_authoritative_full_audio as reb

    monkeypatch.setattr(reb.subprocess, "run", fake_run)
    monkeypatch.setattr(reb, "ffmpeg_bin", lambda: "ffmpeg")

    with pytest.raises(SystemExit):
        rebuild_authoritative_audio(job)
    assert ran["ffmpeg"] is False


def test_backup_unsanitized_moves_with_tmp(tmp_path):
    pieces = [
        _piece(
            speaker="scripture",
            scene_order=1,
            text="인생들아 !",
            voice="M4",
            filter_applied=True,
        ),
        _piece(speaker="narrator", scene_order=2),
    ]
    job = make_job(tmp_path, speakers=["scripture", "narrator"], pieces=pieces)
    src = job / "scene_1.wav"
    assert src.exists()

    moved = backup_unsanitized_wavs(job, scene_orders=[1], dry_run=False)
    assert len(moved) == 1
    assert moved[0]["moved"] is True
    assert not src.exists()
    dest = job / BACKUP_DIR_NAME / "scene_1.wav"
    assert dest.exists()


def test_backup_dry_run_does_not_move(tmp_path):
    job = make_job(tmp_path, speakers=["scripture"])
    src = job / "scene_1.wav"
    moved = backup_unsanitized_wavs(job, scene_orders=[1], dry_run=True)
    assert moved[0]["dry_run"] is True
    assert moved[0]["moved"] is False
    assert src.exists()
    assert not (job / BACKUP_DIR_NAME / "scene_1.wav").exists()


def test_scene_missing_piece_is_missing_provenance(tmp_path):
    # Only scene 1 has a piece; scene 2 WAV exists but no provenance piece
    pieces = [_piece(speaker="narrator", scene_order=1)]
    job = make_job(tmp_path, speakers=["narrator", "narrator"], pieces=pieces)
    result = verify_authoritative_audio(job)
    assert result["ok"] is False
    assert any("provenance" in e.lower() or "scene_2" in e or "order=2" in e for e in result["errors"])
