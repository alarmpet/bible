# -*- coding: utf-8 -*-
"""TTS lock, verse-level split, skip-existing ban, and scripture filter."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_full_job  # noqa: E402
from apply_audio_filter import apply_scripture_filter  # noqa: E402
from verify_voice_provenance import (  # noqa: E402
    PROVENANCE_FIELDS,
    build_piece_provenance,
    enforce_skip_existing,
    load_media_lock,
    prepare_speech_units,
    resolve_total_step,
    run_job_preflight,
    verify_tts_provenance,
    write_tts_provenance,
)

LONG_SCRIPTURE = (
    "(다윗의 시. 영장으로 현악에 맞춘 노래) 내 의의 하나님이여, 내가 부를 때에 "
    "응답하소서 곤란 중에 나를 너그럽게 하셨사오니 나를 긍휼히 여기사 나의 기도를 "
    "들으소서 인생들아 ! 어느 때까지 나의 영광을 변하여 욕되게 하며 허사를 좋아하고 "
    "궤휼을 구하겠는고 (셀라) 여호와께서 자기를 위하여 경건한 자를 택하신 줄 너희가 "
    "알지어다 내가 부를 때에 응답하소서 내 영혼아 네가 어찌하여 낙망하며 어찌하여 "
    "내 속에서 불안하여 하는고 너는 하나님을 바라라 그 얼굴의 도우심을 인하여 "
    "내가 오히려 찬송하리로다"
)


def test_build_full_job_copies_audio_filter(tmp_path, monkeypatch):
    # build_full_job.spk("scripture")["audio_filter"] must equal yaml filter, not ""
    yaml_filter = "asetrate=24000*0.92,aresample=24000,atempo=1.087"
    cfg = {
        "speakers": {
            "narrator": {
                "label": "n",
                "voice": "F5",
                "speed": 0.95,
                "total_step": 8,
                "silence_duration": 0.24,
                "audio_filter": "",
            },
            "scripture": {
                "label": "s",
                "voice": "M4",
                "speed": 0.72,
                "total_step": 10,
                "silence_duration": 0.65,
                "max_chunk_length": 90,
                "audio_filter": yaml_filter,
            },
        }
    }
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "voice_healing.yaml").write_text(
        yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8"
    )
    ep = tmp_path / "runs" / "ep01_anxious_night"
    ep.mkdir(parents=True)
    (ep / "script_segments.json").write_text(
        json.dumps([{"seg_id": "s1", "unit": "u1", "speaker": "scripture", "text": "본문"}]),
        encoding="utf-8",
    )
    monkeypatch.setattr(build_full_job, "ROOT", tmp_path)

    entry = build_full_job.spk("scripture")
    assert entry["audio_filter"] == yaml_filter
    assert entry["audio_filter"] != ""

    build_full_job.main()
    vm = json.loads((ep / "hermes_jobs" / "full" / "voice_map.json").read_text(encoding="utf-8"))
    assert vm["speakers"]["scripture"]["audio_filter"] == yaml_filter
    assert vm["speakers"]["scripture"]["audio_filter"] != ""
    assert "F5/M5" not in vm.get("notes", "")


def test_run_job_rejects_non_m4(tmp_path):
    # voice_map scripture voice M5 -> SystemExit
    (tmp_path / "voice_map.json").write_text(
        json.dumps(
            {
                "speakers": {
                    "narrator": {"voice": "F5", "speed": 0.95},
                    "scripture": {"voice": "M5", "speed": 0.72},
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit):
        run_job_preflight(tmp_path, skip_existing=False)


def test_run_job_rejects_skip_existing_when_lock_forbids():
    with pytest.raises(SystemExit):
        enforce_skip_existing(True)


def test_scripture_is_split_under_90_chars():
    # after sanitize+split, every synthesize text_len <= 90
    units = prepare_speech_units(LONG_SCRIPTURE, "scripture")
    assert units
    assert all(len(u) <= 90 for u in units)
    assert len(units) >= 2
    assert all("!" not in u and "?" not in u for u in units)
    assert all("셀라" not in u and "다윗" not in u for u in units)


def test_empty_sanitized_text_fails_scene():
    with pytest.raises(ValueError, match="empty"):
        prepare_speech_units("(셀라)", "scripture")


def test_apply_scripture_filter_uses_lock_asetrate(tmp_path, monkeypatch):
    import apply_audio_filter as aaf

    src = tmp_path / "in.wav"
    dst = tmp_path / "out.wav"
    src.write_bytes(b"RIFF0000")
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        Path(cmd[-1]).write_bytes(b"OUT")

        class _R:
            returncode = 0
            stdout = ""
            stderr = ""

        return _R()

    monkeypatch.setattr(aaf.subprocess, "run", fake_run)
    monkeypatch.setattr(aaf, "ffmpeg_bin", lambda: "ffmpeg")
    info = apply_scripture_filter(src, dst)
    assert info["filter_applied"] is True
    assert "asetrate=24000*0.92" in info["filter"]
    joined = " ".join(str(x) for x in captured["cmd"])
    assert "asetrate=24000*0.92" in joined
    assert info["pitch_percent"] == -8.0


def test_tts_provenance_shape(tmp_path):
    wav = tmp_path / "piece.wav"
    wav.write_bytes(b"wav")
    rec = build_piece_provenance(
        speaker="scripture",
        voice="M4",
        speed=0.72,
        total_step=10,
        max_chunk=90,
        text="내 영혼아.",
        wav_path=wav,
        filter_applied=True,
    )
    for key in PROVENANCE_FIELDS:
        assert key in rec
    out = write_tts_provenance(tmp_path, [rec])
    assert out.name == "tts_provenance.json"
    result = verify_tts_provenance(out)
    assert result["ok"] is True


def test_resolve_total_step_never_24():
    lock = load_media_lock()
    step = resolve_total_step("scripture", lock)
    assert step != 24
    assert step in lock["voice"]["scripture"]["total_step_candidates"]
    assert step not in lock["voice"]["scripture"]["forbidden_total_step"]
