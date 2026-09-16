import re
from pathlib import Path

import pytest

from lib.ep02_visual_scene_catalog import EP02_SCENES_BY_DIGEST
from lib.visual_brief_provider import (
    CodexCliVisualBriefProvider,
    JsonFileVisualBriefProvider,
    build_fallback_brief,
)
from generate_visual_briefs import resolve_host_ratio, select_host_shot_ids, validate_brief_sequence


def _write_provider_schema(tmp_path):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(
        '{"type":"object","required":["schema_version","briefs"],'
        '"properties":{"schema_version":{"const":1},"briefs":{"type":"array"}}}',
        encoding="utf-8",
    )
    return schema_path


def test_codex_provider_uses_schema_ephemeral_read_only_and_no_shell(tmp_path, monkeypatch):
    # 2026-09-16: found live on Windows -- a bare "codex" with shell=False
    # fails (WinError 2) when codex is an npm-installed codex.CMD shim,
    # because CreateProcess doesn't apply PATHEXT resolution the way a shell
    # does. The provider now resolves the executable via shutil.which() (like
    # run_consensus_round.py's codex_cmd() already did); pin that resolution
    # here instead of depending on the test host's real PATH state.
    monkeypatch.setattr(
        "lib.visual_brief_provider.shutil.which",
        lambda name: r"C:\fake\codex.CMD" if name == "codex" else None,
    )
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        output = Path(args[args.index("--output-last-message") + 1])
        output.write_text('{"schema_version":1,"briefs":[]}', encoding="utf-8")
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    provider = CodexCliVisualBriefProvider(repo_root=tmp_path, runner=fake_run)
    provider.generate("PROMPT", _write_provider_schema(tmp_path))
    args, kwargs = calls[0]
    assert args[:2] == [r"C:\fake\codex.CMD", "exec"]
    assert ["--ephemeral", "--sandbox", "read-only"] == args[2:5]
    assert "--output-schema" in args and "--output-last-message" in args
    assert kwargs["input"] == "PROMPT"
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["shell"] is False


def test_codex_provider_raises_clear_error_when_codex_not_on_path(tmp_path, monkeypatch):
    monkeypatch.setattr("lib.visual_brief_provider.shutil.which", lambda name: None)
    provider = CodexCliVisualBriefProvider(repo_root=tmp_path, runner=lambda *a, **k: None)
    with pytest.raises(FileNotFoundError, match="codex is not on PATH"):
        provider.generate("PROMPT", _write_provider_schema(tmp_path))


def test_codex_provider_surfaces_nonzero_exit_stderr(tmp_path):
    def failed_run(args, **kwargs):
        return type(
            "Result",
            (),
            {"returncode": 7, "stdout": "", "stderr": "authentication failed"},
        )()

    provider = CodexCliVisualBriefProvider(repo_root=tmp_path, runner=failed_run)
    with pytest.raises(RuntimeError, match="authentication failed"):
        provider.generate("PROMPT", _write_provider_schema(tmp_path))


def test_codex_provider_rejects_malformed_json(tmp_path):
    def malformed_run(args, **kwargs):
        output = Path(args[args.index("--output-last-message") + 1])
        output.write_text("not-json", encoding="utf-8")
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    provider = CodexCliVisualBriefProvider(repo_root=tmp_path, runner=malformed_run)
    with pytest.raises(ValueError, match="JSON"):
        provider.generate("PROMPT", _write_provider_schema(tmp_path))


def test_json_file_provider_schema_validates_fixture(tmp_path):
    response_path = tmp_path / "response.json"
    response_path.write_text('{"schema_version":1}', encoding="utf-8")
    provider = JsonFileVisualBriefProvider(response_path)
    with pytest.raises(ValueError, match="briefs"):
        provider.generate("IGNORED", _write_provider_schema(tmp_path))


