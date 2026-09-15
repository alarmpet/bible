import json
import hashlib
import inspect
import wave
from pathlib import Path

import pytest

from build_sentence_audio_master import build_sentence_audio_master
from lib.audio_timeline import get_wav_duration
from lib.sentence_audio_timeline import build_sentence_rows, validate_sentence_timeline
from lib.tts_provider import ToneFixtureProvider

def _s(sid, order, text): return {"sentence_id":sid,"order":order,"chapter":1,"beat":"body","tts_text":text}

def test_sentence_rows_use_measured_duration_and_gap():
    rows=build_sentence_rows([_s("S1",1,"첫"),_s("S2",2,"둘")],{"S1":4,"S2":5},.35)
    assert rows[0]["start_sec"]==0.0 and rows[0]["end_sec"]==4.0
    assert rows[1]["start_sec"]==4.35 and rows[1]["end_sec"]==9.35


def test_sentence_rows_reject_gap_outside_room_tone_policy():
    with pytest.raises(ValueError, match="0.35.*0.50"):
        build_sentence_rows([_s("S1", 1, "첫")], {"S1": 4}, 0.34)
    with pytest.raises(ValueError, match="0.35.*0.50"):
        build_sentence_rows([_s("S1", 1, "첫")], {"S1": 4}, 0.51)

def test_timeline_rejects_missing_or_overlapping_sentence():
    script={"sentences":[_s("S1",1,"첫"),_s("S2",2,"둘")]}
    errors=validate_sentence_timeline(script,{"sentences":[{"sentence_id":"S1","order":1,"start_sec":0,"end_sec":5,"duration_sec":5}]})
    assert any("S2" in e and "missing" in e.lower() for e in errors)


def test_publishable_builder_defaults_to_supertonic3() -> None:
    assert inspect.signature(build_sentence_audio_master).parameters["audio_mode"].default == "supertonic3"


def test_sentence_master_contains_the_declared_inter_sentence_gap(tmp_path):
    script_path = tmp_path / "script.json"
    script_path.write_text(
        json.dumps(
            {
                "episode_id": "TEST",
                "sentences": [
                    _s("S1", 1, "첫 문장"),
                    _s("S2", 2, "둘째 문장"),
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    master = build_sentence_audio_master(
        script_path,
        tmp_path / "build",
        audio_mode="fixture",
        gap_sec=0.35,
    )
    manifest = json.loads((tmp_path / "build" / "sentence_audio_manifest.json").read_text(encoding="utf-8"))

    assert manifest["sentences"][1]["start_sec"] == pytest.approx(2.35, abs=0.02)
    assert get_wav_duration(master) == pytest.approx(manifest["total_duration_sec"], abs=0.03)
    row = manifest["sentences"][0]
    phrase = tmp_path / "build" / "audio" / "sentences" / row["audio_file"]
    assert row["wav_sha256"] == hashlib.sha256(phrase.read_bytes()).hexdigest()
    assert manifest["room_tone"]["mode"] == "deterministic_low_level"

    with wave.open(str(master), "rb") as reader:
        reader.setpos(round(row["end_sec"] * 48_000))
        gap_frames = reader.readframes(round(manifest["gap_sec"] * 48_000))
    assert any(byte != 0 for byte in gap_frames)


def test_sentence_master_can_reassemble_verified_existing_phrases_without_resynthesis(tmp_path, monkeypatch):
    script_path = tmp_path / "script.json"
    script_path.write_text(
        json.dumps(
            {
                "episode_id": "TEST",
                "sentences": [
                    _s("S1", 1, "첫 문장"),
                    _s("S2", 2, "둘째 문장"),
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    build_dir = tmp_path / "build"
    build_sentence_audio_master(script_path, build_dir, audio_mode="fixture", gap_sec=0.35)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("reuse_existing must not synthesize phrases again")

    monkeypatch.setattr("build_sentence_audio_master.ToneFixtureProvider.synthesize_phrase", fail_if_called)
    master = build_sentence_audio_master(
        script_path,
        build_dir,
        audio_mode="fixture",
        gap_sec=0.5,
        reuse_existing=True,
    )
    manifest = json.loads((build_dir / "sentence_audio_manifest.json").read_text(encoding="utf-8"))

    assert manifest["gap_sec"] == 0.5
    assert get_wav_duration(master) == pytest.approx(manifest["total_duration_sec"], abs=0.03)


def test_sentence_master_reuses_matching_text_hash_from_prior_build(tmp_path, monkeypatch):
    prior_script = tmp_path / "prior-script.json"
    prior_script.write_text(
        json.dumps(
            {
                "episode_id": "TEST",
                "sentences": [
                    _s("OLD-1", 1, "그대로 재사용할 문장"),
                    _s("OLD-2", 2, "이전 빌드에만 있는 문장"),
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    prior_build = tmp_path / "prior-build"
    build_sentence_audio_master(
        prior_script,
        prior_build,
        audio_mode="fixture",
        gap_sec=0.35,
    )

    current_script = tmp_path / "current-script.json"
    current_script.write_text(
        json.dumps(
            {
                "episode_id": "TEST",
                "sentences": [
                    _s("NEW-ID", 1, "그대로 재사용할 문장"),
                    _s("NEW-ONLY", 2, "이번에 새로 합성할 문장"),
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    original = ToneFixtureProvider.synthesize_phrase
    synthesized: list[str] = []

    def record_synthesis(self, text, out_wav, *args, **kwargs):
        synthesized.append(text)
        return original(self, text, out_wav, *args, **kwargs)

    monkeypatch.setattr(ToneFixtureProvider, "synthesize_phrase", record_synthesis)
    current_build = tmp_path / "current-build"
    build_sentence_audio_master(
        current_script,
        current_build,
        audio_mode="fixture",
        gap_sec=0.35,
        reuse_from_builds=[prior_build],
    )
    manifest = json.loads(
        (current_build / "sentence_audio_manifest.json").read_text(encoding="utf-8")
    )
    by_id = {row["sentence_id"]: row for row in manifest["sentences"]}

    assert synthesized == ["이번에 새로 합성할 문장"]
    assert by_id["NEW-ID"]["provenance"]["reuse_mode"] == "provider_text_sha256"
    assert by_id["NEW-ID"]["provenance"]["reused_from_sentence_id"] == "OLD-1"
    assert Path(by_id["NEW-ID"]["provenance"]["reused_from_build"]) == prior_build
    assert (current_build / "audio" / "sentences" / "NEW-ID.wav").exists()
