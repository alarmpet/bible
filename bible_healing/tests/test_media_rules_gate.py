# -*- coding: utf-8 -*-
"""TDD gates for media_rules preflight/postflight (tmp fixtures only)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import media_rules_postflight as post  # noqa: E402
import media_rules_preflight as pre  # noqa: E402
from sanitize_script import sanitize_script  # noqa: E402

CLEAN_NARRATION = "불을 껐는데, 머릿속은 아직 환한 밤이 있습니다."
DIRTY_SCRIPTURE = (
    "(다윗의 시. 영장으로 현악에 맞춘 노래) 내 의의 하나님이여, "
    "내가 부를 때에 응답하소서. 인생들아 ! (셀라)"
)


def _lock(**overrides) -> dict:
    base = {
        "version": 2,
        "voice": {
            "narrator": {
                "voice": "F5",
                "speed": 0.95,
                "total_step": 8,
                "silence_seconds": 0.24,
                "audio_filter": "",
            },
            "scripture": {
                "voice": "M4",
                "speed": 0.8,
                "pitch": -14,
                "silence_seconds": 0.25,
                "total_step": 10,
                "total_step_candidates": [8, 10, 12],
                "forbidden_total_step": [24],
                "max_chunk_length": 90,
                "audio_filter": (
                    "asetrate=24000*0.86,aresample=24000,"
                    "highpass=f=60,lowpass=f=7000,equalizer=f=180:t=q:w=1:g=2.5"
                ),
            },
        },
        "speakers": ["narrator", "scripture"],
        "tts": {
            "engine": "supertonic3",
            "skip_existing_forbidden": True,
            "require_sanitize": True,
            "require_verse_split": True,
            "forbid_expression_tags": ["<laugh>", "<breath>", "<sigh>"],
            "punctuation_to_period": ["!", "！", "!?", "❗", "?", "？"],
        },
        "captions": {
            "max_lines": 2,
            "target_chars_per_line": [14, 18],
            "max_chars_per_line": 20,
            "fontName": "Malgun Gothic",
            "fontSizePx_narrator": 96,
            "fontSizePx_scripture": 100,
            "outlinePx": 6,
            "shadowPx": 3,
            "marginV_px": 90,
            "marginL_px": 100,
            "marginR_px": 100,
        },
        "background": {
            "directory": "bible_healing/assets/movie-sample/pingpong-1min",
            "required_count": 12,
            "duration_seconds": 60,
            "speed": 0.333,
            "still_images_forbidden": True,
        },
        "storage": {
            "final_root": r"D:\bible_healing_ep01\final",
            "work_root": r"D:\bible_healing_ep01\work",
        },
        "release_gates": {
            "duration_delta_seconds": 0.5,
            "require_first_caption_matches_first_script": True,
            "require_authoritative_audio": True,
            "require_no_selah_or_bang_in_ass": True,
            "require_no_mid_eojel_split": True,
        },
    }
    base.update(overrides)
    return base


def _voice_map(
    *,
    scripture_voice: str = "M4",
    scripture_speed: float = 0.8,
    scripture_step: int = 10,
    max_chunk: int = 90,
    audio_filter: str | None = None,
    narrator_voice: str = "F5",
    narrator_speed: float = 0.95,
) -> dict:
    if audio_filter is None:
        audio_filter = _lock()["voice"]["scripture"]["audio_filter"]
    return {
        "speakers": {
            "narrator": {
                "voice": narrator_voice,
                "speed": narrator_speed,
                "total_step": 8,
                "silence_duration": 0.24,
                "audio_filter": "",
            },
            "scripture": {
                "voice": scripture_voice,
                "speed": scripture_speed,
                "total_step": scripture_step,
                "silence_duration": 0.65,
                "audio_filter": audio_filter,
                "max_chunk_length": max_chunk,
            },
        }
    }


def _dialogue(start: str, end: str, text: str, style: str = "Narrator") -> str:
    return f"Dialogue: 0,{start},{end},{style},,0,0,0,,{text}"


def _ass_with(events: list[str]) -> str:
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n"
        "WrapStyle: 0\nScaledBorderAndShadow: yes\n\n[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    return header + "\n".join(events) + "\n"


def make_job(
    root: Path,
    *,
    voice_map: dict | None = None,
    render_options: dict | None = None,
    scenes: list[dict] | None = None,
    tts_report: dict | None = None,
    write_provenance: bool = True,
    write_ass: bool = True,
    ass_text: str | None = None,
    write_auth_audio: bool = True,
) -> Path:
    job = root / "hermes_jobs" / "full"
    job.mkdir(parents=True, exist_ok=True)
    (job / "voice_map.json").write_text(
        json.dumps(voice_map or _voice_map(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (job / "render-options.json").write_text(
        json.dumps(
            render_options
            or {
                "engineVoice": "M4",
                "speechSpeed": 0.72,
                "multiVoice": True,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if scenes is None:
        scenes = [
            {
                "scene_id": "s1",
                "order": 1,
                "narration": CLEAN_NARRATION,
                "segments": [{"speaker": "narrator", "text": CLEAN_NARRATION}],
                "meta": {"speaker": "narrator"},
            },
            {
                "scene_id": "s2",
                "order": 2,
                "narration": "내 의의 하나님이여 내가 부를 때에 응답하소서.",
                "segments": [
                    {
                        "speaker": "scripture",
                        "text": "내 의의 하나님이여 내가 부를 때에 응답하소서.",
                    }
                ],
                "meta": {"speaker": "scripture"},
            },
        ]
    (job / "scenes.json").write_text(
        json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    reports = job / "reports"
    reports.mkdir(exist_ok=True)
    if tts_report is not None:
        (reports / "tts_report.json").write_text(
            json.dumps(tts_report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if write_provenance:
        pieces = [
            {
                "speaker": "narrator",
                "voice": "F5",
                "speed": 0.95,
                "total_step": 8,
                "max_chunk": 130,
                "text": CLEAN_NARRATION,
                "text_sha256": "a" * 64,
                "wav_sha256": "b" * 64,
                "filter_applied": False,
                "scene_order": 1,
            },
            {
                "speaker": "scripture",
                "voice": "M4",
                "speed": 0.72,
                "total_step": 10,
                "max_chunk": 90,
                "text": "내 의의 하나님이여 내가 부를 때에 응답하소서.",
                "text_sha256": "c" * 64,
                "wav_sha256": "d" * 64,
                "filter_applied": True,
                "scene_order": 2,
            },
        ]
        (reports / "tts_provenance.json").write_text(
            json.dumps(
                {"ok": True, "engine": "supertonic3", "pieces": pieces},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if write_ass:
        if ass_text is None:
            san = sanitize_script(CLEAN_NARRATION).display
            # Keep first caption short and matching sanitized script start.
            first = san[:18] if len(san) > 18 else san
            ass_text = _ass_with(
                [
                    _dialogue("0:00:00.00", "0:00:04.00", first),
                    _dialogue(
                        "0:00:04.00",
                        "0:00:10.00",
                        "내 의의 하나님이여",
                        style="Scripture",
                    ),
                ]
            )
        (job / "subtitles-full-audio-aligned.ass").write_text(
            ass_text, encoding="utf-8"
        )
    if write_auth_audio:
        rebuild = job / "authoritative_audio_rebuild"
        rebuild.mkdir(exist_ok=True)
        (rebuild / "full-authoritative-audio.wav").write_bytes(b"RIFF" + b"\x00" * 32)
        (rebuild / "voice_provenance.json").write_text(
            json.dumps({"ok": True}, ensure_ascii=False), encoding="utf-8"
        )
    return job


# ---------------------------------------------------------------------------
# Preflight unit checks
# ---------------------------------------------------------------------------


def test_preflight_fails_stale_scripture_voices():
    lock = _lock()
    for voice in ("F3", "M3", "M5"):
        errors = pre.check_voice_map(_voice_map(scripture_voice=voice), lock)
        assert errors, f"expected errors for voice={voice}"
        assert any("voice" in e.lower() or voice in e for e in errors)


def test_preflight_fails_stale_speeds():
    lock = _lock()
    for speed in (0.78, 0.85):
        errors = pre.check_voice_map(_voice_map(scripture_speed=speed), lock)
        assert errors
        assert any("speed" in e.lower() or str(speed) in e for e in errors)


def test_preflight_fails_empty_scripture_audio_filter():
    lock = _lock()
    errors = pre.check_voice_map(_voice_map(audio_filter=""), lock)
    assert any("audio_filter" in e for e in errors)


def test_preflight_fails_total_step_24():
    lock = _lock()
    errors = pre.check_voice_map(_voice_map(scripture_step=24), lock)
    assert any("24" in e or "total_step" in e for e in errors)


def test_preflight_fails_max_chunk_over_90():
    lock = _lock()
    errors = pre.check_voice_map(_voice_map(max_chunk=200), lock)
    assert any("max_chunk" in e or "90" in e for e in errors)


def test_preflight_fails_dirty_scene_text():
    scenes = [
        {
            "order": 1,
            "segments": [{"speaker": "scripture", "text": DIRTY_SCRIPTURE}],
            "meta": {"speaker": "scripture"},
        }
    ]
    errors = pre.check_scenes_text(scenes)
    assert errors
    joined = " ".join(errors)
    assert "!" in joined or "셀라" in joined or "다윗의 시" in joined


def test_preflight_fails_dirty_ass_if_present():
    ass = _ass_with([_dialogue("0:00:00.00", "0:00:02.00", "인생들아! (셀라)")])
    errors = pre.check_ass_text(ass)
    assert errors
    assert any("!" in e or "셀라" in e for e in errors)


def test_preflight_fails_skip_existing_in_tts_report():
    lock = _lock()
    report = {"ok": True, "skip_existing": True, "items": []}
    errors = pre.check_tts_report(report, lock)
    assert any("skip" in e.lower() for e in errors)

    report2 = {"ok": True, "args": {"skip-existing": True}}
    errors2 = pre.check_tts_report(report2, lock)
    assert any("skip" in e.lower() for e in errors2)


def test_preflight_fails_missing_provenance(tmp_path):
    job = make_job(tmp_path, write_provenance=False)
    errors = pre.check_provenance(job)
    assert any("provenance" in e.lower() for e in errors)


def test_preflight_fails_output_root_not_on_d():
    lock = _lock()
    lock["storage"]["final_root"] = r"C:\not_allowed\final"
    errors = pre.check_storage(lock)
    assert any("D:" in e or "output_root" in e.lower() or "final_root" in e for e in errors)


def test_preflight_ok_clean_job(tmp_path, monkeypatch):
    job = make_job(tmp_path)
    lock = _lock()
    # Avoid depending on real background bank / D: mount.
    monkeypatch.setattr(pre, "check_background", lambda *a, **k: [])
    monkeypatch.setattr(pre, "check_storage", lambda *a, **k: [])
    result = pre.run_preflight(job, lock=lock, root=tmp_path)
    assert result["ok"] is True
    assert result["errors"] == []


def test_preflight_config_ignores_stale_job_voice_map(tmp_path, monkeypatch):
    job = make_job(tmp_path, voice_map=_voice_map(scripture_voice="M5", scripture_step=24))
    lock = _lock()
    monkeypatch.setattr(pre, "check_background", lambda *a, **k: [])
    monkeypatch.setattr(pre, "check_storage", lambda *a, **k: [])
    result = pre.run_preflight(job, lock=lock, root=tmp_path)
    assert result["ok"] is True, result
    assert result["errors"] == []
    assert result.get("mode") == "config"


def test_preflight_config_allows_dirty_scripture_in_scenes(tmp_path, monkeypatch):
    scenes = [
        {
            "order": 1,
            "segments": [{"speaker": "scripture", "text": DIRTY_SCRIPTURE}],
            "meta": {"speaker": "scripture"},
        }
    ]
    job = make_job(
        tmp_path,
        scenes=scenes,
        voice_map=_voice_map(
            scripture_voice="M5",
            scripture_step=24,
            max_chunk=200,
            audio_filter="",
        ),
        write_provenance=False,
        write_ass=True,
        ass_text=_ass_with([_dialogue("0:00:00.00", "0:00:02.00", "인생들아! (셀라)")]),
        write_auth_audio=False,
    )
    lock = _lock()
    monkeypatch.setattr(pre, "check_background", lambda *a, **k: [])
    monkeypatch.setattr(pre, "check_storage", lambda *a, **k: [])
    result = pre.run_preflight(job, lock=lock, root=tmp_path)
    assert result["ok"] is True, result
    assert result["errors"] == []
    errors = pre.check_preflight_config(lock, root=tmp_path)
    assert errors == []


# ---------------------------------------------------------------------------
# Postflight unit checks
# ---------------------------------------------------------------------------


def test_postflight_fails_missing_h264_aac():
    probe = {
        "format": {"duration": "10.0"},
        "streams": [
            {"codec_type": "video", "codec_name": "mpeg4"},
            {"codec_type": "audio", "codec_name": "mp3"},
        ],
    }
    errors = post.check_streams(probe)
    assert any("h264" in e.lower() or "avc" in e.lower() or "codec" in e.lower() for e in errors)
    assert any("aac" in e.lower() or "codec" in e.lower() for e in errors)


def test_postflight_fails_missing_moov_or_duration():
    probe = {
        "format": {},
        "streams": [
            {"codec_type": "video", "codec_name": "h264"},
            {"codec_type": "audio", "codec_name": "aac"},
        ],
    }
    errors = post.check_streams(probe)
    assert any("duration" in e.lower() or "moov" in e.lower() for e in errors)


def test_postflight_fails_duration_delta():
    errors = post.check_duration_delta(100.0, 98.0, 0.5)
    assert errors
    assert any("duration" in e.lower() or "delta" in e.lower() for e in errors)


def test_postflight_fails_first_caption_mismatch():
    ass = _ass_with([_dialogue("0:00:00.00", "0:00:02.00", "전혀 다른 첫 줄입니다")])
    errors = post.check_first_caption(ass, CLEAN_NARRATION)
    assert errors
    assert any("first" in e.lower() or "caption" in e.lower() for e in errors)


def test_postflight_fails_first_caption_head_only_in_middle():
    """Head substring mid-caption is not prefix alignment — must fail."""
    san = sanitize_script(CLEAN_NARRATION).display
    head = san[: max(4, min(10, len(san)))]
    # head appears only in the middle, not as a prefix
    mid = f"앞말{head}입니다"
    assert not mid.startswith(head)
    assert head in mid
    ass = _ass_with([_dialogue("0:00:00.00", "0:00:02.00", mid)])
    errors = post.check_first_caption(ass, CLEAN_NARRATION)
    assert errors
    assert any("first_caption" in e for e in errors)


def test_postflight_fails_ass_qa_selah_bang_long_line():
    ass = _ass_with(
        [
            _dialogue("0:00:00.00", "0:00:02.00", "인생들아!"),
            _dialogue("0:00:02.00", "0:00:04.00", "셀라 다윗의 시 본문"),
            _dialogue(
                "0:00:04.00",
                "0:00:06.00",
                "이것은이십자를훨씬넘는매우긴한글자막한줄입니다초과",
            ),
        ]
    )
    errors = post.check_ass_qa(ass)
    assert errors
    joined = " ".join(errors)
    assert "!" in joined or "셀라" in joined or "다윗" in joined or "20" in joined


def test_postflight_ok_with_mocked_probe(tmp_path):
    san = sanitize_script(CLEAN_NARRATION).display
    first = san[:18] if len(san) > 18 else san
    ass = _ass_with(
        [
            _dialogue("0:00:00.00", "0:00:04.00", first),
            _dialogue("0:00:04.00", "0:00:10.00", "내 의의 하나님이여", style="Scripture"),
        ]
    )
    job = make_job(tmp_path, ass_text=ass)
    out = tmp_path / "out.mp4"
    out.write_bytes(b"fake")
    probe = {
        "format": {"duration": "10.0"},
        "streams": [
            {"codec_type": "video", "codec_name": "h264"},
            {"codec_type": "audio", "codec_name": "aac"},
        ],
    }
    result = post.run_postflight(
        out,
        job=job,
        lock=_lock(),
        probe=probe,
    )
    assert result["ok"] is True, result


def test_postflight_fails_when_ffprobe_missing_and_mp4_exists(tmp_path, monkeypatch):
    """MP4 present but no probe → fail closed with ffprobe_unavailable."""
    san = sanitize_script(CLEAN_NARRATION).display
    first = san[:18] if len(san) > 18 else san
    ass = _ass_with([_dialogue("0:00:00.00", "0:00:10.00", first)])
    job = make_job(tmp_path, ass_text=ass)
    out = tmp_path / "out.mp4"
    out.write_bytes(b"fake")
    monkeypatch.setattr(post, "resolve_ffprobe", lambda: None)
    monkeypatch.setattr(post, "ffprobe_media", lambda *a, **k: None)
    result = post.run_postflight(out, job=job, lock=_lock(), probe=None)
    assert result["ok"] is False
    assert any("ffprobe_unavailable" in e for e in result["errors"])
    # Do not invent codec errors without a probe payload.
    assert not any("h264" in e.lower() for e in result["errors"])


def test_postflight_does_not_require_real_d_drive_mp4(tmp_path):
    """Regression: unit path never opens D:\\ deploy mp4."""
    san = sanitize_script(CLEAN_NARRATION).display
    first = san[:18]
    ass = _ass_with([_dialogue("0:00:00.00", "0:00:10.00", first)])
    job = make_job(tmp_path, ass_text=ass)
    out = tmp_path / "local-only.mp4"
    out.write_bytes(b"x")
    probe = {
        "format": {"duration": "10.0"},
        "streams": [
            {"codec_type": "video", "codec_name": "h264"},
            {"codec_type": "audio", "codec_name": "aac"},
        ],
    }
    with mock.patch.object(post, "ffprobe_media") as mocked:
        result = post.run_postflight(out, job=job, lock=_lock(), probe=probe)
        mocked.assert_not_called()
    assert result["ok"] is True
