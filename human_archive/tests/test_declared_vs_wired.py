# -*- coding: utf-8 -*-
"""Task 0 (2026-09-15 overhaul plan): a "declared vs wired" gate for the exact
pattern this plan's diagnosis found repeatedly -- a capability gets a name, a
config entry, a whole module, and nothing in the production call graph ever
invokes it (check_decoded_stream_motion_mae, compile_nollam_prompt,
nollam_decay_20m before Tasks 1/5/7 wired them in for real).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from audit_declared_vs_wired import (  # noqa: E402
    REGISTRY,
    CapabilityCheck,
    audit,
    check_capability,
    find_call_sites,
    main,
)


def test_find_call_sites_ignores_the_def_line_itself():
    text = "def foo(x):\n    return x\n"
    assert find_call_sites(text, "foo") == []


def test_find_call_sites_ignores_async_def_and_class_declarations():
    text = "async def bar(x):\n    pass\n\nclass Baz(object):\n    pass\n"
    assert find_call_sites(text, "bar") == []
    assert find_call_sites(text, "Baz") == []


def test_find_call_sites_finds_a_real_call_on_its_own_line():
    text = "def foo(x):\n    return x\n\nresult = foo(1)\n"
    assert find_call_sites(text, "foo") == [4]


def test_find_call_sites_finds_a_call_in_the_same_file_as_the_definition():
    """The common real pattern this whole gate exists to catch: a helper
    defined in a module that a sibling function in the SAME file never
    actually calls (until it's wired in, exactly like postflight_release.py's
    verify_postflight() not calling check_decoded_stream_motion_mae until
    Task 5's measure_decoded_video_motion_diversity())."""
    text = (
        "def helper(x):\n"
        "    return x * 2\n"
        "\n"
        "def orchestrator(x):\n"
        "    return helper(x) + 1\n"
    )
    assert find_call_sites(text, "helper") == [5]


def test_find_call_sites_does_not_match_a_longer_identifier_sharing_a_prefix():
    text = "def foo(x):\n    return x\n\nresult = foo_extended(1)\n"
    assert find_call_sites(text, "foo") == []


def test_check_capability_passes_when_a_sibling_file_calls_the_declared_function(tmp_path: Path):
    (tmp_path / "scripts" / "lib").mkdir(parents=True)
    (tmp_path / "scripts" / "lib" / "helpers.py").write_text(
        "def widget():\n    return 1\n", encoding="utf-8"
    )
    (tmp_path / "scripts" / "main.py").write_text(
        "from lib.helpers import widget\n\ndef run():\n    return widget()\n", encoding="utf-8"
    )
    check = CapabilityCheck(
        name="widget",
        description="test widget",
        declared_in="scripts/lib/helpers.py",
    )
    result = check_capability(tmp_path, check)
    assert result.status == "PASS"
    assert result.call_sites


def test_check_capability_fails_when_declared_but_never_called(tmp_path: Path):
    (tmp_path / "scripts").mkdir(parents=True)
    (tmp_path / "scripts" / "helpers.py").write_text(
        "def orphan():\n    return 1\n", encoding="utf-8"
    )
    check = CapabilityCheck(
        name="orphan",
        description="test orphan",
        declared_in="scripts/helpers.py",
    )
    result = check_capability(tmp_path, check)
    assert result.status == "FAIL"
    assert result.call_sites == []


def test_check_capability_ignores_calls_inside_excluded_test_directories(tmp_path: Path):
    """A capability only ever exercised from tests/ is exactly the
    "declared but not production-wired" gap this gate exists to catch --
    it must not count as PASS."""
    (tmp_path / "scripts").mkdir(parents=True)
    (tmp_path / "scripts" / "helpers.py").write_text(
        "def only_tested():\n    return 1\n", encoding="utf-8"
    )
    (tmp_path / "tests").mkdir(parents=True)
    (tmp_path / "tests" / "test_helpers.py").write_text(
        "from scripts.helpers import only_tested\n\ndef test_it():\n    assert only_tested() == 1\n",
        encoding="utf-8",
    )
    check = CapabilityCheck(
        name="only_tested",
        description="test-only capability",
        declared_in="scripts/helpers.py",
        production_globs=("scripts/**/*.py", "tests/**/*.py"),
    )
    result = check_capability(tmp_path, check)
    assert result.status == "FAIL"


def test_check_capability_reports_stale_when_the_declaration_is_gone(tmp_path: Path):
    (tmp_path / "scripts").mkdir(parents=True)
    (tmp_path / "scripts" / "helpers.py").write_text("# nothing here\n", encoding="utf-8")
    check = CapabilityCheck(
        name="vanished",
        description="no longer exists",
        declared_in="scripts/helpers.py",
    )
    result = check_capability(tmp_path, check)
    assert result.status == "STALE"


def test_real_registry_has_no_unaccepted_failures():
    """The load-bearing regression test: today's registry (Tasks 1/3/4/5/7/8's
    fixes) must all show as actually wired, and every currently-open gap must
    be explicitly marked accepted=True with a note explaining why -- not
    silently passing and not silently failing CI."""
    results = audit()
    unaccepted_fails = [r for r in results if r.status in ("FAIL", "STALE") and not r.check.accepted]
    assert unaccepted_fails == [], (
        "unexpected unaccepted failures: "
        + ", ".join(f"{r.check.name}({r.status})" for r in unaccepted_fails)
    )


def test_every_accepted_entry_has_an_explanatory_note():
    for check in REGISTRY:
        if check.accepted:
            assert check.notes.strip(), f"{check.name} is accepted but has no notes explaining why"


def test_main_exits_zero_without_strict_even_with_accepted_failures(capsys):
    assert main([]) == 0


def test_main_exits_zero_with_strict_when_only_accepted_failures_exist(capsys):
    # The real registry's only failures are all accepted -- --strict must still pass.
    assert main(["--strict"]) == 0


def test_main_strict_mode_fails_on_an_unaccepted_gap(tmp_path: Path, monkeypatch):
    (tmp_path / "scripts").mkdir(parents=True)
    (tmp_path / "scripts" / "helpers.py").write_text(
        "def orphan():\n    return 1\n", encoding="utf-8"
    )
    import audit_declared_vs_wired as module

    fake_registry = (
        CapabilityCheck(name="orphan", description="unaccepted gap", declared_in="scripts/helpers.py"),
    )
    monkeypatch.setattr(module, "REGISTRY", fake_registry)
    assert main(["--root", str(tmp_path), "--strict"]) == 1
    monkeypatch.setattr(module, "REGISTRY", fake_registry)
    assert main(["--root", str(tmp_path)]) == 0
