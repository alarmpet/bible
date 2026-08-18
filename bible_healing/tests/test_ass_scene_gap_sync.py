# -*- coding: utf-8 -*-
"""ASS timeline must include the same inter-scene gap as authoritative concat."""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from tts_assembly import accumulate_scene_windows  # noqa: E402


def test_second_scene_starts_after_scene_gap():
    windows = accumulate_scene_windows([3.5145, 11.490792], scene_gap=0.6)
    assert windows[0] == (0.0, 3.5145)
    assert abs(windows[1][0] - 4.1145) < 1e-6
    assert abs(windows[1][1] - 15.605292) < 1e-6


def test_ten_scenes_add_nine_gaps():
    durs = [3.5] * 10
    windows = accumulate_scene_windows(durs, scene_gap=0.6)
    assert abs(windows[-1][1] - (35.0 + 9 * 0.6)) < 1e-6


def test_ass_builder_inserts_scene_gap_when_manifest_has_no_starts(tmp_path):
    from build_full_audio_aligned_ass import (
        build_full_audio_aligned_ass,
        parse_ass_events,
    )

    job = tmp_path / "job"
    job.mkdir()
    text1 = "불을 껐는데, 머릿속은 아직 환한 밤이 있습니다."
    text2 = "오늘 한 말이 자꾸 돌아오고 있습니다."
    (job / "scenes.json").write_text(
        __import__("json").dumps(
            [
                {
                    "order": 1,
                    "narration": text1,
                    "segments": [{"speaker": "narrator", "text": text1}],
                    "meta": {"speaker": "narrator"},
                },
                {
                    "order": 2,
                    "narration": text2,
                    "segments": [{"speaker": "narrator", "text": text2}],
                    "meta": {"speaker": "narrator"},
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (job / "scene_audio_manifest.json").write_text(
        __import__("json").dumps(
            {
                "items": [
                    {"order": 1, "duration": 3.5145, "ok": True},
                    {"order": 2, "duration": 11.490792, "ok": True},
                ]
            }
        ),
        encoding="utf-8",
    )
    ass_path = build_full_audio_aligned_ass(job)
    events = parse_ass_events(ass_path.read_text(encoding="utf-8-sig"))
    assert events
    second = next(e for e in events if "오늘 한 말이" in e["text"])
    assert abs(second["start"] - 4.1145) < 0.05
