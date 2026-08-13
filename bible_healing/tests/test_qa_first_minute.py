import json
import shutil
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from qa_first_minute import evaluate_job  # noqa: E402


TEST_ROOT = Path(__file__).resolve().parent / "_qa_first_minute_job"


def _write_job(manifest: dict, scenes: list[dict]) -> Path:
    if TEST_ROOT.exists():
        shutil.rmtree(TEST_ROOT)
    TEST_ROOT.mkdir()
    (TEST_ROOT / "scene_audio_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (TEST_ROOT / "scenes.json").write_text(json.dumps(scenes, ensure_ascii=False), encoding="utf-8")
    return TEST_ROOT


def test_evaluate_job_writes_pass_report_for_valid_opening():
    job = _write_job(
        {"scenes": [{"order": 1, "startSeconds": 0, "endSeconds": 4}, {"order": 2, "startSeconds": 4, "endSeconds": 18}, {"order": 3, "startSeconds": 18, "endSeconds": 30}, {"order": 4, "startSeconds": 30, "endSeconds": 50}, {"order": 5, "startSeconds": 50, "endSeconds": 80}]},
        [
            {"order": 1, "narration": "불을 껐는데 머릿속은 아직 환한 밤입니다.", "meta": {"speaker": "narrator", "hook_phase": "hook"}},
            {"order": 2, "narration": "오늘 한 말이 돌아옵니다.", "meta": {"speaker": "narrator", "hook_phase": "mirror"}},
            {"order": 3, "narration": "당신이 약해서가 아닙니다.", "meta": {"speaker": "narrator", "hook_phase": "validate"}},
            {"order": 4, "narration": "편하다면 어깨의 힘을 내려놓으세요.", "meta": {"speaker": "narrator", "hook_phase": "permission_bridge"}},
            {"order": 5, "narration": "평안히 눕는 밤을 말하는 시편입니다.", "meta": {"speaker": "scripture"}},
        ],
    )
    try:
        report = evaluate_job(job)
        assert report["ok"] is True
        assert report["first_scripture_start_sec"] == 50.0
        assert (job / "reports" / "qa_first_minute.json").exists()
    finally:
        shutil.rmtree(job, ignore_errors=True)


def test_evaluate_job_blocks_late_scripture():
    job = _write_job(
        {"scenes": [{"order": 1, "startSeconds": 0, "endSeconds": 70}]},
        [{"order": 1, "narration": "설명", "meta": {"speaker": "narrator"}}],
    )
    try:
        report = evaluate_job(job)
        assert report["ok"] is False
        assert "missing_first_scripture" in report["violations"]
    finally:
        shutil.rmtree(job, ignore_errors=True)
