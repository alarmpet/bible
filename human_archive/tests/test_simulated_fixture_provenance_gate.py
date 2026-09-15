# -*- coding: utf-8 -*-
"""Task 2, §5.3 rule 4 (human_archive-specific addition to the ported all-manage
fail-closed rules): "시뮬레이션/fixture 모드는 provenance: 'simulated_fixture'로
표기하고 release 게이트를 자동 차단한다."

tri_model_debate_engine.py's orchestrate_deep_tri_model_script() Round 1/2 (the
p_38/p_37/p_36 proposals and cross-critique dicts) are static templated text, not
live model calls -- this is the exact "tri-model AI debate that never called a
model" failure §2 of the 2026-09-15 overhaul plan diagnosed. Rather than attempt
the full quarantine-into-thin-adapter rewrite of tri_model_debate_engine.py /
tri_model_llm_bridge.py in one pass (a large, GUI-event-streaming-coupled rewrite
that can't be live-verified in this environment), this labels that manifest
honestly (metadata.provenance == "simulated_fixture") and makes
verify_postflight() refuse to release a build carrying that label -- the gate
half of the rule, verifiable without running the whole heavy orchestration
function.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from postflight_release import verify_postflight  # noqa: E402


def _write_master_manifest(build_dir: Path, *, provenance: str | None) -> None:
    (build_dir / "generation").mkdir(parents=True, exist_ok=True)
    metadata = {"channel": "test", "title": "test episode"}
    if provenance is not None:
        metadata["provenance"] = provenance
        metadata["provenance_detail"] = "Round 1/2 are static templated text."
    manifest = {"metadata": metadata, "shots": []}
    (build_dir / "generation" / "master_1200s_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )


def test_verify_postflight_blocks_a_build_labeled_simulated_fixture(tmp_path: Path):
    video_path = tmp_path / "candidate.mp4"
    video_path.write_bytes(b"not a real video, just needs to exist")
    _write_master_manifest(tmp_path, provenance="simulated_fixture")

    ok, report = verify_postflight(video_path, build_dir=tmp_path, duration_mode="full")

    assert ok is False
    assert report["checks"]["simulated_fixture_provenance"]["status"] == "FAIL"
    assert any("simulated_fixture" in err for err in report["errors"])


def test_verify_postflight_passes_this_check_when_no_generation_manifest_exists(tmp_path: Path):
    video_path = tmp_path / "candidate.mp4"
    video_path.write_bytes(b"not a real video, just needs to exist")

    _ok, report = verify_postflight(video_path, build_dir=tmp_path, duration_mode="full")

    assert report["checks"]["simulated_fixture_provenance"]["status"] == "PASS"


def test_verify_postflight_passes_this_check_when_provenance_is_something_else(tmp_path: Path):
    video_path = tmp_path / "candidate.mp4"
    video_path.write_bytes(b"not a real video, just needs to exist")
    _write_master_manifest(tmp_path, provenance="live_generation")

    _ok, report = verify_postflight(video_path, build_dir=tmp_path, duration_mode="full")

    assert report["checks"]["simulated_fixture_provenance"]["status"] == "PASS"


def test_verify_postflight_checks_the_audit_consensus_manifest_too(tmp_path: Path):
    video_path = tmp_path / "candidate.mp4"
    video_path.write_bytes(b"not a real video, just needs to exist")
    (tmp_path / "audit").mkdir(parents=True)
    manifest = {"metadata": {"provenance": "simulated_fixture"}}
    (tmp_path / "audit" / "final_consensus_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    ok, report = verify_postflight(video_path, build_dir=tmp_path, duration_mode="full")

    assert ok is False
    assert report["checks"]["simulated_fixture_provenance"]["status"] == "FAIL"


def test_orchestrate_deep_tri_model_script_source_resolves_provenance_from_the_real_debate_round():
    """A lightweight source-level check rather than a full integration test:
    orchestrate_deep_tri_model_script() is a large, GUI-event-streaming-coupled
    function (HistoricalParallelEngine, SentenceHistoricalFactChecker,
    SemanticSubtitleEngine, multiple file writes) that this session did not
    build the fixtures to run end-to-end.

    Task 2's Quarantine follow-up (2026-09-15 overhaul plan §7, task_fcf94ecb)
    replaced Round 1/2's static templated dicts with a real
    run_consensus_round.escalate_claim() round
    (lib/tri_model_real_debate.py), so `provenance` is no longer a literal
    "simulated_fixture" constant in this file -- it is computed by
    `resolve_provenance()` from whether that round actually completed. This
    pins that the manifest still gets its provenance from that real resolution
    (not a re-hardcoded literal), and that the fail-closed
    "simulated_fixture" label this test file's gate tests depend on still
    lives somewhere reachable -- in `lib/tri_model_real_debate.py`'s
    `resolve_provenance()`, verified directly by
    test_tri_model_real_debate.py -- so a future edit that silently drops
    either the wiring or the fallback label is caught."""
    source = (_SCRIPTS_DIR / "tri_model_debate_engine.py").read_text(encoding="utf-8")
    assert "final_manifest" in source
    assert '"provenance": debate_provenance' in source, (
        "final_manifest['metadata']['provenance'] must come from resolve_provenance(), "
        "not a re-hardcoded literal")
    assert "resolve_provenance" in source and "run_structure_debate" in source

    lib_source = (_SCRIPTS_DIR / "lib" / "tri_model_real_debate.py").read_text(encoding="utf-8")
    assert '"simulated_fixture"' in lib_source, (
        "the fail-closed label postflight_release.py gates on must still exist as the "
        "fallback when the real debate round is incomplete")
    assert '"live_orchestration"' in lib_source
