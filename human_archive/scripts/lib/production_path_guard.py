# -*- coding: utf-8 -*-
"""Refuse to release/publish anything that lives under an isolated, non-production
research path.

Added 2026-09-15 per docs/superpowers/plans/2026-09-15-human-archive-nollam-script-visual-motion-multi-llm-overhaul-plan.md
§6: `research/human_library_benchmark_internal_only/` holds a pipeline that reproduces
another channel's specific video (verbatim narration, matched cut timing, replicated
branding). It must never reach a release or publish path, by accident or otherwise.
"""
from __future__ import annotations

from pathlib import Path

ISOLATED_PATH_MARKERS = (
    "human_library_benchmark_internal_only",
    "human_library_replica",  # legacy name, kept in case old paths are passed in
)


class IsolatedResearchPathError(RuntimeError):
    """Raised when a release/publish entrypoint is given a path under an isolated,
    non-production research directory."""


def assert_not_isolated_research_path(*paths: Path | str | None) -> None:
    """Raise IsolatedResearchPathError if any given path resolves under an isolated
    research directory. None entries are ignored."""
    for raw in paths:
        if raw is None:
            continue
        resolved = str(Path(raw).resolve()).replace("\\", "/").lower()
        for marker in ISOLATED_PATH_MARKERS:
            if marker.lower() in resolved:
                raise IsolatedResearchPathError(
                    f"Refusing to release/publish: path contains '{marker}', which marks "
                    f"internal-benchmark-only, do-not-publish content: {raw}"
                )
