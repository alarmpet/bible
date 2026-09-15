from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_ROOT = REPO_ROOT / "human_archive" / "runs" / "ep02_jang_huibin" / "sample-3m-context-final"
CANDIDATE = RUN_ROOT / "candidate" / "HA002-sample-3m-context-final.mp4"
AUDIT_ROOT = REPO_ROOT / "human_archive" / "audits" / "ep02_sample_3m_2026-08-31"
AUDIT_MANIFEST = AUDIT_ROOT / "audit_manifest.json"


def _ffprobe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_context_sample_audit_baseline_is_immutable_and_complete() -> None:
    assert CANDIDATE.exists()
    assert AUDIT_MANIFEST.exists(), "create the read-only audit manifest before changing the sample"
    manifest = json.loads(AUDIT_MANIFEST.read_text(encoding="utf-8"))
    candidate = manifest["candidate"]
    assert candidate["sha256"] == "96F7909D78E6BE1C8DA141CF1A80B8F61B69B2019B36860A4485B168FE960573"
    assert candidate["duration_sec"] == 138.84
    assert candidate["video"]["width"] == 1920
    assert candidate["video"]["height"] == 1080
    assert candidate["video"]["fps"] == "25/1"
    assert candidate["audio"]["sample_rate"] == 48000
    assert candidate["artifact_counts"] == {"audio_wav": 22, "images": 22, "motion_clips": 22, "subtitle_dialogues": 22}
    assert _ffprobe(CANDIDATE)["format"]["format_name"] == "mov,mp4,m4a,3gp,3g2,mj2"