def test_host_selector_scales_with_dynamic_shot_count_and_keeps_spacing():
    shots = [{"shot_id": f"S{i:03d}"} for i in range(1, 113)]
    selected = select_host_shot_ids(shots, ratio=0.10, min_non_host_gap=7)
    positions = [i for i, shot in enumerate(shots) if shot["shot_id"] in selected]

    assert 0.08 <= len(selected) / len(shots) <= 0.12
    assert all(right - left >= 8 for left, right in zip(positions, positions[1:]))


def test_host_selector_honors_a_genuinely_zero_ratio():
    """Found live by a real codex+grok escalate_claim() smoke test
    (2026-09-16): ratio=0.0 (nollam_file_v1's declared host_ratio, "호스트
    아바타 완전 배제") used to still floor to max(1, ceil(count*0.08)) -- at
    least one host shot no matter what. nollam_file_v1 must get zero."""
    shots = [{"shot_id": f"S{i:03d}"} for i in range(1, 113)]
    assert select_host_shot_ids(shots, ratio=0.0) == set()


def test_host_selector_treats_negative_ratio_as_zero_too():
    shots = [{"shot_id": f"S{i:03d}"} for i in range(1, 20)]
    assert select_host_shot_ids(shots, ratio=-0.01) == set()


def test_resolve_host_ratio_reads_nollam_file_v1_zero_from_config():
    assert resolve_host_ratio("nollam_file_v1") == 0.0


def test_resolve_host_ratio_reads_doodle_seonbi_v1_range_midpoint():
    # doodle_seonbi_v1 declares visual.host_ratio: [0.15, 0.25]
    assert resolve_host_ratio("doodle_seonbi_v1") == pytest.approx(0.20)


def test_resolve_host_ratio_keeps_the_historical_default_when_no_profile_given():
    assert resolve_host_ratio(None) == 0.10


def test_resolve_host_ratio_falls_back_for_an_unknown_profile():
    assert resolve_host_ratio("no_such_profile") == 0.10


def test_brief_sequence_must_exactly_match_timing_order():
    shots = [{"shot_id": "S1"}, {"shot_id": "S2"}]
    briefs = [{"shot_id": "S2"}, {"shot_id": "S1"}]

    with pytest.raises(ValueError, match="shot IDs"):
        validate_brief_sequence(shots, briefs)


def test_brief_sequence_requires_direct_depiction_majority():
    shots = [{"shot_id": f"S{i}"} for i in range(10)]
    modes = [
        "diagram_metaphor",
        "diagram_metaphor",
        "historical_reconstruction",
        "diagram_metaphor",
        "diagram_metaphor",
        "evidence_artifact",
        "diagram_metaphor",
        "diagram_metaphor",
        "character_action",
        "place_establishing",
    ]
    briefs = [
        {"shot_id": shot["shot_id"], "visual_mode": mode, "prop_motifs": []}
        for shot, mode in zip(shots, modes)
    ]

    with pytest.raises(ValueError, match="direct depiction ratio"):
        validate_brief_sequence(shots, briefs)


def test_brief_sequence_rejects_same_mode_streak_over_two():
    shots = [{"shot_id": f"S{i}"} for i in range(3)]
    briefs = [
        {
            "shot_id": shot["shot_id"],
            "visual_mode": "historical_reconstruction",
            "prop_motifs": [],
        }
        for shot in shots
    ]

    with pytest.raises(ValueError, match="same visual mode streak"):
        validate_brief_sequence(shots, briefs)


def test_brief_sequence_rejects_repeated_motif_family_in_ten_shot_window():
    shots = [{"shot_id": f"S{i}"} for i in range(10)]
    modes = [
        "historical_reconstruction",
        "evidence_artifact",
        "character_action",
        "place_establishing",
        "historical_reconstruction",
        "evidence_artifact",
        "character_action",
        "place_establishing",
        "historical_reconstruction",
        "evidence_artifact",
    ]
    motifs = [
        ["sealed record case"],
        [],
        [],
        ["closed wooden box"],
        [],
        [],
        [],
        ["archive chest"],
        [],
        [],
    ]
    briefs = [
        {
            "shot_id": shot["shot_id"],
            "visual_mode": mode,
            "prop_motifs": motif,
        }
        for shot, mode, motif in zip(shots, modes, motifs)
    ]

    with pytest.raises(ValueError, match="motif family"):
        validate_brief_sequence(shots, briefs)


