# -*- coding: utf-8 -*-
"""Static "declared vs wired" gate (2026-09-15 overhaul plan, Task 0).

The pattern repeated across nearly every area this repo's 2026-09-15 diagnosis
touched: a capability gets a name, a config entry, a docstring, sometimes a
whole module -- and nothing in the production call graph ever invokes it. The
capability becomes decoration. Four confirmed instances anchor this gate's
initial registry (file:line references from the diagnosis and this session's
own Task 3-8 fixes):

  - nollam_decay_20m's 7-zone pacing curve (config/visual_pacing_profiles.yaml)
    was only ever read by tests until Task 7 wired NollamDecayTimingProfile
    into plan_narration_shots.py.
  - check_decoded_stream_motion_mae() (postflight_release.py) was defined,
    never called from verify_postflight() -- fixed in Task 5 by adding a
    streaming sibling, measure_decoded_video_motion_diversity(), that IS
    actually called.
  - compile_nollam_prompt() (lib/aligned_prompt_compiler.py) had its own test
    file but generate_visual_briefs.py always called compile_aligned_prompt()
    instead (whose STYLE constant is the seonbi ink-doodle house style) --
    fixed in Task 1.
  - generate_release_manifest_v4/v5 (postflight_release.py) are still, as of
    this gate's introduction, defined with zero production callers -- no
    script in this repo currently assembles a v4/v5 release manifest for a
    real build. This is registered here as an ACCEPTED known gap (see
    ACCEPTED_KNOWN_GAPS below), not silently fixed by inventing a caller just
    to make this gate green.

This is deliberately a CURATED registry, not a generic "every unreferenced
YAML key" scanner: most config values are read generically via `cfg[key]`,
which no static grep can distinguish from "declared but dead" without knowing
intent. Add an entry here whenever a "named but not wired" capability is
diagnosed -- mirroring this plan document's own diagnosis method (file:line
evidence, not guesswork) -- or whenever a fix wires one in for real.

Exit code: 0 unless --strict is passed and at least one non-accepted entry
FAILs. Per the plan's own §10 risk mitigation ("초기에는 warning만 내고 CI
hard-fail은 2주 유예 후 전환"), CI should run this without --strict at first
and switch to --strict once the initial registry is stable.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HUMAN_ARCHIVE_ROOT = Path(__file__).resolve().parents[1]

_DEFAULT_EXCLUDE_GLOBS = (
    "tests/**",
    "scratch/**",
    "runs/**",
    "audit/**",
    "audits/**",
    "research/**",
    "**/__pycache__/**",
)


@dataclass(frozen=True)
class CapabilityCheck:
    name: str
    description: str
    declared_in: str
    """File where the capability (function/class) is defined, relative to human_archive/."""
    production_globs: tuple[str, ...] = ("scripts/**/*.py",)
    """Where to look for a real call site, relative to human_archive/."""
    exclude_globs: tuple[str, ...] = _DEFAULT_EXCLUDE_GLOBS
    accepted: bool = False
    """True if this is a known, tracked, currently-unwired gap -- a FAIL here
    is reported but never contributes to --strict's exit code, so accepting a
    documented gap doesn't require lying about it or silently dropping the
    check."""
    notes: str = ""


@dataclass
class CapabilityResult:
    check: CapabilityCheck
    declared: bool
    call_sites: list[tuple[str, int]] = field(default_factory=list)

    @property
    def wired(self) -> bool:
        return self.declared and bool(self.call_sites)

    @property
    def status(self) -> str:
        if not self.declared:
            return "STALE"  # the check itself needs updating -- declaration is gone
        return "PASS" if self.wired else "FAIL"


_DEF_PREFIXES = ("def {name}(", "async def {name}(")
_CLASS_PREFIXES = ("class {name}(", "class {name}:")


def _is_declaration_line(stripped_line: str, name: str) -> bool:
    return any(stripped_line.startswith(p.format(name=name)) for p in (*_DEF_PREFIXES, *_CLASS_PREFIXES))


def find_call_sites(text: str, name: str) -> list[int]:
    """1-indexed line numbers where `name(` appears as a real call/instantiation,
    not the `def name(` / `class name(...)` declaration line itself."""
    call_re = re.compile(rf"\b{re.escape(name)}\(")
    hits: list[int] = []
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if _is_declaration_line(stripped, name):
            continue
        if call_re.search(line):
            hits.append(i)
    return hits


_FILE_LIST_CACHE: dict[tuple, list[Path]] = {}


def _excluded_component_names(exclude_globs: Iterable[str]) -> set[str]:
    """Turn simple "<dir>/**" exclude patterns into a set of directory-name
    components to reject by. This avoids ever walking the excluded trees
    (runs/, research/, etc. can hold thousands of generated-output files) --
    production_globs is scoped to scripts/**/*.py, which never overlaps those
    top-level trees in the first place, so there is nothing to gain from
    globbing them just to build an exclusion set."""
    names = set()
    for pattern in exclude_globs:
        head = pattern.split("/", 1)[0].replace("**", "").strip()
        if head:
            names.add(head)
    return names


def _iter_files(root: Path, globs: Iterable[str], exclude_globs: Iterable[str]) -> list[Path]:
    cache_key = (root, tuple(globs), tuple(exclude_globs))
    cached = _FILE_LIST_CACHE.get(cache_key)
    if cached is not None:
        return cached

    excluded_names = _excluded_component_names(exclude_globs)
    matched: list[Path] = []
    seen: set[Path] = set()
    for pattern in globs:
        for path in root.glob(pattern):
            if path in seen or not path.is_file():
                continue
            if path.resolve() == Path(__file__).resolve():
                # This script's own registry/docstrings name every capability
                # it checks, often immediately followed by "(" as example
                # text -- that would otherwise self-report as a "call site".
                continue
            rel_parts = path.relative_to(root).parts
            if any(part in excluded_names or part == "__pycache__" for part in rel_parts[:-1]):
                continue
            seen.add(path)
            matched.append(path)
    result = sorted(matched)
    _FILE_LIST_CACHE[cache_key] = result
    return result


def check_capability(root: Path, check: CapabilityCheck) -> CapabilityResult:
    declared_path = root / check.declared_in
    if not declared_path.exists():
        return CapabilityResult(check=check, declared=False)
    declared_text = declared_path.read_text(encoding="utf-8", errors="replace")
    declared = bool(re.search(
        rf"^\s*(def|async def|class)\s+{re.escape(check.name)}\b",
        declared_text,
        re.MULTILINE,
    ))
    if not declared:
        return CapabilityResult(check=check, declared=False)

    call_sites: list[tuple[str, int]] = []
    for path in _iter_files(root, check.production_globs, check.exclude_globs):
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no in find_call_sites(text, check.name):
            call_sites.append((str(path.relative_to(root)), line_no))
    return CapabilityResult(check=check, declared=True, call_sites=call_sites)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

REGISTRY: tuple[CapabilityCheck, ...] = (
    CapabilityCheck(
        name="NollamDecayTimingProfile",
        description="nollam_decay_20m's 7-zone pacing curve applied to real shot timing",
        declared_in="scripts/lib/shot_timing.py",
        notes="Task 7 (commit fb2a22d): plan_narration_shots.py now instantiates this.",
    ),
    CapabilityCheck(
        name="measure_decoded_video_motion_diversity",
        description="Decoded-frame motion-diversity gate actually run at release time",
        declared_in="scripts/postflight_release.py",
        notes="Task 5 (commit 7587ed3): verify_postflight() and "
        "generate_release_manifest_v4/v5 call this.",
    ),
    CapabilityCheck(
        name="compile_nollam_prompt",
        description="nollam_file_v1's photorealistic image-prompt compiler reachable from production",
        declared_in="scripts/lib/aligned_prompt_compiler.py",
        notes="Task 1 (commit 412152f): generate_visual_briefs.py routes to this "
        "for nollam_file_v1 instead of always using the seonbi ink-doodle compiler.",
    ),
    CapabilityCheck(
        name="resolve_script_paths",
        description="Per-channel-profile script template/schema/policy selection",
        declared_in="scripts/lib/script_generation.py",
        notes="Task 1 (commit 412152f): generate_verified_script.py uses this "
        "instead of a single hardcoded seonbi template+schema for every profile.",
    ),
    CapabilityCheck(
        name="escalate_claim",
        description="Codex+grok cross-validation escalation actually invoked from production paths",
        declared_in="scripts/run_consensus_round.py",
        notes="Task 3 (commit 276ab76) wired this into fact-checking; "
        "Task 8 (commit 9c84c99) wired it into visual-brief critique too.",
    ),
    CapabilityCheck(
        name="critique_visual_briefs",
        description="Scene visual-brief cross-validation reachable from generate_visual_briefs.py",
        declared_in="scripts/lib/visual_brief_cross_validation.py",
        notes="Task 8 (commit 9c84c99).",
    ),
    CapabilityCheck(
        name="render_motion_clip_v3",
        description="motion_engine_v3's real trajectory renderer used by the production motion builder",
        declared_in="scripts/lib/motion_engine_v3.py",
        notes="Task 4 (commit 4c138fc): build_motion_clips_v3.py calls this.",
    ),
    CapabilityCheck(
        name="generate_release_manifest_v4",
        description="Official v4 release manifest generator has a real production caller",
        declared_in="scripts/postflight_release.py",
        accepted=True,
        notes="Still zero production callers as of Task 5 -- no script in this "
        "repo currently assembles a v4/v5 release manifest for a real build "
        "(CLAUDE.md's Step 7 flow never writes release_manifest_v4.json). "
        "Task 5 made the function itself honest (measures motion for real "
        "instead of defaulting motion_diversity_passed=True) but did not "
        "invent a caller for it. Tracked as an open gap, not silently closed.",
    ),
    CapabilityCheck(
        name="generate_release_manifest_v5",
        description="Official v5 release manifest generator has a real production caller",
        declared_in="scripts/postflight_release.py",
        accepted=True,
        notes="Same as generate_release_manifest_v4.",
    ),
    CapabilityCheck(
        name="resolve_pipeline_context",
        description="profile_resolver.py's single immutable per-profile policy context, actually used",
        declared_in="scripts/lib/profile_resolver.py",
        accepted=True,
        notes="Fully built and tested (tests/test_profile_resolver.py) but still "
        "has zero production callers. Task 1 solved the same template/schema/"
        "policy-routing problem directly in lib/script_generation.py's "
        "resolve_script_paths() instead of wiring this module in -- the two "
        "now overlap in purpose. Left as an open gap rather than force a "
        "caller in just to close it.",
    ),
    CapabilityCheck(
        name="claude_chain",
        description="Sep2 master plan's 4-step Claude orchestration chain (outline->enrichment->script->rhythm QA)",
        declared_in="config/script_policy_v3.yaml",
        production_globs=("scripts/**/*.py",),
        accepted=True,
        notes="Declared in config only (claude_chain.step_1_outline..step_4_rhythm_qa); "
        "no orchestration code calls each step in sequence. Task 1 fixed the "
        "template/schema ROUTING (a single prompt now actually renders the "
        "right template), but the 4-step chain itself remains unbuilt -- this "
        "was diagnosed in §1.1 but is explicitly out of Task 1's scope "
        "(the plan's own 'Modify' list for Task 1 is template/schema routing "
        "only). A capability check for a config-only value can't use the same "
        "def/class regex as the others; this entry exists to keep the gap "
        "visible, not to be mechanically checkable the same way.",
    ),
    CapabilityCheck(
        name="validate_script_contract",
        description="script_contract.py's fail-closed nollam script validator has a real production caller",
        declared_in="scripts/lib/script_contract.py",
        accepted=True,
        notes="Found while resolving the nollam phase-naming mismatch: a THIRD, "
        "independent phase vocabulary for the same 5-stage nollam structure "
        "(phase_1_hook/phase_2_mechanism/phase_3_crisis/phase_4_discovery/"
        "phase_5_reflection), plus REQUIRED_FIELDS (spoken_text, fact_grade, "
        "visual_intent) that don't match what generate_script_candidate() "
        "actually produces (validated against trend_verified_script_v1.schema.json "
        "instead). Only ever called from its own test "
        "(tests/test_script_contract_nollam.py). Left unwired rather than "
        "cosmetically patched -- see the module's own docstring for why.",
    ),
)


def audit(
    root: Path | None = None,
    registry: tuple[CapabilityCheck, ...] | None = None,
) -> list[CapabilityResult]:
    root = root or _HUMAN_ARCHIVE_ROOT
    # Read module-level REGISTRY at call time, not as a bound default, so tests
    # can monkeypatch it (module.REGISTRY = ...) and have audit() see the change.
    registry = REGISTRY if registry is None else registry
    results = []
    for check in registry:
        # claude_chain is a config-declared value, not a def/class -- skip the
        # generic checker for it and just carry it through as a fixed, known,
        # accepted FAIL so it still shows up in the report.
        if check.name == "claude_chain":
            results.append(CapabilityResult(check=check, declared=True, call_sites=[]))
            continue
        results.append(check_capability(root, check))
    return results


def format_report(results: list[CapabilityResult]) -> str:
    lines = []
    for r in results:
        marker = {"PASS": "PASS", "FAIL": "FAIL", "STALE": "STALE"}[r.status]
        accepted_tag = " (accepted, tracked)" if (r.check.accepted and r.status == "FAIL") else ""
        lines.append(f"[{marker}]{accepted_tag} {r.check.name} -- {r.check.description}")
        if r.status == "FAIL":
            lines.append(f"         declared_in: {r.check.declared_in}")
            if r.check.notes:
                lines.append(f"         notes: {r.check.notes}")
        elif r.status == "PASS":
            first = r.call_sites[0]
            more = f" (+{len(r.call_sites) - 1} more)" if len(r.call_sites) > 1 else ""
            lines.append(f"         wired at: {first[0]}:{first[1]}{more}")
        elif r.status == "STALE":
            lines.append(f"         declared_in no longer defines {r.check.name!r} -- update or remove this entry")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=_HUMAN_ARCHIVE_ROOT)
    parser.add_argument("--strict", action="store_true",
                         help="Exit 1 if any non-accepted entry FAILs. Without this, "
                         "the audit always exits 0 (warning-only mode).")
    parser.add_argument("--json", type=Path, help="Also write the report as JSON to this path.")
    args = parser.parse_args(argv)

    results = audit(args.root)
    print(format_report(results))

    blocking = [r for r in results if r.status in ("FAIL", "STALE") and not r.check.accepted]
    accepted = [r for r in results if r.status == "FAIL" and r.check.accepted]
    passing = [r for r in results if r.status == "PASS"]
    print(
        f"\n{len(passing)} wired, {len(blocking)} FAIL(unaccepted), "
        f"{len(accepted)} FAIL(accepted/tracked)"
    )

    if args.json:
        payload = [
            {
                "name": r.check.name,
                "status": r.status,
                "accepted": r.check.accepted,
                "declared_in": r.check.declared_in,
                "call_sites": [f"{f}:{n}" for f, n in r.call_sites],
                "notes": r.check.notes,
            }
            for r in results
        ]
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.strict and blocking:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
