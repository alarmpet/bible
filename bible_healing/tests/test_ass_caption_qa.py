# -*- coding: utf-8 -*-
"""QA for the single Korean two-line ASS caption path."""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from build_ass_from_cues import build_ass  # noqa: E402
from build_cues_from_manifest import build  # noqa: E402
from build_full_audio_aligned_ass import (  # noqa: E402
    build_full_audio_aligned_ass,
    qa_ass,
)

PROD_ASS = (
    Path(__file__).resolve().parents[1]
    / "runs"
    / "ep01_anxious_night"
    / "hermes_jobs"
    / "full"
    / "subtitles-full-audio-aligned.ass"
)

CLEAN_NARRATION = "불을 껐는데, 머릿속은 아직 환한 밤이 있습니다."
DIRTY_SCRIPTURE = (
    "(다윗의 시. 영장으로 현악에 맞춘 노래) 내 의의 하나님이여, "
    "내가 부를 때에 응답하소서. 인생들아 ! (셀라)"
)


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
    scenes: list[dict] | None = None,
    manifest_scenes: list[dict] | None = None,
    pieces: list[dict] | None = None,
    write_provenance: bool = False,
) -> Path:
    job = root / "hermes_jobs" / "full"
    job.mkdir(parents=True, exist_ok=True)
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
                "narration": DIRTY_SCRIPTURE,
                "segments": [{"speaker": "scripture", "text": DIRTY_SCRIPTURE}],
                "meta": {"speaker": "scripture"},
            },
        ]
    if manifest_scenes is None:
        manifest_scenes = [
            {
                "order": 1,
                "startSeconds": 0.0,
                "endSeconds": 4.0,
                "text": CLEAN_NARRATION,
                "duration": 4.0,
            },
            {
                "order": 2,
                "startSeconds": 4.0,
                "endSeconds": 10.0,
                "text": DIRTY_SCRIPTURE,
                "duration": 6.0,
            },
        ]
    (job / "scenes.json").write_text(
        json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    last_end = float(manifest_scenes[-1]["endSeconds"]) if manifest_scenes else 0.0
    man = {
        "status": "measured-and-locked",
        "durationSeconds": last_end,
        "scenes": manifest_scenes,
    }
    (job / "scene_audio_manifest.json").write_text(
        json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if write_provenance:
        reports = job / "reports"
        reports.mkdir(exist_ok=True)
        (reports / "tts_provenance.json").write_text(
            json.dumps(
                {"ok": True, "engine": "supertonic3", "pieces": pieces or []},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    return job


def test_import_does_not_write_production_ass():
    before = PROD_ASS.stat().st_mtime_ns if PROD_ASS.exists() else None
    import build_full_audio_aligned_ass as mod

    importlib.reload(mod)
    after = PROD_ASS.stat().st_mtime_ns if PROD_ASS.exists() else None
    assert before == after
    assert not hasattr(mod, "chunks")
    assert callable(mod.build_full_audio_aligned_ass)


def test_qa_fails_on_selah():
    ass = _ass_with([_dialogue("0:00:00.00", "0:00:02.00", "평안히 눕고 셀라 자기도 하리니")])
    result = qa_ass(ass)
    assert result["ok"] is False
    assert any("셀라" in e for e in result["errors"])


def test_qa_fails_on_david_psalm_title():
    ass = _ass_with([_dialogue("0:00:00.00", "0:00:02.00", "다윗의 시 내 의의 하나님이여")])
    result = qa_ass(ass)
    assert result["ok"] is False
    assert any("다윗의 시" in e for e in result["errors"])


def test_qa_fails_on_bang():
    ass = _ass_with([_dialogue("0:00:00.00", "0:00:02.00", "인생들아!")])
    result = qa_ass(ass)
    assert result["ok"] is False
    assert any("!" in e for e in result["errors"])


def test_qa_fails_on_yeongjang_and_paren():
    ass = _ass_with([_dialogue("0:00:00.00", "0:00:02.00", "(영장으로 현악에 맞춘 노래)")])
    result = qa_ass(ass)
    assert result["ok"] is False
    joined = " ".join(result["errors"])
    assert "영장" in joined or "(" in joined


def test_qa_fails_on_line_over_20():
    ass = _ass_with([_dialogue("0:00:00.00", "0:00:02.00", "가" * 21)])
    result = qa_ass(ass)
    assert result["ok"] is False
    assert any("20" in e for e in result["errors"])


def test_qa_fails_on_more_than_two_lines():
    text = r"첫 줄입니다\N둘째 줄입니다\N셋째 줄입니다"
    ass = _ass_with([_dialogue("0:00:00.00", "0:00:02.00", text)])
    result = qa_ass(ass)
    assert result["ok"] is False
    assert any("줄" in e or "line" in e.lower() or r"\N" in e for e in result["errors"])


def test_qa_fails_on_reversed_times():
    ass = _ass_with([_dialogue("0:00:03.00", "0:00:01.00", "짧은 본문입니다")])
    result = qa_ass(ass)
    assert result["ok"] is False
    assert any("역전" in e or "reverse" in e.lower() or "time" in e.lower() for e in result["errors"])


def test_qa_fails_on_zero_events():
    result = qa_ass(_ass_with([]))
    assert result["ok"] is False
    assert result["event_count"] == 0
    assert any("event" in e.lower() or "dialogue" in e.lower() for e in result["errors"])


def test_builder_uses_items_manifest_durations(tmp_path):
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
    job = tmp_path / "items_job"
    job.mkdir()
    (job / "scenes.json").write_text(
        json.dumps(scenes, ensure_ascii=False), encoding="utf-8"
    )
    (job / "scene_audio_manifest.json").write_text(
        json.dumps(
            {
                "ok": True,
                "items": [
                    {"order": 1, "path": "scene_1.wav", "duration": 4.0},
                    {"order": 2, "path": "scene_2.wav", "duration": 6.0},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    text = build_full_audio_aligned_ass(job).read_text(encoding="utf-8-sig")
    assert "Dialogue:" in text
    result = qa_ass(text)
    assert result["ok"] is True, result
    assert result["event_count"] > 0
    assert abs(result["last_end_seconds"] - 10.6) <= 0.5


def test_tmp_job_sanitizes_and_passes_qa(tmp_path):
    job = make_job(tmp_path)
    out = build_full_audio_aligned_ass(job)
    assert out.exists()
    assert out.name == "subtitles-full-audio-aligned.ass"
    assert out.resolve() != PROD_ASS.resolve()
    text = out.read_text(encoding="utf-8-sig")
    result = qa_ass(text)
    assert result["ok"] is True, result
    body = text.split("[Events]", 1)[-1]
    assert "셀라" not in body
    assert "다윗의 시" not in body
    assert "영장" not in body
    assert "(" not in body
    assert "!" not in body


def test_lock_typography_in_generated_header(tmp_path):
    job = make_job(tmp_path)
    text = build_full_audio_aligned_ass(job).read_text(encoding="utf-8-sig")
    assert "ScaledBorderAndShadow: yes" in text
    assert "Style: Narrator,Malgun Gothic,96," in text
    assert "Style: Scripture,Malgun Gothic,100," in text
    narr = next(ln for ln in text.splitlines() if ln.startswith("Style: Narrator,"))
    parts = narr.split(",")
    assert parts[16] == "6"
    assert parts[17] == "3"
    assert parts[21] == "90"


def test_fallback_timing_drift_within_half_second(tmp_path):
    job = make_job(tmp_path, write_provenance=False)
    text = build_full_audio_aligned_ass(job).read_text(encoding="utf-8-sig")
    result = qa_ass(text)
    assert result["ok"] is True, result
    assert abs(result["last_end_seconds"] - 10.0) <= 0.5


def test_provenance_piece_windows_used(tmp_path):
    pieces = [
        {
            "speaker": "narrator",
            "voice": "F5",
            "text": CLEAN_NARRATION,
            "scene_order": 1,
            "duration": 2.0,
        },
        {
            "speaker": "scripture",
            "voice": "M4",
            "text": "내 의의 하나님이여 내가 부를 때에 응답하소서.",
            "scene_order": 2,
            "duration": 2.5,
        },
        {
            "speaker": "scripture",
            "voice": "M4",
            "text": "여호와께서 자기를 위하여 경건한 자를 택하신 줄 너희가 알지어다.",
            "scene_order": 2,
            "duration": 2.5,
        },
    ]
    job = make_job(tmp_path, pieces=pieces, write_provenance=True)
    text = build_full_audio_aligned_ass(job).read_text(encoding="utf-8-sig")
    result = qa_ass(text)
    assert result["ok"] is True, result
    events = result["events"]
    scene1 = [e for e in events if e["style"] == "Narrator"]
    assert scene1
    assert max(e["end"] for e in scene1) == pytest.approx(4.0, abs=1e-3)
    scene2 = [e for e in events if e["style"] == "Scripture"]
    assert scene2
    assert min(e["start"] for e in scene2) >= 4.0 - 1e-6
    # Piece durs 2.5+2.5 are shorter than the 6s scene; scale to the scene end.
    assert max(e["end"] for e in scene2) == pytest.approx(10.0, abs=1e-3)
    later = [e for e in scene2 if "알지어다" in e["text"]]
    assert later
    assert min(e["start"] for e in later) >= 7.0 - 1e-3


def test_generated_ass_keeps_adjective_with_noun(tmp_path):
    job = make_job(tmp_path)
    body = build_full_audio_aligned_ass(job).read_text(encoding="utf-8-sig")
    body = body.split("[Events]", 1)[-1]
    assert r"환한\N" not in body
    assert "환한 밤이" in body or "밤이 있습니다" in body


def test_cues_from_manifest_uses_korean_splitter(tmp_path):
    job = make_job(tmp_path)
    build(job)
    cues = json.loads((job / "cues.json").read_text(encoding="utf-8"))["cues"]
    assert cues
    for cue in cues:
        text = cue["text"]
        assert "셀라" not in text
        assert "다윗의 시" not in text
        assert "!" not in text
        lines = text.replace("\n", r"\N").split(r"\N")
        assert len(lines) <= 2
        assert all(len(line) <= 20 for line in lines)
    joined = " ".join(cue["text"] for cue in cues)
    assert "환한 밤이" in joined or "밤이 있습니다" in joined
    assert not any(cue["text"].replace(r"\N", "").endswith("환한") for cue in cues)


def test_build_ass_from_cues_uses_lock_font_sizes(tmp_path):
    job = make_job(tmp_path)
    build(job)
    text = build_ass(job).read_text(encoding="utf-8-sig")
    assert "Style: Narrator,Malgun Gothic,96," in text
    assert "Style: Scripture,Malgun Gothic,100," in text
    assert "ScaledBorderAndShadow: yes" in text
    result = qa_ass(text)
    assert result["ok"] is True, result