def test_brief_sequence_counts_visual_props_not_abstract_boundary_wording():
    shots = [{"shot_id": f"S{i}"} for i in range(10)]
    modes = [
        "historical_reconstruction",
        "evidence_artifact",
        "character_action",
        "place_establishing",
        "historical_reconstruction",
        "evidence_artifact",
        "character_action",
        "place_establishing",
        "historical_reconstruction",
        "evidence_artifact",
    ]
    actions = [
        "A theatrical light boundary separates fact from staging.",
        "An attendant crosses a courtyard.",
        "A cord marks an evidentiary boundary.",
        "Officials enter a palace hall.",
        "Material contrast creates a supported boundary.",
        "A document rests beneath an inspection lamp.",
        "A messenger carries a wrapped object.",
        "The camera settles on the residence.",
        "Witnesses wait in profile.",
        "A plain baton rests on a stone riser.",
    ]
    motifs = [
        ["theatrical shadow", "evidence light"],
        ["courtyard paving"],
        ["inspection cord", "evidence pebble"],
        ["palace hall"],
        ["material contrast", "decision baton"],
        ["document", "inspection lamp"],
        ["wrapped object"],
        ["residence courtyard"],
        ["court attire"],
        ["stone riser", "plain baton"],
    ]
    briefs = [
        {
            "shot_id": shot["shot_id"],
            "visual_mode": mode,
            "action": action,
            "prop_motifs": motif,
        }
        for shot, mode, action, motif in zip(shots, modes, actions, motifs)
    ]

    validate_brief_sequence(shots, briefs)


def test_fallback_brief_preserves_narration_and_avoids_forced_host():
    shot={"shot_id":"S1","sentence_spans":[{"sentence_id":"S1"}],"chapter":1}
    brief=build_fallback_brief(shot,{"S1":"왕권의 처분을 두고 대신들이 반대했습니다"})
    assert brief["narration_digest"]
    assert brief["visual_mode"] != "host_chapter_hinge"
    assert "1701" not in str(brief)
    assert brief["semantic_anchors"]

def test_record_silence_brief_is_concrete_and_not_placeholder():
    shot={"shot_id":"S2","sentence_spans":[{"sentence_id":"S2"}],"chapter":1}
    brief=build_fallback_brief(shot,{"S2":"실록에도 승정원일기에도 난동 기록은 없습니다"})
    assert "narration-specific" not in brief["focal_subject"]
    assert "sealed" in brief["action"].lower() or "closed" in brief["action"].lower()
    assert len(brief["semantic_anchors"]) >= 2


def test_unknown_narration_fails_closed_instead_of_emitting_generic_palace_scene():
    shot={"shot_id":"UNKNOWN","sentence_spans":[{"sentence_id":"S1"}],"chapter":1}
    with pytest.raises(ValueError, match="No concrete visual scene rule"):
        build_fallback_brief(shot,{"S1":"아직 시각 규칙이 없는 완전히 새로운 내레이션입니다"})


def test_ep02_curated_catalog_covers_all_former_generic_shots_without_hangul_prompts():
    assert len(EP02_SCENES_BY_DIGEST) == 74
    for digest, scene in EP02_SCENES_BY_DIGEST.items():
        assert digest
        assert len(scene["anchors"]) >= 3
        rendered = " ".join([*scene["anchors"], scene["action"], scene["place"]])
        assert not re.search(r"[가-힣]", rendered)
        assert "described by the narration" not in rendered
